"""Explicit isolated 250k shard experiment; never resumes the formal writer."""
import hashlib,json,os,sqlite3,sys,time,uuid
from pathlib import Path
from rag.tantivy_build import atomic,create_index,stored_ids
from rag.tantivy_manifest import sha

START=2575674
END=2825674
OLD=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1')
HOME=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-shards-v16')
SHARD=HOME/'shard-01'
AUDIT_CHECK=lambda:None

def read(p):return json.loads(Path(p).read_text())

def build(plan):
 import tantivy
 from evaluation.tantivy_supervision_v3 import Guard
 from evaluation.tantivy_native_trace_v8 import wait_ready,phase
 g=Guard(plan);wait_ready(g.plan);folder=SHARD;folder.mkdir(exist_ok=False)
 con=sqlite3.connect(folder/'mapping.sqlite3');source=sqlite3.connect((OLD/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
 con.execute('create table rows(position integer primary key,rowid integer unique,fragment_id text,body_sha text,terms_sha text)')
 idx=create_index(folder/'tantivy');writer=None;primary=None;cleanup=[];n=0;h=hashlib.sha256();started=time.time()
 try:
  writer=idx.writer(heap_size=128000000,num_threads=1)
  for row in source.execute('select * from input where position>=? and position<? order by position',(START,END)):
   if n%1000==0:g.check('feed')
   assert row[0]==START+n and hashlib.sha256(row[5].encode()).hexdigest()==row[4]
   con.execute('insert into rows values(?,?,?,?,?)',row[:5]);h.update(json.dumps(row[:5]).encode());writer.add_document(tantivy.Document(terms=row[5],rowid=row[1]));n+=1
   if n%1000==0:atomic(folder/'progress.json',{'fed_not_committed':n,'wall':time.time()})
  assert n==END-START
  g.check('commit');phase('commit');t=time.time();opstamp=writer.commit();commit=time.time()-t
  phase('merge_wait/close');t=time.time();w=writer;writer=None;w.wait_merging_threads();merge=time.time()-t
  con.commit();atomic(folder/'built.json',{'n':n,'range':[START,END],'mapping_hash':h.hexdigest(),'opstamp':opstamp,'seconds':time.time()-started,'commit_seconds':commit,'merge_seconds':merge,'commits':1,'normal_close':True})
 except BaseException as e:
  primary=repr(e);atomic(folder/'primary-error.json',{'error':primary,'fed':n,'wall':time.time()});raise
 finally:
  if writer is not None:
   try:writer.wait_merging_threads()
   except BaseException as e:cleanup.append(repr(e))
  source.close();con.close();g.event('stage_closed',primary=primary,cleanup_errors=cleanup)

def audit():
 import tantivy
 from evaluation.tantivy_full_build_v1 import SOURCE,K
 from rag.storage import KnowledgeStore
 folder=SHARD;built=read(folder/'built.json');n=0;h=hashlib.sha256();started=time.time()
 sp=sqlite3.connect((OLD/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);mapping=sqlite3.connect((folder/'mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);seen=sqlite3.connect((folder/('audit-seen-'+uuid.uuid4().hex+'.sqlite3')).resolve().as_uri(),uri=True)
 try:
  with KnowledgeStore(SOURCE,readonly=True,validated_pdf_cache=True) as store:
   for row in mapping.execute('select * from rows order by position'):
    if n%1000==0:AUDIT_CHECK()
    expected=sp.execute('select * from input where position=?',(START+n,)).fetchone();assert row==expected[:5]
    assert hashlib.sha256(expected[5].encode()).hexdigest()==row[4]
    e=store.evidence(row[2],K);assert hashlib.sha256(e.text.encode()).hexdigest()==row[3]
    h.update(json.dumps(row).encode());n+=1
  assert n==END-START and h.hexdigest()==built['mapping_hash']
  seen.execute('create table seen(rowid integer primary key)');idx=tantivy.Index.open(str(folder/'tantivy'));batch=[];count=0
  for rid in stored_ids(idx,folder/'tantivy'):
   batch.append((rid,));count+=1
   if count%1000==0:AUDIT_CHECK()
   if len(batch)==1000:seen.executemany('insert into seen values(?)',batch);batch=[]
  if batch:seen.executemany('insert into seen values(?)',batch)
  seen.execute('attach database ? as mapped',((folder/'mapping.sqlite3').resolve().as_uri()+'?mode=ro',))
  assert count==END-START and not seen.execute('select rowid from seen except select rowid from mapped.rows limit 1').fetchone() and not seen.execute('select rowid from mapped.rows except select rowid from seen limit 1').fetchone()
  atomic(folder/'acceptance.json',{'passed':True,'complete_id_set':True,'n':n,'range':[START,END],'mapping_hash':h.hexdigest(),'all_bodies_terms_ids_verified':True,'new_process':True,'seconds':time.time()-started})
 finally:sp.close();mapping.close();seen.close()

def launch():
 import psutil
 from evaluation.tantivy_full_controller_v1 import idle
 from evaluation.tantivy_supervision_v3 import supervise
 cp=read(OLD/'build/checkpoint.json');proof=read(OLD/'checkpoint-recovery-v10/user-manual-once-17/after-audit.json')
 assert cp==proof['checkpoint'] and proof['passed'] and cp['count']==START
 assert idle(),'User service busy'
 HOME.mkdir(exist_ok=False);control=HOME/'build-control';control.mkdir()
 available=psutil.virtual_memory().available;limit=min(2*1024**3,available//2);assert limit>=384*1024**2
 deps=OLD/'native-diagnostic-v8/deps'
 p={'deadline':time.time()+4*3600,'grace_seconds':45,'kill_on_supervisor_exit':True,'cwd':str(Path.cwd()),'data_root':str(HOME),'memory_limit':limit,'disk_limit':160*1024**3,'min_free':30*1024**3,'pressure_available':512*1024**2,'native_trace':{'dependencies':str(deps),'dependency_files':{str(f):sha(f) for f in (deps/'frida').rglob('*') if f.is_file() and f.suffix in ('.pyd','.dll','.py')},'roots':[str(HOME/'shard-01/tantivy')],'directory':str(control/'trace'),'ready_file':str(control/'trace-ready.json'),'errors_only':True,'inject_pos_failure':False}}
 atomic(control/'plan.json',p);atomic(HOME/'scope.json',{'authorization':'2026-11-10 first250k only; no formal recovery18','start':START,'end':END,'old_checkpoint':cp,'input_identity':read(OLD/'build-identity.json'),'memory_available':available,'memory_limit':limit,'writer_heap':128000000,'threads':1,'commit':'once at end then wait_merging_threads once','code_sha256':sha(__file__),'models':0})
 rc=supervise(control/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_shard_v16','worker',str(control/'plan.json')],control/'logs',idle)
 print('build supervisor exit',rc,flush=True);return rc

if __name__=='__main__':
 if sys.argv[1:] == ['launch']:raise SystemExit(launch())
 elif sys.argv[1:] == ['audit']:audit()
 elif len(sys.argv)==3 and sys.argv[1]=='worker':build(sys.argv[2])
 else:raise SystemExit('launch | audit | worker PLAN')
