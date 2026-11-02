import tempfile,hashlib,unittest,json
from contextlib import closing
from pathlib import Path
from rag.tantivy_build import CheckpointBuild
from rag.tantivy_manifest import IndexIdentityError
class BuildTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)/'build';self.identity={'expected':4,'snapshot':'synthetic_fixture','tokenizer':'same-v1','code':'test-v1'}
 def tearDown(self):self.t.cleanup()
 def rows(self,start,end):
  return [[i,i+1,'f'+str(i),'b'*64,hashlib.sha256(('voltage '+str(i)).encode()).hexdigest(),'voltage '+str(i)] for i in range(start,end)]
 def test_normal_checkpoint_and_reopen(self):
  b=CheckpointBuild(self.root,self.identity);b.append(self.rows(0,2));b.close();b=CheckpointBuild(self.root,self.identity);b.append(self.rows(2,4));self.assertEqual(b.con.execute('select count(*) from rows').fetchone()[0],4);b.close()
 def test_native_ahead_mapping_is_recovered_without_duplicate_add(self):
  b=CheckpointBuild(self.root,self.identity)
  with self.assertRaises(RuntimeError):b.append(self.rows(0,2),fail_after_native=True)
  b.close();b=CheckpointBuild(self.root,self.identity);self.assertEqual(b.con.execute('select count(*) from rows').fetchone()[0],2);b.append(self.rows(2,4));b.close()
 def test_wrong_resume_identity_rejected(self):
  b=CheckpointBuild(self.root,self.identity);b.close()
  with self.assertRaises(IndexIdentityError):CheckpointBuild(self.root,{**self.identity,'snapshot':'wrong'})
 def test_single_owner(self):
  b=CheckpointBuild(self.root,self.identity)
  try:
   with self.assertRaises(OSError):CheckpointBuild(self.root,self.identity)
  finally:b.close()
 def test_cumulative_budget_not_reset(self):
  clock=[0];b=CheckpointBuild(self.root,self.identity,total_seconds=2,wall=lambda:clock[0]);clock[0]=3;b.close()
  with self.assertRaises(TimeoutError):CheckpointBuild(self.root,self.identity,total_seconds=100,wall=lambda:4)

 def test_preparation_and_writer_share_total_budget(self):
  from rag.tantivy_build import PreparationStage
  clock=[0];p=PreparationStage(self.root,self.identity,total_seconds=5,segment_seconds=4,wall=lambda:clock[0]);clock[0]=3;p.close()
  b=CheckpointBuild(self.root,self.identity,total_seconds=100,segment_seconds=10,wall=lambda:clock[0]);self.assertEqual(b.deadline,5);clock[0]=6
  with self.assertRaises(TimeoutError):b.admit()
  b.close()
 def test_spool_prefix_survives_reopen(self):
  from rag.tantivy_build import InputSpool
  path=self.root.parent/'spool.sqlite3';a=InputSpool(path,self.identity);a.append(self.rows(0,2));one=a.checkpoint();a.close();b=InputSpool(path,self.identity);self.assertEqual(b.checkpoint(),one);b.append(self.rows(2,4));self.assertEqual(b.checkpoint()['count'],4);b.close()
 def test_mapping_ahead_refused(self):
  b=CheckpointBuild(self.root,self.identity);b.append(self.rows(0,2));b.close()
  import sqlite3
  with closing(sqlite3.connect(self.root/'mapping.sqlite3')) as con:con.execute("insert into rows values(2,3,'f2','b','t')");con.commit()
  with self.assertRaises(IndexIdentityError):CheckpointBuild(self.root,self.identity)
 def test_new_process_acceptance_and_rename_recovery(self):
  import subprocess,sys
  from rag.tantivy_build import finalize_publish
  b=CheckpointBuild(self.root,self.identity);b.append(self.rows(0,4));b.close()
  command='from rag.tantivy_build import accept_complete;import sys,json;accept_complete(sys.argv[1],json.loads(sys.argv[2]))'
  subprocess.run([sys.executable,'-c',command,str(self.root),json.dumps(self.identity)],check=True,capture_output=True,timeout=20)
  target=self.root.parent/'published';self.root.rename(target);self.assertFalse((target/'manifest.json').exists())
  finalize_publish(target,self.identity,knowledge_version='synthetic',source_total=4,scope='full');self.assertTrue((target/'manifest.json').exists())
 def test_mapping_tamper_refused(self):
  b=CheckpointBuild(self.root,self.identity);b.append(self.rows(0,2));b.close()
  import sqlite3
  with closing(sqlite3.connect(self.root/'mapping.sqlite3')) as con:con.execute("update rows set body_sha='changed' where position=0");con.commit()
  with self.assertRaises(IndexIdentityError):CheckpointBuild(self.root,self.identity)
 def test_publish_rejects_incomplete_and_never_overwrites(self):
  from rag.tantivy_build import accept_complete,publish
  from rag.tantivy_manifest import load_manifest
  b=CheckpointBuild(self.root,self.identity);b.append(self.rows(0,2));b.close()
  with self.assertRaises(IndexIdentityError):accept_complete(self.root,self.identity)
  b=CheckpointBuild(self.root,self.identity);b.append(self.rows(2,4));b.close();accept_complete(self.root,self.identity);target=self.root.parent/'published'
  publish(self.root,target,self.identity,knowledge_version='synthetic',source_total=4,scope='full');load_manifest(target/'manifest.json','synthetic',isolated=True)
  with self.assertRaises(IndexIdentityError):load_manifest(target/'manifest.json','synthetic')
  with self.assertRaises(FileExistsError):publish(target,target,self.identity,knowledge_version='synthetic',source_total=4,scope='full')

if __name__=='__main__':unittest.main()
