"""Synthetic regression for the label-blind NLI semantic adapter."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from tests.test_support_dataset import sample
from evaluation.support_dataset import task_key, digest
from evaluation.support_nli import semantic_pair, semantic_pair_v1, output_mapping, prepare

class NLIBoundaries(unittest.TestCase):
    def fixture(self):
        s=sample();s.update(split='train',group_id='fixture-family')
        s['task']['claim']['assertion_role']='asserted'
        s['task']['claim']['basis_target']='document_body'
        s['task']['other_basis']=[];s['sample_id']=task_key(s['task'])
        return s
    def test_label_and_basis_choices_cannot_leak_or_select_evidence(self):
        a=self.fixture();b=deepcopy(a)
        b['supervision'].update(status='confirmed',label='contradicted',reviewer_id='fixture-user',
                                basis_ids=[b['task']['evidence'][0]['basis_id']],note='SECRET')
        b['recipe']={'secret':'SECRET'};b['observations']=[{'rationale':'SECRET','structure_valid':True}]
        self.assertEqual(semantic_pair(a),semantic_pair(b))
        for e in a['task']['evidence']:self.assertIn(e['text'],semantic_pair(a)['premise'])
    def test_negation_quantity_conditions_and_metadata_separate(self):
        s=self.fixture();s['task']['claim'].update(proposition='When connected, 5 MW is not 5 MVA.',text='When connected, 5 MW is not 5 MVA.',qualifiers=['Only when connected'])
        e=s['task']['evidence'][0];e['metadata'].update(applicability=['Australian NEM'],locator='TEMP_ID_SECRET',source_uri='https://secret.invalid')
        s['sample_id']=task_key(s['task']);pair=semantic_pair(s)
        self.assertIn('5 MW is not 5 MVA',pair['hypothesis']);self.assertIn('Only when connected',pair['hypothesis'])
        self.assertFalse(pair['document_context']['is_official_technical_prose'])
        self.assertNotIn('Index applicability',pair['premise']);self.assertNotIn('SECRET',pair['premise'])
        self.assertIn('Australian NEM',str(pair['document_context']))

    def test_metadata_and_auxiliary_never_enter_body_route(self):
        for mode in ('metadata','auxiliary','hold','attribution'):
            s=self.fixture()
            if mode=='metadata':s['task']['claim']['basis_target']='metadata'
            elif mode=='attribution':s['task']['claim']['category']='index-versus-body'
            else:s['quality_review']={'disposition':'auxiliary_only' if mode=='auxiliary' else 'hold'}
            s['sample_id']=task_key(s['task'])
            with self.assertRaises(ValueError):semantic_pair(s)

    def test_legacy_projection_is_still_available_and_versioned(self):
        s=self.fixture();s['task']['evidence'][0]['metadata']['applicability']=['Fixture jurisdiction']
        s['sample_id']=task_key(s['task'])
        self.assertEqual(semantic_pair_v1(s)['version'],'support-nli-semantic-pair-v1')
        self.assertIn('Index applicability',semantic_pair_v1(s)['premise'])
        self.assertNotIn('Fixture jurisdiction',semantic_pair(s)['premise'])
    def test_unimplemented_stance_and_other_basis_rejected(self):
        for change in ('stance','basis'):
            s=self.fixture()
            if change=='stance':s['task']['claim']['assertion_role']='reported_not_asserted'
            else:s['task']['other_basis']=[{'basis_id':'fixture','text':'execution record'}]
            s['sample_id']=task_key(s['task'])
            with self.assertRaises(ValueError):semantic_pair(s)
    def test_real_mapping_order_is_not_assumed(self):
        self.assertEqual(output_mapping(SimpleNamespace(id2label={0:'contradiction',1:'neutral',2:'entailment'})),{0:'contradicted',1:'insufficient_evidence',2:'supported'})
        with self.assertRaises(ValueError):output_mapping(SimpleNamespace(id2label={0:'LABEL_0',1:'LABEL_1',2:'LABEL_2'}))
    def test_overlong_is_recorded_not_truncated(self):
        class Tokenizer:
            def __call__(self,a,b,**kwargs):
                assert kwargs['truncation'] is False
                return {'input_ids':SimpleNamespace(shape=(1,513))}
        encoded,records,excluded=prepare([self.fixture()],Tokenizer(),512)
        self.assertFalse(encoded);self.assertEqual(len(excluded),1)
        self.assertEqual(records[0]['treatment'],'excluded_over_context_no_truncation')

if __name__=='__main__':unittest.main()
