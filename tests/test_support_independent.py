"""Public offline synthetic_fixture for independent baseline failure isolation."""
import asyncio
import unittest
from evaluation import support_baseline as b
from model_adapter.contracts import ModelSettings, ModelTimeoutError, ModelAuthenticationError, ModelBalanceError
from model_adapter.runtime import ModelClient
from tests.test_support_dataset import sample
from tests.test_support_baseline import FakeAdapter, prediction


class IndependentTests(unittest.TestCase):
    def test_local_bad_output_once_correction_then_next_sample(self):
        a,c=sample('first'),sample('second')
        adapter=FakeAdapter([{'predictions':[]},{'predictions':[]},{'predictions':[prediction(c)]}])
        checkpoints=[]
        r=asyncio.run(b.execute([a,c],ModelClient(adapter,ModelSettings('synthetic_fixture')),checkpoint=checkpoints.append))
        self.assertEqual(r['actual_calls'],3)
        self.assertEqual([p['status'] for p in r['predictions']],['failed','complete'])
        self.assertEqual([x['correction'] for x in r['records']],[False,True,False])
        self.assertEqual(len(checkpoints),2)
        self.assertEqual(r['issues'][0]['scope'],'sample')

    def test_timeout_continues_without_second_attempt(self):
        a,c=sample('first'),sample('second')
        adapter=FakeAdapter([ModelTimeoutError(),{'predictions':[prediction(c)]}])
        r=asyncio.run(b.execute([a,c],ModelClient(adapter,ModelSettings('synthetic_fixture'))))
        self.assertEqual(r['actual_calls'],2)
        self.assertEqual(r['records'][0]['error_code'],'MODEL_TIMEOUT')
        self.assertEqual(r['predictions'][1]['status'],'complete')

    def test_timeout_waits_for_underlying_worker_before_next_sample(self):
        from concurrent.futures import Future
        class Worker(FakeAdapter):
            async def complete(self,request):
                if not self.requests:
                    self.requests.append(request);self._active=Future()
                    asyncio.get_running_loop().call_later(.03,self._active.set_result,None)
                    raise ModelTimeoutError()
                if not self._active.done():raise AssertionError('unsafe worker reuse')
                return await super().complete(request)
        a,c=sample('first'),sample('second')
        r=asyncio.run(b.execute([a,c],ModelClient(Worker([{'predictions':[prediction(c)]}]),ModelSettings('synthetic_fixture'))))
        self.assertEqual(r['actual_calls'],2)
        self.assertEqual(r['predictions'][1]['status'],'complete')

    def test_auth_balance_stop_global(self):
        for exc in (ModelAuthenticationError(),ModelBalanceError()):
            a,c=sample('first'),sample('second')
            r=asyncio.run(b.execute([a,c],ModelClient(FakeAdapter([exc]),ModelSettings('synthetic_fixture'))))
            self.assertEqual(r['actual_calls'],1)
            self.assertEqual(r['issues'][0]['scope'],'global')
            self.assertEqual(r['predictions'][1]['status'],'not_completed')

    def test_three_class_metrics_keep_abstention_and_failed_coverage(self):
        a,c=sample('first'),sample('second')
        for s in (a,c):s['supervision'].update(status='confirmed',label='supported',reviewer_id='synthetic_fixture',basis_ids=['q1'])
        adapter=FakeAdapter([{'predictions':[dict(prediction(a),label='not_assessable',basis_ids=[])]},ModelTimeoutError()])
        r=asyncio.run(b.execute([a,c],ModelClient(adapter,ModelSettings('synthetic_fixture'))))
        m=b.metrics([a,c],r,class_labels=b.LABELS[:3])
        self.assertEqual(m['confirmed_without_prediction'],1)
        self.assertEqual(m['semantic_metrics']['confusion_matrix']['supported']['not_assessable'],1)
        self.assertEqual(m['semantic_metrics']['macro_f1'],0)


if __name__=='__main__':unittest.main()
