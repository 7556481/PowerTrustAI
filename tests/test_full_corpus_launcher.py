"""Synthetic startup wait; no credentials, HTTP or model calls."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from backend.launcher import open_local
class FullCorpusLauncherTests(unittest.TestCase):
 def test_large_corpus_startup_does_not_expire_at_40_seconds(self):
  with patch('backend.launcher.time.monotonic',side_effect=[0,41,1801]),patch('backend.launcher.health_at',return_value=None) as health,patch('backend.launcher.time.sleep'):
   with self.assertRaises(RuntimeError):open_local(SimpleNamespace(), 'http://127.0.0.1:8765')
   health.assert_called_once()
