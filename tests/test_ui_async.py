"""Real browser client under delayed response DOM doubles; offline only."""
from pathlib import Path
import shutil
import subprocess
import unittest


class AsyncClientTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Optional Node runtime unavailable')
    def test_slow_auxiliaries_have_bounded_independent_lifecycles(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', 'tests/ui_slow_aux_probe.js'], cwd=root,
                                capture_output=True, text=True, encoding='utf8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Optional Node runtime unavailable')
    def test_old_gets_cannot_replace_new_selection_or_unlock_new_read(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', 'tests/ui_async_probe.js'], cwd=root,
                                capture_output=True, text=True, encoding='utf8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
