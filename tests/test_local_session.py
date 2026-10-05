"""Public synthetic fixtures: no real secrets, paid calls or real run store."""
import json,re,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from backend.local_session import LocalSessions
from tests import test_local_api as api_tests
TestClient=api_tests.TestClient

class SessionRegistryTests(unittest.TestCase):
 def test_expiry_single_use_restart_and_digest_only(self):
  with tempfile.TemporaryDirectory() as d:
   r=LocalSessions(Path(d)/'run.db');h=r.issue('http://127.0.0.1:8765')
   nonce=re.search(r'name="ticket" value="([^"]+)"',h)[1]
   self.assertNotIn(nonce,'http://127.0.0.1:8765/session/bootstrap')
   value=r.redeem(nonce);self.assertTrue(r.valid(value));self.assertIsNone(r.redeem(nonce))
   self.assertNotIn(value,r.path.read_text());self.assertNotIn(nonce,r.path.read_text())
   restored=LocalSessions(Path(d)/'run.db');self.assertTrue(restored.valid(value))
   with patch('backend.local_session.time.time',return_value=time.time()+r.lifetime+1):self.assertFalse(restored.valid(value))
   restored.forget(value);self.assertFalse(LocalSessions(Path(d)/'run.db').valid(value))
 def test_expired_ticket_and_database_identity(self):
  with tempfile.TemporaryDirectory() as d:
   r=LocalSessions(Path(d)/'a.db');h=r.issue('http://127.0.0.1:8765');nonce=re.search(r'name="ticket" value="([^"]+)"',h)[1]
   with patch('backend.local_session.time.time',return_value=time.time()+61):self.assertIsNone(r.redeem(nonce))
   self.assertNotEqual(r.cookie,LocalSessions(Path(d)/'b.db').cookie)

@unittest.skipUnless(TestClient,'Optional API dependencies')
class SessionHTTPTests(unittest.TestCase):
 setUp=api_tests.APITests.setUp
 tearDown=api_tests.APITests.tearDown
 def bootstrap(self):
  response=self.client.post('/session/launch',headers=self.headers,json={});self.assertEqual(response.status_code,200)
  nonce=re.search(r'name="ticket" value="([^"]+)"',response.json()['html'])[1]
  response=self.client.post('/session/bootstrap',data={'ticket':nonce},headers={'Origin':'null'},follow_redirects=False)
  self.assertEqual(response.status_code,303);self.assertEqual(response.headers['location'],'/')
  cookie=response.headers['set-cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=strict',cookie)
  return nonce
 def test_cookie_auth_and_wrong_bearer_logout_no_requests(self):
  self.assertEqual(self.client.get('/session').status_code,401)
  self.bootstrap();self.assertEqual(self.client.get('/session').status_code,200)
  self.assertEqual(self.client.get('/runs/page/0').status_code,200)
  self.assertEqual(self.client.get('/session',headers={'Authorization':'Bearer wrong-fixture'}).status_code,401)
  self.assertEqual(self.client.post('/session/launch',json={}).status_code,403)
  self.assertEqual(self.client.post('/session/logout',json={}).status_code,200)
  self.assertEqual(self.client.get('/runs/page/0').status_code,401);self.assertFalse(self.factory.created)
 def test_explicit_remember_upgrade_uses_cookie_not_returned_bearer(self):
  self.assertEqual(self.client.post('/session/remember',json={}).status_code,401)
  r=self.client.post('/session/remember',headers=self.headers,json={})
  self.assertEqual(r.status_code,200);self.assertEqual(set(r.json()),{'version','connected'})
  self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertEqual(self.client.get('/session').status_code,200)
  self.assertEqual(self.client.post('/session/remember',json={}).status_code,403)
 def test_origin_protection_and_nonce_validation(self):
  self.assertEqual(self.client.post('/session/launch',json={}).status_code,401)
  nonce=self.bootstrap()
  self.assertEqual(self.client.post('/session/bootstrap',data={'ticket':nonce}).status_code,401)
  self.assertEqual(self.client.post('/runs',headers={'Origin':'https://evil.example'},json={'mode':'question_answer','question':'fixture'}).status_code,403)
  self.assertEqual(self.client.post('/session/bootstrap',content=b'\xff').status_code,401)
  self.assertFalse(self.factory.created)
 def test_session_survives_application_restart_without_replaying_runs(self):
  self.bootstrap();cookie=dict(self.client.cookies)
  self.client.__exit__(None,None,None)
  from backend.api import create_app
  self.client=TestClient(create_app(self.config,factory=self.factory,access_token='fictional-test-token-not-a-secret'))
  self.client.__enter__();self.client.cookies.update(cookie)
  self.assertEqual(self.client.get('/session').status_code,200);self.assertFalse(self.factory.created)

if __name__=='__main__':unittest.main()
