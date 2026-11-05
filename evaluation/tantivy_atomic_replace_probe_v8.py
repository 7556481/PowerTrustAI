"""One bounded synthetic Windows handle-sharing probe; never opens a real index."""
import ctypes
from ctypes import wintypes as W
import json
import time

from evaluation.tantivy_full_build_v1 import ROOT
from rag.tantivy_build import atomic


def main():
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
    api.CreateFileW.restype = W.HANDLE
    api.CloseHandle.argtypes = [W.HANDLE]
    api.MoveFileExW.argtypes = [W.LPCWSTR, W.LPCWSTR, W.DWORD]
    api.MoveFileExW.restype = W.BOOL
    out = ROOT / 'native-diagnostic-v8/atomic-sharing-probe'
    out.mkdir(exist_ok=False)
    results = []
    for name, share in [('no_reader', None), ('reader_shares_delete', 7), ('reader_no_share_delete', 3)]:
        folder = out / name
        folder.mkdir()
        src, dest = folder / '.tmp-fixed', folder / '.managed.json'
        src.write_bytes(b'new synthetic metadata')
        dest.write_bytes(b'old synthetic metadata')
        reader = None
        if share is not None:
            reader = api.CreateFileW(str(dest), 0x80000000, share, None, 3, 0x80, None)
            if reader == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
        row = {'synthetic': True, 'case': name, 'share_mask': share, 'wall': time.time()}
        try:
            ok = api.MoveFileExW(str(src), str(dest), 1)
            row.update(success=bool(ok), winerror=None if ok else ctypes.get_last_error())
        finally:
            if reader is not None:
                api.CloseHandle(reader)
        # This is an explicitly separated synthetic ownership check, not a retry
        # of a real failed writer or an adopted error-retry policy.
        if not row['success']:
            ok = api.MoveFileExW(str(src), str(dest), 1)
            row.update(after_owned_reader_close_success=bool(ok), after_close_error=None if ok else ctypes.get_last_error())
        row['delivered_bytes_are_new'] = dest.read_bytes() == b'new synthetic metadata'
        results.append(row)
    atomic(out / 'result.json', {'cases': results, 'actual_blocking_holder': 'unknown; synthetic probe cannot identify it', 'models': 0})
    print(json.dumps(results))


if __name__ == '__main__':
    main()
