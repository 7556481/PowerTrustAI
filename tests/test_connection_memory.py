"""Fixed server token and optional current-browser connection tests."""
from pathlib import Path
from dataclasses import replace
import tempfile,unittest,shutil,subprocess
from backend.local_access import token_for
from backend.config import ServiceConfig
from backend.api import create_app
from fastapi.testclient import TestClient

class ConnectionTests(unittest.TestCase):
 def test_fixed_token_reused_across_restarts_and_model_configuration(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'managed-token';base=ServiceConfig(profile='synthetic_fixture',run_db=Path(directory)/'runs.sqlite3',token_file=path)
   value=token_for(path);before=path.stat().st_mtime_ns
   for config in (base,replace(base,nli_enabled=True)):
    with TestClient(create_app(config)) as client:
     self.assertEqual(client.get('/runs/page/0',headers={'Authorization':'Bearer '+value}).status_code,200)
     self.assertEqual(client.get('/runs/page/0').status_code,401)
     self.assertEqual(client.get('/ui/connection_memory.js').status_code,200)
   self.assertEqual(token_for(path),value);self.assertEqual(path.stat().st_mtime_ns,before)
 def test_invalid_existing_file_is_not_rebuilt(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'token';p.write_text('invalid',encoding='ascii')
   with self.assertRaises(ValueError):token_for(p)
   self.assertEqual(p.read_text(encoding='ascii'),'invalid')
 def test_daily_path_is_independent_of_profile_and_model(self):
  root=ServiceConfig().token_file
  self.assertEqual(root,replace(ServiceConfig(),profile='synthetic_fixture',nli_enabled=True).token_file)
  self.assertEqual(root,ServiceConfig.from_environment(demo=True).token_file)
 @unittest.skipUnless(shutil.which('node'),'optional Node runtime unavailable')
 def test_actual_client_optin_forget_reload_and_401(self):
  root=Path(__file__).resolve().parents[1]
  result=subprocess.run(['node',str(root/'tests/ui_connection_memory_probe.js'),str(root/'backend/static')],capture_output=True,text=True,encoding='utf-8',timeout=15)
  self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
