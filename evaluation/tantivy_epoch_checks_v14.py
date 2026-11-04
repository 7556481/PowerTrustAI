"""Real Windows file-sharing and original writer integration, no model calls."""
import hashlib,json,os,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import psutil
from evaluation.tantivy_input_epoch_v14 import Lease,WorkerLease,InputEpoch
from rag.tantivy_build import atomic,CheckpointBuild,InputSpool
from rag.tantivy_manifest import sha,IndexIdentityError

class EpochChecks(unittest.TestCase):
 def test_real_share_locks_and_worker_duplication(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source';p.write_bytes(b'unchanged input');lease=Lease()
   try:
    row=lease.pin(p);receipt={'pid':os.getpid(),'created':psutil.Process().create_time(),'deadline':time.time()+60,'files':[row]}
    rp=Path(d)/'receipt.json';atomic(rp,receipt);receipt.update(receipt_path=str(rp),receipt_sha256=sha(rp))
    for action in (lambda:p.write_bytes(b'wrong'),lambda:p.unlink(),lambda:os.replace(p,Path(d)/'moved')):
     with self.assertRaises(PermissionError):action()
    code='import json,sys;from evaluation.tantivy_input_epoch_v14 import WorkerLease; r=json.loads(sys.argv[1]);w=WorkerLease(r);w.check(force=True);w.close();print("duplicated")'
    r=subprocess.run([sys.executable,'-X','utf8','-c',code,json.dumps(receipt)],capture_output=True,text=True,timeout=20)
    self.assertEqual(r.returncode,0,r.stderr);self.assertIn('duplicated',r.stdout)
    self.assertEqual(p.read_bytes(),b'unchanged input')
    with self.assertRaises(IndexIdentityError):WorkerLease(dict(receipt,created=receipt['created']+1))
    atomic(rp,{'modified':True})
    with self.assertRaises(IndexIdentityError):WorkerLease(receipt)
    lease.close()
    with self.assertRaises(OSError):WorkerLease(receipt)
   finally:lease.close()
   p.write_bytes(b'closed lease permits write')

 def test_controller_exit_invalidates_duplicated_handles(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input';p.write_text('test');rp=Path(d)/'r.json'
   code='import sys,os,time,psutil;from pathlib import Path;from evaluation.tantivy_input_epoch_v14 import Lease;from rag.tantivy_build import atomic; l=Lease();r={"pid":os.getpid(),"created":psutil.Process().create_time(),"deadline":time.time()+60,"files":[l.pin(Path(sys.argv[1]))]};atomic(Path(sys.argv[2]),r);input();l.close()'
   child=subprocess.Popen([sys.executable,'-X','utf8','-c',code,str(p),str(rp)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   lease=None
   try:
    until=time.time()+10
    while not rp.exists() and time.time()<until:time.sleep(.05)
    receipt=json.loads(rp.read_text());receipt.update(receipt_path=str(rp),receipt_sha256=sha(rp));lease=WorkerLease(receipt)
    child.communicate('\n',timeout=10)
    with self.assertRaises(IndexIdentityError):lease.check(force=True)
   finally:
    if lease:lease.close()
    if child.poll() is None:child.terminate();child.wait()

 def test_same_epoch_two_original_writer_reopens(self):
  import evaluation.tantivy_epoch_writer_v14 as worker
  from evaluation.tantivy_checkpoint_recovery_v10 import audit
  with tempfile.TemporaryDirectory() as d:
   from rag.storage import KnowledgeStore
   root=Path(d);source=root/'source.sqlite3'
   with KnowledgeStore(source):pass
   Path(str(source)+'.manifest.json').write_text('{}')
   identity={'expected':6,'source_stat':[source.stat().st_size,source.stat().st_mtime_ns]};atomic(root/'build-identity.json',identity)
   rows=[[i,-i-1,'f'+str(i),'body',hashlib.sha256(b'fixed terms').hexdigest(),'fixed terms'] for i in range(6)]
   spool=InputSpool(root/'spool.sqlite3',identity);spool.append(rows);proof=spool.checkpoint();spool.close()
   atomic(root/'input-complete.json',{'n':6,'mapping_hash':proof['prefix_hash']})
   b=CheckpointBuild(root/'build',identity,total_seconds=300,segment_seconds=120);b.append(rows[:2]);b.close()
   with patch('evaluation.tantivy_medium_measure_v2.seal_checked') as sealing,patch('rag.tantivy_members.inventory',return_value={'native':674,'total':6}):
    epoch=InputEpoch(root,source,'synthetic',time.time()+300)
    try:
     for turn in (1,2):
      proof_path=root/('proof'+str(turn)+'.json');audit(root/'build',identity,root/'spool.sqlite3',proof_path)
      control=root/str(turn);control.mkdir();plan=control/'plan.json'
      atomic(plan,{'deadline':time.time()+200,'input_epoch':epoch.receipt,'recovery_proof':str(proof_path)})
      atomic(control/'supervisor-owner.json',{'pid':os.getpid(),'created':psutil.Process().create_time()})
      with patch.object(worker,'ROOT',root),patch.object(worker,'wait_ready'),patch.object(worker,'phase'):
       worker.run(plan)
      self.assertEqual(json.loads((root/'build/checkpoint.json').read_text())['count'],6)
     self.assertEqual(sealing.call_count,1)
     audit(root/'build',identity,root/'spool.sqlite3',root/'final.json')
    finally:epoch.close()

if __name__=='__main__':unittest.main()
