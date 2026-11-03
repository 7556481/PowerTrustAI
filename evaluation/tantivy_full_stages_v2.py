"""Audited recovery v2: complete durable input first, writer-only feeding later."""
import json,time,sqlite3,hashlib,sys,os
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K,StreamingSpool,StreamingCheckpoint,prepare,PauseCheckpoint
from rag.tantivy_build import PreparationStage,atomic
from evaluation.tantivy_full_identity_v1 import FullCheckpoint
from rag.storage import KnowledgeStore
from rag.tantivy_members import inventory
from evaluation.tantivy_supervision_v3 import Guard,Expired
from rag.tantivy_manifest import IndexIdentityError

def run(mode,plan_path):
 os.environ['RUST_BACKTRACE']='full';g=Guard(plan_path);identity=json.loads((ROOT/'build-identity.json').read_text());started=time.monotonic();sp=None;owner=None;primary=None;feeding=False;native_owner=False
 diagnostic=g.plan.get('diagnostic_run');phase=lambda name:None
 if diagnostic:
  from evaluation.tantivy_native_trace_v8 import wait_ready,phase
  if ROOT.resolve()==__import__('evaluation.tantivy_full_build_v1',fromlist=['ROOT']).ROOT.resolve():raise RuntimeError('Diagnostic stage cannot write formal checkpoint')
  wait_ready(g.plan);phase('source/input verification')
 import psutil
 supervisor=json.loads(g.path.with_name('supervisor-owner.json').read_text())
 supervisor_pid=supervisor['pid'];supervisor_created=supervisor['created'];last_parent_check=[0.]
 def check():
  now=time.monotonic()
  if now-last_parent_check[0]>=.5:
   try:alive=psutil.Process(supervisor_pid).create_time()==supervisor_created
   except psutil.NoSuchProcess:alive=False
   if not alive:raise Expired('supervisor identity lost; no further work admitted')
   last_parent_check[0]=now
  if time.time()>=g.plan['deadline']-60 or g.path.with_name('stop.json').exists():raise Expired('deadline/stop')
  if g.path.with_name('pause.json').exists():
   if feeding:return
   raise PauseCheckpoint('resource/user pause at safe boundary')
 try:
  check()
  if [SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns]!=identity['source_stat']:raise IndexIdentityError('Source file identity changed')
  with KnowledgeStore(SOURCE,readonly=True,validated_pdf_cache=True) as source:
   from evaluation.tantivy_medium_measure_v2 import seal_checked
   import evaluation.tantivy_medium_measure_v2 as old
   from unittest.mock import patch
   with patch.object(old,'checkpoint',check):seal_checked(source,K)
   inv=inventory(source,K)
   if inv['total']!=identity['expected']:raise IndexIdentityError('Source member total changed')
   source.connection.execute('pragma cache_size=-8192');source.connection.execute('attach database ? as reuse',('file:'+str(ROOT.parent/'tantivy-stability-v2/input/spool.sqlite3').replace('\\','/')+'?mode=ro',))
   remaining=max(0,g.plan['deadline']-time.time()-60)
   owner=PreparationStage(ROOT/'build',identity,total_seconds=96*3600,segment_seconds=remaining,checkpoint=check)
   mapped_db=sqlite3.connect((ROOT/'build/mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
   try:
    mapped_count=mapped_db.execute('select count(*) from rows').fetchone()[0];mapped_hash=hashlib.sha256();pos=0
    for m in mapped_db.execute('select * from rows order by position'):
     if pos%1000==0:check()
     if m[0]!=pos:raise IndexIdentityError('Mapping position gap before writer admission')
     mapped_hash.update(json.dumps(m).encode());pos+=1
   finally:mapped_db.close()
   if diagnostic:
    from types import SimpleNamespace
    input_path=__import__('pathlib').Path(diagnostic['input_spool']).resolve()
    input_con=sqlite3.connect(input_path.as_uri()+'?mode=ro',uri=True)
    sp=SimpleNamespace(con=input_con,close=input_con.close)
   else:sp=StreamingSpool(ROOT/'spool.sqlite3',identity,checkpoint=check)
   sp.con.execute('pragma cache_size=-4096');h=hashlib.sha256();n=0
   audit=json.loads((ROOT/'recovery-audit-1.json').read_text());prefix_file=ROOT/'spool-prefix.json';prefix=json.loads(prefix_file.read_text()) if prefix_file.exists() else None
   pending_file=ROOT/'build/prepared.json';pending=json.loads(pending_file.read_text()) if pending_file.exists() else None
   boundaries={mapped_count};bindings={0:hashlib.sha256().hexdigest()}
   if pending:boundaries.add(pending['end'])
   for row in sp.con.execute('select * from input order by position'):
    check()
    if row[0]!=n or row[1]!=(-(n+1) if n<inv['native'] else n-inv['native']+1) or hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:raise IndexIdentityError('Existing input prefix/hash/order changed')
    if pending and pending['start']<=n<pending['end'] and list(row[:5])!=pending['rows'][n-pending['start']]:raise IndexIdentityError('Prepared input metadata changed')
    h.update(json.dumps(row[:-1]).encode());n+=1
    if n in boundaries:bindings[n]=h.hexdigest()
    if n==audit['committed'] and h.hexdigest()!=audit['mapping_hash']:raise IndexIdentityError('Audited committed input prefix changed')
    if prefix and n==prefix['n'] and h.hexdigest()!=prefix['mapping_hash']:raise IndexIdentityError('Prepared checkpoint digest changed')
   if bindings.get(mapped_count)!=mapped_hash.hexdigest():raise IndexIdentityError('Committed mapping metadata differs from verified input prefix')
   if mode=='prepare':
    while n<identity['expected']:
     check();batch=prepare(source,inv,n,10000,check)
     if not batch:raise IndexIdentityError('Missing source members')
     sp.append(batch)
     for row in batch:h.update(json.dumps(row[:5]).encode())
     n+=len(batch);atomic(ROOT/'spool-prefix.json',{'n':n,'mapping_hash':h.hexdigest(),'identity':identity['knowledge_version']});atomic(ROOT/'progress-v2.json',{'phase':'preparing durable input, no writer','spooled':n,'mapped':150674,'expected':identity['expected'],'wall':time.time(),'segment':str(plan_path)})
    atomic(ROOT/'input-complete.json',{'n':n,'mapping_hash':h.hexdigest()})
   else:
    complete=json.loads((ROOT/'input-complete.json').read_text())
    if n!=identity['expected'] or h.hexdigest()!=complete['mapping_hash']:raise IndexIdentityError('Full input digest mismatch before writer feeding')
    # All source/input/committed metadata checks precede native writer creation.
    owner.close();owner=None;check();remaining=max(0,g.plan['deadline']-time.time()-60)
    phase('native recovery/writer creation')
    owner=FullCheckpoint(ROOT/'build',identity,authorized_full=True,segment_seconds=remaining,checkpoint=check);native_owner=True
    owner.writer.phase=phase
    recovered=owner.con.execute('select count(*) from rows').fetchone()[0]
    if bindings.get(recovered)!=owner.mapping_hash():raise IndexIdentityError('Recovered native commit not bound to verified spool')
    target=diagnostic['target'] if diagnostic else n
    if not recovered<=target<=min(n,recovered+1000000) and diagnostic:raise RuntimeError('Diagnostic member ceiling changed')
    while True:
     check();mapped=owner.con.execute('select count(*) from rows').fetchone()[0]
     if mapped==target:break
     pending=ROOT/'build/prepared.json';limit=min(5000,target-mapped)
     if pending.exists():p=json.loads(pending.read_text());limit=p['end']-p['start']
     batch=sp.con.execute('select * from input where position>=? order by position limit ?',(mapped,limit)).fetchall()
     feeding=True
     phase('feed')
     try:owner.append(batch)
     except BaseException as e:
      atomic(g.path.with_name('native-root-error.json'),{'primary':repr(e),'cause':repr(e.__cause__),'context':repr(e.__context__),'extra_commit_attempted':False})
      raise
     finally:feeding=False
     batch_count=len(batch);del batch
     if 'p' in locals():del p
     atomic(ROOT/'progress-v2.json',{'phase':'writer-only committed checkpoint','spooled':n,'mapped':mapped+batch_count,'expected':n,'wall':time.time(),'segment':str(plan_path)})
    if diagnostic:atomic(ROOT/'diagnostic-complete.json',{'committed':target,'original_progress_unchanged':True,'wall':time.time()})
    else:atomic(ROOT/'built-complete.json',{'n':n,'not_yet_accepted':True})
 except (Expired,TimeoutError,PauseCheckpoint) as e:primary=e;g.event('normal_stage_stop',error=type(e).__name__)
 except BaseException as e:primary=e;g.event('stage_failure',error=repr(e));raise
 finally:
  if sp:sp.close()
  cleanup=[]
  if owner:
   if not native_owner:owner.close()
   else:cleanup=owner.close(primary=primary)
  g.event('stage_closed',mode=mode,primary=repr(primary),cleanup_errors=cleanup,elapsed=time.monotonic()-started)
  if cleanup and (primary is None or isinstance(primary,(Expired,TimeoutError,PauseCheckpoint))):
   raise RuntimeError('Native cleanup failed; primary retained separately; audit required') from primary
  # An already-propagating primary remains the outward exception. Cleanup is
  # separately recorded above; never replace the first failure with join failure.
if __name__=='__main__':run(sys.argv[1],sys.argv[2])
