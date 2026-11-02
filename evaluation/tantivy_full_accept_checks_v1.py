import json,tempfile,unittest
from pathlib import Path
from evaluation.tantivy_full_accept_v1 import audited_history
from rag.tantivy_manifest import IndexIdentityError
class AdmissionChecks(unittest.TestCase):
 def test_unresolved_failure_or_orphan_blocks_acceptance(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(IndexIdentityError):audited_history(Path(t),{'segments':[{'index':4,'status':'running'}]})
 def test_known_failures_require_explicit_valid_audits(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);segments=[{'index':1,'status':'failed-needs-proof','exit_code':1},{'index':3,'status':'interrupted-preparation-audited','exit_code':None}]
   (r/'recovery-audit-1.json').write_text(json.dumps({'passed':True,'committed':150674,'native_unique_id_set_matches':True,'source_and_spool_prefix_matches':True}))
   (r/'recovery-audit-3.json').write_text(json.dumps({'passed':True,'source_positive_members_match':True,'native_unchanged':True}))
   proof=audited_history(r,{'segments':segments});self.assertEqual(proof['1']['exit_code'],1);self.assertIsNone(proof['3']['exit_code'])
if __name__=='__main__':unittest.main()
