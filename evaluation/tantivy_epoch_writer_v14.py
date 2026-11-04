"""Original checkpoint/writer with a live immutable-input epoch admission."""
import json
import sqlite3
import time
from pathlib import Path
import psutil
from evaluation.tantivy_input_epoch_v14 import WorkerLease,proof_unchanged
from evaluation.tantivy_full_build_v1 import ROOT,PauseCheckpoint
from evaluation.tantivy_full_identity_v1 import FullCheckpoint
from evaluation.tantivy_supervision_v3 import Guard,Expired
from evaluation.tantivy_native_trace_v8 import wait_ready,phase
from rag.tantivy_build import atomic
from rag.tantivy_manifest import IndexIdentityError

def run(plan_path):
    g=Guard(plan_path);wait_ready(g.plan);p=g.plan;start=time.monotonic();b=None;con=None;primary=None;feeding=False
    parent=json.loads(g.path.with_name('supervisor-owner.json').read_text())
    lease=WorkerLease(p['input_epoch'])
    def check():
        lease.check()
        try:alive=abs(psutil.Process(parent['pid']).create_time()-parent['created'])<.001
        except psutil.NoSuchProcess:alive=False
        if not alive:raise Expired('Supervisor exited')
        if time.time()>=p['deadline']-60 or g.path.with_name('stop.json').exists():raise Expired('deadline/stop')
        if not feeding and g.path.with_name('pause.json').exists():raise PauseCheckpoint('resource/user pause at safe boundary')
    try:
        phase('live input epoch and dynamic recovery admission');check()
        identity=lease.receipt['identity'];proof=proof_unchanged(ROOT/'build',p['recovery_proof'],check)
        if lease.receipt['count']!=identity['expected']:raise IndexIdentityError('Input epoch member count changed')
        con=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);con.execute('pragma cache_size=-4096')
        phase('native recovery/writer creation')
        b=FullCheckpoint(ROOT/'build',identity,authorized_full=True,segment_seconds=max(0,p['deadline']-time.time()-60),checkpoint=check);b.writer.phase=phase
        mapped=b.con.execute('select count(*) from rows').fetchone()[0]
        if mapped!=proof['native_committed'] or b.mapping_hash()!=proof['input_prefix_hashes'][str(mapped)]:raise IndexIdentityError('Recovered mapping not bound to audited input')
        while mapped<identity['expected']:
            check();pending=ROOT/'build/prepared.json';limit=min(5000,identity['expected']-mapped)
            if pending.exists():
                journal=json.loads(pending.read_text());limit=journal['end']-journal['start']
            rows=con.execute('select * from input where position>=? order by position limit ?',(mapped,limit)).fetchall()
            feeding=True;phase('feed')
            try:b.append(rows)
            finally:feeding=False
            mapped+=len(rows);del rows
            atomic(ROOT/'progress-v2.json',{'phase':'epoch writer committed checkpoint','mapped':mapped,'expected':identity['expected'],'wall':time.time(),'segment':str(plan_path),'input_epoch':lease.receipt['receipt_path']})
        atomic(ROOT/'built-complete.json',{'n':mapped,'not_yet_accepted':True})
    except (Expired,TimeoutError,PauseCheckpoint) as error:primary=error;g.event('normal_stage_stop',error=type(error).__name__)
    except BaseException as error:primary=error;g.event('stage_failure',error=repr(error));raise
    finally:
        if con:con.close()
        cleanup=b.close(primary=primary) if b else []
        lease.close();g.event('stage_closed',primary=repr(primary),cleanup_errors=cleanup,elapsed=time.monotonic()-start)
        if cleanup and (primary is None or isinstance(primary,(Expired,TimeoutError,PauseCheckpoint))):raise RuntimeError('Cleanup failure requires audit')
