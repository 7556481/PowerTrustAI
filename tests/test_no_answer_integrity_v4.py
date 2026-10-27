"""Applicable no-answer completion is separate from substantive audit."""
import asyncio
import json
from dataclasses import replace
import unittest
from unittest.mock import patch
from tests import test_backend_lifecycle_v4 as lifecycle
from tests.test_local_service import task
from backend.service import ApplicationService
from backend.store import StorageError

class NoAnswerTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=lifecycle.LifecycleTests.asyncSetUp
    asyncTearDown=lifecycle.LifecycleTests.asyncTearDown

    async def test_normal_no_answer_complete_applicable_stages_but_not_fact_assessed(self):
        self.factory.mode='no_answer';await self.service.start();rid=await self.service.submit(task())
        await asyncio.wait_for(self.service.queue.join(),2)
        r=self.service.result(rid)
        print(json.dumps(dict(case='no_answer',status=r['execution']['status'],complete=r['execution']['required_stages_complete'],
             integrity=r['decision'].get('execution_integrity'),decision=r['decision']['kind'],rounds=len(r['review_rounds']))))
        self.assertTrue(r['execution']['required_stages_complete'])
        self.assertFalse(r['execution']['all_required_checks_assessed'])
        self.assertEqual(r['decision']['kind'],'needs_information');self.assertEqual(r['review_rounds'],[])

    async def test_sequential_and_graph_no_answer_and_failure_table(self):
        for path in ('sequential','langgraph_v1'):
            for kind in ('no_answer','generation_failure','after_generation_cancel','snapshot_only','ordinary_complete','partial_audit_failure'):
                with self.subTest(path=path,kind=kind):
                    await self.service.stop()
                    config=replace(self.config,execution_path=path)
                    mode='component_error' if kind=='partial_audit_failure' else 'normal' if kind in ('ordinary_complete','generation_failure') else 'no_answer'
                    self.factory=lifecycle.LifecycleFactory(config,mode)
                    self.service=ApplicationService(config,self.store,self.factory)
                    original_create=self.factory.create;generated=asyncio.Event();held=asyncio.Event()
                    def create(rid,observer):
                        bundle=original_create(rid,observer)
                        if kind=='generation_failure':
                            async def bad(inputs):raise RuntimeError('synthetic generation failed')
                            bundle.harness.generation.run=bad
                        if kind=='after_generation_cancel':
                            original=bundle.harness.run
                            async def run(*args,**kw):
                                result=await original(*args,**kw);generated.set();await held.wait();return result
                            bundle.harness.run=run
                        return bundle
                    self.factory.create=create
                    original_checkpoint=self.store.checkpoint
                    def checkpoint(rid,snapshot):
                        original_checkpoint(rid,snapshot)
                        if kind=='snapshot_only' and snapshot['event'].component=='review_not_applicable':
                            raise StorageError('synthetic after snapshot failure')
                    await self.service.start()
                    with patch.object(self.store,'checkpoint',checkpoint):
                        rid=await self.service.submit(task())
                        if kind=='after_generation_cancel':
                            await asyncio.wait_for(generated.wait(),5);self.service.worker.cancel()
                            await asyncio.gather(self.service.worker,return_exceptions=True)
                        await asyncio.wait_for(self.service.queue.join(),5)
                    stored=json.dumps(self.store.get(rid)['result'],sort_keys=True)
                    result=self.service.result(rid);ex=result['execution']
                    expected=kind in ('no_answer','ordinary_complete')
                    self.assertEqual(ex['required_stages_complete'],expected)
                    if kind=='no_answer':
                        self.assertEqual(ex['status'],'finished');self.assertEqual(ex['substantive_audit_status'],'not_applicable')
                        self.assertFalse(ex['all_required_checks_assessed']);self.assertEqual(result['decision']['kind'],'needs_information')
                        self.assertEqual(result['review_rounds'],[]);self.assertEqual(result['findings']['model_fact'],[])
                        stages={v['event']['component'] for v in self.store.events(rid)}
                        self.assertFalse(stages & {'claim_extraction','evidence_verification','power_domain_review'})
                    elif kind in ('after_generation_cancel','snapshot_only'):
                        self.assertTrue(result['no_substantive_answer']);self.assertEqual(ex['status'],'interrupted')
                        self.assertTrue(ex['partial_only']);self.assertFalse(ex['all_required_checks_assessed'])
                        self.assertIn('执行未完成',result['presentation']['reasons'][0])
                    self.assertEqual(json.dumps(self.store.get(rid)['result'],sort_keys=True),stored)
                    print(json.dumps(dict(path=path,case=kind,status=ex['status'],no_answer=result['no_substantive_answer'],
                        complete=ex['required_stages_complete'],checked=ex['all_required_checks_assessed'],
                        decision=result['decision']['kind'] if result['decision'] else None,audit_status=ex['substantive_audit_status'])))


class NoAnswerAPITests(unittest.TestCase):
    def test_normal_no_answer_both_paths_is_not_a_pass(self):
        from fastapi.testclient import TestClient
        from backend.api import create_app
        from backend.config import ServiceConfig
        from pathlib import Path
        import tempfile
        for path in ('sequential','langgraph_v1'):
            with self.subTest(path=path),tempfile.TemporaryDirectory() as directory:
                config=ServiceConfig(profile='synthetic_fixture',execution_path=path,run_db=Path(directory)/'runs.sqlite3',token_file=Path(directory)/'unused')
                factory=lifecycle.LifecycleFactory(config,'no_answer');headers={'Authorization':'Bearer synthetic-no-answer-not-secret'}
                with TestClient(create_app(config,factory=factory,access_token='synthetic-no-answer-not-secret')) as client:
                    rid=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic missing evidence'}).json()['run_id']
                    async def settled():await asyncio.wait_for(client.app.state.service.queue.join(),5)
                    client.portal.call(settled)
                    r=client.get('/runs/'+rid+'/result',headers=headers).json()
                    self.assertTrue(r['execution']['required_stages_complete']);self.assertFalse(r['execution']['all_required_checks_assessed'])
                    self.assertEqual(r['execution']['substantive_audit_status'],'not_applicable')
                    self.assertEqual(r['decision']['kind'],'needs_information');self.assertFalse(r['answer_adoption']['approved'])
                    self.assertEqual(r['review_rounds'],[]);self.assertIn('不适用',r['presentation']['reasons'][0])

