"""Thin UI API security and durable history, synthetic only."""
import unittest
from tests import test_local_api as api_tests
from agents.fakes import FakeConfig
from core.models import VerificationStatus

@unittest.skipUnless(api_tests.TestClient is not None,'Optional HTTP dependencies unavailable')
class UITests(unittest.TestCase):
    setUp=api_tests.APITests.setUp
    tearDown=api_tests.APITests.tearDown
    run_task=api_tests.APITests.run_task
    def test_static_allowlist_csp_and_cross_origin(self):
        page=self.client.get('/')
        self.assertEqual(page.status_code,200)
        self.assertIn('zh-CN',page.text)
        self.assertIn("script-src 'self'",page.headers['content-security-policy'])
        self.assertNotIn('unsafe-inline',page.headers['content-security-policy'])
        self.assertEqual(page.headers['cache-control'],'no-store')
        self.assertEqual(self.client.get('/ui/app.js').status_code,200)
        self.assertEqual(self.client.get('/ui/anything').status_code,404)
        self.assertEqual(self.client.get('/runs/page/0').status_code,401)
        response=self.client.post('/runs',headers=dict(self.headers,Origin='https://evil.example'),
                                  json={'mode':'question_answer','question':'fixture'})
        self.assertEqual(response.status_code,403)
        self.assertFalse(self.factory.created)

    def test_history_pagination_excludes_inputs_and_config(self):
        for _ in range(21):self.run_task()
        first=self.client.get('/runs/page/0',headers=self.headers).json()
        second=self.client.get('/runs/page/20',headers=self.headers).json()
        self.assertEqual(len(first['items']),20);self.assertEqual(len(second['items']),1)
        self.assertEqual(first['next_offset'],20);self.assertIsNone(second['next_offset'])
        self.assertFalse({r['run_id'] for r in first['items']}&{r['run_id'] for r in second['items']})
        self.assertEqual(set(first['items'][0]),{'run_id','status','created_utc','mode','profile'})
        self.assertEqual(self.client.get('/runs/page/-1',headers=self.headers).status_code,422)

    def test_feedback_targets_preserve_historical_version_bindings(self):
        self.factory.fake_config=FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,VerificationStatus.SUPPORTED))
        rid=self.run_task(True);base='/runs/'+rid
        r=self.client.get(base+'/result',headers=self.headers).json()
        self.assertEqual({a['version'] for a in r['answer']['versions']},{1,2})
        self.assertEqual({f['answer_version'] for f in r['feedback_targets']},{1,2})
        for f in r['feedback_targets']:
            self.assertEqual(self.client.post(base+'/reviews',headers=self.headers,json=dict(f,action='pending')).status_code,201)
            self.assertEqual(self.client.post(base+'/reviews',headers=self.headers,json=dict(f,answer_version=999,action='pending')).status_code,409)

    def test_new_answer_pending_review_is_not_complete_from_old_round(self):
        import time
        self.factory.fake_config=FakeConfig(verification_delay=.4,domain_delay=.01,
            verification_statuses=(VerificationStatus.CONTRADICTED,VerificationStatus.SUPPORTED))
        rid=self.client.post('/runs',headers=self.headers,json={'mode':'assess_existing','question':'fixture',
                              'existing_answer':'Reactive power affects voltage.'}).json()['run_id']
        for _ in range(150):
            r=self.client.get('/runs/'+rid+'/result',headers=self.headers).json()
            if r.get('answer',{}).get('final',{}).get('version')==2 and r['execution']['status']=='running':
                self.assertFalse(r['execution']['required_stages_complete'])
                self.assertFalse(r['execution']['all_required_checks_assessed'])
                break
            time.sleep(.01)
        else:self.fail('Did not observe pending revision review')

