"""The preview uses existing service objects but cannot create paid adapters."""
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from tools.ui_fixture import fixture_app, SyntheticUIFactory
from backend.config import ServiceConfig


class IsolatedPreviewTests(unittest.TestCase):
    def test_temp_store_scenarios_normal_auth_and_no_real_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(ServiceConfig, 'from_environment', side_effect=AssertionError('env forbidden')), \
                 patch('model_adapter.deepseek.create_adapter', side_effect=AssertionError('real adapter forbidden')), \
                 patch('rag.storage.KnowledgeStore', side_effect=AssertionError('index forbidden')):
                with TestClient(fixture_app(directory)) as client:
                    self.assertEqual(client.get('/runs/page/0').status_code, 401)
                    health = client.get('/health').json()
                    self.assertEqual(health['profile'], 'synthetic_fixture')
                    self.assertFalse(client.app.state.service.config.nli_enabled)
                    self.assertEqual(client.app.state.service.config.run_db.parent, Path(directory).resolve())
                    # Ticket remains internal to this test; never printed or archived.
                    html = client.get('/fixture/connect').text
                    ticket = re.search(r'name="ticket" value="([^"]+)"', html).group(1)
                    response = client.post('/session/bootstrap', content='ticket='+ticket,
                                           headers={'content-type':'application/x-www-form-urlencoded'})
                    self.assertEqual(response.status_code, 200)
                    rows = client.get('/runs/page/0').json()
                    self.assertEqual(len(rows['items']), 20)
                    self.assertEqual(len(client.get('/runs/page/20').json()['items']), 4)
                    cases = client.app.state.fixture_cases
                    result = client.get('/runs/'+cases['一次修订与版本1/2']+'/result').json()
                    self.assertEqual({v['version'] for v in result['answer']['versions']}, {1,2})
                    self.assertEqual(client.get('/runs/'+cases['已取消']).json()['status'], 'cancelled')
                    self.assertEqual(client.get('/runs/'+cases['装配执行失败']).json()['status'], 'failed')

    def test_real_configuration_rejected_before_factory_use(self):
        with self.assertRaises(ValueError):
            SyntheticUIFactory(ServiceConfig(profile='real'))
