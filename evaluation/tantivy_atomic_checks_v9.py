"""Real Windows file/handle tests, one fresh process per native shim install."""
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from evaluation.tantivy_full_build_v1 import ROOT
from rag.tantivy_build import atomic
from rag.tantivy_manifest import sha

OUT = Path(os.environ.get('PTAI_ATOMIC_TEST_ROOT', str(ROOT / 'atomic-compat-v9')))
DLL = OUT / 'ptai_atomic_compat_v9.dll'


def child(case, directory):
    from evaluation.tantivy_atomic_compat_v9 import install, stats
    folder = Path(directory)
    folder.mkdir()
    if case == 'failed_index_reopen':
        return failed_index_reopen(folder)
    src, dst = folder / '.tmp-synthetic', folder / '.managed.json'
    old, new = b'{"state":"old-complete"}', b'{"state":"new-complete"}'
    src.write_bytes(new)
    dst.write_bytes(old)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong]
    if case == 'log_failure':
        (folder/'native.jsonl').mkdir()
    lib = install({'dll': str(DLL), 'sha256': sha(DLL), 'root': str(folder), 'log': str(folder/'native.jsonl')},
                  time.time() + (.3 if case == 'deadline' else 20), folder/'stop.json')
    lib.ptai_test_replace.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
    lib.ptai_test_replace.restype = ctypes.c_int
    reader = None
    if case in ('release', 'persistent', 'cancel', 'deadline', 'stop', 'interrupt_during', 'log_failure'):
        reader = kernel.CreateFileW(str(dst), 0x80000000, 3, None, 3, 0x80, None)
        assert reader != ctypes.c_void_p(-1).value
    if case == 'readonly':
        assert kernel.SetFileAttributesW(str(dst), 1)
    if case == 'invalid':
        dst = folder/'missing/.managed.json'
    if case == 'before':
        (folder/'ready').touch()
        time.sleep(30)
    if case == 'release':
        def release():
            time.sleep(.12)
            kernel.CloseHandle(reader)
        thread = threading.Thread(target=release)
        thread.start()
    if case in ('cancel', 'stop'):
        def stop():
            time.sleep(.06)
            if case == 'cancel':
                lib.ptai_cancel()
            else:
                (folder/'stop.json').touch()
        thread = threading.Thread(target=stop)
        thread.start()
    started = time.monotonic()
    if case == 'interrupt_during':
        (folder/'ready').touch()
    ok = bool(lib.ptai_test_replace(str(src), str(dst), 1))
    error = ctypes.get_last_error() if not ok else None
    elapsed = time.monotonic()-started
    if case in ('release', 'cancel', 'stop'):
        thread.join()
    if reader is not None and case != 'release':
        kernel.CloseHandle(reader)
    if case == 'readonly':
        kernel.SetFileAttributesW(str(dst), 0x80)
    events = [json.loads(x) for x in (folder/'native.jsonl').read_text().splitlines()] if (folder/'native.jsonl').is_file() else []
    result = {'case': case, 'success': ok, 'error': error, 'elapsed': elapsed, 'stats': stats(), 'events': events,
              'old_or_new_complete': dst.read_bytes() in (old,new) if dst.exists() else case=='invalid',
              'source_exists': src.exists(), 'target_new': dst.read_bytes()==new if dst.exists() else False}
    atomic(folder/'result.json', result)
    if case == 'after':
        (folder/'ready').touch()
        time.sleep(30)


def failed_index_reopen(folder):
    """Real writer hits a persistent synthetic reader; last commit stays readable."""
    import tantivy
    from evaluation.tantivy_atomic_compat_v9 import install, stats
    from rag.tantivy_build import create_index, stored_ids
    root=folder/'index'
    root.mkdir()
    lib=install({'dll':str(DLL),'sha256':sha(DLL),'root':str(root),'log':str(folder/'native.jsonl')},time.time()+20,folder/'stop.json')
    index=create_index(root)
    writer=index.writer(heap_size=128000000,num_threads=1)
    for i in range(100):writer.add_document(tantivy.Document(rowid=i,terms='synthetic controlled metadata'))
    writer.commit()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
    kernel.CreateFileW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    reader=kernel.CreateFileW(str(root/'.managed.json'),0x80000000,3,None,3,0x80,None)
    assert reader!=ctypes.c_void_p(-1).value
    primary=cleanup=None
    try:
        for i in range(100,5100):writer.add_document(tantivy.Document(rowid=i,terms='second synthetic segment'))
        writer.commit()
    except Exception as error:primary=repr(error)
    finally:
        try:writer.wait_merging_threads()
        except Exception as error:cleanup=repr(error)
        kernel.CloseHandle(reader)
    assert primary is not None
    # Brand-new process, no writer or shim, all committed IDs must survive.
    code='import sys,json,tantivy; from pathlib import Path; from rag.tantivy_build import stored_ids; p=Path(sys.argv[1]); print(json.dumps(sorted(stored_ids(tantivy.Index.open(str(p)),p))))'
    r=subprocess.run([sys.executable,'-X','utf8','-c',code,str(root)],capture_output=True,text=True,check=True)
    ids=json.loads(r.stdout)
    assert ids==list(range(100)),ids
    atomic(folder/'result.json',{'case':'failed_index_reopen','primary':primary,'cleanup':cleanup,'stats':stats(),'reopened_committed_count':len(ids),'old_or_new_complete':True})


class AtomicCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = OUT / ('short-'+str(time.time_ns()))
        cls.directory.mkdir()
        cls.results=[]

    def run_case(self, name):
        path = self.directory/name
        r = subprocess.run([sys.executable, '-X','utf8','-m',__name__,name,str(path)], capture_output=True, text=True, timeout=25)
        self.assertEqual(r.returncode,0,r.stderr)
        row=json.loads((path/'result.json').read_text())
        self.assertTrue(row['old_or_new_complete'])
        self.results.append(row)
        return row

    def test_normal(self):
        r=self.run_case('normal');self.assertTrue(r['success']);self.assertEqual(r['stats']['initial_failures'],0)

    def test_transient_reader(self):
        r=self.run_case('release');self.assertTrue(r['target_new']);self.assertEqual(r['stats']['recovered'],1);self.assertGreater(len(r['events']),1)

    def test_persistent_reader(self):
        r=self.run_case('persistent');self.assertFalse(r['success']);self.assertTrue(r['source_exists']);self.assertFalse(r['target_new']);self.assertEqual(r['stats']['exhausted'],1);self.assertLess(r['elapsed'],2.1)

    def test_readonly(self):
        r=self.run_case('readonly');self.assertFalse(r['success']);self.assertEqual(r['error'],5);self.assertEqual(len(r['events']),1)

    def test_invalid_path(self):
        r=self.run_case('invalid');self.assertFalse(r['success']);self.assertTrue(r['source_exists']);self.assertEqual(r['stats']['recovered'],0)

    def test_cancel(self):
        r=self.run_case('cancel');self.assertFalse(r['success']);self.assertEqual(r['error'],995);self.assertLess(r['elapsed'],.5)

    def test_stop_file(self):
        r=self.run_case('stop');self.assertFalse(r['success']);self.assertEqual(r['error'],995)

    def test_deadline(self):
        r=self.run_case('deadline');self.assertFalse(r['success']);self.assertEqual(r['error'],1460);self.assertLess(r['elapsed'],.7)

    def test_log_failure_stops_retry(self):
        r=self.run_case('log_failure');self.assertFalse(r['success']);self.assertTrue(r['source_exists']);self.assertEqual(r['stats']['log_failed'],1);self.assertLess(r['elapsed'],.5)

    def test_failed_writer_committed_index_readable(self):
        r=self.run_case('failed_index_reopen');self.assertEqual(r['reopened_committed_count'],100);self.assertGreater(r['stats']['exhausted'],0)

    def test_interruption_boundaries(self):
        import psutil
        for case in ('before','interrupt_during','after'):
            path=self.directory/case
            p=subprocess.Popen([sys.executable,'-X','utf8','-m',__name__,case,str(path)],creationflags=subprocess.CREATE_NO_WINDOW)
            created=psutil.Process(p.pid).create_time()
            try:
                until=time.monotonic()+10
                while not (path/'ready').exists() and p.poll() is None and time.monotonic()<until:time.sleep(.01)
                self.assertTrue((path/'ready').exists())
                if case=='interrupt_during':time.sleep(.03)
                # Verified owned launcher AND descendants, never any user process.
                root=psutil.Process(p.pid)
                self.assertEqual(root.create_time(),created)
                children=root.children(recursive=True)
                for q in reversed(children):q.kill()
                root.kill();p.wait(5)
                body=(path/'.managed.json').read_bytes()
                self.assertIn(json.loads(body)['state'],('old-complete','new-complete'))
                self.assertEqual(json.loads(body)['state'],'new-complete' if case=='after' else 'old-complete')
            finally:
                if p.poll() is None:p.kill();p.wait()

    @classmethod
    def tearDownClass(cls):
        atomic(cls.directory/'summary.json',{'cases':cls.results,'models':0,'synthetic':True})


if __name__=='__main__':
    if len(sys.argv)==3:
        child(sys.argv[1],sys.argv[2])
    else:
        unittest.main()
