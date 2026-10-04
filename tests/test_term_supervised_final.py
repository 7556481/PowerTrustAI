from copy import deepcopy
import unittest
from evaluation.term_supervised_final import merge_batch, evaluate_saved
from tests.test_supervised_retrieval import fixture

def data():
    q=fixture();q['question_id']='Q';old={'questions':[q]}
    candidate={'candidate_id':'Q-N01','fragment_id':'f-new','status':'ai_proposed','relevance':2,
        'support_relation':'partial_answer_basis','conditions':['conditional'],'scope':'fixture',
        'reason':'synthetic_fixture','contexts':[{'id':'Q-N01-X1','status':'unreviewed','relevance':None}],'visual_checked':None}
    batch={'version':'v','status':'ai_annotated_under_user_supervision','questions':[{'question_id':'Q','status':'ai_proposed','new_candidates':[candidate]}],
        'annotation_provenance':{'human_confirmed':False},'annotation_summary':{'new_candidates_judged':1,'contexts_unreviewed':1,'relevance_counts':{'2':1}}}
    mapping={'questions':{'Q':{'Q-N01':{'fragment_id':'f-new','origins':[]}}}}
    template={'version':'v','questions':[deepcopy(batch['questions'][0])]}
    return old,mapping,batch,template

class FinalImportTests(unittest.TestCase):
    def test_old_labels_and_combinations_immutable(self):
        old,m,b,t=data();original=deepcopy(old);merged,bound=merge_batch(old,m,b,t)
        self.assertEqual(old,original);self.assertEqual(merged['questions'][0]['necessary_evidence_combinations'],original['questions'][0]['necessary_evidence_combinations'])
        self.assertFalse(merged['supplementary_annotation_batch']['annotation_provenance']['human_confirmed'])
        self.assertIsNone(merged['questions'][0]['fragment_relevance'][-1]['visual_checked'])
        self.assertEqual(bound,m['questions'])
    def test_unknown_field_rejected(self):
        old,m,b,t=data();b['questions'][0]['new_candidates'][0]['invented']=True
        with self.assertRaisesRegex(ValueError,'unknown fields'):merge_batch(old,m,b,t)
    def test_fragment_id_mismatch_rejected(self):
        old,m,b,t=data();b['questions'][0]['new_candidates'][0]['fragment_id']='other'
        with self.assertRaisesRegex(ValueError,'mapping mismatch'):merge_batch(old,m,b,t)
    def test_context_cannot_be_counted_or_regraded(self):
        old,m,b,t=data();b['questions'][0]['new_candidates'][0]['contexts'][0]['relevance']=3
        with self.assertRaisesRegex(ValueError,'context unknown'):merge_batch(old,m,b,t)
    def test_same_pool_denominator_and_real_unknown_rank(self):
        old,m,b,t=data();merged,_=merge_batch(old,m,b,t)
        oldmap={'questions':{'Q':{'candidates':{bid:{'fragment_id':'f-'+bid} for bid in ('a','b','c','d')}}}}
        methods=lambda ids:{name:{'hits':[{'fragment_id':fid,'rank':i} for i,fid in enumerate(ids,1)]} for name in ('bm25','dense','rrf')}
        exp={'results':[{'id':'Q','query':'synthetic_fixture','family':'f','split':'development','language':'en',
            'variants':{'baseline':methods(['f-a']),'term_expansion':methods(['f-unknown','f-new','f-a'])}}]}
        row=evaluate_saved(merged,oldmap,m,exp)[0];a=row['variants']['baseline']['bm25']['metrics'];z=row['variants']['term_expansion']['bm25']['metrics']
        self.assertEqual(a['grade2_pool_count'],3);self.assertEqual(z['grade2_pool_count'],3)
        self.assertAlmostEqual(a['recall_ge2_judged_core_pool_at5'],1/3)
        self.assertIsNone(z['mrr_ge2_at5']);self.assertEqual(z['bounds_grade3']['mrr_lower'],1/3)

if __name__=='__main__':unittest.main()
