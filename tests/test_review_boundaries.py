"""Development regressions, not an independent power-knowledge acceptance set."""
from dataclasses import replace
from pathlib import Path
import unittest

from agents.evidence_verification import parse_verification
from core.models import VerificationStatus
from core.validation import ContractError, validate_review
from services.evidence_scope import make_snapshot, citation_coverage, validate_snapshot
from tests.test_evidence_verification import input_for, verification_json


def basis(value, category, name):
    finding = value["findings"][0]
    finding.update(claim_category=category, assessment_basis=name, excerpts=[], metadata_refs=[], scope_id=None)
    return finding


class BasisTests(unittest.TestCase):
    def test_metadata_requires_exact_fields_not_body_quote(self):
        inputs = input_for()
        value = verification_json(inputs)
        f = basis(value, "source_quality_metadata", "metadata")
        f["metadata_refs"] = [{"evidence_id": "independent", "field_path": "source_type", "value": "synthetic_fixture"}]
        out = parse_verification(value, inputs)
        self.assertFalse(out.findings[0].excerpts)
        self.assertEqual(out.findings[0].metadata_refs[0].field_path, "source_type")
        f["metadata_refs"][0]["value"] = "official"
        with self.assertRaises(ContractError): parse_verification(value, inputs)

    def test_unknown_metadata_and_technical_class_cannot_evade_quote_check(self):
        inputs = input_for()
        value = verification_json(inputs)
        f = basis(value, "source_quality_metadata", "metadata")
        f["metadata_refs"] = [{"evidence_id": "independent", "field_path": "provenance.publisher", "value": "Unknown"}]
        with self.assertRaises(ContractError): parse_verification(value, inputs)
        f.update(claim_category="technical_fact", assessment_basis="metadata")
        with self.assertRaises(ContractError): parse_verification(value, inputs)

    def test_metadata_unrelated_body_excerpts_are_rejected(self):
        inputs = input_for()
        value = verification_json(inputs)
        f = basis(value, "source_quality_metadata", "metadata")
        f["excerpts"] = [{"evidence_id": "independent", "quote": inputs.seed_evidence[0].text}]
        with self.assertRaises(ContractError): parse_verification(value, inputs)

    def test_absence_of_full_input_requires_not_assessable(self):
        inputs = input_for()
        value = verification_json(inputs)
        f = basis(value, "input_evidence_coverage", "generation_input_evidence")
        with self.assertRaises(ContractError): parse_verification(value, inputs)
        f["status"] = "not_assessable"
        out = parse_verification(value, inputs)
        self.assertEqual(out.findings[0].status, VerificationStatus.NOT_ASSESSABLE)
        self.assertIsNone(out.findings[0].scope_id)

    def test_complete_input_not_cited_subset_or_later_retrieval(self):
        inputs = input_for()
        snapshot = make_snapshot(inputs.answer, inputs.original_evidence, "synthetic-fixed")
        inputs = replace(inputs, generation_snapshot=snapshot)
        value = verification_json(inputs)
        f = basis(value, "input_evidence_coverage", "generation_input_evidence")
        f.update(scope_id=snapshot.snapshot_id, excerpts=[{"evidence_id": "original", "quote": inputs.original_evidence[0].text}])
        out = parse_verification(value, inputs)
        self.assertEqual(out.findings[0].scope_id, snapshot.snapshot_id)
        f["excerpts"][0]["evidence_id"] = "independent"
        with self.assertRaises(ContractError): parse_verification(value, inputs)
        f["excerpts"] = []
        f["scope_id"] = "wrong-scope"
        with self.assertRaises(ContractError): parse_verification(value, inputs)

    def test_snapshot_binding_and_hash_are_verified(self):
        inputs = input_for()
        snapshot = make_snapshot(inputs.answer, inputs.seed_evidence, "synthetic-fixed")
        for invalid in (replace(snapshot, answer_version=99), replace(snapshot, evidence=())):
            with self.assertRaises(ContractError): validate_snapshot(invalid, inputs.answer)
        with self.assertRaises(ContractError):
            validate_snapshot(snapshot, replace(inputs.answer, text="Different same-version answer."))

    def test_partial_binding_cannot_be_reported_as_complete(self):
        inputs = input_for(answer_text="Synthetic first proposition. Synthetic second proposition.")
        binding = inputs.answer.citations[0]
        answer = replace(inputs.answer, citations=(replace(binding, start_offset=2, end_offset=len(inputs.answer.text)-5),))
        inputs = replace(inputs, answer=answer)
        out = parse_verification(verification_json(inputs), inputs)
        review = out.citation_reviews[0]
        self.assertTrue(review.binding_warnings)
        self.assertTrue(review.partial_claim_ids)
        self.assertIn("partial_claim_anchor_coverage_requires_review", review.coverage_issues)
        bad = replace(out, citation_reviews=(replace(review, partial_claim_ids=(), coverage_issues=()),))
        with self.assertRaises(ContractError): validate_review(bad, answer, inputs.claims, out.evidence, True)

    def test_answer_scope_and_advice_do_not_claim_technical_truth(self):
        inputs = input_for()
        value = verification_json(inputs)
        f = basis(value, "answer_scope", "answer_text")
        self.assertEqual(parse_verification(value, inputs).findings[0].assessment_basis, "answer_text")
        f.update(claim_category="review_recommendation", assessment_basis="review_advice")
        with self.assertRaises(ContractError): parse_verification(value, inputs)
        f["status"] = "not_assessable"
        self.assertEqual(parse_verification(value, inputs).findings[0].status, VerificationStatus.NOT_ASSESSABLE)

    def test_independent_support_does_not_clear_original_citation(self):
        inputs = input_for(original_text="Unrelated original source.")
        value = verification_json(inputs, "supported", "insufficient_evidence")
        out = parse_verification(value, inputs)
        self.assertEqual(out.findings[0].status, VerificationStatus.SUPPORTED)
        self.assertEqual(out.citation_reviews[0].status, VerificationStatus.INSUFFICIENT_EVIDENCE)
        self.assertIn("independent_support_uses_unbound_evidence_not_original_citation_support", out.citation_reviews[0].coverage_issues)
        value["citation_reviews"][0].update(status="supported", excerpts=value["findings"][0]["excerpts"])
        with self.assertRaises(ContractError): parse_verification(value, inputs)

    def test_tampered_metadata_cannot_bypass_core(self):
        inputs = input_for()
        value = verification_json(inputs)
        f = basis(value, "source_quality_metadata", "metadata")
        f["metadata_refs"] = [{"evidence_id": "independent", "field_path": "source_type", "value": "synthetic_fixture"}]
        out = parse_verification(value, inputs)
        finding = out.findings[0]
        bad = replace(out, findings=(replace(finding, metadata_refs=(replace(finding.metadata_refs[0], value_json='"official"'),)),))
        with self.assertRaises(ContractError): validate_review(bad, inputs.answer, inputs.claims, out.evidence, True)


class ArchivedDevelopmentTests(unittest.TestCase):
    def test_actual_q1_archive_replay_and_citation3_boundary(self):
        path = Path(__file__).resolve().parents[1] / "data/retrieval_local/deepseek/evidence-review-q1-fixed-v2.json"
        if not path.exists():
            self.skipTest("Optional private development archive absent; synthetic boundary tests still run")
        from evaluation.evidence_review_replay import replay
        _, inputs, out, _ = replay(path)
        self.assertEqual(len(out.findings), 17)
        citation = out.citation_reviews[3]
        self.assertEqual(citation.status, VerificationStatus.SUPPORTED)  # historical judgment preserved
        partial, issues = citation_coverage(inputs.answer, inputs.claims, 3, out.findings)
        self.assertTrue(partial)
        self.assertIn("independent_support_uses_unbound_evidence_not_original_citation_support", issues)
        binding = inputs.answer.citations[3]
        pv = next(c for c in inputs.claims if "margin on a PV curve" in c.proposition)
        self.assertLess(binding.end_offset, pv.end_offset)
        finding = next(f for f in out.findings if f.claim_id == pv.claim_id)
        self.assertFalse(set(finding.evidence_ids) <= set(binding.evidence_ids))
        self.assertIsNone(inputs.generation_snapshot)
