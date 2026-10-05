"""Public failure injection verifies diagnostics omit sensitive exception text."""
import unittest
from unittest.mock import patch
from model_adapter.deepseek import DeepSeekAdapter
from model_adapter.contracts import ModelSettings,ModelConnectionError
class NetworkDiagnosticsTests(unittest.TestCase):
 def test_permission_error_retains_only_safe_type_and_stage(self):
  class Connection:
   def connect(self):raise PermissionError(13,'fictional-sensitive-message-never-retain')
   def close(self):pass
  adapter=DeepSeekAdapter(ModelSettings('fixture'))
  try:
   with patch('model_adapter.deepseek.credential_from_environment',return_value='fictional_fixture'),patch('model_adapter.deepseek.http.client.HTTPSConnection',return_value=Connection()):
    with self.assertRaises(ModelConnectionError) as caught:adapter._http(b'{}',1,100)
   d=caught.exception.diagnostic
   self.assertEqual(d['exception_type'],'PermissionError');self.assertEqual(d['stage'],'connect_tls');self.assertEqual(d['errno'],13)
   self.assertNotIn('fictional',str(d));self.assertNotIn('fictional',str(caught.exception))
  finally:adapter.close()
if __name__=='__main__':unittest.main()
