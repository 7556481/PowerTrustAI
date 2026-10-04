"""Synthetic fixtures only; ordinary tests never download/load real weights."""
from types import SimpleNamespace
import tempfile
import unittest
from evaluation.reranker_trial import union_candidates,coverage,sha,verify_saved_evidence
from rag.reranker import ONNXReranker,stable_order,pair_encoding
from tests.test_supervised_retrieval import fixture
from evaluation.term_expansion_trial import marked_score

class FakeTokenizer:
    def no_padding(self):pass
    def no_truncation(self):self.limit=None
    def enable_truncation(self,**kwargs):self.limit=kwargs['max_length']
    def encode(self,q,text):
        keep=len(text) if self.limit is None else max(0,self.limit-len(q)-4)
        sequences=[None]+[0]*len(q)+[None,None]+[1]*min(len(text),keep)+[None]
        offsets=[(0,0)]+[(i,i+1) for i in range(len(q))]+[(0,0),(0,0)]+[(i,i+1) for i in range(min(len(text),keep))]+[(0,0)]
        return SimpleNamespace(ids=[0]*len(sequences),sequence_ids=sequences,offsets=offsets)

class RerankerTests(unittest.TestCase):
    def test_union_deduplicates_preserves_origins(self):
        pool=union_candidates({'bm25':[{'fragment_id':'f','score':1}], 'dense':[{'fragment_id':'f','score':.7}]})
        self.assertEqual(len(pool),1);self.assertEqual(len(pool['f']['origins']),2)
    def test_stable_tie_and_negative_logits(self):
        self.assertEqual(stable_order([-1,-1,2],['z','a','b']),[2,1,0])
        with self.assertRaises(ValueError):stable_order([float('nan')],['f'])
    def test_empty_score_without_dependency(self):
        self.assertEqual(ONNXReranker.__new__(ONNXReranker).score('query',[]),([],[]))
    def test_missing_model_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError,'Optional reranker unavailable'):ONNXReranker(directory)
    def test_truncation_explicit_offsets(self):
        encoded,note=pair_encoding(FakeTokenizer(),'query','x'*600)
        self.assertEqual(note['encoded_tokens'],512);self.assertTrue(note['truncated'])
        self.assertEqual(note['kept_body_char_end'],503);self.assertEqual(note['body_chars'],600)
    def test_query_not_silently_truncated(self):
        with self.assertRaisesRegex(ValueError,'Query too long'):pair_encoding(FakeTokenizer(),'x'*509,'body')
    def test_candidate_version_hash(self):
        self.assertNotEqual(sha({'knowledge_version':'k1','id':'f'}),sha({'knowledge_version':'k2','id':'f'}))
    def test_recall_vs_sorting_diagnostic(self):
        q=fixture();c={bid:{'fragment_id':'f-'+bid} for bid in ('a','b','c','d')}
        v=coverage(q,c,{'f-a','f-b'},set());self.assertEqual(v['direct_basis']['a'],'ranking_failure')
        self.assertTrue(v['scope_complete_candidate_coverage'])
        v=coverage(q,c,{'f-b'},set());self.assertEqual(v['direct_basis']['a'],'recall_missing')
    def test_unknown_preserves_actual_position(self):
        q=fixture();m={'candidates':{bid:{'fragment_id':'f-'+bid} for bid in ('a','b','c','d')}}
        v=marked_score(q,m,['unlabeled','f-a'])
        self.assertIsNone(v['mrr_ge2_at5']);self.assertEqual(v['bounds_grade3']['mrr_lower'],.5)
    def test_evidence_version_binding_not_relaxed(self):
        saved={'text':'exact','provenance':{'knowledge_version':'old','fragment_id':'f'}}
        with self.assertRaisesRegex(ValueError,'binding mismatch'):verify_saved_evidence(None,'f','new',saved)
    def test_evidence_text_tampering_rejected(self):
        from dataclasses import make_dataclass,asdict
        P=make_dataclass('P',[('knowledge_version',str),('fragment_id',str)])
        E=make_dataclass('E',[('text',str),('provenance',P)])
        e=E('exact',P('k','f'));store=SimpleNamespace(evidence=lambda fid,kv:e)
        saved=asdict(e);self.assertEqual(verify_saved_evidence(store,'f','k',saved),saved)
        saved['text']='rewritten'
        with self.assertRaisesRegex(ValueError,'integrity mismatch'):verify_saved_evidence(store,'f','k',saved)

if __name__=='__main__':unittest.main()
