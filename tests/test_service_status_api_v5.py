"""Produce the actual v4 pending/confirmed API states consumed by UI v5."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import ServiceConfig
from backend.serialization import dumps
from backend.store import StorageError
from tests.test_backend_lifecycle_v4 import LifecycleFactory


class ServiceStatusAPITests(unittest.TestCase):
    def test_pending_interruption_and_saved_results_are_distinct_without_replay(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(ServiceConfig,'from_environment',side_effect=AssertionError('env forbidden')), \
             patch('model_adapter.deepseek.create_adapter',side_effect=AssertionError('real adapter forbidden')), \
             patch('rag.storage.KnowledgeStore',side_effect=AssertionError('index forbidden')):
            p=Path(directory);config=ServiceConfig(profile='synthetic_fixture',run_db=p/'runs.sqlite3',token_file=p/'unused')
            factory=LifecycleFactory(config,'close_error');headers={'Authorization':'Bearer synthetic-status-not-secret'}
            with TestClient(create_app(config,factory=factory,access_token='synthetic-status-not-secret')) as client:
                first=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic first'}).json()['run_id']
                async def entered():await asyncio.wait_for(factory.cleanup_entered.wait(),3)
                client.portal.call(entered);service=client.app.state.service
                saved=client.portal.call(lambda:dumps(service.store.get(first)['result']))
                waiting=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic waiting'}).json()['run_id']
                original=service.store.mark
                def mark(rid,*args,**kwargs):
                    if rid==waiting:raise StorageError('synthetic waiting interruption write unavailable')
                    return original(rid,*args,**kwargs)
                with patch.object(service.store,'mark',mark):
                    client.portal.call(factory.cleanup_release.set)
                    async def settled():
                        await asyncio.wait_for(asyncio.shield(service.worker),3)
                        await asyncio.wait_for(service.queue.join(),1)
                    client.portal.call(settled)
                health=client.get('/health').json();state=client.get('/runs/'+waiting,headers=headers).json()
                result=client.get('/runs/'+waiting+'/result',headers=headers).json()
                self.assertFalse(health['service_lifecycle']['accepting_work']);self.assertEqual(health['status'],'degraded')
                self.assertEqual(state['status'],'queued');self.assertEqual(state['pending_terminal_status'],'interrupted')
                self.assertFalse(state['persistence_confirmed']);self.assertEqual(result['execution'],state)
                self.assertFalse(result['result_available']);self.assertEqual(factory.created,[first])
                rejected=client.post('/runs',headers=headers,json={'mode':'question_answer','question':'synthetic rejected'})
                self.assertEqual(rejected.status_code,503)
                self.assertEqual(client.get('/runs/page/0',headers=headers).status_code,200)
                saved_result=client.get('/runs/'+first+'/result',headers=headers).json()
                self.assertEqual(saved_result['execution']['status'],'finished');self.assertTrue(saved_result['execution']['persisted_result_available'])
                self.assertEqual(client.portal.call(lambda:dumps(service.store.get(first)['result'])),saved)
                answer=saved_result['answer']['final']
                self.assertEqual(client.post('/runs/'+first+'/reviews',headers=headers,json=dict(answer_id=answer['answer_id'],answer_version=answer['version'],action='note',source='ai_assisted_user_supervised',note='synthetic status feedback')).status_code,201)
                self.assertEqual(len(client.get('/runs/'+first+'/reviews',headers=headers).json()),1)
                self.assertEqual(client.portal.call(lambda:dumps(service.store.get(first)['result'])),saved)
                print(json.dumps(dict(case='actual_isolated_api',health={k:health[k] for k in ('status','reason','storage_healthy','service_lifecycle')},
                    waiting_state={k:state[k] for k in ('status','pending_terminal_status','persistence_confirmed','service_fault_code','persisted_result_available')},
                    waiting_result_available=result['result_available'],finished_status=saved_result['execution']['status'],new_post_status=rejected.status_code,
                    history_read_status=200,feedback_append_status=201,saved_raw_equal=True,component_runs=len(factory.created))))
