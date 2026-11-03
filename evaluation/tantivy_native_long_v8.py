"""One observed long-lifecycle diagnostic. Never resumes the formal build.

Uses the real supervision/stage/checkpoint code, a verified derived checkpoint
copy and read-only existing complete input. No scheduler or automatic retries.
"""
import json
import os
import shutil
import sys
import time
import importlib.metadata
import subprocess
from pathlib import Path

import psutil

from evaluation.tantivy_full_build_v1 import ROOT, REUSE
from rag.tantivy_build import atomic, owner
from rag.tantivy_manifest import sha


def freeze_and_run():
    from evaluation.tantivy_supervision_v3 import supervise
    from evaluation.tantivy_full_controller_v1 import idle
    import tantivy
    import tantivy.tantivy as extension
    with owner(ROOT):
        ledger_path = ROOT / 'construction-ledger.json'
        ledger = json.loads(ledger_path.read_text())
        now = time.time()
        if now >= ledger['deadline']:
            raise TimeoutError('Original construction budget expired')
        for pid, created in json.loads((ROOT / 'controls/16/process-identities.json').read_text()).items():
            try:
                if abs(psutil.Process(int(pid)).create_time() - created) < .001:
                    raise RuntimeError('Previous isolated build process still alive')
            except psutil.NoSuchProcess:
                pass
        original_cp = json.loads((ROOT / 'build/checkpoint.json').read_text())
        if original_cp['count'] != 685674:
            raise RuntimeError('Frozen original prefix changed')
        if not REUSE.is_file():
            raise RuntimeError('Existing read-only reuse spool is missing before diagnostic admission')
        from evaluation.tantivy_native_holders_v8 import holders
        holders_at_start = holders([p for p in (ROOT / 'build/tantivy').iterdir() if p.is_file()])
        if holders_at_start.get('error') or holders_at_start.get('holders'):
            raise RuntimeError('Original index file ownership requires inspection: ' + json.dumps(holders_at_start))
        out = ROOT / 'native-diagnostic-v8/long'
        out.mkdir(exist_ok=False)  # No rerun or overwrite of this one run.
        control = out / 'control'
        control.mkdir()
        before_cp = sha(ROOT / 'build/checkpoint.json')
        code_files = [
            'evaluation/tantivy_native_long_v8.py', 'evaluation/tantivy_native_trace_v8.py',
            'evaluation/tantivy_native_trace_v8.js', 'evaluation/tantivy_full_stages_v2.py',
            'evaluation/tantivy_full_identity_v1.py', 'evaluation/tantivy_supervision_v3.py',
            'evaluation/tantivy_full_build_v1.py', 'evaluation/tantivy_owned_job_v1.py',
            'rag/tantivy_build.py',
        ]
        plan = {
            'deadline': min(ledger['deadline'], now + 7200), 'kill_on_supervisor_exit': True,
            'grace_seconds': 45, 'cwd': str(Path.cwd()), 'data_root': str(ROOT),
            'extra_data_roots': [str((ROOT / 'build').resolve())],
            'memory_limit': ledger['memory_limit'], 'disk_limit': 157 * 1024**3,
            'min_free': 30 * 1024**3, 'pressure_available': 512 * 1024**2,
            'diagnostic_run': {'original_committed': 685674, 'target': 1685674,
                               'max_added': 1000000, 'root': str(out), 'input_spool': str(ROOT / 'spool.sqlite3'),
                               'reuse_spool': str(REUSE)},
            'native_trace': {'directory': str(out / 'trace'),
                'dependencies': str(ROOT / 'native-diagnostic-v8/deps'),
                'dependency_files': {str(p): sha(p) for p in (ROOT / 'native-diagnostic-v8/deps/frida').rglob('*') if p.is_file() and p.suffix in ('.pyd', '.dll', '.py')},
                'roots': [str(out / 'build/tantivy')],
                'ready_file': str(control / 'trace-ready.json'), 'inject_pos_failure': False},
            'frozen_code': {p: sha(p) for p in code_files},
            'runtime': {'python': sys.executable, 'python_version': sys.version,
                        'tantivy': importlib.metadata.version('tantivy'), 'extension': extension.__file__,
                        'extension_sha256': sha(extension.__file__), 'cwd': str(Path.cwd()),
                        'account': psutil.Process().username(), 'frida': '17.25.2'},
            'code_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'original_ledger_deadline': ledger['deadline'], 'models': 0,
            'original_holders_point_observation': holders_at_start,
        }
        atomic(control / 'plan.json', plan)
        entry = {'version': 8, 'start': now, 'deadline': plan['deadline'], 'status': 'running',
                 'plan': str(control / 'plan.json'), 'formal_progress_unchanged': True}
        ledger.setdefault('diagnostic_runs', []).append(entry)
        ledger['wall_elapsed'] = now - ledger['start_wall']
        atomic(ledger_path, ledger)
        rc, primary = None, None
        try:
            # All copying remains within the existing resource/time budget.
            from evaluation.tantivy_supervision_v3 import derived_bytes
            if derived_bytes(plan) > plan['disk_limit'] or shutil.disk_usage(out).free < plan['min_free'] + 2*1024**3:
                raise RuntimeError('No diagnostic copy resource admission')
            with owner(ROOT / 'build'):
                dest = out / 'build'
                dest.mkdir()
                (dest / 'tantivy').mkdir()
                copied = {}
                for source in [*(ROOT / 'build/tantivy').iterdir(),
                               *[ROOT / 'build' / n for n in ('mapping.sqlite3', 'checkpoint.json', 'prepared.json', 'budget.json')]]:
                    if not source.is_file() or source.name.endswith('.lock'):
                        continue
                    if time.time() >= plan['deadline']:
                        raise TimeoutError('Diagnostic deadline during copy')
                    digest = sha(source)
                    target = dest / 'tantivy' / source.name if source.parent.name == 'tantivy' else dest / source.name
                    shutil.copyfile(source, target)
                    if sha(source) != digest or sha(target) != digest:
                        raise RuntimeError('Diagnostic checkpoint copy changed')
                    copied[str(target.relative_to(out))] = digest
                atomic(out / 'copied-checkpoint.json', copied)
                for name in ('build-identity.json', 'recovery-audit-1.json', 'spool-prefix.json', 'input-complete.json'):
                    shutil.copyfile(ROOT / name, out / name)
                    if sha(ROOT / name) != sha(out / name):
                        raise RuntimeError('Diagnostic input metadata copy changed')
            command = [sys.executable, '-X', 'utf8', '-m', 'evaluation.tantivy_native_long_v8', 'worker', str(control / 'plan.json')]
            rc = supervise(control / 'plan.json', command, out / 'logs', idle)
            if rc == 0 and time.time() < plan['deadline'] - 45:
                audit_control = out / 'audit-control'
                audit_control.mkdir()
                audit_plan = dict(plan)
                audit_plan.pop('native_trace')
                atomic(audit_control / 'plan.json', audit_plan)
                audit_rc = supervise(audit_control / 'plan.json',
                    [sys.executable, '-X', 'utf8', '-m', 'evaluation.tantivy_native_long_v8', 'audit', str(audit_control / 'plan.json')],
                    out / 'audit-logs', idle)
                if audit_rc:
                    rc = audit_rc
        except BaseException as error:
            primary = repr(error)
            raise
        finally:
            entry.update(end=time.time(), exit_code=rc, error=primary, status='ended' if rc == 0 else 'failed-needs-inspection')
            ledger['wall_elapsed'] = time.time() - ledger['start_wall']
            atomic(ledger_path, ledger)
            final = json.loads((ROOT / 'build/checkpoint.json').read_text())
            copy_cp = out / 'build/checkpoint.json'
            copy_count = json.loads(copy_cp.read_text())['count'] if copy_cp.exists() else None
            event_file = control / 'events.jsonl'
            events = [json.loads(line) for line in event_file.read_text().splitlines()] if event_file.exists() else []
            worker_primary = next((e.get('primary') for e in reversed(events) if e.get('kind') == 'stage_closed'), None)
            atomic(out / 'result.json', {'exit_code': rc, 'primary': primary, 'ended': time.time(),
                   'worker_primary': worker_primary,
                   'formal_checkpoint_unchanged': sha(ROOT / 'build/checkpoint.json') == before_cp,
                   'formal_committed': final['count'], 'diagnostic_committed': copy_count,
                   'diagnostic_added': copy_count - 685674 if copy_count is not None else None,
                   'original_deadline': ledger['deadline'],
                   'remaining_seconds': max(0, ledger['deadline'] - time.time()), 'models': 0})
        return rc if rc is not None else 1


def worker(plan_path):
    import evaluation.tantivy_full_stages_v2 as stage
    plan = json.loads(Path(plan_path).read_text())
    for path, digest in plan['frozen_code'].items():
        if sha(path) != digest:
            raise RuntimeError('Frozen diagnostic code changed before admission')
    stage.ROOT = Path(plan['diagnostic_run']['root'])
    stage.run('write', plan_path)


def audit(plan_path):
    """New-process reopen and all-ID proof; no writer and no all_query(n)."""
    import hashlib
    import sqlite3
    import tantivy
    from evaluation.tantivy_supervision_v3 import Guard
    from rag.tantivy_build import stored_ids
    guard = Guard(plan_path)
    root = Path(guard.plan['diagnostic_run']['root'])
    guard.check('read-only identity audit')
    index = tantivy.Index.open(str(root / 'build/tantivy'))
    seen = sqlite3.connect((root / 'audit-seen.sqlite3').resolve().as_uri(), uri=True)
    try:
        seen.execute('pragma cache_size=-8192')
        seen.execute('create table seen(rowid integer primary key)')
        seen.execute('attach database ? as mapping', ((root / 'build/mapping.sqlite3').resolve().as_uri()+'?mode=ro',))
        count, batch = 0, []
        for rid in stored_ids(index, root / 'build/tantivy'):
            batch.append((rid,))
            count += 1
            if len(batch) == 5000:
                guard.check('read-only identity audit')
                seen.executemany('insert into seen values(?)', batch)
                seen.commit()
                batch = []
        if batch:
            seen.executemany('insert into seen values(?)', batch)
            seen.commit()
        guard.check('read-only identity audit')
        if count != seen.execute('select count(*) from mapping.rows').fetchone()[0]:
            raise RuntimeError('Native count/mapping mismatch')
        seen.set_progress_handler(lambda: 1 if time.time() >= guard.plan['deadline'] else 0, 10000)
        if seen.execute('select rowid from seen except select rowid from mapping.rows limit 1').fetchone():
            raise RuntimeError('Native ID not in mapping')
        digest = hashlib.sha256()
        n = 0
        for row in seen.execute('select * from mapping.rows order by position'):
            if n % 5000 == 0:
                guard.check('read-only identity audit')
            if row[0] != n or row[1] != (-(n+1) if n < 674 else n-674+1):
                raise RuntimeError('ID namespace/position changed')
            digest.update(json.dumps(row).encode())
            n += 1
        cp = json.loads((root / 'build/checkpoint.json').read_text())
        if count != n or cp['count'] != n or cp['mapping_hash'] != digest.hexdigest():
            raise RuntimeError('Checkpoint mapping digest mismatch')
        guard.check('read-only identity audit')
        atomic(root / 'reopen-audit.json', {'passed': True, 'count': count, 'unique_native_equals_mapping': True,
                'mapping_hash': digest.hexdigest(), 'bounded_batches': 5000, 'wall': time.time()})
    finally:
        seen.close()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'worker':
        worker(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == 'audit':
        audit(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == '--once':
        raise SystemExit(freeze_and_run())
    else:
        raise SystemExit('Use --once; never resumes formal construction')
