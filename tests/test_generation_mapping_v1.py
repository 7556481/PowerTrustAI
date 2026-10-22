"""Synthetic/offline contracts and real Harness wiring, never semantic scores."""
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from agents.contracts import GenerationInput, GenerationOutput
from agents.fakes import FakeConfig, make_fake_harness
from agents.generation import EvidenceGenerationAgent, parse_units
from agents.generation_mapping_v1 import (
    CONTRACT_VERSION, VERSION, EvidenceMappingGenerationAgent, GenerationCatalog,
    candidate_messages, parse_candidate,
)
from core.models import Evidence, EvidenceBinding, TaskMode, TaskRequest, VerificationStatus
from core.validation import validate_types
from harness.contracts import RunBudget
from harness.states import RunState
from model_adapter.contracts import ModelBudgetError, ModelConnectionError, ModelOutputError, ModelResponse, ModelSettings
from model_adapter.runtime import ModelBudget, model_scope
from services.claim_extractor import ModelClaimExtractor
from services.evidence_scope import validate_snapshot
from services.response_diagnostics import DiagnosticStorageError
from services.validation_diagnostics import ValidationErrors


def inputs():
    evidence = (Evidence("synthetic-e1", "fixture", "v1", "paragraph 1",
                         "Only in mode M, P changes Q.", "synthetic_fixture"),
                Evidence("synthetic-e2", "fixture-other", "v2", "paragraph 2",
                         "Unselected context must remain in the full input snapshot.", "synthetic_fixture"))
    return GenerationInput(TaskRequest("synthetic-map", TaskMode.QUESTION_ANSWER,
                                      "synthetic", "说明P如何影响Q及必要条件。"), evidence,
                           (EvidenceBinding("synthetic-e1", "user_reference"),), "synthetic-k-v1",
                           ("保留必要条件。",))


def wire(inp=None, *, product_guidance=False):
    inp = inp or inputs()
    catalog = GenerationCatalog(inp, product_guidance)
    quote = next(iter(catalog.by_wire))
    condition = next(k for k, v in catalog.conditions.items() if v["quote_id"] == quote)
    return {"answer_units": [
        {"kind": "technical", "text": "在模式M下，P使Q变化。", "evidence_ids": ["synthetic-e1"]},
        {"kind": "technical", "text": "该装置保证运行二十年。", "evidence_ids": []}],
        "assumptions": [], "missing_information": [], "evidence_sufficient": True,
        "diagnostic_map": [{"point": "P与Q的关系及条件", "unit_indexes": [0],
                            "quote_ids": [quote], "condition_ids": [condition],
                            "note": "PRIVATE_MAP_NOTE：原文仅支持模式M下的关系。"}]}


class Adapter:
    def __init__(self, *items):
        self.items, self.requests = items, []

    async def complete(self, request):
        self.requests.append(request)
        item = self.items[min(len(self.requests) - 1, len(self.items) - 1)]
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            item = item(request)
        return item if isinstance(item, ModelResponse) else ModelResponse(json.dumps(item, ensure_ascii=False))


def agent(adapter, **kwargs):
    return EvidenceMappingGenerationAgent(adapter, ModelSettings("synthetic", timeout_seconds=1), **kwargs)


class ParseTests(unittest.TestCase):
    def test_original_answer_parser_and_program_locations_reused(self):
        inp, value = inputs(), wire()
        catalog = GenerationCatalog(inp, False)
        answer, sufficient, mapping = parse_candidate(value, inp, catalog)
        old_answer = parse_units({k: v for k, v in value.items() if k != "diagnostic_map"}, inp)[0]
        self.assertEqual(answer, old_answer)
        self.assertTrue(sufficient)
        unit = mapping[0]["units"][0]
        self.assertEqual(answer.text[unit["start_offset"]:unit["end_offset"]], value["answer_units"][0]["text"])
        basis = mapping[0]["bases"][0]
        self.assertIn(basis["quote_id"], catalog.by_wire)
        self.assertEqual(inp.evidence[0].text[basis["start_offset"]:basis["end_offset"]], basis["text"])
        self.assertEqual(len(mapping[0]["units"]), 1)
        self.assertIn("二十年", answer.text)  # An unmapped assertion is deliberately retained.

    def test_identity_changes_with_question_requirements_and_evidence(self):
        inp = inputs()
        original = GenerationCatalog(inp, False)
        changed = [replace(inp, request=replace(inp.request, question="另一个问题")),
                   replace(inp, answer_requirements=("其他要求",)),
                   replace(inp, evidence=(replace(inp.evidence[0], source_version="changed"),))]
        for other in changed:
            catalog = GenerationCatalog(other, False)
            self.assertNotEqual(original.input_sha256, catalog.input_sha256)
            with self.assertRaises(ValidationErrors):
                parse_candidate(wire(), other, catalog)
        self.assertNotEqual(original.input_sha256, GenerationCatalog(inp, True).input_sha256)

    def test_mapping_invalid_cases_do_not_mark_answer_invalid(self):
        for case in ("quote", "condition", "parent", "bool_index", "index", "duplicate",
                     "missing_note", "empty", "missing", "offset", "blank", "too_many"):
            with self.subTest(case=case):
                value, inp = wire(), inputs()
                row = value["diagnostic_map"][0]
                if case == "quote": row["quote_ids"] = ["foreign"]
                elif case == "condition": row["condition_ids"] = ["foreign"]
                elif case == "parent": row["quote_ids"] = []
                elif case == "bool_index": row["unit_indexes"] = [True]
                elif case == "index": row["unit_indexes"] = [2]
                elif case == "duplicate": row["quote_ids"] *= 2
                elif case == "missing_note": del row["note"]
                elif case == "empty": value["diagnostic_map"] = []
                elif case == "missing": del value["diagnostic_map"]
                elif case == "offset": row["start_offset"] = 0
                elif case == "blank": row["note"] = " "
                elif case == "too_many": value["diagnostic_map"] *= 7
                with self.assertRaises(ValidationErrors) as caught:
                    parse_candidate(value, inp, GenerationCatalog(inp, False))
                layers = caught.exception.diagnostic["candidate_layers"]
                self.assertEqual(layers["answer"], "valid")
                self.assertEqual(layers["mapping"], "invalid")

    def test_answer_and_mapping_failures_are_independent(self):
        for both in (False, True):
            value = wire()
            value["answer_units"][0]["evidence_ids"] = ["foreign"]
            if both: value["diagnostic_map"][0]["note"] = ""
            with self.assertRaises(ValidationErrors) as caught:
                parse_candidate(value, inputs(), GenerationCatalog(inputs(), False))
            layers = caught.exception.diagnostic["candidate_layers"]
            self.assertEqual(layers["answer"], "invalid")
            self.assertEqual(layers["mapping"], "invalid" if both else "valid")

    def test_envelope_extra_field_rejected_even_with_two_valid_layers(self):
        value = wire()
        value["all_correct"] = True
        with self.assertRaises(ValidationErrors) as caught:
            parse_candidate(value, inputs(), GenerationCatalog(inputs(), False))
        self.assertEqual(caught.exception.diagnostic["candidate_layers"],
                         {"answer": "valid", "mapping": "valid", "envelope": "invalid"})

    def test_gap_and_no_condition_do_not_require_fake_ids_or_complete_mapping(self):
        value = wire()
        value["diagnostic_map"][0].update(unit_indexes=[], quote_ids=[], condition_ids=[],
                                            note="缺少直接解释，尚不能给出该点。")
        answer, _, mapping = parse_candidate(value, inputs(), GenerationCatalog(inputs(), False))
        self.assertEqual(mapping[0]["units"], [])
        self.assertEqual(mapping[0]["bases"], [])
        self.assertIn("二十年", answer.text)


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("Offline test: no network"))
        guard.start()
        self.addCleanup(guard.stop)

    async def test_one_request_standard_output_and_complete_snapshot(self):
        adapter = Adapter(wire())
        result = await agent(adapter).run_with_diagnostics(inputs())
        self.assertIs(type(result.output), GenerationOutput)
        validate_types(result.output, GenerationOutput)
        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(result.output.evidence_snapshot.evidence, inputs().evidence)
        self.assertEqual(result.output.evidence_snapshot.evidence_bindings, inputs().evidence_bindings)
        self.assertEqual(result.output.evidence_snapshot.answer_requirements, inputs().answer_requirements)
        validate_snapshot(result.output.evidence_snapshot, result.output.answer)
        self.assertEqual(result.output.model_records[0].response_contract_version, CONTRACT_VERSION)
        self.assertEqual(result.report["failure_counts"]["mapping_only"], 0)
        self.assertTrue(result.report["candidate_valid"])
        payload = json.loads(adapter.requests[0].messages[-1].content)
        self.assertTrue(payload["SOURCE_CONDITION_CANDIDATES"])
        self.assertTrue(all("text" not in row for row in payload["QUOTE_CANDIDATES"]))
        messages_text = "\n".join(m.content for m in adapter.requests[0].messages)
        self.assertEqual(messages_text.count(inputs().evidence[0].text), 1)
        self.assertNotIn("diagnostic_map", asdict(result.output))

    async def test_product_profile_reuses_strict_answer_parser_without_default_selection(self):
        result = await agent(Adapter(wire(product_guidance=True)), product_guidance=True).run_with_diagnostics(inputs())
        expected = parse_units({k: v for k, v in wire(product_guidance=True).items()
                                if k != "diagnostic_map"}, inputs(), product_guidance=True)[0]
        self.assertEqual(result.output.answer, expected)
        self.assertEqual(result.output.prompt_version, VERSION + "-product")
        self.assertTrue(result.report["candidate_valid"])

    async def test_mapping_only_correction_retains_first_failure(self):
        bad = wire()
        bad["diagnostic_map"][0]["quote_ids"] = ["foreign"]
        adapter = Adapter(bad, wire())
        result = await agent(adapter).run_with_diagnostics(inputs())
        self.assertEqual(len(adapter.requests), 2)
        self.assertTrue(adapter.requests[1].correction)
        self.assertEqual(adapter.requests[1].messages[:4], adapter.requests[0].messages)
        self.assertEqual(result.report["failure_counts"]["mapping_only"], 1)
        self.assertEqual(result.report["failure_counts"]["answer_invalid"], 0)
        self.assertTrue(result.report["candidate_valid"])
        self.assertEqual(result.report["attempts"][0]["layers"]["answer"], "valid")
        self.assertEqual(result.output.model_records[0].validation_error["candidate_layers"]["mapping"], "invalid")

    async def test_final_mapping_failure_is_not_released_to_harness_review(self):
        task = replace(inputs().request, provided_evidence=inputs().evidence)
        generation_input = replace(inputs(), request=task, knowledge_version=None,
                                   evidence_bindings=tuple(EvidenceBinding(e.evidence_id, "user_reference")
                                                           for e in inputs().evidence))
        bad = wire(generation_input)
        bad["diagnostic_map"][0]["note"] = ""
        adapter = Adapter(bad)
        h = make_fake_harness()
        h.generation = agent(adapter)
        result = await h.run(task, RunBudget(max_revision_rounds=0), answer_requirements=inputs().answer_requirements)
        self.assertEqual(result.state, RunState.FAILED)
        self.assertIsNone(result.answer)
        self.assertFalse(h.verification.inputs)
        self.assertFalse(h.domain_review.inputs)
        self.assertEqual(len(result.model_records), 2)
        for record in result.model_records:
            self.assertEqual(record.validation_error["candidate_layers"]["answer"], "valid")
            self.assertEqual(record.validation_error["candidate_layers"]["mapping"], "invalid")

    async def test_answer_failure_and_unchecked_json_are_not_mapping_only(self):
        bad = wire()
        bad["answer_units"][0]["evidence_ids"] = ["foreign"]
        for response, expected in ((bad, "answer_invalid"), (ModelResponse("{bad"), "unchecked"),
                                   (ModelResponse('{"x":1,"x":2}'), "unchecked")):
            adapter = Adapter(response)
            with self.assertRaises(ModelOutputError) as caught:
                await agent(adapter).run_with_diagnostics(inputs())
            report = caught.exception.candidate_report
            self.assertFalse(report["candidate_valid"])
            self.assertEqual(report["failure_counts"][expected], 2)
            self.assertEqual(report["failure_counts"]["mapping_only"], 0)
        bad["diagnostic_map"][0]["note"] = ""
        with self.assertRaises(ModelOutputError) as caught:
            await agent(Adapter(bad)).run_with_diagnostics(inputs())
        self.assertEqual(caught.exception.candidate_report["failure_counts"]["both_invalid"], 2)

    async def test_shared_budget_and_transport_do_not_trigger_more_calls(self):
        bad = wire()
        bad["diagnostic_map"][0]["condition_ids"] = ["foreign"]
        adapter, budget = Adapter(bad), ModelBudget(limit=1)
        with model_scope(budget), self.assertRaises(ModelBudgetError) as caught:
            await agent(adapter).run_with_diagnostics(inputs())
        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(caught.exception.candidate_report["failure_counts"]["mapping_only"], 1)
        adapter = Adapter(ModelConnectionError())
        with self.assertRaises(ModelConnectionError) as caught:
            await agent(adapter).run_with_diagnostics(inputs())
        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(caught.exception.candidate_report["failure_counts"]["unchecked"], 1)

    async def test_empty_evidence_zero_calls_and_candidate_not_applicable(self):
        adapter = Adapter(wire())
        result = await agent(adapter).run_with_diagnostics(replace(inputs(), evidence=(), evidence_bindings=()))
        self.assertFalse(adapter.requests)
        self.assertFalse(result.output.substantive_answer)
        self.assertEqual(result.report["status"], "not_applicable_no_evidence")
        self.assertEqual(result.mapping, ())

    async def test_development_only_default_unchanged_and_existing_answer_rejected(self):
        from backend.config import ServiceConfig
        self.assertEqual(ServiceConfig().verification_schema, 13)
        self.assertEqual(make_fake_harness().execution_path, "sequential")
        adapter = Adapter(wire())
        with self.assertRaises(ValueError):
            await agent(adapter).run(replace(inputs(), request=replace(inputs().request, mode=TaskMode.ASSESS_EXISTING)))
        self.assertFalse(adapter.requests)
        original = EvidenceGenerationAgent(Adapter({k: v for k, v in wire().items() if k != "diagnostic_map"}),
                                           ModelSettings("synthetic"), schema_version=3)
        output = await original.run(inputs())
        self.assertNotIn(VERSION, output.prompt_version)

    async def test_private_report_preserves_validity_and_full_binding(self):
        root = Path(__file__).resolve().parents[1] / "data/retrieval_local"
        root.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix="generation-map-test-", dir=root)
        self.assertTrue(Path(directory.name).resolve().is_relative_to(root.resolve()))
        self.addCleanup(directory.cleanup)
        candidate = agent(Adapter(wire()), diagnostic_dir=directory.name)
        result = await candidate.run_with_diagnostics(inputs())
        saved = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
        self.assertEqual(saved["report"], result.report)
        self.assertTrue(saved["input_sha256"])
        self.assertTrue(saved["answer_sha256"])
        self.assertEqual(saved["mapping"][0]["note"], wire()["diagnostic_map"][0]["note"])

    async def test_storage_failures_do_not_release_unpersisted_candidate(self):
        candidate = agent(Adapter(wire()))
        from unittest.mock import Mock
        candidate.diagnostics = Mock()
        candidate.diagnostics.save_generation_input.side_effect = DiagnosticStorageError()
        candidate.diagnostics.save_scope.side_effect = DiagnosticStorageError()
        with self.assertRaises(DiagnosticStorageError) as caught:
            await candidate.run_with_diagnostics(inputs())
        self.assertFalse(candidate.client.adapter.requests)
        self.assertFalse(caught.exception.candidate_report["candidate_valid"])
        self.assertTrue(caught.exception.candidate_report["report_storage_failed"])
        candidate = agent(Adapter(wire()))
        with patch.object(candidate, "_save_report", side_effect=DiagnosticStorageError()):
            with self.assertRaises(DiagnosticStorageError) as caught:
                await candidate.run_with_diagnostics(inputs())
        self.assertEqual(len(candidate.client.adapter.requests), 1)
        self.assertFalse(caught.exception.candidate_report["candidate_valid"])
        self.assertEqual(caught.exception.candidate_report["attempts"][0]["layers"]["answer"], "valid")

    async def test_private_failure_report_distinguishes_mapping_only_without_partial_answer(self):
        root = Path(__file__).resolve().parents[1] / "data/retrieval_local"
        root.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix="generation-map-test-", dir=root)
        self.assertTrue(Path(directory.name).resolve().is_relative_to(root.resolve()))
        self.addCleanup(directory.cleanup)
        bad = wire()
        bad["diagnostic_map"][0]["note"] = ""
        with self.assertRaises(ModelOutputError):
            await agent(Adapter(bad), diagnostic_dir=directory.name).run_with_diagnostics(inputs())
        saved = [json.loads(p.read_text(encoding="utf-8")) for p in Path(directory.name).glob("scope-*.json")]
        report = next(p for p in saved if "report" in p)
        self.assertEqual(report["report"]["failure_counts"]["mapping_only"], 2)
        self.assertEqual(report["report"]["failure_counts"]["answer_invalid"], 0)
        self.assertIsNone(report["answer_sha256"])
        self.assertEqual(report["mapping"], [])

    async def test_cancellation_stops_without_correction_or_fallback(self):
        started = asyncio.Event()

        class WaitingAdapter:
            requests = 0

            async def complete(self, request):
                self.requests += 1
                started.set()
                await asyncio.Event().wait()

        adapter, budget = WaitingAdapter(), ModelBudget(limit=2)
        with model_scope(budget):
            task = asyncio.create_task(agent(adapter).run_with_diagnostics(inputs()))
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError) as caught:
                await task
        self.assertEqual(adapter.requests, 1)
        self.assertEqual(budget.used, 1)
        self.assertEqual(len(budget.records), 1)
        self.assertFalse(caught.exception.candidate_report["candidate_valid"])
        self.assertEqual(caught.exception.candidate_report["execution_error_code"], "CANCELLED")

    async def test_concurrent_same_agent_has_no_shared_sidecar_state(self):
        candidate = agent(Adapter(wire()))
        first, second = await asyncio.gather(candidate.run_with_diagnostics(inputs()),
                                             candidate.run_with_diagnostics(inputs()))
        self.assertIsNot(first.report, second.report)
        self.assertEqual(len(first.report["attempts"]), 1)
        self.assertEqual(len(second.report["attempts"]), 1)
        self.assertEqual(len(first.output.model_records), 1)
        self.assertEqual(len(second.output.model_records), 1)
        self.assertEqual(first.mapping, second.mapping)

    async def test_unmapped_actual_assertion_gets_real_extraction_and_both_reviews(self):
        captured = []

        def extraction_response(request):
            payload = json.loads(request.messages[1].content)
            captured.append(payload)
            return {"claims": [{"anchor_id": a["anchor_id"], "proposition": a["text"],
                    "claim_type": "technical", "components": [{"category": "technical_fact",
                    "proposition": a["text"], "basis_target": "technical_content",
                    "verification_obligation": "technical_truth"}], "assertion_role": "asserted",
                    "semantic_qualifiers": []} for a in payload["ANSWER_ANCHORS"]], "non_claims": []}

        h = make_fake_harness(FakeConfig(reference_input_evidence=True,
                              verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)))
        task = replace(inputs().request, provided_evidence=inputs().evidence)
        gen_inputs = replace(inputs(), request=task, knowledge_version=None,
                             evidence_bindings=tuple(EvidenceBinding(e.evidence_id, "user_reference")
                                                     for e in inputs().evidence))
        h.generation = agent(Adapter(wire(gen_inputs)))
        extractor_adapter = Adapter(extraction_response)
        h.extractor = ModelClaimExtractor(extractor_adapter, ModelSettings("synthetic"),
                                         typed_components=True, protocol_version=7)
        result = await h.run(task, RunBudget(max_revision_rounds=0), answer_requirements=inputs().answer_requirements)
        self.assertEqual(result.state, RunState.REVIEW_REQUIRED, result.termination_reason)
        self.assertEqual(len(result.extraction_output.claims), 2)
        self.assertIn("二十年", result.extraction_output.claims[1].text)
        self.assertEqual(h.verification.inputs[0].answer.text, result.answer.text)
        self.assertEqual(h.domain_review.inputs[0].answer.text, result.answer.text)
        self.assertEqual(len(h.verification.inputs[0].claims), 2)
        self.assertEqual(len(h.domain_review.inputs[0].claims), 2)
        for payload in (asdict(h.verification.inputs[0]), asdict(h.domain_review.inputs[0]), *captured):
            text = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("PRIVATE_MAP_NOTE", text)
            self.assertNotIn('"diagnostic_map"', text)
        self.assertEqual(result.generation_output.evidence_snapshot.evidence, inputs().evidence)


if __name__ == "__main__":
    unittest.main()
