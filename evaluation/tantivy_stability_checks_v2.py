"""Small synthetic checks, without private corpus, model or production service."""
import hashlib,json,os,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from evaluation import tantivy_stability_v2 as v

class Checks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=patch.object(v,'LOCAL',self.root);self.p.start()
 def tearDown(self):self.p.stop();self.tmp.cleanup()
 def test_fresh_build_reopen_and_no_overwrite(self):
  (self.root/'input').mkdir();c=sqlite3.connect(self.root/'input/spool.sqlite3');c.execute('create table rows(position integer primary key,rowid integer unique,fragment_id text,body_sha text,terms_sha text,terms text)')
  for i in range(1500):
   t='voltage condition '+str(i%13);c.execute('insert into rows values(?,?,?,?,?,?)',(i,i+1,'f'+str(i),v.v1.digest(t),v.v1.digest(t),t))
  c.commit();c.close();v.save(self.root/'resource-and-diagnostic-plan.json',dict(writer_heap=128000000,index_threads=1))
  code="from pathlib import Path; import sys; from evaluation import tantivy_stability_v2 as v; v.LOCAL=Path(sys.argv[1]); getattr(v,sys.argv[2])('tiny',1500)"
  for action in ['build_sample','validate_sample']:
   r=subprocess.run([sys.executable,'-X','utf8','-c',code,str(self.root),action],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
  a=v.read(self.root/'tiny/acceptance.json');self.assertTrue(a['complete_id_set']);self.assertEqual(a['n'],1500)
  with self.assertRaises(AssertionError):v.build_sample('tiny',1500)
 def test_commit_keeps_underlying_failure_before_generic_join(self):
  class Writer:
   def add_document(self,_):raise ValueError('writer killed')
   def commit(self):raise OSError('synthetic original worker I/O detail')
   def wait_merging_threads(self):raise RuntimeError('Worker thread failed')
  class Index:
   def writer(self,**_):return Writer()
  (self.root/'DX').mkdir();v.save(self.root/'resource-and-diagnostic-plan.json',dict(diagnostics=[dict(id='DX',heap=32000000,lifecycle='single writer')]))
  (self.root/'fixed-window.jsonl').write_text(json.dumps(dict(rowid=1,terms='synthetic'))+'\n',encoding='utf8')
  with patch.object(v.v1,'index',return_value=Index()):
   with self.assertRaises(ValueError):v.diagnose('DX')
  r=v.read(self.root/'DX/result.json');self.assertIn('original worker I/O',r['commit_detail'][0]['text']);self.assertIn('Worker thread failed',r['join_detail'][0]['text'])
 def test_startup_checkpoint_preserves_sha256(self):
  from evaluation import tantivy_medium_measure_v2 as m
  data=b'synthetic immutable identity';expected=hashlib.sha256(data).hexdigest();calls=[]
  def seal(*_):
   h=hashlib.sha256();h.update(data[:8]);h.update(data[8:]);return h.hexdigest()
  with patch('rag.corpus_index.seal',side_effect=seal),patch.object(m,'checkpoint',side_effect=lambda:calls.append(1)):
   self.assertEqual(m.seal_checked(None,None),expected)
  self.assertEqual(len(calls),2)
 def test_supervision_counts_descendants(self):
  if sys.platform!='win32':self.skipTest('Windows process-tree supervisor')
  v.save(self.root/'resource-and-diagnostic-plan.json',dict(tree_budget=1024**3,disk_limit=1024**3,min_free=1024,deadline=time.time()+60,pressure_available=0))
  original=subprocess.Popen
  def launch(args,**kw):
   args=list(args);args[args.index('evaluation.tantivy_stability_v2')]='evaluation.tantivy_stability_checks_v2';return original(args,**kw)
  with patch.object(v,'health',return_value=True),patch.object(v.subprocess,'Popen',side_effect=launch):r=v.supervise('tree',['spawn'])
  rows=[json.loads(x) for x in (self.root/'tree/resources.jsonl').read_text().splitlines()];self.assertEqual(r['exit_code'],0);self.assertGreaterEqual(max(len(x['processes']) for x in rows),3)
  for row in rows:self.assertEqual(row['tree_rss'],sum(x['rss'] for x in row['processes']))
  self.assertEqual(r['peak_tree_rss'],max(x['tree_rss'] for x in rows))

if __name__=='__main__':
 if sys.argv[1:]==['spawn']:
  held=bytearray(8*1024*1024);p=subprocess.Popen([sys.executable,'-c','import time; b=bytearray(4*1024*1024); time.sleep(.8)']);p.wait()
 else:unittest.main()
