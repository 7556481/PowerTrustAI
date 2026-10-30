import tempfile,json,unittest
from pathlib import Path
from evaluation.tantivy_supervision_v3 import Guard,Writer,Expired
class Checks(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)/'plan.json';self.p.write_text(json.dumps({'deadline':10}));self.clock=[0];self.g=Guard(self.p,wall=lambda:self.clock[0],mono=lambda:self.clock[0],sleep=lambda _:self.clock.__setitem__(0,self.clock[0]+1))
 def tearDown(self):self.t.cleanup()
 def test_before_and_during_feed_and_restart(self):
  self.g.check('start');self.clock[0]=11
  for g in [self.g,Guard(self.p,wall=lambda:11)]:
   with self.assertRaises(Expired):g.check('feed')
 def test_pause_resumes_only_before_expiry(self):
  self.p.with_name('pause.json').write_text('user busy')
  with self.assertRaises(Expired):self.g.check('feed')
  self.assertEqual(self.clock[0],10)
 def test_cleanup_once_primary_survives(self):
  calls=[]
  class Inner:
   def commit(self):calls.append('commit');raise OSError('cleanup commit')
   def wait_merging_threads(self):calls.append('wait');raise OSError('cleanup merge')
  w=Writer(Inner(),self.g);primary=ValueError('primary');self.assertEqual(len(w.close(primary)),2);self.assertEqual(w.close(primary),[]);self.assertEqual(calls,['commit','wait'])
 def test_expired_commit_does_not_consume_before_cleanup(self):
  class Inner:
   def commit(self):return 1
   def wait_merging_threads(self):return None
  w=Writer(Inner(),self.g);self.clock[0]=11
  with self.assertRaises(Expired):w.commit()
  self.assertFalse(w.closed);w.close();self.assertTrue(w.closed)

 def test_stalled_commit_or_merge_has_bounded_grace(self):
  import sys,time
  from evaluation.tantivy_supervision_v3 import supervise
  for phase in ['commit','merge']:
   self.p.with_name('stop.json').unlink(missing_ok=True)
   plan={'deadline':time.time()+.5,'grace_seconds':.3,'cwd':str(Path.cwd()),'data_root':str(self.p.parent),'memory_limit':512*1024**2,'disk_limit':1024**3,'min_free':1024,'pressure_available':0}
   self.p.write_text(json.dumps(plan));out=self.p.parent/phase
   rc=supervise(self.p,[sys.executable,'-c','import time; time.sleep(30)'],out,lambda:True)
   self.assertNotEqual(rc,0);self.assertTrue((out/'INVALID.json').exists())
 def test_pid_reuse_is_not_terminated(self):
  from unittest.mock import patch
  from evaluation.tantivy_supervision_v3 import terminate_verified
  import psutil,os
  with patch.object(psutil.Process,'kill') as kill:
   terminate_verified({os.getpid():psutil.Process().create_time()-100});kill.assert_not_called()
 def test_gap_is_observation_not_resource_success(self):
  self.g.event('observation_gap',seconds=100,unobserved_resources=True)
  event=json.loads(self.p.with_name('events.jsonl').read_text().splitlines()[-1]);self.assertTrue(event['unobserved_resources'])


 def test_segment_address_enumeration_complete(self):
  import tantivy
  from evaluation import tantivy_bounded_v1 as v
  idx=v.index(self.p.parent/'index');w=idx.writer(heap_size=16000000,num_threads=1)
  for i in range(4):w.add_document(tantivy.Document(terms='synthetic',rowid=i))
  w.commit()
  for i in range(4,11):w.add_document(tantivy.Document(terms='other',rowid=i))
  w.commit();w.wait_merging_threads();idx.reload();meta=json.loads((self.p.parent/'index/meta.json').read_text());search=idx.searcher();ids=[]
  for ordinal,seg in enumerate(meta['segments']):
   for doc in range(seg['max_doc']):ids.append(search.doc(tantivy.DocAddress(ordinal,doc))['rowid'][0])
  self.assertEqual(sorted(ids),list(range(11)));self.assertEqual(len(ids),len(set(ids)));self.assertEqual(sum(x['max_doc'] for x in meta['segments']),search.num_docs)


 def test_supervisor_gap_resume_expires_before_more_work(self):
  import time,sys
  from unittest.mock import patch
  from evaluation import tantivy_supervision_v3 as v
  self.clock[0]=time.time();self.p.write_text(json.dumps(dict(deadline=self.clock[0]+5,grace_seconds=.1,cwd=str(Path.cwd()),data_root=str(self.p.parent),memory_limit=512*1024**2,disk_limit=1024**3,min_free=1024,pressure_available=0)))
  g=v.Guard(self.p,wall=lambda:self.clock[0]);
  calls=[0]
  def idle():
   calls[0]+=1
   if calls[0]>1:self.clock[0]+=10
   return True
  with patch.object(v,'Guard',return_value=g):rc=v.supervise(self.p,[sys.executable,'-c','import time;time.sleep(20)'],self.p.parent/'gap',idle)
  self.assertNotEqual(rc,0);events=[json.loads(x) for x in self.p.with_name('events.jsonl').read_text().splitlines()];self.assertTrue(any(x['kind']=='observation_gap' and x['unobserved_resources'] for x in events))
 def test_restarted_supervisor_expires_and_stops_recorded_child(self):
  import subprocess,sys,time,psutil
  from evaluation.tantivy_supervision_v3 import supervise
  child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
  try:
   self.p.write_text(json.dumps(dict(deadline=time.time()-1,grace_seconds=.1)));self.p.with_name('process-identities.json').write_text(json.dumps({child.pid:psutil.Process(child.pid).create_time()}))
   rc=supervise(self.p,['never-launch-expired'],self.p.parent/'restarted',lambda:True);self.assertEqual(rc,1);child.wait(timeout=5)
  finally:
   if child.poll() is None:child.kill();child.wait()


 def test_stage_boundary_pause_refresh(self):
  self.p.with_name('pause.json').write_text('old user task');self.g.check('next phase',refresh=lambda:True);self.assertFalse(self.p.with_name('pause.json').exists())
 def test_unavailable_health_prevents_child_start(self):
  import time
  from evaluation.tantivy_supervision_v3 import supervise
  self.p.write_text(json.dumps(dict(deadline=time.time()+.2)))
  def unavailable():raise OSError('synthetic health unavailable')
  with self.assertRaises(Expired):supervise(self.p,['must-not-launch'],self.p.parent/'unavailable',unavailable)

if __name__=='__main__':unittest.main()
