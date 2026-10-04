import asyncio
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from evaluation import support_baseline as b
from evaluation import support_dataset as d
from model_adapter.contracts import ModelSettings,ModelResponse,ModelConnectionError
from model_adapter.runtime import ModelClient
from tests.test_support_dataset import sample

class FakeAdapter:
    def __init__(self,responses):self.responses=iter(responses);self.requests=[]
    async def complete(self,request):
        self.requests.append(request);item=next(self.responses)
        if isinstance(item,Exception):raise item
        return ModelResponse(d.canonical(item),'synthetic_fixture',finish_reason='stop')

def prediction(s,**changes):return dict(sample_id=s['sample_id'],label='supported',basis_ids=['q1'],rationale='synthetic_fixture',**changes)

class SupportBaselineTests(unittest.TestCase):
    def test_input_does_not_leak_model_or_expected_labels(self):
        s=sample();s['supervision']['suggestion_label']='SECRET_EXPECTATION'
        s['observations'][0]['model_rationale']='SECRET_OBSERVATION';s['recipe']={'label':'SECRET_RECIPE'}
        request=d.canonical(b.model_input([s]))
        self.assertNotIn('SECRET',request);self.assertNotIn('supervision',request);self.assertIn(s['task']['evidence'][0]['text'],request)

    def test_batches_and_capacity_preserve_whole_text(self):
        samples=[sample('claim '+str(i)) for i in range(3)]
        batches,excluded=b.pack(samples,max_items=2);self.assertEqual([len(x) for x in batches],[2,1]);self.assertFalse(excluded)
        batches,excluded=b.pack(samples,max_message_chars=len(b.PROMPT)+5)
        self.assertFalse(batches);self.assertEqual(len(excluded),3)
        self.assertEqual(excluded[0]['reason'],'complete_sample_exceeds_message_capacity')

    def test_cross_sample_basis_duplicate_unknown_and_missing_ids(self):
        a=sample();other=sample('other claim');other['task']['evidence'][0]['basis_id']='foreign';other['sample_id']=d.task_key(other['task'])
        for rows in ([prediction(a),prediction(a)], [dict(prediction(a),basis_ids=['foreign'])], [dict(prediction(a),sample_id='unknown')], []):
            with self.subTest(rows=rows),self.assertRaises(b.StructuredValidationError):b.parse_predictions({'predictions':rows},[a])
        rows=[prediction(a),dict(prediction(other),basis_ids=['foreign'])]
        self.assertEqual(len(b.parse_predictions({'predictions':rows},[a,other])),2)

    def test_once_correction_and_exact_accounting(self):
        s=sample();adapter=FakeAdapter([{'predictions':[]},{'predictions':[prediction(s)]}])
        result=asyncio.run(b.execute([s],ModelClient(adapter,ModelSettings('synthetic_fixture'))))
        self.assertEqual(result['actual_calls'],2);self.assertEqual([r['correction'] for r in result['records']],[False,True])
        self.assertEqual(result['predictions'][0]['status'],'complete');self.assertFalse(result['issues'])

    def test_failure_stops_and_keeps_valid_peer_and_records(self):
        a=sample();other=sample('other');third=sample('third')
        adapter=FakeAdapter([{'predictions':[prediction(a)]},ModelConnectionError()])
        result=asyncio.run(b.execute([a,other,third],ModelClient(adapter,ModelSettings('synthetic_fixture')),max_items=2))
        self.assertEqual(result['actual_calls'],2);self.assertEqual(len(adapter.requests),2)
        self.assertEqual(result['predictions'][0]['status'],'valid_partial');self.assertEqual(len(result['records']),2)
        self.assertEqual(result['issues'][0]['code'],'MODEL_CONNECTION_FAILED')
        self.assertEqual(next(r for r in result['predictions'] if r['sample_id']==third['sample_id'])['status'],'not_completed')

    def test_pending_has_no_accuracy_and_review_reuses_predictions(self):
        s=sample();d.group([s]);result=asyncio.run(b.execute([s],ModelClient(FakeAdapter([{'predictions':[prediction(s)]}]),ModelSettings('synthetic_fixture'))))
        self.assertIsNone(b.metrics([s],result)['semantic_metrics'])
        s['supervision'].update(status='confirmed',label='contradicted',reviewer_id='fixture-user',basis_ids=['q1'])
        metrics=b.metrics([s],result)['semantic_metrics'];self.assertEqual(metrics['false_supported'],1)
        self.assertEqual(metrics['non_supported_gold_denominator'],1);self.assertEqual(metrics['supported_prediction_denominator'],1)
        self.assertEqual(metrics['confusion_matrix']['contradicted']['supported'],1)

    def test_training_export_excludes_pending(self):
        s=sample();d.group([s])
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(b.training_export([s],Path(directory)/'pending'),0)
            s['supervision'].update(status='confirmed',label='supported',reviewer_id='fixture-user',basis_ids=['q1'])
            self.assertEqual(b.training_export([s],Path(directory)/'confirmed'),1)
            self.assertIn('fixture-user',(Path(directory)/'confirmed/supervised.jsonl').read_text(encoding='utf8'))

    def test_changed_task_cannot_reuse_predictions(self):
        s=sample();result={'predictions':[prediction(s)],'task_hashes':{s['sample_id']:'wrong'}}
        with self.assertRaises(ValueError):b.metrics([s],result)

    def test_timeout_stops_without_retry_and_keeps_failed_record(self):
        class Slow:
            async def complete(self,request):await asyncio.sleep(1)
        s=sample();result=asyncio.run(b.execute([s],ModelClient(Slow(),ModelSettings('synthetic_fixture',timeout_seconds=.01))))
        self.assertEqual(result['actual_calls'],1);self.assertEqual(result['issues'][0]['code'],'MODEL_TIMEOUT')
        self.assertEqual(result['records'][0]['error_code'],'MODEL_TIMEOUT')

    def test_pending_export_cannot_become_gold_by_direct_wrong_basis(self):
        s=sample();d.group([s]);s['supervision'].update(status='confirmed',label='supported',reviewer_id='fixture',basis_ids=['other'])
        with tempfile.TemporaryDirectory() as directory,self.assertRaises(AssertionError):b.training_export([s],Path(directory)/'invalid')

if __name__=='__main__':unittest.main()
