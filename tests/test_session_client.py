import shutil,subprocess,unittest
from pathlib import Path
class SessionClientTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('node'),'Optional Node unavailable')
 def test_actual_cookie_client_reload_and_logout(self):
  root=Path(__file__).resolve().parents[1]
  p=subprocess.run(['node',str(root/'tests/ui_session_probe.js'),str(root/'backend/static/app.js')],capture_output=True,text=True,encoding='utf-8',timeout=15)
  self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
