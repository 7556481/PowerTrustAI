"""Three-member integration for writer admission; never accesses the full source."""
import hashlib,json,os,sqlite3,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import psutil
from tests import test_corpus_index as source_fixture
from rag.storage import KnowledgeStore
from rag.tantivy_members import members
from rag.tantivy_build import CheckpointBuild,InputSpool,atomic,stored_ids
from rag.tantivy_manifest import IndexIdentityError
import evaluation.tantivy_full_stages_v2 as module
class StageChecks(unittest.TestCase):
 def setup_input(self,base,fixture,*,bad=False):
  root=base/'full';root.mkdir();reuse=base/'tantivy-stability-v2/input';reuse.mkdir(parents=True);c=sqlite3.connect(reuse/'spool.sqlite3');c.execute('create table rows(rowid integer primary key,fragment_id text,body_sha text,terms_sha text,terms text)');c.commit();c.close()
  with KnowledgeStore(fixture.p,readonly=True) as source:rows=list(members(source,fixture.k))
  self.assertEqual(len(rows),3);source=Path(fixture.p);identity={'expected':3,'knowledge_version':fixture.k,'source_stat':[source.stat().st_size,source.stat().st_mtime_ns]};atomic(root/'build-identity.json',identity)
  b=CheckpointBuild(root/'build',identity);b.append(rows[:1]);b.close()
  if bad:
   c=sqlite3.connect(root/'build/mapping.sqlite3');c.execute("update rows set body_sha='synthetic-corrupt'");c.commit();c.close()
  sp=InputSpool(root/'spool.sqlite3',identity);sp.append(rows);sp.close();h=hashlib.sha256();h.update(json.dumps(rows[0][:-1]).encode());atomic(root/'recovery-audit-1.json',{'committed':1,'mapping_hash':h.hexdigest()})
  for row in rows[1:]:h.update(json.dumps(row[:-1]).encode())
  atomic(root/'spool-prefix.json',{'n':3,'mapping_hash':h.hexdigest()});atomic(root/'input-complete.json',{'n':3,'mapping_hash':h.hexdigest()});control=root/'control';control.mkdir();plan=control/'plan.json';atomic(plan,{'deadline':time.time()+120});atomic(control/'supervisor-owner.json',{'pid':os.getpid(),'created':psutil.Process().create_time()});return root,plan
 def test_full_spool_precedes_writer_and_reopen_is_complete(self):
  fixture=source_fixture.CorpusTests();fixture.setUp()
  try:
   with tempfile.TemporaryDirectory() as t:
    root,plan=self.setup_input(Path(t),fixture)
    with patch.object(module,'ROOT',root),patch.object(module,'SOURCE',Path(fixture.p)),patch.object(module,'K',fixture.k):module.run('write',plan)
    self.assertEqual(json.loads((root/'built-complete.json').read_text())['n'],3)
    import tantivy
    self.assertEqual(set(stored_ids(tantivy.Index.open(str(root/'build/tantivy')),root/'build/tantivy')),{-1,1,2})
    self.assertIsNone(json.loads((root/'build/budget.json').read_text())['active_since'])
  finally:fixture.tearDown()
 def test_mapping_mismatch_rejected_before_opening_native_writer(self):
  fixture=source_fixture.CorpusTests();fixture.setUp()
  try:
   with tempfile.TemporaryDirectory() as t:
    root,plan=self.setup_input(Path(t),fixture,bad=True)
    with patch.object(module,'ROOT',root),patch.object(module,'SOURCE',Path(fixture.p)),patch.object(module,'K',fixture.k),patch.object(module,'FullCheckpoint') as writer:
     with self.assertRaisesRegex(IndexIdentityError,'mapping metadata'):module.run('write',plan)
     writer.assert_not_called()
    self.assertFalse((root/'built-complete.json').exists());self.assertIsNone(json.loads((root/'build/budget.json').read_text())['active_since'])
  finally:fixture.tearDown()
 def test_native_primary_survives_cleanup_failure(self):
  from types import SimpleNamespace
  fixture=source_fixture.CorpusTests();fixture.setUp()
  try:
   with tempfile.TemporaryDirectory() as t:
    root,plan=self.setup_input(Path(t),fixture);primary=ValueError('first native add error')
    c=sqlite3.connect((root/'build/mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    def fail(rows):raise primary
    def close(primary=None):c.close();return ['later native join error']
    fake=SimpleNamespace(con=c,writer=SimpleNamespace(),mapping_hash=lambda:json.loads((root/'build/checkpoint.json').read_text())['mapping_hash'],append=fail,close=close)
    with patch.object(module,'ROOT',root),patch.object(module,'SOURCE',Path(fixture.p)),patch.object(module,'K',fixture.k),patch.object(module,'FullCheckpoint',return_value=fake):
     with self.assertRaises(ValueError) as caught:module.run('write',plan)
     self.assertIs(caught.exception,primary)
    events=[json.loads(x) for x in (root/'control/events.jsonl').read_text().splitlines()]
    closed=next(x for x in events if x['kind']=='stage_closed')
    self.assertIn('first native add error',closed['primary']);self.assertEqual(closed['cleanup_errors'],['later native join error'])
  finally:fixture.tearDown()
if __name__=='__main__':unittest.main()
