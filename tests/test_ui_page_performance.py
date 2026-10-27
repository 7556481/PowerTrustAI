"""Nonempty bounded page fixture preserves auth, bindings and isolated hooks."""
from pathlib import Path
import tempfile
import re
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.config import ServiceConfig
from tools.ui_page_performance import performance_app, SAMPLES


class PageFixtureTests(unittest.TestCase):
    def test_fixed_nonempty_samples_and_measurement_only_script(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(ServiceConfig,'from_environment',side_effect=AssertionError('env forbidden')), \
             patch('model_adapter.deepseek.create_adapter',side_effect=AssertionError('adapter forbidden')), \
             patch('rag.storage.KnowledgeStore',side_effect=AssertionError('index forbidden')):
            with TestClient(performance_app(directory,'backend/static/app.js')) as client:
                self.assertEqual(client.get('/runs/'+SAMPLES[0]+'/result').status_code,401)
                samples=client.app.state.page_samples
                self.assertLess(samples['database_bytes'],20*1024*1024)
                ticket=re.search(r'name="ticket" value="([^"]+)"',client.get('/fixture/connect').text).group(1)
                client.post('/session/bootstrap',content='ticket='+ticket,headers={'content-type':'application/x-www-form-urlencoded'})
                for sample in samples['samples']:
                    self.assertTrue(all(sample[k]>0 for k in ('events','answers','findings','evidence','reviews')))
                    result=client.get('/runs/'+sample['run_id']+'/result').json()
                    for row in client.get('/runs/'+sample['run_id']+'/reviews').json():
                        self.assertTrue(any(a['answer_id']==row['answer_id'] and a['version']==row['answer_version'] for a in result['answer']['versions']))
                script=client.get('/ui/app.js')
                self.assertIn('fixtureMetrics',script.text)
                self.assertNotIn('eval(',script.text)
                self.assertIn("script-src 'self'",script.headers['content-security-policy'])
                self.assertNotIn('fixtureMetrics',Path('backend/static/app.js').read_text(encoding='utf8'))
