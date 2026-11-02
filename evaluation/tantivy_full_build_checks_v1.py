import hashlib,json,tempfile,unittest,sqlite3
from pathlib import Path
from evaluation.tantivy_full_build_v1 import StreamingCheckpoint,StreamingSpool
from rag.tantivy_build import CheckpointBuild,accept_complete
class FullBuildChecks(unittest.TestCase):
 def test_streaming_hash_equals_original_after_append_and_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'build';identity={'expected':4,'source':'synthetic_fixture'}
   def rows(a,b):return [[i,i+1,'f'+str(i),'b'*64,hashlib.sha256(('voltage '+str(i)).encode()).hexdigest(),'voltage '+str(i)] for i in range(a,b)]
   b=StreamingCheckpoint(root,identity);b.append(rows(0,2));b.append(rows(2,4));self.assertEqual(b.mapping_hash(),CheckpointBuild.mapping_hash(b));b.close()
   b=StreamingCheckpoint(root,identity);self.assertEqual(b.mapping_hash(),CheckpointBuild.mapping_hash(b));b.close();self.assertTrue(accept_complete(root,identity)['passed'])
 def test_recovery_native_commit_before_mapping(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'build';identity={'expected':1};text='synthetic_fixture';row=[[0,-1,'f','b',hashlib.sha256(text.encode()).hexdigest(),text]]
   b=StreamingCheckpoint(root,identity)
   with self.assertRaises(RuntimeError):b.append(row,fail_after_native=True)
   b.close();b=StreamingCheckpoint(root,identity);self.assertEqual(b.con.execute('select count(*) from rows').fetchone()[0],1);b.close()
 def test_prepare_matches_original_three_member_fixture(self):
  from tests import test_corpus_index as fixture
  from rag.storage import KnowledgeStore
  from rag.tantivy_members import inventory,members
  from evaluation import tantivy_full_build_v1 as mod
  from unittest.mock import patch
  f=fixture.CorpusTests();f.setUp()
  try:
   assert Path(f.p).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
   cache=Path(f.tmp.name)/'reuse.sqlite3';c=sqlite3.connect(cache);c.execute('create table rows(rowid integer primary key,fragment_id text,body_sha text,terms_sha text,terms text)');c.commit();c.close()
   with KnowledgeStore(f.p,readonly=True) as st:
    inv=inventory(st,f.k);self.assertEqual(inv['total'],3);st.connection.execute('attach database ? as reuse',(str(cache),))
    expected=list(members(st,f.k))
    with patch.object(mod,'K',f.k):actual=mod.prepare(st,inv,0,10,lambda:None)+mod.prepare(st,inv,1,10,lambda:None)
    self.assertEqual([tuple(r) for r in actual],expected)
  finally:f.tearDown()
 def test_spool_reopen_same_order(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'spool.sqlite3';id={'source':'synthetic_fixture'};text='voltage';row=[0,-1,'f','b',hashlib.sha256(text.encode()).hexdigest(),text]
   s=StreamingSpool(p,id);s.append([row]);before=s.checkpoint();s.close();s=StreamingSpool(p,id);self.assertEqual(before,s.checkpoint());s.close()
if __name__=='__main__':unittest.main()
