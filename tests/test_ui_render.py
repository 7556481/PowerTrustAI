"""Execute actual UI in a public DOM fixture; never submit a paid task."""
from pathlib import Path
import shutil
import subprocess
import unittest

class RenderTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'optional Node runtime unavailable for actual-script DOM probe')
    def test_saved_retrieval_config_and_downstream_render(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run(['node',str(root/'tests/ui_render_probe.js'),str(root/'backend/static/app.js')],
                              capture_output=True,text=True,encoding='utf8',timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
