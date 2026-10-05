"""Synthetic supervision subset and sealed document holdout boundaries."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tests import test_support_nli as fixtures
from evaluation.support_dataset import task_key,digest
from evaluation.support_nli_expanded import (confirm_authorized,validate_layout,
    heldout_metrics,match_effective,evaluate_document_holdout)

class ExpandedBoundaries(unittest.TestCase):
    def sample(self,split,source,group):
        s=fixtures.NLIBoundaries().fixture();s['split']=split;s['group_id']=group
        s['task']['claim']['proposition']+=' '+group
        for e in s['task']['evidence']:e['metadata']['source_id']=source
        s['sample_id']=task_key(s['task']);s['quality_review']={'disposition':'candidate_ready','basis_scope':'delivered_document_prose'}
        s['supervision'].update(status='confirmed',label='supported',reviewer_id='fixture-owner',source='ai_assisted_user_supervised',basis_ids=[s['task']['evidence'][0]['basis_id']])
        return s
    def layout(self):
        return [self.sample('train','dev-doc','train-family'),self.sample('validation','dev-doc','val-family')],[self.sample('future_document_heldout_evaluation_review','held-doc','held-family')]
    def test_confirm_exact_subset_preserves_pending_and_received_reason(self):
        s=self.sample('future_training_development','dev-doc','family');s['supervision'].update(status='pending',label=None,reviewer_id=None,basis_ids=[])
        e=deepcopy(s['task']['evidence'][0]);e['basis_id']='second-basis';e['text']='Second delivered paragraph does not replace the first.';e['text_sha256']=digest(e['text']);e['end_offset']=e['start_offset']+len(e['text']);s['task']['evidence'].append(e);s['sample_id']=task_key(s['task'])
        original=deepcopy(s);basis=[s['task']['evidence'][0]['basis_id']]
        template={'reviews':[{'sample_id':s['sample_id'],'task_sha256':s['sample_id'],'suggestion_label':'contradicted','suggestion_basis_ids':basis,'note':'Specific received reason'}]}
        result,events=confirm_authorized([s],template,event_id='fixture-event',reviewer_id='fixture-owner')
        self.assertEqual(s,original);self.assertEqual(result[0]['supervision']['basis_ids'],basis)
        self.assertEqual(events[0]['note'],'Specific received reason');self.assertEqual(result[0]['supervision']['source'],'ai_assisted_user_supervised')
    def test_layout_rejects_document_overlap_wrong_role_pending_and_duplicate(self):
        for mode in ('document','role','pending','duplicate'):
            dev,hold=self.layout()
            if mode=='document':
                for e in hold[0]['task']['evidence']:e['metadata']['source_id']='dev-doc'
                hold[0]['sample_id']=task_key(hold[0]['task'])
            elif mode=='role':hold[0]['split']='validation'
            elif mode=='pending':hold[0]['supervision'].update(status='pending',label=None,reviewer_id=None)
            else:hold=[deepcopy(dev[0])]
            with self.assertRaises((ValueError,AssertionError)):validate_layout(dev,hold)

    def test_reordered_confirmation_template_binds_event_reason_by_identity(self):
        dev,_=self.layout()
        for s in dev:s['supervision'].update(status='pending',label=None,reviewer_id=None,basis_ids=[])
        rows=[{'sample_id':s['sample_id'],'task_sha256':s['sample_id'],
            'suggestion_label':label,'suggestion_basis_ids':[s['task']['evidence'][0]['basis_id']],
            'note':reason} for s,label,reason in zip(dev,('supported','contradicted'),('First reason','Second reason'))]
        confirmed,events=confirm_authorized(dev,{'reviews':list(reversed(rows))},event_id='fixture',reviewer_id='fixture-owner')
        expected={r['sample_id']:r for r in rows}
        for s in confirmed:
            self.assertEqual(s['supervision']['note'],expected[s['sample_id']]['note'])
            self.assertEqual(s['review_history'][-1]['sample_id'],s['sample_id'])
        for e in events:self.assertEqual(e['note'],expected[e['sample_id']]['note'])
    def test_valid_layout_and_exact_counts(self):
        dev,hold=self.layout();self.assertEqual(validate_layout(dev,hold),{'train':1,'validation':1,'heldout':1})
        with self.assertRaises(ValueError):validate_layout(dev,hold,{'train':2,'validation':1,'heldout':1})
    def test_holdout_prediction_cannot_start_before_selection_seal(self):
        with TemporaryDirectory() as directory,patch('evaluation.support_nli_expanded.verify_freeze'),patch('evaluation.support_nli_expanded.load_model') as loader:
            with self.assertRaises(FileNotFoundError):evaluate_document_holdout({'output':directory})
            loader.assert_not_called();self.assertFalse((Path(directory)/'heldout-started.json').exists())
    def test_token_preflight_mismatch_rejected(self):
        with self.assertRaises(ValueError):match_effective([{'sample_id':'id','tokens':513}],[{'sample_id':'id','tokens':512}],{'id'})
    def test_wrong_support_two_denominators_and_confusion_are_explicit(self):
        rows=[]
        for i,label in enumerate(('supported','contradicted','insufficient_evidence')):
            s=self.sample('future_document_heldout_evaluation_review','held-doc',str(i));s['task']['claim']['proposition']='Target '+str(i);s['sample_id']=task_key(s['task']);s['supervision']['label']=label;rows.append(s)
        preds=[{'sample_id':s['sample_id'],'label':'supported','status':'complete'} for s in rows]
        m=heldout_metrics(rows,preds);d=m['nli_diagnostics']
        self.assertEqual(d['false_supported_count'],2);self.assertEqual(d['non_supported_completed'],2)
        self.assertEqual(d['wrong_support_among_supported_predictions'],2/3)
        self.assertEqual(m['three_class_confusion']['matrix'],[[1,0,0],[1,0,0],[1,0,0]])

if __name__=='__main__':unittest.main()
