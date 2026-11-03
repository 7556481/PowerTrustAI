"""Bounded, PID+creation-time checked file tracing for an isolated build only.

No system driver, service, global logger, ACL change or production dependency.
Frida is loaded exclusively from the frozen ignored diagnostic dependencies.
"""
import ctypes
import json
import sys
import threading
import time
from pathlib import Path

import psutil

FRIDA_VERSION = '17.25.2'


def phase(name):
    """Synchronous stage marker observed in the same process before native work."""
    try:
        ctypes.windll.kernel32.OutputDebugStringW('PTAI_NATIVE_PHASE:' + name)
    except BaseException:
        pass  # An observation marker must never replace a native primary error.


class BoundedLog:
    def __init__(self, path, limit, fallback=None):
        self.path, self.limit, self.size = Path(path), limit, 0
        self.fallback = fallback or sys.stderr
        self.failed = False

    def emit(self, row):
        data = (json.dumps(row, ensure_ascii=True) + '\n').encode()
        try:
            if self.size + len(data) > self.limit:
                raise OSError('diagnostic log size ceiling reached')
            with self.path.open('ab') as file:
                file.write(data)
                file.flush()
            self.size += len(data)
            return True
        except BaseException as error:
            self.failed = True
            try:
                self.fallback.write(json.dumps(dict(row, diagnostic_logging_error=repr(error))) + '\n')
                self.fallback.flush()
            except BaseException:
                pass
            return False


class TraceSession:
    def __init__(self, config, pid, created, stop_path):
        self.config, self.pid, self.created = config, pid, created
        self.stop_path = Path(stop_path)
        self.directory = Path(config['directory'])
        self.directory.mkdir(exist_ok=True)
        self.log = BoundedLog(self.directory / 'files.jsonl', 32 * 1024**2)
        self.errors = BoundedLog(self.directory / 'first-native-errors.jsonl', 8 * 1024**2)
        self.ready = threading.Event()
        self.session = self.script = None
        self.finished = False
        self.lock = threading.Lock()

    def stop(self, reason):
        # Tracing failure ends diagnostic admission; it never changes writer error results.
        try:
            self.stop_path.write_text(json.dumps({'reason': reason, 'wall': time.time()}))
        except OSError:
            pass

    def message(self, message, data):
        with self.lock:
            row = message.get('payload') if message.get('type') == 'send' else None
            if not isinstance(row, dict):
                self.errors.emit({'observer_error': message, 'wall': time.time()})
                self.stop('native trace script failed')
                return
            if row.get('pid') != self.pid:
                self.stop('native trace PID mismatch')
                return
            row['process_created'] = self.created
            ok = self.log.emit(row)
            if row.get('failed'):
                ok = self.errors.emit(row) and ok
            if not ok:
                self.stop('native trace log failure/ceiling')
            if row.get('operation') == 'trace_ready':
                self.ready.set()

    def start(self):
        if abs(psutil.Process(self.pid).create_time() - self.created) >= .001:
            raise RuntimeError('Native trace process identity changed')
        # A Windows venv python.exe may be a redirector with a real Python child.
        # Attach the process that executes the worker, not merely Popen.pid.
        launcher_pid, launcher_created = self.pid, self.created
        admission = Path(self.config['ready_file']).with_name('worker-admission.json')
        start = time.monotonic()
        while not admission.exists():
            if time.monotonic() - start > 20:
                raise TimeoutError('Worker did not identify itself for tracing')
            time.sleep(.05)
        identity = json.loads(admission.read_text())
        actual = psutil.Process(identity['pid'])
        if abs(actual.create_time() - identity['created']) >= .001:
            raise RuntimeError('Worker admission PID was reused')
        lineage = [actual, *actual.parents()]
        if not any(p.pid == launcher_pid and abs(p.create_time() - launcher_created) < .001 for p in lineage):
            raise RuntimeError('Trace target is not this owned launcher/descendant')
        self.pid, self.created = actual.pid, actual.create_time()
        self.log.emit({'operation': 'verified_worker_identity', 'launcher_pid': launcher_pid,
                       'launcher_created': launcher_created, 'worker': identity})
        sys.path.insert(0, self.config['dependencies'])
        from rag.tantivy_manifest import sha
        for path, digest in self.config.get('dependency_files', {}).items():
            if sha(path) != digest:
                raise RuntimeError('Native trace binary/source identity changed')
        import frida
        if frida.__version__ != FRIDA_VERSION:
            raise RuntimeError('Native trace dependency identity mismatch')
        self.session = frida.get_local_device().attach(self.pid)
        self.session.on('detached', lambda reason, *args: self.stop('trace detached before stage ended') if not self.finished and reason != 'process-terminated' else None)
        source = Path(__file__).with_suffix('.js').read_text(encoding='utf8')
        agent = {'roots': self.config['roots'], 'inject_pos_failure': self.config.get('inject_pos_failure', False), 'errors_only': self.config.get('errors_only', False)}
        self.script = self.session.create_script(source.replace('CONFIG', json.dumps(agent), 1))
        self.script.on('message', self.message)
        self.script.load()
        if not self.ready.wait(15):
            raise RuntimeError('Native trace did not reach ready boundary')
        if self.log.failed or self.errors.failed or self.stop_path.exists():
            raise RuntimeError('Native tracing failed before worker admission')
        if abs(psutil.Process(self.pid).create_time() - self.created) >= .001:
            raise RuntimeError('Native trace process identity changed during attachment')
        Path(self.config['ready_file']).write_text(json.dumps({'pid': self.pid, 'created': self.created, 'wall': time.time()}))

    def close(self):
        self.finished = True
        if self.session:
            try:
                self.session.detach()
            except BaseException as error:
                self.errors.emit({'observer_close_error': repr(error), 'wall': time.time()})


def wait_ready(plan):
    import os
    config = plan['native_trace']
    ready = Path(config['ready_file'])
    from rag.tantivy_build import atomic
    atomic(ready.with_name('worker-admission.json'), {'pid': os.getpid(), 'created': psutil.Process().create_time(),
           'executable': sys.executable, 'process_exe': psutil.Process().exe(),
           'account': psutil.Process().username(), 'cwd': str(Path.cwd())})
    started = time.monotonic()
    while not ready.exists():
        if time.monotonic() - started > 90 or time.time() >= plan['deadline']:
            raise TimeoutError('No native tracing admission')
        time.sleep(.05)
    receipt = json.loads(ready.read_text())
    if receipt['pid'] != os.getpid() or abs(receipt['created'] - psutil.Process().create_time()) >= .001:
        raise RuntimeError('Trace admission belongs to another process')
