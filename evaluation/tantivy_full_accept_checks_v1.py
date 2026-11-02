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
 def test_small_complete_publication_keeps_quality_gate_closed(self):
  import time
  from unittest.mock import patch
  from tests.test_corpus_index import CorpusTests
  from rag.storage import KnowledgeStore
  from rag.tantivy_members import members
  from rag.tantivy_build import CheckpointBuild,InputSpool,atomic
  from rag.tantivy_manifest import load_manifest
  import evaluation.tantivy_full_accept_v1 as module
  fixture=CorpusTests();fixture.setUp()
  try:
   with tempfile.TemporaryDirectory() as t:
    root=Path(t)
    self.assertTrue(root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
    with KnowledgeStore(fixture.p,readonly=True) as source:rows=list(members(source,fixture.k))
    self.assertEqual(len(rows),3);identity={'expected':3,'source':'synthetic_fixture'}
    b=CheckpointBuild(root/'build',identity);b.append(rows);b.close();sp=InputSpool(root/'spool.sqlite3',identity);sp.append(rows);sp.close()
    atomic(root/'build-identity.json',identity);atomic(root/'construction-ledger.json',{'deadline':time.time()+120,'segments':[{'index':0,'status':'complete','exit_code':0}]});atomic(root/'built-complete.json',{'n':3})
    plan=root/'plan.json';atomic(plan,{'deadline':time.time()+120})
    with patch.object(module,'ROOT',root),patch.object(module,'SOURCE',Path(fixture.p)),patch.object(module,'K',fixture.k):module.run(plan)
    receipt=json.loads((root/'acceptance-complete.json').read_text());self.assertEqual(receipt['n'],3)
    manifest=root/'accepted/manifest.json';self.assertEqual(load_manifest(manifest,fixture.k,isolated=True)['quality_gate'],'unreviewed_fast_delivery_v1')
    with self.assertRaises(IndexIdentityError):load_manifest(manifest,fixture.k)
    self.assertEqual(json.loads((root/'accepted/acceptance.json').read_text())['n'],3)
  finally:fixture.tearDown()
if __name__=='__main__':unittest.main()
