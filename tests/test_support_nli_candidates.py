"""Synthetic source anchoring and review allocation checks."""
from copy import deepcopy
import unittest
from evaluation.support_dataset import digest, task_key
from evaluation.support_nli_candidates import exact_anchor,validate_pending
from tests import test_support_nli as nli_fixture

class CandidateBoundaries(unittest.TestCase):
    def fixture(self):
        s=nli_fixture.NLIBoundaries().fixture();s['training_eligible']=False
        e=s['task']['evidence'][0];e['start_offset']=3;e['end_offset']=3+len(e['text'])
        e['metadata']['source_id']='fixture-doc';e['metadata']['provenance']={'file_page':1}
        s['sample_id']=task_key(s['task'])
        return s,{'fixture-doc':{1:'---'+e['text']+' trailer'}}
    def test_normalized_matching_retains_whitespace_and_offsets(self):
        text='header\nIf A\n  and B,\tC is required.\nfooter'
        a,b,quote=exact_anchor(text,'If A and B','C is required.')
        self.assertEqual(quote,'If A\n  and B,\tC is required.')
        self.assertEqual(text[a:b],quote)
    def test_ambiguous_or_missing_source_is_rejected(self):
        with self.assertRaises(ValueError):exact_anchor('start end start end','start','end')
        with self.assertRaises(ValueError):exact_anchor('start only','start','missing')
    def test_pending_exact_span_and_no_existing_task_reuse(self):
        s,pages=self.fixture();self.assertEqual(validate_pending([s],pages)['pending'],1)
        with self.assertRaises(ValueError):validate_pending([s],pages,[s])
        with self.assertRaises(ValueError):validate_pending([s],{'fixture-doc':{1:'wrong original'}})
    def test_confirmed_or_training_eligible_candidate_is_rejected(self):
        s,pages=self.fixture();s['training_eligible']=True
        with self.assertRaises(ValueError):validate_pending([s],pages)
        s['training_eligible']=False;s['supervision'].update(status='confirmed',label='supported',reviewer_id='fixture')
        with self.assertRaises(ValueError):validate_pending([s],pages)
    def test_parent_cannot_cross_future_allocation(self):
        s,pages=self.fixture();b=deepcopy(s)
        b['task']['claim']['proposition']='Distinct candidate concept';b['sample_id']=task_key(b['task'])
        b['group_id']='other';b['split']='validation';b['origins']=[{'parent_sample_id':s['sample_id']}]
        with self.assertRaises(ValueError):validate_pending([s,b],pages)

if __name__=='__main__':unittest.main()
