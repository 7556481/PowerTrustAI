"""v2 continuation, same global96h ledger and explicit prior-failure audit."""
import json,time,sys,sqlite3,os
from pathlib import Path
from evaluation.tantivy_full_build_v1 import ROOT
from evaluation.tantivy_full_controller_v1 import idle
from evaluation.tantivy_supervision_v3 import supervise,Expired
from rag.tantivy_build import atomic,owner
from rag.tantivy_manifest import sha

def main():
 if sys.argv[1:]==['--bounded-recovery-v10']:return bounded_main()
 with owner(ROOT):
  import psutil
  atomic(ROOT/'controller-v3-identity.json',{'pid':psutil.Process().pid,'created':psutil.Process().create_time()})
  ledger_file=ROOT/'construction-ledger.json';ledger=json.loads(ledger_file.read_text());audit=json.loads((ROOT/'recovery-audit-1.json').read_text());assert audit['passed'] and audit['committed']==150674
  if ledger['segments'][-1]['status']=='running':raise RuntimeError('Live/orphan segment must be audited first')
  history=ROOT/'driver-revisions-v2.json'
  if not history.exists():atomic(history,{'reason':'Restore validated prepare-before-writer lifecycle; initial failed stream retained','audit':str(ROOT/'recovery-audit-1.json'),'input_schema_unchanged':True,'effective_code':{p:sha(p) for p in ['evaluation/tantivy_full_stages_v2.py','evaluation/tantivy_full_controller_v2.py']}})
  while time.time()<ledger['deadline'] and not (ROOT/'built-complete.json').exists():
   mode='write' if (ROOT/'input-complete.json').exists() else 'prepare';i=len(ledger['segments']);control=ROOT/'controls'/str(i);control.mkdir(exist_ok=False);logs=ROOT/'segments'/str(i)
   p={'deadline':min(ledger['deadline'],time.time()+4*3600),'kill_on_supervisor_exit':True,'grace_seconds':45,'cwd':str(Path.cwd()),'data_root':str(ROOT),'memory_limit':ledger['memory_limit'],'disk_limit':157*1024**3,'min_free':30*1024**3,'pressure_available':512*1024**2}
   location=ROOT/'native-location-v7.json'
   if location.exists():
    extra=Path(json.loads(location.read_text())['build_root']).resolve()
    if not extra.is_relative_to(ROOT.parent.resolve()):raise RuntimeError('Derived build root outside authorized storage')
    p['extra_data_roots']=[str(extra)]
   atomic(control/'plan.json',p)
   segment={'index':i,'phase':mode,'driver':'v2','start':time.time(),'status':'running','control':str(control)};ledger['segments'].append(segment);atomic(ledger_file,ledger)
   try:rc=supervise(control/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_full_stages_v2',mode,str(control/'plan.json')],logs,idle)
   except Expired:rc=0
   segment.update(end=time.time(),exit_code=rc,status='complete' if rc==0 else 'failed-needs-proof');ledger['wall_elapsed']=time.time()-ledger['start_wall'];atomic(ledger_file,ledger)
   if rc or (logs/'INVALID.json').exists():break
  atomic(ROOT/'controller-v2-result.json',{'built':(ROOT/'built-complete.json').exists(),'ended':time.time(),'models':0,'ledger':str(ledger_file)})
def bounded_main():
 """Same full stages/supervisor; explicit persistent three-fault admission gate."""
 from evaluation.tantivy_checkpoint_control_v10 import HOME,plan,execute,audit_segment,original
 from evaluation.tantivy_checkpoint_recovery_v10 import admit_recovery,classify,dead
 import psutil,shutil
 original()
 with owner(ROOT):
  ready=json.loads((HOME/'controlled/result.json').read_text())
  if not ready.get('passed') or not ready.get('formal_progress_unchanged'):raise RuntimeError('Controlled recovery did not pass')
  policy_path=HOME/'formal-policy.json'
  ledger_file=ROOT/'construction-ledger.json';ledger=json.loads(ledger_file.read_text())
  if policy_path.exists():raise RuntimeError('Existing bounded recovery run must be inspected, never reset/restarted automatically')
  state={'version':10,'entries':[],'limit':3,'original_deadline':ledger['deadline'],'initial_authorization':'User explicitly permits685674 initial admission and counts it in3; previous formal16 cause remains unknown','status':'initial-audit'}
  atomic(policy_path,state)
  atomic(ROOT/'controller-v3-identity.json',{'pid':os.getpid(),'created':psutil.Process().create_time(),'driver':'bounded-v10'})
  reason={'kind':'explicit-initial-admission','previous_formal_failure':'unknown generic worker error; not retroactively labelled replacement fault'}
  before=audit_segment(ROOT/'build',HOME/'formal-initial-audit.json',HOME/'formal-initial-control',ledger['deadline'],[ROOT/'controls/16/process-identities.json'])
  if before['native_committed']!=685674:raise RuntimeError('Authorized initial prefix changed')
  needs_recovery=True;current=None
  try:
   while time.time()<ledger['deadline'] and not (ROOT/'built-complete.json').exists():
    if needs_recovery:
     current=admit_recovery(state,before['native_committed'],ledger['deadline'],reason)
     atomic(policy_path,state)
     archive=HOME/'formal-recoveries'/str(current['number']);archive.mkdir(parents=True,exist_ok=False)
     atomic(archive/'admission-audit.json',before)
     # Preserve the derived failure scene before the original writer may GC it.
     frozen=archive/'before';(frozen/'tantivy').mkdir(parents=True)
     with owner(ROOT/'build'):
      for f in [*(ROOT/'build/tantivy').iterdir(),*[ROOT/'build'/n for n in ('mapping.sqlite3','checkpoint.json','prepared.json','budget.json')]]:
       if not f.is_file() or f.name.endswith('.lock'):continue
       if time.time()>=ledger['deadline']:raise TimeoutError('Original deadline during failure-scene archive')
       from evaluation.tantivy_supervision_v3 import derived_bytes
       resource=plan(ledger['deadline'])
       if derived_bytes(resource)+f.stat().st_size>resource['disk_limit'] or shutil.disk_usage(ROOT).free-f.stat().st_size<resource['min_free']:raise RuntimeError('Failure archive exceeds original space budget')
       dest=frozen/'tantivy'/f.name if f.parent.name=='tantivy' else frozen/f.name
       h=sha(f);shutil.copyfile(f,dest)
       if sha(f)!=h or sha(dest)!=h:raise RuntimeError('Failure scene changed while preserving it')
     current.update(state='writer-admission-ready',audit=str(archive/'admission-audit.json'),before_checkpoint=before['checkpoint'])
     state['status']='running';atomic(policy_path,state);needs_recovery=False
    i=len(ledger['segments']);control=ROOT/'controls'/str(i);p=plan(min(ledger['deadline'],time.time()+4*3600),traced_build=ROOT/'build/tantivy')
    segment={'index':i,'phase':'write','driver':'bounded-v10','start':time.time(),'status':'running','control':str(control),'recovery_number':current['number']}
    ledger['segments'].append(segment);atomic(ledger_file,ledger)
    rc=execute(control,p,'formal-write')
    segment.update(end=time.time(),exit_code=rc,status='complete' if rc==0 else 'failed-needs-proof');ledger['wall_elapsed']=time.time()-ledger['start_wall'];atomic(ledger_file,ledger)
    # Worker, Rust merge threads and observer supervisor have all exited before
    # this fresh-process proof. Native-before-mapping may be rolled forward later.
    before=audit_segment(ROOT/'build',HOME/('after-segment-'+str(i)+'.json'),HOME/('audit-segment-'+str(i)),ledger['deadline'],[control/'process-identities.json'])
    current.update(after_checkpoint=before['checkpoint'],after_native_committed=before['native_committed'],actual_added=before['native_committed']-current['before_committed'],last_audit=str(HOME/('after-segment-'+str(i)+'.json')))
    atomic(policy_path,state)
    if rc:
     if (control/'stop.json').exists():raise RuntimeError('Resource/deadline/observer stop is not a replacement fault recovery')
     invalid=json.loads((control/'logs/INVALID.json').read_text())
     if invalid.get('stop_requested') is not None:raise RuntimeError('Controlled stop cannot be relabelled native fault')
     admission=json.loads((control/'worker-admission.json').read_text())
     events=[json.loads(line) for line in (control/'trace/first-native-errors.jsonl').read_text().splitlines()]
     if any(e.get('pid')!=admission['pid'] or abs(e.get('process_created',0)-admission['created'])>=.001 for e in events):raise RuntimeError('Failure trace process identity mismatch')
     stage_events=[json.loads(line) for line in (control/'events.jsonl').read_text().splitlines()]
     primary=next((e.get('primary') for e in reversed(stage_events) if e.get('kind')=='stage_closed'),None)
     reason=classify(events,primary,ROOT/'build/tantivy');current['failure']=reason;current['state']='failed-after-audited-commits';atomic(policy_path,state)
     needs_recovery=True
    else:
     current['state']='clean-checkpoint';atomic(policy_path,state)
   state.update(status='built-awaiting-full-acceptance' if (ROOT/'built-complete.json').exists() else 'original-deadline-ended',ended=time.time());atomic(policy_path,state)
  except BaseException as error:
   state.update(status='stopped-no-automatic-retry',error=repr(error),ended=time.time());atomic(policy_path,state);raise
  finally:
   atomic(ROOT/'controller-v2-result.json',{'built':(ROOT/'built-complete.json').exists(),'ended':time.time(),'models':0,'bounded_recovery_policy':str(policy_path)})

if __name__=='__main__':
 import os
 main()
