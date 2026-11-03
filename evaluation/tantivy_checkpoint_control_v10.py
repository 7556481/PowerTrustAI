"""Small recovery admission helpers around the existing full-build supervisor.

Original Tantivy wheel only. No compatibility DLL and no writer retry loop.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K
from evaluation.tantivy_checkpoint_recovery_v10 import dead
from rag.tantivy_build import atomic,owner
from rag.tantivy_manifest import sha

HOME=ROOT/'checkpoint-recovery-v10'
MODULE='evaluation.tantivy_checkpoint_control_v10'
ORIGINAL_PYD='69c2221c2ce1a896bf7b493147a750b5501f5aaebdfdd0dbbc176fc483ef8702'
FILES=['evaluation/tantivy_checkpoint_recovery_v10.py','evaluation/tantivy_checkpoint_control_v10.py','evaluation/tantivy_full_controller_v2.py','evaluation/tantivy_full_stages_v2.py','evaluation/tantivy_full_identity_v1.py','evaluation/tantivy_native_trace_v8.py','evaluation/tantivy_native_trace_v8.js','evaluation/tantivy_supervision_v3.py','rag/tantivy_build.py']


def original():
    import tantivy.tantivy as extension
    import importlib.metadata
    if importlib.metadata.version('tantivy')!='0.27.0' or sha(extension.__file__)!=ORIGINAL_PYD:
        raise RuntimeError('Original Tantivy0.27 binary identity mismatch')


def plan(until,*,traced_build=None):
    l=json.loads((ROOT/'construction-ledger.json').read_text())
    if time.time()>=min(until,l['deadline']):raise TimeoutError('Original deadline expired')
    # This lightweight controller stays outside the supervised segment tree.
    # Reserve64MiB inside, not in addition to, the original850MiB tree cap.
    m=psutil.Process().memory_info()
    if max(m.rss,getattr(m,'private',m.rss))>64*1024**2:raise MemoryError('Recovery controller exceeds its reserved memory')
    p={'deadline':min(until,l['deadline']),'grace_seconds':45,'kill_on_supervisor_exit':True,'cwd':str(Path.cwd()),'data_root':str(ROOT),
       'extra_data_roots':[str((ROOT/'build').resolve())],'memory_limit':l['memory_limit']-64*1024**2,'controller_reserved_bytes':64*1024**2,
       'disk_limit':157*1024**3,'min_free':30*1024**3,'pressure_available':512*1024**2,'frozen_code':{n:sha(n) for n in FILES}}
    if traced_build:
        deps=ROOT/'native-diagnostic-v8/deps'
        p['native_trace']={'dependencies':str(deps),'dependency_files':{str(f):sha(f) for f in (deps/'frida').rglob('*') if f.is_file() and f.suffix in ('.pyd','.dll','.py')},
                           'roots':[str(Path(traced_build).resolve())],'errors_only':True,'inject_pos_failure':False}
    return p


def execute(control,p,role):
    """One isolated supervisor process per segment; observers also exit before audit."""
    control=Path(control);control.mkdir(parents=True,exist_ok=False)
    if p.get('native_trace'):
        p['native_trace'].update(directory=str(control/'trace'),ready_file=str(control/'trace-ready.json'))
    atomic(control/'plan.json',p)
    with (control/'coordinator-stdout.log').open('w') as out,(control/'coordinator-stderr.log').open('w') as err:
        child=subprocess.Popen([sys.executable,'-X','utf8','-m',MODULE,'segment',str(control/'plan.json'),role],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        proc=psutil.Process(child.pid);created=proc.create_time();atomic(control/'segment-supervisor.json',{'pid':child.pid,'created':created})
        while child.poll() is None:
            if time.time()>=p['deadline']+60:
                if abs(psutil.Process(child.pid).create_time()-created)<.001:
                    # Closing this verified supervisor closes its owned worker Job.
                    child.terminate()
                child.wait(10);raise TimeoutError('Segment supervisor exceeded its deadline plus grace')
            time.sleep(.2)
        rc=child.returncode
    roster=control/'process-identities.json'
    if roster.exists():
        # Give the original Frida client normal shutdown time; never kill a
        # process merely because an observer is slow. Live ownership blocks resume.
        until=time.monotonic()+45
        while True:
            try:dead(json.loads(roster.read_text()));break
            except RuntimeError:
                if time.monotonic()>=until:raise
                time.sleep(.1)
    return rc


def audit_segment(build,output,control,until,prior_rosters=()):
    p=plan(until);p.update(audit_build=str(build),build_identity=str(ROOT/'build-identity.json'),audit_spool=str(ROOT/'spool.sqlite3'),audit_source=str(SOURCE),audit_output=str(output),prior_rosters=[str(x) for x in prior_rosters])
    if execute(control,p,'audit'):raise RuntimeError('Read-only checkpoint recovery audit failed')
    return json.loads(Path(output).read_text())


def controlled():
    original();HOME.mkdir(exist_ok=True)
    out=HOME/'controlled';out.mkdir(exist_ok=False)
    with owner(ROOT):
        l=json.loads((ROOT/'construction-ledger.json').read_text());until=min(l['deadline'],time.time()+7200)
        old=ROOT/'native-diagnostic-v8/long'
        dead(json.loads((old/'corrected-control/process-identities.json').read_text()))
        summary=json.loads((old/'native-failure-summary.json').read_text())
        if summary['first_causal_file_error']['operation']!='MoveFileExW' or summary['first_causal_file_error']['winerror']!=5:
            raise RuntimeError('Controlled source is not the captured replacement fault')
        formal_sha=sha(ROOT/'build/checkpoint.json');(out/'build/tantivy').mkdir(parents=True)
        from evaluation.tantivy_supervision_v3 import derived_bytes
        admission=plan(until)
        if derived_bytes(admission)>admission['disk_limit'] or shutil.disk_usage(ROOT).free<32*1024**3:raise RuntimeError('Copy resource admission failed')
        copied={}
        with owner(old/'build'):
            sources=[*(old/'build/tantivy').iterdir(),*[old/'build'/n for n in ('mapping.sqlite3','budget.json','checkpoint.json','prepared.json')]]
            for source in sources:
                if not source.is_file() or source.name.endswith('.lock'):continue
                if time.time()>=until:raise TimeoutError('Copy deadline expired')
                dest=out/'build/tantivy'/source.name if source.parent.name=='tantivy' else out/'build'/source.name
                before=sha(source);shutil.copyfile(source,dest)
                if sha(source)!=before or sha(dest)!=before:raise RuntimeError('Checkpoint copy not byte-identical')
                copied[str(dest.relative_to(out))]=before
        atomic(out/'copied-files.json',copied)
        entry={'version':10,'start':time.time(),'deadline':until,'scope':'controlled recovery copy only','max_added':10000,'formal_unchanged_sha':formal_sha,'status':'auditing'}
        l.setdefault('checkpoint_recovery_validations',[]).append(entry);atomic(ROOT/'construction-ledger.json',l)
        try:
            before=audit_segment(out/'build',out/'before.json',out/'before-control',until)
            if before['native_committed']!=875674:raise RuntimeError('Controlled committed prefix changed')
            p=plan(until,traced_build=out/'build/tantivy');p.update(controlled_build=str(out/'build'),proof=str(out/'before.json'),controlled_target=885674)
            rc=execute(out/'write-control',p,'controlled-write')
            entry['write_exit_code']=rc
            if rc:raise RuntimeError('Controlled recovery failed; no retry admitted')
            after=audit_segment(out/'build',out/'after.json',out/'after-control',until)
            if after['native_committed']!=885674 or after['mapped']!=885674:raise RuntimeError('Controlled recovery target not committed')
            if sha(ROOT/'build/checkpoint.json')!=formal_sha:raise RuntimeError('Formal checkpoint changed during isolation')
            atomic(out/'result.json',{'passed':True,'before':875674,'after':885674,'added':10000,'formal_progress_unchanged':True,'original_binary':ORIGINAL_PYD,'original_fault_fixed':False,'wall':time.time()})
            entry.update(status='passed',added=10000)
        except BaseException as e:
            entry.update(status='failed-no-retry',error=repr(e));raise
        finally:
            entry['end']=time.time();l['wall_elapsed']=time.time()-l['start_wall'];atomic(ROOT/'construction-ledger.json',l)


def controlled_writer(plan_path):
    from evaluation.tantivy_native_trace_v8 import wait_ready,phase
    from evaluation.tantivy_supervision_v3 import Guard
    from evaluation.tantivy_full_identity_v1 import FullCheckpoint
    import sqlite3
    g=Guard(plan_path);wait_ready(g.plan);original();p=g.plan;build=Path(p['controlled_build'])
    proof=json.loads(Path(p['proof']).read_text())
    def check():
        g.check('controlled recovery')
        if g.path.with_name('pause.json').exists():raise RuntimeError('Controlled recovery service/resource pause; no retry')
    for name,data in proof['required_files'].items():
        if sha(build/'tantivy'/name,check)!=data['sha256']:raise RuntimeError('Committed file changed after admission')
    if sha(build/'mapping.sqlite3')!=proof['mapping_file_sha256'] or sha(build/'tantivy/meta.json')!=proof['meta_sha256'] or sha(build/'tantivy/.managed.json')!=proof['managed_sha256']:
        raise RuntimeError('Admitted checkpoint changed before writer')
    if proof['journal_sha256'] and sha(build/'prepared.json')!=proof['journal_sha256']:raise RuntimeError('Admitted journal changed')
    identity=json.loads((ROOT/'build-identity.json').read_text())
    if [SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns]!=identity['source_stat']:raise RuntimeError('Source identity stat changed')
    phase('controlled native recovery');b=None;primary=None
    con=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    try:
        b=FullCheckpoint(build,identity,total_seconds=96*3600,segment_seconds=max(0,p['deadline']-time.time()-60),authorized_full=True,checkpoint=check)
        b.writer.phase=phase
        count=b.con.execute('select count(*) from rows').fetchone()[0]
        if count!=proof['native_committed']:raise RuntimeError('Recovered boundary changed; no feed')
        while count<p['controlled_target']:
            check();phase('controlled feed')
            rows=con.execute('select * from input where position>=? order by position limit 5000',(count,)).fetchall()
            b.append(rows);count+=len(rows);g.event('controlled_committed',count=count)
    except BaseException as e:primary=e;raise
    finally:
        con.close()
        cleanup=b.close(primary=primary) if b else []
        g.event('stage_closed',primary=repr(primary),cleanup_errors=cleanup)


def finish_controlled_readonly():
    """Finish this same write attempt's proof after delayed observer exit.

    Does not create a writer, reset the original deadline, or repeat any append.
    Original failed gate receipt is retained independently.
    """
    out=HOME/'controlled'
    with owner(ROOT):
        l=json.loads((ROOT/'construction-ledger.json').read_text());entry=l['checkpoint_recovery_validations'][-1]
        if entry.get('status')!='failed-no-retry' or not entry.get('error','').startswith("RuntimeError('Prior owned process still alive:"):
            raise RuntimeError('Not the delayed owned-process exit gate')
        if (out/'result.json').exists() or (out/'after-control').exists():raise RuntimeError('Read-only completion already attempted')
        events=[json.loads(s) for s in (out/'write-control/events.jsonl').read_text().splitlines()]
        closed=next(e for e in reversed(events) if e['kind']=='stage_closed')
        exited=next(e for e in reversed(events) if e['kind']=='exit')
        if closed['primary']!='None' or closed['cleanup_errors'] or exited['code']!=0 or (out/'write-control/stop.json').exists():
            raise RuntimeError('The original controlled writer did not finish cleanly')
        dead(json.loads((out/'write-control/process-identities.json').read_text()))
        if sha(ROOT/'build/checkpoint.json')!=entry['formal_unchanged_sha']:raise RuntimeError('Formal checkpoint changed')
        after=audit_segment(out/'build',out/'after.json',out/'after-control',entry['deadline'],[out/'write-control/process-identities.json'])
        if after['native_committed']!=885674 or after['mapped']!=885674:raise RuntimeError('Controlled committed IDs changed')
        result={'passed':True,'before':875674,'after':885674,'added':10000,'formal_progress_unchanged':True,'original_binary':ORIGINAL_PYD,'original_fault_fixed':False,'write_attempts':1,'read_only_completion_after_delayed_exit':True,'original_gate_stop_preserved':dict(entry),'wall':time.time()}
        atomic(out/'result.json',result)
        entry.update(status='passed-after-readonly-proof',added=10000,readonly_proof_completed=time.time())
        l['wall_elapsed']=time.time()-l['start_wall'];atomic(ROOT/'construction-ledger.json',l)


def segment(plan_path,role):
    from evaluation.tantivy_supervision_v3 import supervise
    from evaluation.tantivy_full_controller_v1 import idle
    p=json.loads(Path(plan_path).read_text())
    for name,h in p['frozen_code'].items():
        if sha(name)!=h:raise RuntimeError('Frozen construction code changed')
    original()
    if role=='audit':command=[sys.executable,'-X','utf8','-m','evaluation.tantivy_checkpoint_recovery_v10',plan_path]
    elif role=='controlled-write':command=[sys.executable,'-X','utf8','-m',MODULE,'controlled-worker',plan_path]
    elif role=='formal-write':command=[sys.executable,'-X','utf8','-m','evaluation.tantivy_full_stages_v2','write',plan_path]
    else:raise RuntimeError('Unsupported checkpoint role')
    return supervise(plan_path,command,Path(plan_path).parent/'logs',idle)


if __name__=='__main__':
    if sys.argv[1:] == ['--controlled-once']:controlled()
    elif sys.argv[1:] == ['--finish-readonly-once']:finish_controlled_readonly()
    elif len(sys.argv)==3 and sys.argv[1]=='controlled-worker':controlled_writer(sys.argv[2])
    elif len(sys.argv)==4 and sys.argv[1]=='segment':raise SystemExit(segment(sys.argv[2],sys.argv[3]))
    else:raise SystemExit('Use --controlled-once or the frozen segment worker')
