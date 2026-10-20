import asyncio
from copy import deepcopy
import unittest

from evaluation import requirement_trial_v3 as trial
from model_adapter.contracts import ModelSettings,ModelConnectionError
from model_adapter.runtime import ModelClient
from tests.test_text_bound_review import Adapter
from tests.test_requirement_review_v3 import fixture,prediction


class RequirementTrialTests(unittest.TestCase):
    def test_once_each_no_correction_no_truth_in_messages(self):
        tasks=[fixture() for _ in range(3)]
        for i,t in enumerate(tasks):t['sample_id']='fixture-'+str(i)
        adapter=Adapter([prediction(t) for t in tasks]);saved={}
        result=asyncio.run(trial.execute(tasks,ModelClient(adapter,ModelSettings('synthetic_fixture')),None,
            lambda sid,kind,v:saved.update({(sid,kind):v})))
        self.assertEqual(result['actual_calls'],3)
        self.assertEqual(len([1 for sid,kind in saved if kind=='result']),3)
        self.assertTrue(all('requirements' in r.messages[1].content for r in adapter.requests))
        self.assertTrue(all('SECRET' not in r.messages[1].content for r in adapter.requests))

    def test_one_correction_then_valid_preserves_derived_coverage(self):
        t=fixture();v=prediction(t);v['requirements'][1].update(coverage='missing',unit_ids=[])
        adapter=Adapter([{},v]);saved={}
        result=asyncio.run(trial.execute([t],ModelClient(adapter,ModelSettings('synthetic_fixture')),None,
            lambda sid,kind,v:saved.update({kind:v})))
        self.assertEqual(result['actual_calls'],2)
        self.assertEqual(saved['result']['prediction']['program_coverage']['value'],'incomplete')
        self.assertEqual([r['correction'] for r in result['records']],[False,True])

    def test_invalid_twice_stops_before_next_item(self):
        t=fixture();other=deepcopy(t);other['sample_id']='other';saved={};adapter=Adapter([{},{}])
        result=asyncio.run(trial.execute([t,other],ModelClient(adapter,ModelSettings('synthetic_fixture')),None,
            lambda sid,kind,v:saved.update({(sid,kind):v})))
        self.assertEqual(result['actual_calls'],2)
        self.assertTrue(result['controls'][0]['stop'])
        self.assertNotIn(('other','accepted'),saved)

    def test_transport_failure_no_retry(self):
        adapter=Adapter([ModelConnectionError()]);result=asyncio.run(trial.execute([fixture()],
            ModelClient(adapter,ModelSettings('synthetic_fixture')),None,lambda *args:None))
        self.assertEqual(result['actual_calls'],1);self.assertTrue(result['controls'][0]['stop'])


if __name__=='__main__':unittest.main()
