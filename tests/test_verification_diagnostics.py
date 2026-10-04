"""synthetic_fixture regression; not a replay of unsaved historical responses."""
from dataclasses import replace
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agents.evidence_verification import ModelEvidenceVerificationAgent, parse_verification, PROMPT_VERSION, SYSTEM
from core.validation import ContractError, InputError, validate_review
from model_adapter.contracts import ModelOutputError, ModelResponse
from model_adapter.runtime import ModelBudget, model_scope
from services.response_diagnostics import LOCAL_ROOT, ResponseDiagnostics, DiagnosticStorageError
from services.structured_model import strict_json
from tests.test_evidence_verification import input_for, verification_json, SETTINGS, v4_response
from tests.test_generation import ScriptAdapter


class VerificationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.inputs = input_for()
        self.value = verification_json(self.inputs)

    def error(self, path):
        with self.assertRaises(ContractError) as caught:
            parse_verification(self.value, self.inputs)
        self.assertEqual(caught.exception.diagnostic["field_path"], path)
        self.assertEqual(caught.exception.diagnostic["stage"], "evidence_verification")
        return caught.exception.diagnostic

    def test_dimensions_object_not_array(self):
        self.value["findings"][0]["checked_dimensions"] = {"quantity": "ok"}
        self.assertEqual(self.error("$.findings[0].checked_dimensions")["constraint"], "expected_array")

    def test_missing_and_extra_fields(self):
        del self.value["citation_reviews"][0]["excerpts"]
        self.error("$.citation_reviews[0].excerpts")
        self.value = verification_json(self.inputs)
        self.value["findings"][0]["secret-synthetic-field"] = "synthetic-private-value"
        diagnostic = self.error("$.findings[0]")
        self.assertNotIn("secret-synthetic", str(diagnostic))

    def test_unknown_status_and_wrong_version(self):
        self.value["findings"][0]["status"] = "pass"
        self.error("$.findings[0].status")
        self.value = verification_json(self.inputs)
        self.value["answer_version"] = True
        self.error("$.answer_version")

    def test_independent_and_original_roles_not_interchangeable(self):
        self.value["findings"][0]["excerpts"][0]["evidence_id"] = "original"
        self.error("$.findings[0].excerpts[0].evidence_id")
        self.value = verification_json(self.inputs)
        self.value["citation_reviews"][0]["excerpts"][0]["evidence_id"] = "independent"
        self.error("$.citation_reviews[0].excerpts[0].evidence_id")

    def test_quote_and_definitive_status_constraints(self):
        self.value["findings"][0]["excerpts"][0]["quote"] = "Rewritten fictional quote."
        self.error("$.findings[0].excerpts[0].quote")
        self.value = verification_json(self.inputs)
        self.value["findings"][0]["excerpts"] = []
        self.error("$.findings[0].excerpts")

    def test_coverage_and_index(self):
        self.value["citation_reviews"] = []
        self.error("$.citation_reviews")
        self.value = verification_json(self.inputs)
        self.value["citation_reviews"][0]["citation_index"] = "0"
        self.error("$.citation_reviews[0].citation_index")

    def test_core_bottom_error_has_exact_path(self):
        output = parse_verification(self.value, self.inputs)
        finding = output.findings[0]
        forged = replace(output, findings=(replace(finding, excerpts=(replace(finding.excerpts[0], text="forged"),)),))
        with self.assertRaises(ContractError) as caught:
            validate_review(forged, self.inputs.answer, self.inputs.claims, output.evidence, True)
        self.assertEqual(caught.exception.diagnostic["field_path"], "$.findings[0].excerpts[0].text")
        self.assertEqual(caught.exception.diagnostic["constraint"], "evidence excerpt text mismatch")

    def test_prompt_states_bounded_types(self):
        self.assertIn("0..16", SYSTEM)
        self.assertIn("not checklist completion", SYSTEM)
        self.assertIn("zero-based integer", SYSTEM)


class ArchiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_archive_two_failures_exact_replay_and_no_body_in_logs(self):
        LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic_fixture-", dir=LOCAL_ROOT) as tmp:
            inputs = input_for()
            first, second = verification_json(inputs), verification_json(inputs)
            first["findings"][0]["checked_dimensions"] = {"quantity": "synthetic_fixture"}
            second["citation_reviews"][0]["excerpts"][0]["quote"] = "Synthetic missing quote."
            first, second = v4_response(first), v4_response(second)
            first["findings"][0]["dimension_findings"] = {"quantity": "synthetic_fixture"}
            raw = [json.dumps(v) for v in (first, second)]
            adapter = ScriptAdapter(*(ModelResponse(t, "synthetic_fixture", finish_reason="stop") for t in raw))
            budget, logs = ModelBudget(2), io.StringIO()
            with model_scope(budget), contextlib.redirect_stdout(logs), self.assertRaises(ModelOutputError) as caught:
                await ModelEvidenceVerificationAgent(adapter, SETTINGS, diagnostic_dir=tmp).run(inputs)
            self.assertEqual(len(adapter.requests), 2)
            for record, text in zip(budget.records, raw):
                artifact = json.loads(Path(record.diagnostic_path).read_text(encoding="utf-8"))
                self.assertEqual(artifact["response_text"], text)
                self.assertEqual(artifact["prompt_version"], PROMPT_VERSION)
                self.assertEqual(artifact["validation_error"], record.validation_error)
                self.assertNotIn("messages", artifact)
                self.assertNotIn("Authorization", artifact)
                with self.assertRaises(ContractError) as replay:
                    parse_verification(strict_json(artifact["response_text"]), inputs)
                self.assertEqual(replay.exception.diagnostic, artifact["validation_error"])
                self.assertNotIn(text, logs.getvalue())
            correction = json.loads(adapter.requests[1].messages[-1].content)
            self.assertEqual(correction["validation_error"], budget.records[0].validation_error)
            self.assertEqual(caught.exception.diagnostic, budget.records[1].validation_error)

    async def test_success_saved_and_overwrite_not_used(self):
        LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic_fixture-", dir=LOCAL_ROOT) as tmp:
            inputs = input_for()
            text = json.dumps(v4_response(verification_json(inputs)))
            adapter = ScriptAdapter(ModelResponse(text), ModelResponse(text))
            agent = ModelEvidenceVerificationAgent(adapter, SETTINGS, diagnostic_dir=tmp)
            paths = []
            for _ in range(2):
                output = await agent.run(inputs)
                paths.append(output.model_records[0].diagnostic_path)
            self.assertNotEqual(*paths)
            self.assertIsNone(json.loads(Path(paths[0]).read_text())["validation_error"])

    async def test_archive_failure_preserves_error_and_no_retry(self):
        inputs = input_for()
        value = verification_json(inputs)
        value["findings"] = []
        value = v4_response(value)
        adapter = ScriptAdapter(ModelResponse(json.dumps(value)))
        budget = ModelBudget(2)
        with patch.object(ResponseDiagnostics, "save", side_effect=DiagnosticStorageError()), model_scope(budget), self.assertRaises(DiagnosticStorageError):
            await ModelEvidenceVerificationAgent(adapter, SETTINGS, diagnostic_dir=LOCAL_ROOT / "synthetic_fixture").run(inputs)
        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(budget.records[0].validation_error["field_path"], "$.findings")

    async def test_archive_path_cannot_be_outside_ignored_root(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(InputError):
            ResponseDiagnostics(tmp)
