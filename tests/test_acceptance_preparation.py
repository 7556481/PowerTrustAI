"""Offline experiment-budget and archived-trace checks; no paid calls."""
from pathlib import Path
from dataclasses import replace, asdict
import json
import unittest

from core.models import AnswerDraft, CitationBinding
from evaluation.acceptance_trial import reserve, review_worst_calls
from evaluation.acceptance_preparation import PRIVATE, baseline, archived_review
from evaluation.archive_replay import replay_failed_review, restore


class PreparationTests(unittest.TestCase):
    def test_mixed_input_component_needs_explicit_local_basis_and_reports_index_range(self):
        from tests.test_verification_v5 import inputs_for, wire
        from services.evidence_scope import make_snapshot
        from agents.verification_contract_v7 import parse_v7
        from core.validation import ContractError
        from core.models import VerificationStatus
        i = inputs_for("technical_fact", "input_evidence_coverage")
        snapshot = make_snapshot(i.answer, i.seed_evidence, i.knowledge_version,
                                 request=i.request, prompt_version="synthetic_fixture")
        i = replace(i, generation_snapshot=snapshot)
        value = wire(i, [{"type": "input_snapshot_reference"}],
                     statuses=["insufficient_evidence", "supported"], indexes=[[], [0]])
        out = parse_v7(value, i)
        self.assertEqual(out.findings[0].status, VerificationStatus.INSUFFICIENT_EVIDENCE)
        # This checks structure only, not semantic truth of the synthetic proposition.
        value["findings"][0]["bases"] = []
        with self.assertRaises(ContractError) as caught:
            parse_v7(value, i)
        error = next(e for e in caught.exception.diagnostic["errors"]
                     if e["constraint"] == "existing_integer_basis_indexes_required")
        self.assertEqual(error["bases_count"], 0)
        self.assertEqual(error["allowed_basis_indexes"], [])
        value["findings"][0]["component_reviews"][1]["basis_indexes"] = []
        with self.assertRaises(ContractError) as caught:
            parse_v7(value, i)
        error = next(e for e in caught.exception.diagnostic["errors"]
                     if e["constraint"] == "component_requires_corresponding_basis_input_snapshot_reference")
        self.assertEqual(error["legal_basis_shape"], {"type": "input_snapshot_reference"})

    def test_category_disagreement_preserves_frozen_type_and_cannot_grant_support(self):
        from tests.test_verification_v5 import inputs_for, wire
        from services.evidence_scope import make_snapshot
        from agents.verification_contract_v7 import parse_v7
        from core.validation import ContractError
        i = inputs_for("technical_fact")
        i = replace(i, generation_snapshot=make_snapshot(i.answer, i.seed_evidence, i.knowledge_version,
                    request=i.request, prompt_version="synthetic_fixture"))
        value = wire(i, [], statuses=["not_assessable"], indexes=[[]])
        part = value["findings"][0]["component_reviews"][0]
        part["classification_issue"] = {"suggested_category": "input_evidence_coverage",
                                        "rationale": "synthetic input statement was classified as technical"}
        out = parse_v7(value, i)
        self.assertEqual(out.claims[0].components[0].category, "technical_fact")
        self.assertEqual(out.findings[0].status.value, "not_assessable")
        part["status"] = "supported"
        with self.assertRaises(ContractError):
            parse_v7(value, i)
        part["status"] = "insufficient_evidence"
        part.pop("classification_issue")
        value["findings"][0]["bases"] = [{"type": "input_snapshot_reference"}]
        part["basis_indexes"] = [0]
        with self.assertRaises(ContractError) as caught:
            parse_v7(value, i)
        self.assertTrue(any(e["constraint"] == "snapshot_not_support_for_other_claim_types"
                            for e in caught.exception.diagnostic["errors"]))

    @unittest.skipUnless((PRIVATE / "acceptance-real-v2.json").exists(), "Private development archive not distributed")
    def test_quantity_history_replays_failed_and_keeps_valid_peers(self):
        rows = replay_failed_review(PRIVATE / "acceptance-real-v2.json", "quantity-unit-error")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["same_historical_paths_and_constraints"] for r in rows))
        self.assertEqual(len(rows[1]["retained_items"]), 2)

    @unittest.skipUnless((PRIVATE / "acceptance-real-v3.json").exists(), "Private development archive not distributed")
    def test_archive_extraction_reuse_requires_exact_frozen_answer_and_ancestry(self):
        import asyncio
        from evaluation.archive_replay import find_frozen_extraction, FrozenArchivedExtraction
        from evaluation.acceptance_preparation import KNOWLEDGE
        from harness.evidence_review_demo import restore_answer
        data = json.loads((PRIVATE / "acceptance-real-v3.json").read_text(encoding="utf-8"))
        answer = restore_answer(data["runs"][1]["revision"]["answer"])
        extracted, source = find_frozen_extraction(PRIVATE / "acceptance-real-v3.json", answer, KNOWLEDGE)
        self.assertEqual(Path(source["path"]).name, "acceptance-real-v2.json")
        service = FrozenArchivedExtraction(answer, extracted)
        self.assertEqual(asyncio.run(service.extract(answer)), extracted)
        with self.assertRaises(ValueError):
            asyncio.run(service.extract(replace(answer, text=answer.text + " Altered.")))
        with self.assertRaises(ValueError):
            find_frozen_extraction(PRIVATE / "acceptance-real-v3.json", answer, "changed-knowledge")

    @unittest.skipUnless((PRIVATE / "acceptance-real-v1.json").exists(), "Private development archive not distributed")
    def test_actual_failed_responses_still_fail_with_same_constraints(self):
        rows = replay_failed_review(PRIVATE / "acceptance-real-v1.json")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["replay_status"] == "failed" and r["same_historical_paths_and_constraints"] for r in rows))
        self.assertTrue(all(len(r["retained_items"]) == 4 for r in rows))
        from harness.contracts import HarnessResult
        data = json.loads((PRIVATE / "acceptance-real-v1.json").read_text(encoding="utf-8"))
        initial = data["runs"][1]["initial"]
        restored = restore(initial, HarnessResult)
        self.assertEqual(json.loads(json.dumps(asdict(restored))), initial)

    def test_worst_case_accounts_for_every_original_citation_and_correction(self):
        answer = AnswerDraft("synthetic", 2, "A. B.", citations=(
            CitationBinding(0, 2, ("e1",)), CitationBinding(3, 5, ("e2",))))
        self.assertEqual(review_worst_calls(answer), 10)
        self.assertFalse(reserve(16, 25, review_worst_calls(answer)))
        self.assertTrue(reserve(15, 25, review_worst_calls(answer)))
        with self.assertRaises(ValueError):
            reserve(-1, 25, 2)

    def test_baseline_does_not_include_credentials_or_legacy(self):
        data = baseline()
        files = data["source_files"]
        self.assertTrue(files)
        self.assertFalse(any(Path(p).name.startswith(".env") or ".venv" in p or
                             "power-system-hallucination" in p for p in files))
        self.assertTrue(all(r["demonstration_only"] for r in data["current"]["rules"]))

    @unittest.skipUnless((PRIVATE / "stability-minimal-v3-rereview.json").exists(), "Private historical archives not distributed")
    def test_archived_trace_actions_and_literal_anchors_are_checked_without_relabeling(self):
        data = archived_review()
        self.assertEqual(data["decision"]["kind"], "review_required")
        self.assertFalse(data["execution_issues"])
        self.assertEqual(len(data["finding_comparison"]), 7)
        self.assertTrue(data["automatic_anchor_checks"])
        self.assertTrue(all(c["valid"] for c in data["automatic_anchor_checks"]))
        self.assertTrue(any(a["output_status"] == "invalid_structure" for a in data["archives"]))
        self.assertFalse(data["final_round"]["extraction"]["uncovered_spans"])
        self.assertTrue(data["final_round"]["extraction"]["non_claim_spans"])


if __name__ == "__main__":
    unittest.main()
