"""synthetic_fixture responses; never credentials, env files, or network."""
from copy import deepcopy
import json
import unittest

from core.models import AnswerDraft
from model_adapter.contracts import ModelOutputError, ModelResponse
from model_adapter.runtime import ModelBudget, model_scope
from services.claim_extractor import ModelClaimExtractor, parse_extraction, SYSTEM, PROMPT_VERSION
from services.structured_model import strict_json
from services.validation_diagnostics import StructuredValidationError
from tests.test_evidence_verification import extraction_json, SETTINGS
from tests.test_generation import ScriptAdapter
from harness.evidence_review_demo import render_review


class ClaimDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.answer = AnswerDraft("synthetic_fixture", 2, "电压正常。 Voltage may need assessment.")
        self.value = extraction_json(self.answer, "Voltage may need assessment.")

    def assert_diagnostic(self, value, path, constraint):
        with self.assertRaises(StructuredValidationError) as caught:
            parse_extraction(value, self.answer)
        diagnostic = caught.exception.diagnostic
        self.assertEqual(diagnostic, {"stage": "claim_extraction", "field_path": path, "constraint": constraint})
        self.assertNotIn(self.answer.text, str(caught.exception))

    def test_missing_field_and_unknown_field_are_safe(self):
        del self.value["claims"][0]["qualifiers"]
        self.assert_diagnostic(self.value, "$.claims[0].qualifiers", "required_field_missing")
        value = extraction_json(self.answer)
        value["secret-synthetic-never-echo"] = "private-synthetic-value"
        self.assert_diagnostic(value, "$", "unexpected_fields_not_allowed")

    def test_boolean_version_and_wrong_version(self):
        self.value["answer_version"] = True
        self.assert_diagnostic(self.value, "$.answer_version", "expected_integer_not_boolean")
        self.value["answer_version"] = 3
        self.assert_diagnostic(self.value, "$.answer_version", "must_match_frozen_answer_version")

    def test_rewritten_proposition_is_not_used_for_location(self):
        self.value["claims"][0]["proposition"] = "Further assessment may be necessary for voltage."
        result = parse_extraction(self.value, self.answer)
        claim = result.claims[0]
        self.assertEqual(self.answer.text[claim.start_offset:claim.end_offset], claim.text)
        self.assertNotEqual(claim.text, claim.proposition)
        self.value["claims"][0]["quote"] = claim.proposition
        self.assert_diagnostic(self.value, "$.claims[0].quote", "exact_source_quote_with_adjacent_context_not_found")

    def test_midword_and_partial_sentence_are_distinct(self):
        self.value["claims"][0]["quote"] = "oltage may need assessment."
        self.assert_diagnostic(self.value, "$.claims[0].quote", "boundary_inside_word")
        self.value["claims"][0]["quote"] = "Voltage may need assessment"
        self.assert_diagnostic(self.value, "$.claims[0].quote", "complete_sentence_or_paragraph_boundaries_required")

    def test_ambiguity_requires_context_not_first_match(self):
        self.answer = AnswerDraft("synthetic_fixture", 2, "One. Same. Two. Same.")
        value = extraction_json(self.answer, "Same.")
        self.assert_diagnostic(value, "$.claims[0].quote", "ambiguous_quote_requires_literal_prefix_or_suffix")
        value["claims"][0]["prefix"] = "Two. "
        result = parse_extraction(value, self.answer)
        self.assertEqual(result.claims[0].start_offset, self.answer.text.rindex("Same."))

    def test_qualifier_and_duplicate_paths(self):
        self.value["claims"][0]["qualifiers"] = ["must"]
        self.assert_diagnostic(self.value, "$.claims[0].qualifiers[0]", "must_be_literal_substring_of_source_quote")
        self.value["claims"][0]["qualifiers"] = ["may"]
        self.value["claims"].append(deepcopy(self.value["claims"][0]))
        self.assert_diagnostic(self.value, "$.claims[1]", "duplicate_anchor_and_proposition_not_allowed")

    def test_arrays_and_nonclaim_overlap(self):
        self.value["claims"] = []
        self.assert_diagnostic(self.value, "$.claims", "item_count_must_be_1_to_32")
        self.value = extraction_json(self.answer)
        self.value["non_claims"] = [{"quote": self.answer.text, "reason": "synthetic_fixture"}]
        self.assert_diagnostic(self.value, "$.non_claims[0].quote", "must_not_overlap_claim_anchor")

    def test_duplicate_keys_and_nonfinite_json(self):
        for text, constraint in (( '{"secret-synthetic":1,"secret-synthetic":2}', "duplicate_object_keys_not_allowed"),
                                 ('{"value":NaN}', "nonfinite_numbers_not_allowed")):
            with self.assertRaises(StructuredValidationError) as caught:
                strict_json(text)
            self.assertEqual(caught.exception.diagnostic["stage"], "json_parse")
            self.assertEqual(caught.exception.diagnostic["constraint"], constraint)
            self.assertNotIn("secret-synthetic", str(caught.exception))

    def test_prompt_matches_strict_source_contract(self):
        self.assertIn("quote MUST", SYSTEM)
        self.assertIn("NOT the source quote", SYSTEM)
        self.assertIn("at most 64", SYSTEM)
        self.assertNotIn("prefer the whole", SYSTEM)
        self.assertNotEqual(PROMPT_VERSION, "atomic-claims-v1")

    def test_failed_markdown_retains_safe_diagnostics_before_early_exit(self):
        from dataclasses import asdict
        from model_adapter.contracts import ModelCallRecord
        from core.models import ExecutionStatus
        diagnostic = {"stage": "claim_extraction", "field_path": "$.claims[0].quote",
                      "constraint": "complete_sentence_or_paragraph_boundaries_required"}
        record = ModelCallRecord(1, "synthetic_fixture", PROMPT_VERSION, False,
                                 ExecutionStatus.SUCCEEDED, 1, validation_error=diagnostic)
        payload = {"input_sha256": "synthetic_fixture", "knowledge_version": "synthetic_fixture",
                   "runs": [{"question_number": 1, "question": "synthetic_fixture",
                             "result": {"state": "failed", "termination_reason": "synthetic_fixture",
                                        "answer": asdict(self.answer), "model_records": [asdict(record)],
                                        "extraction_output": None, "verification_output": None,
                                        "execution_issues": [{"message": "synthetic_fixture execution issue"}]}}]}
        report = render_review(payload)
        self.assertIn("$.claims[0].quote", report)
        self.assertIn("synthetic_fixture execution issue", report)
        self.assertIn("Verification not completed", report)


class CorrectionDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_specific_error_reaches_correction_and_records(self):
        answer = AnswerDraft("synthetic_fixture", 1, "A fact.")
        invalid, valid = extraction_json(answer), extraction_json(answer)
        invalid["claims"][0]["quote"] = "A rewritten fact."
        adapter = ScriptAdapter(ModelResponse(json.dumps(invalid)), ModelResponse(json.dumps(valid)))
        budget = ModelBudget(2)
        with model_scope(budget):
            await ModelClaimExtractor(adapter, SETTINGS).extract(answer)
        correction = json.loads(adapter.requests[1].messages[-1].content)
        self.assertEqual(correction["validation_error"]["field_path"], "$.claims[0].quote")
        self.assertEqual(correction["validation_error"], budget.records[0].validation_error)
        self.assertEqual(budget.used, 2)
        self.assertIsNone(budget.records[1].validation_error)

    async def test_both_failures_preserved_and_second_error_is_specific(self):
        answer = AnswerDraft("synthetic_fixture", 1, "A fact.")
        value = extraction_json(answer)
        value["answer_version"] = 9
        adapter = ScriptAdapter(ModelResponse("not json"), ModelResponse(json.dumps(value)))
        budget = ModelBudget(2)
        with model_scope(budget), self.assertRaises(ModelOutputError) as caught:
            await ModelClaimExtractor(adapter, SETTINGS).extract(answer)
        self.assertEqual(len(adapter.requests), 2)
        self.assertEqual(budget.records[0].validation_error["stage"], "json_parse")
        self.assertEqual(budget.records[0].validation_error["line"], 1)
        self.assertEqual(budget.records[1].validation_error["field_path"], "$.answer_version")
        self.assertEqual(caught.exception.diagnostic, budget.records[1].validation_error)
        self.assertIn("must_match_frozen_answer_version", str(caught.exception))
