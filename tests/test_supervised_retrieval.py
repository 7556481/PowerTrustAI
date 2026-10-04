"""Known-score math and supervised annotation boundary regressions; no API."""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest

from evaluation.supervised_retrieval import score_question, validate, load, BASE


def fixture():
    rows=[{"blind_id":bid,"fragment_id":"f-"+bid,"role":"candidate","status":"ai_proposed",
        "relevance":g,"reason":"fixture","support_relation":"fixture"} for bid,g in (("a",3),("b",2),("c",1),("d",0))]
    rows.append({"blind_id":"x","fragment_id":"f-x","role":"adjacent_context","status":"unreviewed","relevance":None})
    return {"fragment_relevance":rows,"necessary_evidence_combinations":{"groups":[["a","b"]]},
        "answerability":{"value":"answerable_with_scope_limits"},"supplementary_reference_evidence":[]}


class SupervisedMetricTests(unittest.TestCase):
    def test_known_rank_math(self):
        value=score_question(fixture(),["b","c","a"],["a","b","c","d"])
        self.assertEqual(value["hit_ge2_at5"],1)
        self.assertEqual(value["mrr_ge2_at5"],1)
        self.assertAlmostEqual(value["direct_grade3_mrr_at5"],1/3)
        self.assertEqual(value["recall_ge2_judged_core_pool_at5"],1)
        expected=(3+1/math.log2(3)+7/math.log2(4))/(7+3/math.log2(3)+1/math.log2(4))
        self.assertAlmostEqual(value["ndcg_graded_judged_core_pool_at5"],expected)

    def test_partial_combination_not_complete(self):
        value=score_question(fixture(),["a","c"],["a","b","c","d"])
        self.assertEqual(value["hit_ge2_at5"],1)
        self.assertEqual(value["combination_max_member_coverage_at5"],.5)
        self.assertFalse(value["any_necessary_group_covered_at5"])
        self.assertFalse(value["scope_limited_answer_basis_complete_at5"])
        self.assertEqual(value["combination_details"][0]["missing_ids"],["b"])

    def test_aux_partial_gate_even_all_members_retrieved(self):
        q=fixture();q["evidence_combination_completeness"]="partial_not_sufficient"
        value=score_question(q,["a","b"],["a","b","c","d"])
        self.assertTrue(value["any_necessary_group_covered_at5"])
        self.assertFalse(value["scope_limited_answer_basis_complete_at5"])

    def test_partial_answerability_gate_without_aux(self):
        q=fixture();q["answerability"]["value"]="partially_answerable"
        value=score_question(q,["a","b"],["a","b","c","d"])
        self.assertTrue(value["any_necessary_group_covered_at5"])
        self.assertFalse(value["scope_limited_answer_basis_complete_at5"])

    def test_empty_groups_not_vacuous_success(self):
        q=fixture();q["necessary_evidence_combinations"]["groups"]=[]
        value=score_question(q,["a"],["a","b","c","d"])
        self.assertIsNone(value["any_necessary_group_covered_at5"])
        self.assertFalse(value["scope_limited_answer_basis_complete_at5"])

    def test_unknown_context_not_zero(self):
        value=score_question(fixture(),["b"],["a","b","c","d"])
        self.assertEqual(value["unknown_context_count"],1)
        self.assertEqual(value["judged_core_count"],4)
        self.assertAlmostEqual(value["recall_ge2_judged_core_pool_at5"],.5)

    def test_unknown_ranked_item_not_zero(self):
        q=fixture();q["fragment_relevance"][0]["status"]="unreviewed";q["fragment_relevance"][0]["relevance"]=None
        value=score_question(q,["a","b"],["a","b","c","d"])
        self.assertIsNone(value["hit_ge2_at5"])
        self.assertIsNone(value["ndcg_graded_judged_core_pool_at5"])
        self.assertEqual(value["unknown_top5_ids"],["a"])

    def test_cross_question_reference_not_credit(self):
        q=fixture();q["supplementary_reference_evidence"]=[{"source_blind_id":"other-c1","counts_as_retrieval_hit":False}]
        value=score_question(q,["d"],["a","b","c","d"])
        self.assertEqual(value["hit_ge2_at5"],0)
        self.assertEqual(value["supplementary_reference_hit_credit"],0)

    def test_no_positive_recall_undefined_hit_zero(self):
        q=fixture()
        for row in q["fragment_relevance"]:
            if row["role"]=="candidate":row["relevance"]=0
        value=score_question(q,["a"],["a","b","c","d"])
        self.assertEqual(value["hit_ge2_at5"],0)
        self.assertIsNone(value["recall_ge2_judged_core_pool_at5"])
        self.assertIsNone(value["ndcg_graded_judged_core_pool_at5"])

    def test_alternative_groups_or_members_and(self):
        q=fixture();q["necessary_evidence_combinations"]["groups"]=[["a","b"],["c"]]
        value=score_question(q,["c"],["a","b","c","d"])
        self.assertTrue(value["any_necessary_group_covered_at5"])


IMPORT=BASE.parent/"annotations/supervised-v3-eval-v1/annotations-30-supervised-v3.json"


@unittest.skipUnless(IMPORT.exists(),"local user-supervised archive absent")
class SavedSupervisedAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.data=load(IMPORT);self.mapping=load(BASE/"mapping.json")
        self.dataset=load(BASE.parent/"dataset-v1.json");self.comparison=load(BASE.parent/"comparison-v2.json")

    def check(self):
        return validate(self.data,self.mapping,self.dataset,self.comparison)

    def test_real_archive_field_adapter(self):
        inventory,diagnostics=self.check()
        self.assertFalse(diagnostics)
        self.assertIn("evidence_combination_completeness",inventory["$.questions[D01]"])
        self.assertIn("supplementary_reference_evidence",inventory["$.questions[D05]"])
        self.assertFalse(self.data["annotation_provenance"]["human_confirmed"])

    def test_unknown_aux_not_discarded(self):
        self.data["questions"][0]["unrecognized_aux"]=True
        with self.assertRaisesRegex(ValueError,"unadapted fields"):
            self.check()

    def test_binding_corruption_rejected(self):
        self.data["questions"][0]["fragment_relevance"][0]["fragment_id"]="foreign"
        with self.assertRaisesRegex(ValueError,"binding mismatch"):
            self.check()

    def test_cross_reference_credit_rejected(self):
        q=next(q for q in self.data["questions"] if q["question_id"]=="D05")
        q["supplementary_reference_evidence"][0]["counts_as_retrieval_hit"]=True
        with self.assertRaisesRegex(ValueError,"retrieval credit"):
            self.check()

    def test_unknown_enum_rejected(self):
        q=next(q for q in self.data["questions"] if q["question_id"]=="D01")
        q["evidence_combination_completeness"]="invented"
        with self.assertRaisesRegex(ValueError,"unadapted value"):
            self.check()

    def test_saved_rank_real_statcom_regression(self):
        q=next(q for q in self.data["questions"] if q["question_id"]=="D08")
        qm=self.mapping["questions"]["D08"]
        bm=score_question(q,[h["blind_id"] for h in qm["original_methods"]["bm25"]],qm["candidates"])
        hybrid=score_question(q,[h["blind_id"] for h in qm["original_methods"]["rrf"]],qm["candidates"])
        self.assertAlmostEqual(bm["direct_grade3_mrr_at5"],.25)
        self.assertEqual(hybrid["direct_grade3_hit_at5"],0)


if __name__=="__main__":unittest.main()
