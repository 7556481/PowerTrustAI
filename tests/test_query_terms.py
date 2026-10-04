import unittest
from rag.query_terms import expand_query
from evaluation.term_expansion_trial import marked_score
from tests.test_supervised_retrieval import fixture

class QueryTermTests(unittest.TestCase):
    def test_english_unchanged(self):
        self.assertEqual(expand_query('What limits generator capability?'),('What limits generator capability?',()))
    def test_chinese_only_lexical_additions(self):
        text='发电机的无功限制';expanded,matched=expand_query(text)
        self.assertTrue(expanded.startswith(text+' '));self.assertIn('generator',expanded)
        self.assertNotIn('synchronous',expanded)
    def test_no_question_id_dependency(self):
        a=expand_query('母线电压正常是否稳定？')[0]
        self.assertEqual(a,expand_query('母线电压正常是否稳定？')[0])
        self.assertEqual(expand_query('D05'),('D05',()))
    def test_unknown_preserves_rank(self):
        q=fixture();qm={'candidates':{bid:{'fragment_id':'f-'+bid} for bid in ('a','b','c','d')}}
        r=marked_score(q,qm,['f-unknown','f-a'])
        self.assertIsNone(r['mrr_ge2_at5']);self.assertEqual(r['bounds_ge2']['mrr_lower'],.5)
        self.assertEqual(r['bounds_ge2']['mrr_upper'],1);self.assertEqual(r['top5_annotation_coverage'],.5)
        self.assertEqual(len(q['fragment_relevance']),5)
    def test_partial_group_not_full_answer(self):
        q=fixture();q['evidence_combination_completeness']='partial_not_sufficient'
        qm={'candidates':{bid:{'fragment_id':'f-'+bid} for bid in ('a','b','c','d')}}
        r=marked_score(q,qm,['f-a','f-b'])
        self.assertTrue(r['any_necessary_group_covered_at5']);self.assertFalse(r['scope_limited_answer_basis_complete_at5'])

if __name__=='__main__':unittest.main()
