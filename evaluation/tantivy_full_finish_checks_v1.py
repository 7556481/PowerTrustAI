import json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import psutil
from rag.tantivy_build import atomic
import evaluation.tantivy_full_finish_v1 as module
class FinishAdmissionChecks(unittest.TestCase):
 def test_expired_budget_does_not_start_acceptance(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);atomic(r/'controller-v3-identity.json',{'pid':os.getpid(),'created':psutil.Process().create_time()});atomic(r/'construction-ledger.json',{'deadline':time.time()-1,'memory_limit':1024**3,'segments':[]})
   with patch.object(module,'ROOT',r),patch.object(module,'supervise') as supervise:
    with self.assertRaises(TimeoutError):module.main()
    supervise.assert_not_called()
   self.assertEqual(json.loads((r/'postbuild/result.json').read_text())['status'],'stopped_requires_inspection')
 def test_dead_controller_without_complete_receipt_does_not_retry(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);atomic(r/'controller-v3-identity.json',{'pid':os.getpid(),'created':0});atomic(r/'construction-ledger.json',{'deadline':time.time()+60,'memory_limit':1024**3,'segments':[]})
   with patch.object(module,'ROOT',r),patch.object(module,'supervise') as supervise:
    with self.assertRaisesRegex(RuntimeError,'without completed build'):module.main()
    supervise.assert_not_called()
if __name__=='__main__':unittest.main()
