"""Actual isolated ASGI health/admission/readback, no public failure switches."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.config import ServiceConfig
from backend.serialization import dumps
from tests.test_backend_lifecycle_v4 import LifecycleFactory


class LifecycleAPITests(unittest.TestCase):
    def test_cleanup_fault_health_refusal_waiting_and_original_result(self):
        for mode in ('close_error','drain_error'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                p=Path(directory);config=ServiceConfig(profile='synthetic_fixture',run_db=p/'runs.sqlite3',token_file=p/'unused')
                factory=LifecycleFactory(config,mode)
                headers={'Authorization':'Bearer synthetic-lifecycle-not-a-secret'}
                with TestClient(create_app(config,factory=factory,access_token='synthetic-lifecycle-not-a-secret')) as client:
                    self.assertEqual(client.get('/health').json()['status'],'ready')
                    first=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic voltage'}).json()['run_id']
                    async def entered():await asyncio.wait_for(factory.cleanup_entered.wait(),3)
                    client.portal.call(entered);service=client.app.state.service
                    saved=client.portal.call(lambda:dumps(service.store.get(first)['result']))
                    result_before=client.get('/runs/'+first+'/result',headers=headers).json()
                    waiting=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic waiting'}).json()['run_id']
                    client.portal.call(factory.cleanup_release.set)
                    async def settled():
                        await asyncio.wait_for(asyncio.shield(service.worker),3)
                        await asyncio.wait_for(service.queue.join(),1)
                    client.portal.call(settled)
                    health=client.get('/health').json()
                    self.assertEqual(health['status'],'degraded');self.assertTrue(health['storage_healthy'])
                    self.assertFalse(health['active_run']);self.assertEqual(health['queued'],0)
                    self.assertFalse(health['service_lifecycle']['accepting_work'])
                    self.assertNotIn('do not expose',str(health))
                    with patch.object(factory,'preflight',side_effect=AssertionError('must refuse before prepare')):
                        rejected=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic rejected'})
                    self.assertEqual(rejected.status_code,503);self.assertEqual(rejected.json()['detail']['code'],'SERVICE_UNAVAILABLE')
                    state=client.get('/runs/'+waiting,headers=headers).json()
                    self.assertEqual(state['status'],'interrupted');self.assertEqual(state['error_code'],'SERVICE_LIFECYCLE_FAILED')
                    self.assertEqual(client.portal.call(lambda:dumps(service.store.get(first)['result'])),saved)
                    result_after=client.get('/runs/'+first+'/result',headers=headers)
                    self.assertEqual(result_after.status_code,200)
                    for key in ('answer','decision','findings','review_rounds'):
                        self.assertEqual(result_after.json()[key],result_before[key])
                    answer=result_after.json()['answer']['final']
                    self.assertEqual(client.post('/runs/'+first+'/reviews',headers=headers,json=dict(answer_id=answer['answer_id'],answer_version=answer['version'],action='note',note='synthetic feedback')).status_code,201)
                    self.assertEqual(factory.created,[first])
                    # Only after fault assertions: demonstrate safe explicit stop can retry drain.
                    if mode=='drain_error':factory.mode='normal'
