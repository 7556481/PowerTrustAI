import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
import psutil
class JobChecks(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows ownership boundary')
 def test_abrupt_supervisor_exit_kills_only_owned_child(self):
  with tempfile.TemporaryDirectory() as d:
   file=Path(d)/'owned.json';script=Path(d)/'supervisor.py'
   script.write_text("from evaluation.tantivy_owned_job_v1 import OwnedJob\nimport subprocess,sys,os,json,time,psutil\nfrom pathlib import Path\nj=OwnedJob();p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);j.assign(p)\nPath(sys.argv[1]).write_text(json.dumps({'pid':p.pid,'created':psutil.Process(p.pid).create_time()}))\ntime.sleep(.2);os._exit(17)\n".replace('\n','\n'))
   # -c preserves repository imports; temporary script owns no service process.
   runner=subprocess.Popen([sys.executable,'-c',script.read_text(),str(file)])
   self.assertEqual(runner.wait(timeout=10),17);identity=json.loads(file.read_text());deadline=time.monotonic()+5
   while time.monotonic()<deadline:
    try:
     p=psutil.Process(identity['pid'])
     if p.create_time()!=identity['created'] or not p.is_running():break
    except psutil.NoSuchProcess:break
    time.sleep(.05)
   else:self.fail('Owned child survived abrupt supervisor exit')
   self.assertTrue(psutil.Process(os.getpid()).is_running())
if __name__=='__main__':unittest.main()
