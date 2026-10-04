"""Synthetic contract tests plus optional private Q2 development archive replay."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import asyncio
import tempfile
import unittest

from agents.contracts import EvidenceVerificationInput
from agents.evidence_verification import ModelEvidenceVerificationAgent, parse_verification, DIMENSIONS, PROMPT_VERSION, RESPONSE_CONTRACT_VERSION
from agents.verification_contract_v4 import examples
from core.models import AnswerDraft, Claim, Evidence, TaskRequest, TaskMode
from core.validation import ContractError
from model_adapter.contracts import ModelOutputError, ModelResponse
from model_adapter.runtime import ModelBudget, model_scope
from services.evidence_scope import make_snapshot
from services.validation_diagnostics import ValidationErrors
from tests.test_evidence_verification import input_for, verification_json, v4_response, SETTINGS
from tests.test_generation import ScriptAdapter


class TypedContractTests(unittest.TestCase):
    def setUp(self):
        self.inputs = input_for()
        self.value = v4_response(verification_json(self.inputs))

    def parse(self):
        return parse_verification(self.value, self.inputs, schema_version=4)

    def test_deterministic_bindings_are_not_model_fields_or_check_completion(self):
        out = self.parse()
        f = out.findings[0]
        self.assertEqual(out.answer_version, self.inputs.answer.version)
        self.assertEqual(f.required_dimensions, DIMENSIONS)
        self.assertFalse(f.checked_dimensions)
        self.assertFalse(f.dimension_findings)
        self.value["answer_version"] = 999
        with self.assertRaises(ContractError): self.parse()

    def test_dimension_observations_are_explicit_and_not_auto_filled(self):
        self.value["findings"][0]["dimension_findings"] = [{"dimension": "negation", "observation": "Synthetic negation needs review."}]
        out = self.parse()
        self.assertEqual(len(out.findings[0].dimension_findings), 1)
        self.assertFalse(out.findings[0].checked_dimensions)
        self.value["findings"][0]["dimension_findings"] *= 2
        with self.assertRaises(ValidationErrors): self.parse()

    def test_metadata_branch_reads_input_value_not_model_value(self):
        f = self.value["findings"][0]
        f.update(claim_category="source_quality_metadata", evidence={"metadata_refs": [{"evidence_id": "independent", "field_path": "source_type"}]})
        out = self.parse()
        self.assertEqual(out.findings[0].metadata_refs[0].value_json, '"synthetic_fixture"')
        self.assertFalse(out.findings[0].excerpts)
        f["evidence"]["metadata_refs"][0]["value"] = "official"
        with self.assertRaises(ValidationErrors): self.parse()

    def test_insufficient_evidence_uses_explicit_null_not_invented_quote(self):
        f = self.value["findings"][0]
        f.update(status="insufficient_evidence", evidence=None)
        self.assertFalse(self.parse().findings[0].excerpts)
        del f["evidence"]
        with self.assertRaises(ValidationErrors): self.parse()

    def test_definitive_text_judgments_still_require_exact_excerpts(self):
        f = self.value["findings"][0]
        for evidence in (None, {"excerpts": []}, {"excerpts": [{"evidence_id": "independent", "quote": "Fabricated."}]}):
            f["evidence"] = evidence
            with self.assertRaises(ValidationErrors): self.parse()

    def test_coverage_scope_comes_only_from_complete_snapshot(self):
        f = self.value["findings"][0]
        f.update(claim_category="input_evidence_coverage", status="not_assessable", evidence=None)
        self.assertIsNone(self.parse().findings[0].scope_id)
        f["status"] = "supported"
        with self.assertRaises(ValidationErrors): self.parse()
        snapshot = make_snapshot(self.inputs.answer, self.inputs.seed_evidence, None)
        self.inputs = replace(self.inputs, generation_snapshot=snapshot)
        f["evidence"] = {"excerpts": []}
        self.assertEqual(self.parse().findings[0].scope_id, snapshot.snapshot_id)
        f["scope_id"] = "spoof"
        with self.assertRaises(ValidationErrors): self.parse()

    def test_original_citation_cannot_use_independent_evidence(self):
        self.value["citation_reviews"][0]["evidence"] = self.value["findings"][0]["evidence"]
        with self.assertRaises(ValidationErrors) as caught: self.parse()
        self.assertTrue(any(e["field_path"].startswith("$.citation_reviews") for e in caught.exception.diagnostics))

    def test_all_independent_detected_errors_are_returned_together(self):
        f = self.value["findings"][0]
        del f["status"]
        del f["applicability_conditions"]
        f["rationale"] = ""
        f["evidence"]["excerpts"] = [{"evidence_id": "unknown", "quote": "A."}, {"evidence_id": "independent", "quote": "Missing."}]
        with self.assertRaises(ValidationErrors) as caught: self.parse()
        paths = {e["field_path"] for e in caught.exception.diagnostics}
        self.assertTrue({"$.findings[0].status", "$.findings[0].applicability_conditions", "$.findings[0].rationale",
                         "$.findings[0].evidence.excerpts[0].evidence_id", "$.findings[0].evidence.excerpts[1].quote"} <= paths)

    def test_all_prompt_examples_parse_with_their_hypothetical_context(self):
        for value in examples():
            answer = AnswerDraft("example-answer", 1, "Exact source text.")
            evidence = Evidence("example-evidence", "synthetic", "v1", "fixture", answer.text, "synthetic_fixture")
            claims = (Claim("example-claim", answer.answer_id, 1, answer.text, 0, len(answer.text), "technical"),) if value["findings"] else ()
            if value["citation_reviews"]:
                from core.models import CitationBinding
                answer = replace(answer, citations=(CitationBinding(0, len(answer.text), (evidence.evidence_id,)),))
            inputs = EvidenceVerificationInput(TaskRequest("synthetic", TaskMode.ASSESS_EXISTING, "fixture", "Q?", existing_answer=answer), answer, claims, (evidence,), original_evidence=(evidence,))
            if value["findings"] and value["findings"][0]["claim_category"] == "input_evidence_coverage" and value["findings"][0]["status"] == "supported":
                inputs = replace(inputs, generation_snapshot=make_snapshot(answer, (evidence,), None))
            parse_verification(value, inputs, schema_version=4)


class CorrectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_correction_receives_all_errors_and_preserves_budget(self):
        inputs = input_for()
        valid = v4_response(verification_json(inputs))
        invalid = json.loads(json.dumps(valid))
        del invalid["findings"][0]["rationale"]
        del invalid["findings"][0]["evidence"]
        adapter = ScriptAdapter(ModelResponse(json.dumps(invalid)), ModelResponse(json.dumps(valid)))
        budget = ModelBudget(2)
        local = Path(__file__).resolve().parents[1] / "data/retrieval_local"
        with tempfile.TemporaryDirectory(dir=local) as directory:
            with model_scope(budget):
                await ModelEvidenceVerificationAgent(adapter, SETTINGS, diagnostic_dir=directory).run(inputs)
            for record in budget.records:
                self.assertEqual(record.response_contract_version, RESPONSE_CONTRACT_VERSION)
                archive = json.loads(Path(record.diagnostic_path).read_text(encoding="utf-8"))
                self.assertEqual(archive["response_contract_version"], RESPONSE_CONTRACT_VERSION)
                self.assertEqual(archive["prompt_version"], PROMPT_VERSION)
            self.assertEqual(len(json.loads(Path(budget.records[0].diagnostic_path).read_text(encoding="utf-8"))["validation_error"]["errors"]), 2)
        correction = json.loads(adapter.requests[1].messages[-1].content)
        self.assertEqual(len(correction["validation_errors"]), 2)
        self.assertEqual(budget.used, 2)

    async def test_v4_contract_version_is_recorded_on_transport_failure(self):
        from model_adapter.contracts import ModelConnectionError
        adapter = ScriptAdapter(ModelConnectionError())
        budget = ModelBudget(2)
        with model_scope(budget):
            with self.assertRaises(ModelConnectionError):
                await ModelEvidenceVerificationAgent(adapter, SETTINGS).run(input_for())
        self.assertEqual(budget.used, 1)
        self.assertEqual(budget.records[0].response_contract_version, RESPONSE_CONTRACT_VERSION)


class HistoricalQ2Tests(unittest.TestCase):
    def test_real_archives_remain_failed_under_v3_with_all_omissions(self):
        path = Path(__file__).resolve().parents[1] / "data/retrieval_local/deepseek/evidence-review-q2-q5-v1.json"
        if not path.exists(): self.skipTest("Private Q2 development archive unavailable")
        from harness.evidence_review_demo import restore_answer, restore_evidence
        from services.claim_extractor import parse_extraction
        from services.structured_model import strict_json
        p = json.loads(path.read_text(encoding="utf-8")); r = p["runs"][0]["result"]
        def load(rec):
            artifact = json.loads(Path(rec["diagnostic_path"]).read_text(encoding="utf-8"))
            self.assertEqual(hashlib.sha256(artifact["response_text"].encode()).hexdigest(), artifact["response_sha256"])
            return strict_json(artifact["response_text"])
        answer = restore_answer(r["answer"])
        claims = parse_extraction(load(r["model_records"][0]), answer).claims
        evidence = tuple(restore_evidence(e) for e in r["evidence"])
        retrieved = {eid for rec in r["retrieval_records"] for eid in rec["core_evidence_ids"] + rec["context_evidence_ids"]}
        original = {eid for c in answer.citations for eid in c.evidence_ids}
        inputs = EvidenceVerificationInput(TaskRequest("offline-q2", TaskMode.ASSESS_EXISTING, "voltage", p["runs"][0]["question"], existing_answer=answer),
            answer, claims, tuple(e for e in evidence if e.evidence_id in retrieved),
            original_evidence=tuple(e for e in evidence if e.evidence_id in original))
        self.assertEqual(r["state"], "review_required")
        # Synthetic no-judgment responses exercise today's input construction with
        # the actual archived answer/claims; they do not reclassify historical review.
        fixture = {"findings": [{"claim_id": c.claim_id, "claim_category": "technical_fact",
            "status": "not_assessable", "rationale": "synthetic_fixture: input construction only",
            "applicability_conditions": [], "evidence": None} for c in claims],
            "citation_reviews": [{"citation_index": i, "status": "not_assessable",
            "rationale": "synthetic_fixture: input construction only", "applicability_conditions": [],
            "evidence": None} for i in range(len(answer.citations))]}
        adapter = ScriptAdapter(ModelResponse(json.dumps(fixture)))
        out = asyncio.run(ModelEvidenceVerificationAgent(adapter, SETTINGS).run(inputs))
        wire = json.loads(adapter.requests[0].messages[1].content)
        self.assertEqual(wire["answer"]["answer_id"], answer.answer_id)
        self.assertEqual(wire["answer"]["version"], answer.version)
        self.assertIsNone(wire["GENERATION_INPUT_SNAPSHOT"])
        self.assertEqual(len(wire["claims"]), 11)
        self.assertEqual(out.answer_id, answer.answer_id)
        self.assertEqual(out.answer_version, answer.version)
        self.assertEqual(adapter.requests[0].prompt_version, PROMPT_VERSION)
        self.assertIn("V4 ONLY", adapter.requests[0].messages[0].content)
        self.assertNotIn("Copy supplied answer_id", adapter.requests[0].messages[0].content)
        self.assertEqual(out.model_records[0].response_contract_version, RESPONSE_CONTRACT_VERSION)
        for rec, expected in zip(r["model_records"][1:], (11, 2)):
            value = load(rec)
            with self.assertRaises(ValidationErrors) as caught:
                parse_verification(value, inputs, schema_version=3)
            self.assertEqual(len(caught.exception.diagnostics), expected)
            with self.assertRaises(ValidationErrors):
                parse_verification(value, inputs, schema_version=4)  # No implicit migration of raw historical responses.
