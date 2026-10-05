"""Synthetic reception, basis scope, and label-blind merged-family splits."""
from copy import deepcopy
import unittest
from tests import test_support_nli as fixtures
from evaluation.support_dataset import task_key
from evaluation.support_nli_review import receive_pending,merge_groups,propose_split

class ReviewBoundaries(unittest.TestCase):
    def fixture(self):
        s=fixtures.NLIBoundaries().fixture();s['supervision'].update(status='pending',label=None,reviewer_id=None)
        s['split']='future_training_development';s['group_id']='first'
        s['task']['evidence']=s['task']['evidence'][:1]
        e=s['task']['evidence'][0];e['metadata'].update(source_id='fixture-doc',provenance={'file_page':1})
        s['sample_id']=task_key(s['task'])
        r={'sample_id':s['sample_id'],'task_sha256':s['sample_id'],'family':s['group_id'],
           'future_allocation':s['split'],'claim':s['task']['claim']['proposition'],
           'evidence_text':e['text'],'document_id':'fixture-doc','file_page':1,
           'disposition':'candidate_ready','status':'pending','original_suggestion':s['supervision']['suggestion_label'],
           'proposed_label':'contradicted','basis_ids':[e['basis_id']],'rationale':'review-specific reason'}
        t={'sample_id':s['sample_id'],'task_sha256':s['sample_id'],'suggestion_label':'contradicted',
           'suggestion_basis_ids':r['basis_ids'],'note':r['rationale'],'status':'pending','label':None,'reviewer_id':None,'basis_ids':[]}
        return s,r,t
    def test_received_suggestion_pending_and_history_unchanged(self):
        s,r,t=self.fixture();original=deepcopy(s)
        result,changes=receive_pending([s],{'reviews':[r]},{'reviews':[t]})
        self.assertEqual(s,original);self.assertEqual(result[0]['task'],s['task'])
        self.assertIsNone(result[0]['supervision']['label'])
        self.assertEqual(result[0]['supervision']['rationale'],'review-specific reason')
        self.assertEqual(result[0]['supervision_history'][0],s['supervision'])
    def test_bad_hash_basis_delivery_or_confirmation_rejected(self):
        for field,value in [('task_sha256','bad'),('basis_ids',['not-delivered']),('evidence_text','changed'),('status','confirmed')]:
            s,r,t=self.fixture();r[field]=value
            with self.assertRaises(ValueError):receive_pending([s],{'reviews':[r]},{'reviews':[t]})
    def test_primary_template_must_use_received_label_not_old_suggestion(self):
        s,r,t=self.fixture();t['suggestion_label']='supported'
        with self.assertRaises(ValueError):receive_pending([s],{'reviews':[r]},{'reviews':[t]})
    def test_hold_does_not_block_other_primary(self):
        s,r,t=self.fixture();b=deepcopy(s);b['task']['claim']['proposition']='Other target';b['sample_id']=task_key(b['task'])
        q=deepcopy(r);q.update(sample_id=b['sample_id'],task_sha256=b['sample_id'],claim=b['task']['claim']['proposition'],disposition='hold',proposed_label=None,basis_ids=[])
        result,_=receive_pending([s,b],{'reviews':[r,q]},{'reviews':[t]})
        self.assertEqual(len(result),2);self.assertFalse(result[1]['eligible_for_baseline'])
    def test_shared_evidence_and_parent_are_union_and_split_label_blind(self):
        a,_,_=self.fixture();rows=[a]
        for i in range(3):
            b=deepcopy(a);b['task']['claim']['proposition']='Distinct target '+str(i);b['sample_id']=task_key(b['task']);b['group_id']='group-'+str(i)
            if i>0:
                e=b['task']['evidence'][0];e['text']='Independent original evidence '+str(i)*50
                from evaluation.support_dataset import digest
                e.update(text_sha256=digest(e['text']),end_offset=e['start_offset']+len(e['text']))
                b['sample_id']=task_key(b['task'])
            rows.append(b)
        g=merge_groups(rows);self.assertEqual(g['groups'][rows[0]['sample_id']],g['groups'][rows[1]['sample_id']])
        p=propose_split(rows,g,seed=1);altered=deepcopy(rows)
        for b in altered:b['supervision']['suggestion_label']='supported'
        self.assertEqual(p,propose_split(altered,merge_groups(altered),seed=1))

    def test_pending_training_rejected_before_loading_or_creating_output(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from evaluation.support_nli import run_training
        s,_,_=self.fixture();s['split']='train'
        with TemporaryDirectory() as directory:
            output=Path(directory)/'never-created'
            with patch('evaluation.support_nli.read',side_effect=[{'output':str(output),'data':'fixture'}, {'samples':[s]}]), patch('evaluation.support_nli.load_model') as loader:
                with self.assertRaises(ValueError):run_training(SimpleNamespace(config='fixture'))
                loader.assert_not_called();self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
