import asyncio
from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from core.validation import ContractError
from evaluation.format_stability_inputs_v1 import build,prepare
from evaluation.format_stability_trial_v1 import execute,fields_complete,run
from evaluation import premise_bound_review_v6 as v6
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from tests.test_text_bound_review import Adapter


def prediction(t):
    return {'sample_id':t['sample_id'],'requirements':[
        {'requirement_id':r['requirement_id'],'coverage':'covered',
         'unit_ids':[t['answer_units'][0]['unit_id']],'rationale':'preset reason'}
        for r in t['requirements']], 'units':[
        {'unit_id':u['unit_id'],'rationale':'preset unit reason', 'judgments':[
            {'proposition':u['text'],'claim_type':'literature_statement','support':'insufficient_evidence',
             'basis_ids':[],'rationale':'preset judgment reason'}]}
        for u in t['answer_units']], 'rationale':'preset synthetic output, not semantic evidence'}


class TrialTests(unittest.TestCase):
    def test_reordering_does_not_affect_completeness(self):
        t=build()[1];v=prediction(t);v['units'].reverse();v['requirements'].reverse()
        self.assertTrue(fields_complete(v,t)['complete'])

    def test_missing_duplicate_foreign_ids_fail(self):
        t=build()[1]
        for key,ident in [('requirements','requirement_id'),('units','unit_id')]:
            for mode in ['missing','duplicate','foreign']:
                v=prediction(t)
                if mode=='missing':v[key].pop()
                elif mode=='duplicate':v[key][1]=deepcopy(v[key][0])
                else:v[key][1][ident]='foreign'
                self.assertFalse(fields_complete(v,t)['complete'])

    def test_blank_reason_illegal_enum_can_be_complete_not_valid(self):
        t=build()[0]
        for mode in ['blank','enum']:
            v=prediction(t)
            if mode=='blank':v['units'][0]['rationale']='  '
            else:v['requirements'][0]['coverage']='illegal'
            self.assertTrue(fields_complete(v,t)['complete'])
            with self.assertRaises(ContractError):v6.parse(v,t)

    def test_missing_reason_and_unparseable_shape_incomplete(self):
        t=build()[0];v=prediction(t);del v['units'][0]['rationale']
        self.assertFalse(fields_complete(v,t)['complete'])
        self.assertFalse(fields_complete(None,t)['complete'])

    def test_all_eight_keep_original_sample_ids_and_shared_budget(self):
        tasks=build();order=prepare(tasks);lookup={t['sample_id']:t for t in tasks}
        adapter=Adapter([prediction(lookup[i['sample_id']]) for i in order]);saved={}
        result=asyncio.run(execute({'order':order},tasks,ModelClient(adapter,ModelSettings('fixture')),
            None,lambda rid,kind,v:saved.update({(rid,kind):v})))
        self.assertEqual(result['actual_calls'],8)
        self.assertEqual(len(result['controls']),8)
        self.assertEqual([r['invocation_id'] for r in result['records']],[i['request_id'] for i in order])
        self.assertTrue(all(r['response_contract_version']==v6.VERSION for r in result['records']))
        self.assertEqual(adapter.requests[0].messages[1],adapter.requests[1].messages[1])

    def test_final_failure_stops_unexecuted_pair(self):
        tasks=build();order=prepare(tasks);adapter=Adapter([{},{}]);saved={}
        r=asyncio.run(execute({'order':order},tasks,ModelClient(adapter,ModelSettings('fixture')),
            None,lambda rid,kind,v:saved.update({(rid,kind):v})))
        self.assertEqual(r['actual_calls'],2);self.assertEqual(len(r['controls']),1)
        self.assertTrue(r['controls'][0]['stop'])
        self.assertNotIn((order[1]['request_id'],'accepted'),saved)

    def test_storage_failure_stops_before_model_call(self):
        tasks=build();adapter=Adapter([])
        def persist(*args):raise OSError('synthetic storage failure')
        r=asyncio.run(execute({'order':prepare(tasks)},tasks,
            ModelClient(adapter,ModelSettings('fixture')),None,persist))
        self.assertEqual(r['actual_calls'],0);self.assertTrue(r['controls'][0]['stop'])

    def test_existing_attempt_refuses_resume(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name);(path/'attempt.json').write_text('attempted')
            with patch('evaluation.format_stability_trial_v1.preflight',return_value=({},[])):
                with self.assertRaises(FileExistsError):run(path)
