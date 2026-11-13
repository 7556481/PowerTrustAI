import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from backend.assembly import ComponentFactory, Bundle, ConfigurationError
from backend.config import ServiceConfig
from backend.managed import ManagedFactory
from tools.managed_overlap import read_managed
from tests.fixture_paths import synthetic_diagnostics
from dataclasses import replace

class ManagedReleaseTests(unittest.TestCase):
    def test_actual_factory_selection_and_trace(self):
        class Client:
            adapter = object()
        def create(*args, **kwargs):
            agents = {key:SimpleNamespace(client=Client()) for key in ('generation','extractor','verification','revision')}
            return Bundle(SimpleNamespace(retriever=None, **agents))
        with synthetic_diagnostics() as temporary:
            config = replace(ServiceConfig(), run_db=Path(temporary)/'runs.sqlite3')
            with patch.object(ComponentFactory, 'create', create):
                for selection in ('component','overlap'):
                    factory = ManagedFactory(config, selection)
                    bundle = factory.create('fixture-'+selection, None)
                    self.assertEqual(getattr(bundle.harness,'fact_domain_retrieval_overlap',False), selection=='overlap')
            events = [json.loads(line) for line in (Path(temporary)/'managed-overlap-events.jsonl').read_text().splitlines()]
            self.assertEqual([row['enabled'] for row in events],[False,True])

    def test_absent_config_is_component_and_bad_config_rejected(self):
        with synthetic_diagnostics() as temporary:
            path=Path(temporary)/'managed.json'
            self.assertEqual(read_managed(path)['factory'],'component')
            path.write_text('{"version":"unknown","factory":"overlap","port":8765}')
            with self.assertRaises(ValueError): read_managed(path)

    def test_policy_guard_and_first_observation(self):
        with synthetic_diagnostics() as temporary:
            config=replace(ServiceConfig(),run_db=Path(temporary)/'runs.sqlite3',verification_schema=14)
            factory=ManagedFactory(config,'overlap')
            with patch.dict('os.environ',{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):
                with self.assertRaises(ConfigurationError):factory.preflight()
            factory.emit('natural','retrieval_start',purpose='domain_review')
            factory.emit('natural','fact_http_worker_begin')
            factory.emit('natural','retrieval_return',purpose='domain_review')
            row=json.loads((Path(temporary)/'overlap-first-natural-observation.json').read_text())
            self.assertTrue(row['overlap_observed'])
            self.assertTrue(row['first_natural_task_observed'])

    def test_graceful_stop_health_socket_closed_is_stopped(self):
        from http.client import RemoteDisconnected
        from tools.managed_overlap import health_at
        with patch('backend.launcher.urlopen',side_effect=RemoteDisconnected()):
            self.assertIsNone(health_at('http://127.0.0.1:8779'))
