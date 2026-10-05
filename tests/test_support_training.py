"""Synthetic-only data/training boundary regressions; no torch/model required."""
from copy import deepcopy
import unittest
from evaluation import support_training as t
from evaluation.support_review_quality import quality_entry,apply_quality_layer
from evaluation.support_dataset import task_key
from tests.test_support_dataset import sample


class TrainingBoundaryTests(unittest.TestCase):
    def setUp(self):
        s=sample();s.update(group_id='synthetic_fixture-family',split='train')
        s['task']['evidence'][0]['metadata']['source_id']='synthetic_fixture-document'
        s['sample_id']=task_key(s['task'])
        e=quality_entry(s,disposition='candidate_ready',proposed_label='supported',flags=[],rationale='fixture')
        self.s=apply_quality_layer([s],[e])[0]
        self.template={'reviews':[{'sample_id':s['sample_id'],'task_sha256':s['sample_id'],
            'suggestion_label':'contradicted','suggestion_basis_ids':['q1']}]}

    def confirmed(self):
        return t.confirm_template([self.s],self.template,event_id='synthetic_fixture-event',reviewer_id='local-user-fixture')[0][0]

    def test_template_is_authority_not_stale_internal_suggestion(self):
        s=self.confirmed()
        self.assertEqual(s['supervision']['label'],'contradicted')
        self.assertEqual(s['supervision']['basis_ids'],['q1'])
        self.assertEqual(self.s['supervision']['status'],'pending')
        self.assertEqual(s['supervision']['source'],'ai_assisted_user_supervised')

    def test_auxiliary_wrong_hash_and_missing_user_cannot_confirm(self):
        for field,value in [('task_sha256','wrong'),('suggestion_label','not_assessable')]:
            r=deepcopy(self.template);r['reviews'][0][field]=value
            with self.assertRaises(ValueError):t.confirm_template([self.s],r,event_id='fixture',reviewer_id='fixture')
        s=deepcopy(self.s);s['quality_review']['disposition']='auxiliary_only'
        with self.assertRaises(ValueError):t.confirm_template([s],self.template,event_id='fixture',reviewer_id='fixture')
        with self.assertRaises(ValueError):t.confirm_template([self.s],self.template,event_id='fixture',reviewer_id='')

    def test_every_delivered_source_requires_permission(self):
        s=self.confirmed()
        selected,excluded=t.select_materials([s],['synthetic_fixture-document'])
        self.assertEqual(len(selected),1)
        self.assertFalse(excluded)
        selected,excluded=t.select_materials([s],[])
        self.assertFalse(selected)
        self.assertEqual(excluded[0]['reason'],'source_training_permission_unconfirmed')

    def test_pair_keeps_exact_evidence_and_omits_leakage_fields(self):
        s=self.confirmed();s['recipe']={'hint':'SECRET_RECIPE'}
        s['supervision']['note']='SECRET_REVIEW'
        text=' '.join(t.text_pair(s))
        self.assertIn(s['task']['evidence'][0]['text'],text)
        self.assertIn(s['task']['claim']['proposition'],text)
        self.assertNotIn('SECRET',text)

    def test_family_and_near_duplicate_split_rejected(self):
        a=self.confirmed();b=deepcopy(a)
        b['task']['claim']['proposition']+=' today';b['sample_id']=task_key(b['task']);b['split']='test'
        with self.assertRaises(ValueError):t.check_partition([a,b])
        b['group_id']='another'
        # identical proposition is also a near duplicate, even with a different family ID.
        b['task']['claim']['proposition']=a['task']['claim']['proposition']
        with self.assertRaises(ValueError):t.check_partition([a,b])

    def test_new_split_deterministic_family_only_and_original_preserved(self):
        samples=[]
        for i in range(5):
            s=deepcopy(self.confirmed());s['group_id']='synthetic_fixture-'+str(i)
            s['task']['claim']['proposition']='distinct fixture target '+str(i)
            s['sample_id']=task_key(s['task']);samples.append(s)
        a,plan=t.development_split(samples,seed=7)
        b,again=t.development_split(samples,seed=7)
        self.assertEqual(plan,again)
        self.assertEqual(a,b)
        self.assertEqual({s['split'] for s in a},{'train','validation','test'})
        self.assertTrue(all(s['split']=='train' for s in samples))
        self.assertTrue(all(s['original_split']=='train' for s in a))


if __name__=='__main__':unittest.main()
