"""Optional framework tests; synthetic fixtures only, never load .env."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
try:
    from fastapi.testclient import TestClient
    from backend.api import create_app
except ImportError:TestClient=None
from backend.config import ServiceConfig
from tests.test_local_service import FixtureFactory

@unittest.skipUnless(TestClient is not None,'Install optional requirements-api.txt for HTTP tests')
class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        self.config=ServiceConfig(profile='synthetic_fixture',run_db=p/'run.db',token_file=p/'token')
        self.headers={'Authorization':'Bearer fictional-test-token-not-a-secret'}
        self.factory=FixtureFactory(self.config)
        self.client=TestClient(create_app(self.config,factory=self.factory,access_token='fictional-test-token-not-a-secret'))
        self.client.__enter__()
    def tearDown(self):self.client.__exit__(None,None,None);self.tmp.cleanup()
    def run_task(self,existing=False):
        data={'mode':'assess_existing' if existing else 'question_answer','question':'synthetic_fixture voltage'}
        if existing:data['existing_answer']='Reactive power affects voltage.'
        r=self.client.post('/runs',headers=self.headers,json=data);self.assertEqual(r.status_code,202)
        rid=r.json()['run_id']
        for _ in range(150):
            if self.client.get('/runs/'+rid,headers=self.headers).json()['status'] not in ('queued','running'):break
            time.sleep(.01)
        return rid

    def test_http_two_modes_trace_result_evidence_and_feedback(self):
        for existing in (False,True):
            rid=self.run_task(existing);base='/runs/'+rid
            result=self.client.get(base+'/result',headers=self.headers).json()
            self.assertTrue(result['execution']['required_stages_complete']);self.assertTrue(self.client.get(base+'/trace',headers=self.headers).json()['events'])
            e=result['evidence'][0];self.assertEqual(self.client.get(base+'/evidence/'+e['evidence_id'],headers=self.headers).json()['text'],e['text'])
            a=result['answer']['final'];f=result['findings']['model_fact'][0]
            feedback={'answer_id':a['answer_id'],'answer_version':a['version'],'finding_id':f['finding_id'],'action':'pending','source':'ai_assisted_user_supervised','note':'synthetic_fixture'}
            self.assertEqual(self.client.post(base+'/reviews',headers=self.headers,json=feedback).status_code,201)
            self.assertEqual(self.client.post(base+'/reviews',headers=self.headers,json=dict(feedback,answer_version=999)).status_code,409)
            self.assertEqual(len(self.client.get(base+'/reviews',headers=self.headers).json()),1)
            self.assertEqual(self.client.get(base+'/result',headers=self.headers).json()['decision'],result['decision'])

    def test_auth_validation_no_key_echo_paths_or_query_tokens(self):
        self.assertEqual(self.client.get('/health').status_code,200)
        self.assertEqual(self.client.post('/runs',json={'mode':'question_answer','question':'fixture'}).status_code,401)
        for key in ('api_key','base_url','db_path','file_path','sql','model_id'):
            r=self.client.post('/runs',headers=self.headers,json={'mode':'question_answer','question':'fixture',key:'fictional-sensitive-value'})
            self.assertEqual(r.status_code,422);self.assertNotIn('fictional-sensitive-value',r.text)
        self.assertEqual(self.client.get('/health?token=fictional',headers=self.headers).status_code,400)
        self.assertEqual(self.client.get('/health',headers={'Host':'evil.example'}).status_code,400)
        self.assertEqual(self.client.post('/runs',headers=self.headers,json={'mode':'assess_existing','question':'fixture'}).status_code,422)

    def test_pending_result_explicit_and_client_does_not_replay(self):
        from agents.fakes import FakeConfig
        self.factory.fake_config=FakeConfig(verification_delay=.1,domain_delay=.1)
        r=self.client.post('/runs',headers=self.headers,json={'mode':'question_answer','question':'fixture'});rid=r.json()['run_id']
        response=self.client.get('/runs/'+rid+'/result',headers=self.headers)
        self.assertIn(response.status_code,(200,202));self.assertIn('execution',response.json())
        time.sleep(.15)
        self.client.get('/runs/'+rid+'/result',headers=self.headers)
        self.assertEqual(len(self.factory.created),1)

    def test_config_unavailable_503_not_simulated_fallback(self):
        with patch.object(self.factory,'preflight',side_effect=__import__('backend.assembly',fromlist=['ConfigurationError']).ConfigurationError('missing')):
            self.assertFalse(self.client.get('/health').json()['configuration_ready'])
            self.assertEqual(self.client.post('/runs',headers=self.headers,json={'mode':'question_answer','question':'fixture'}).status_code,503)
        self.assertEqual(len(self.factory.created),0)

    def test_persisted_result_survives_app_restart(self):
        rid=self.run_task();before=self.client.get('/runs/'+rid+'/result',headers=self.headers).json()
        self.client.__exit__(None,None,None)
        self.client=TestClient(create_app(self.config,factory=self.factory,access_token='fictional-test-token-not-a-secret'));self.client.__enter__()
        after=self.client.get('/runs/'+rid+'/result',headers=self.headers).json()
        self.assertEqual(before,after);self.assertEqual(len(self.factory.created),1)

