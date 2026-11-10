"""Durable authorized shard construction; no paid calls or production mutation."""
import json,sys,time,sqlite3,shutil,os,subprocess
from contextlib import closing
from pathlib import Path
import psutil
from rag.tantivy_build import atomic,owner,digest
from rag.tantivy_manifest import sha
from evaluation.tantivy_shard_v16 import HOME,OLD,read

AUTH=HOME/'full-authorization-20261110.json'
STATE=HOME/'continuous-state.json'

def guard():
 a=read(AUTH)
 if time.time()>=a['deadline']:raise TimeoutError('Authorized60h absolute deadline expired')
 if (HOME/'operator-stop.json').exists():raise RuntimeError('Operator stop retained')
 if shutil.disk_usage(HOME).free<a['min_free']:raise RuntimeError('Disk reserve below30GiB')
 return a

def resources():
 from evaluation.tantivy_full_controller_v1 import idle
 while not idle() or psutil.virtual_memory().available<768*1024**2:
  guard();time.sleep(1)
 a=guard();limit=min(2*1024**3,psutil.virtual_memory().available//2)
 if limit<384*1024**2:raise MemoryError('Insufficient memory')
 return a,limit

def run_stage(folder,start,end,role,control):
 from evaluation.tantivy_supervision_v3 import supervise
 from evaluation.tantivy_full_controller_v1 import idle
 from evaluation.tantivy_checkpoint_recovery_v10 import dead
 a,limit=resources();control.mkdir(exist_ok=False)
 physical=(OLD/'build').resolve()
 p={'deadline':min(a['deadline'],time.time()+14400),'grace_seconds':45,'kill_on_supervisor_exit':True,
    'cwd':str(Path.cwd()),'data_root':str(HOME),'extra_data_roots':[str(OLD),str(physical)],
    'memory_limit':limit-64*1024**2,'controller_reserved_bytes':64*1024**2,'disk_limit':a['disk_limit'],'min_free':a['min_free'],'pressure_available':512*1024**2,
    'shard_dir':str(folder),'start':start,'end':end,'role':role,
    'code':{f:sha(f) for f in ['evaluation/tantivy_shard_continuous_v17.py','evaluation/tantivy_shard_v16.py']}}
 if role=='build':
  deps=OLD/'native-diagnostic-v8/deps'
  p['native_trace']={'dependencies':str(deps),'dependency_files':{str(f):sha(f) for f in (deps/'frida').rglob('*') if f.is_file() and f.suffix in ('.pyd','.dll','.py')},'roots':[str(folder/'tantivy')],'directory':str(control/'trace'),'ready_file':str(control/'trace-ready.json'),'errors_only':True,'inject_pos_failure':False}
 atomic(control/'plan.json',p)
 with (control/'coordinator-stdout.log').open('w') as out,(control/'coordinator-stderr.log').open('w') as err:
  child=subprocess.Popen([sys.executable,'-X','utf8','-m','evaluation.tantivy_shard_continuous_v17','supervisor',str(control/'plan.json')],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
  created=psutil.Process(child.pid).create_time();atomic(control/'segment-supervisor.json',{'pid':child.pid,'created':created})
  while child.poll() is None:
   if time.time()>=min(p['deadline']+90,a['deadline']):
    atomic(control/'stop.json',{'reason':'supervisor absolute expiry','wall':time.time()})
    if abs(psutil.Process(child.pid).create_time()-created)<.001:child.terminate()
    child.wait(10);raise TimeoutError('Owned isolated supervisor expired; job closed')
   time.sleep(.2)
  rc=child.returncode
 roster=control/'process-identities.json'
 if roster.exists():
  until=min(p['deadline']+p['grace_seconds'],a['deadline'])
  while True:
   try:dead(read(roster));break
   except RuntimeError:
    guard()
    if time.time()>=until:raise
    identities=[];memory=0
    for pid,created in read(roster).items():
     try:
      process=psutil.Process(int(pid))
      if abs(process.create_time()-created)<.001:
       m=process.memory_info();memory+=max(m.rss,getattr(m,'private',m.rss));identities.append({'pid':int(pid),'created':created,'name':process.name(),'exe':process.exe()})
     except psutil.NoSuchProcess:pass
    if memory>p['memory_limit']:raise MemoryError('Owned observer exit wait exceeds tree budget')
    atomic(control/'waiting-for-owned-exit.json',{'wall':time.time(),'until':until,'owned':identities,'memory':memory,'no_new_writer':True})
    time.sleep(.2)
 return rc

def stage(path):
 from evaluation.tantivy_checkpoint_control_v10 import original
 from evaluation.tantivy_supervision_v3 import Guard
 import evaluation.tantivy_shard_v16 as worker
 p=read(path);original()
 for f,h in p['code'].items():
  if sha(f)!=h:raise RuntimeError('Frozen worker changed')
 guard();worker.START=p['start'];worker.END=p['end'];worker.SHARD=Path(p['shard_dir'])
 if p['role']=='build':worker.build(path)
 else:
  g=Guard(path);worker.AUDIT_CHECK=lambda:g.check('complete shard audit');worker.audit()

def seal(folder,start,end):
 acceptance=read(folder/'acceptance.json');built=read(folder/'built.json')
 if not acceptance['passed'] or acceptance['range']!=[start,end] or built['range']!=[start,end]:raise RuntimeError('Acceptance identity mismatch')
 files={str(f.relative_to(folder)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f,guard)} for f in (folder/'tantivy').rglob('*') if f.is_file() and not f.name.endswith('.lock')}
 files['mapping.sqlite3']={'bytes':(folder/'mapping.sqlite3').stat().st_size,'sha256':sha(folder/'mapping.sqlite3',guard)}
 return {'input_range':[start,end],'count':end-start,'index':str(folder/'tantivy'),'mapping':str(folder/'mapping.sqlite3'),'files':files,'acceptance_sha256':sha(folder/'acceptance.json'),'state':'sealed-isolated-readonly','sealed_wall':time.time()}

def main():
 with owner(HOME):
  a=guard();manifest=read(HOME/'shards.json');cursor=manifest['covered']
  if STATE.exists():
   with (HOME/'controller-history.jsonl').open('a',encoding='utf8') as history:history.write(json.dumps(read(STATE))+'\n')
  if cursor<2825674:raise RuntimeError('Initial sealed inventory missing')
  # Never silently skip changed sealed members on resume.
  for entry in manifest['shards']:
   if 'files' in entry:
    folder=Path(entry['index']).parent
    for f,v in entry['files'].items():
     if sha(folder/f,guard)!=v['sha256']:raise RuntimeError('Sealed shard changed')
  with closing(sqlite3.connect((OLD/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as sp:
   if sp.execute('select identity from meta').fetchone()[0]!=digest(read(OLD/'build-identity.json')):raise RuntimeError('Spool identity mismatch')
  while cursor<a['expected']:
   guard();end=min(cursor+250000,a['expected']);number=len(manifest['shards'])
   for attempt in range(2):
    folder=HOME/f'shard-{number:03d}-attempt-{attempt}';base=HOME/f'control-{number:03d}-{attempt}'
    resuming=folder.exists() or base.with_name(base.name+'-build').exists()
    if resuming:
     from evaluation.tantivy_checkpoint_recovery_v10 import dead
     prior=base.with_name(base.name+'-build');dead(read(prior/'process-identities.json'))
     events=[json.loads(x) for x in (prior/'events.jsonl').read_text().splitlines()]
     closed=next(x for x in reversed(events) if x['kind']=='stage_closed');exited=next(x for x in reversed(events) if x['kind']=='exit')
     built=read(folder/'built.json')
     if exited['code']!=0 or closed['primary'] is not None or closed['cleanup_errors'] or not built['normal_close'] or built['range']!=[cursor,end]:raise RuntimeError('Unsealed stage is not a proven normally closed build')
     if base.with_name(base.name+'-audit').exists():
      prior_audit=base.with_name(base.name+'-audit');dead(read(prior_audit/'process-identities.json'))
      ae=[json.loads(x) for x in (prior_audit/'events.jsonl').read_text().splitlines()]
      if next(x for x in reversed(ae) if x['kind']=='exit')['code']!=0 or not read(folder/'acceptance.json')['passed']:raise RuntimeError('Existing audit failed; preserve evidence')
    atomic(STATE,{'state':'building','start':cursor,'end':end,'attempt':attempt,'folder':str(folder),'wall':time.time(),'deadline':a['deadline']})
    control=base.with_name(base.name+'-build');rc=0 if resuming else run_stage(folder,cursor,end,'build',control)
    if rc:
     from evaluation.tantivy_checkpoint_recovery_v10 import classify
     events=[json.loads(x) for x in (control/'trace/first-native-errors.jsonl').read_text().splitlines()] if (control/'trace/first-native-errors.jsonl').exists() else []
     stages=[json.loads(x) for x in (control/'events.jsonl').read_text().splitlines()]
     primary=next((x.get('primary') for x in reversed(stages) if x['kind']=='stage_closed'),None)
     failure=classify(events,primary,folder/'tantivy');atomic(folder/'classification.json',failure)
     if failure.get('kind')!='identified-managed-atomic-replace-win5' or attempt==1:raise RuntimeError('Build stopped; no further rebuild authorized')
     continue
    atomic(STATE,{'state':'auditing','start':cursor,'end':end,'folder':str(folder),'wall':time.time(),'deadline':a['deadline']})
    audit_control=base.with_name(base.name+'-audit')
    if audit_control.exists():audit_control=base.with_name(base.name+'-audit-revalidate-'+str(time.time_ns()))
    if run_stage(folder,cursor,end,'audit',audit_control):raise RuntimeError('Audit failed; retain field evidence')
    entry=seal(folder,cursor,end);manifest['shards'].append(entry);cursor=end
    manifest.update(covered=cursor,covered_range=[0,cursor],unbuilt=a['expected']-cursor)
    atomic(HOME/'shards.json',manifest);atomic(STATE,{'state':'sealed','covered':cursor,'wall':time.time(),'deadline':a['deadline']});print('SEALED',cursor,'/',a['expected'],flush=True);break
  atomic(STATE,{'state':'construction-complete-awaiting-full-offline-acceptance','covered':cursor,'wall':time.time(),'deadline':a['deadline']})

if __name__=='__main__':
 try:
  if len(sys.argv)==3 and sys.argv[1]=='supervisor':
   from evaluation.tantivy_supervision_v3 import supervise
   from evaluation.tantivy_full_controller_v1 import idle
   path=Path(sys.argv[2])
   def service_idle():
    if (HOME/'operator-stop.json').exists():atomic(path.with_name('stop.json'),read(HOME/'operator-stop.json'))
    return idle()
   raise SystemExit(supervise(path,[sys.executable,'-X','utf8','-m','evaluation.tantivy_shard_continuous_v17','stage',str(path)],path.parent/'logs',service_idle))
  elif len(sys.argv)==3 and sys.argv[1]=='stage':stage(sys.argv[2])
  elif sys.argv[1:]==['run']:main()
  else:raise SystemExit('run | stage PLAN')
 except BaseException as e:
  if sys.argv[1:]==['run']:
   atomic(STATE,{'state':'stopped','error':repr(e),'wall':time.time(),'deadline':read(AUTH)['deadline']})
  raise
