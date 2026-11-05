"""Opt-in build-only IAT shim; fixed Tantivy binary and isolated DLL required.

Only the loaded Tantivy extension's MoveFileExW import is redirected, before a
writer is created. No production dependency, index format, or scoring changes.
"""
import ctypes
import json
from pathlib import Path
from rag.tantivy_manifest import sha

ORIGINAL_PYD = '69c2221c2ce1a896bf7b493147a750b5501f5aaebdfdd0dbbc176fc483ef8702'
_library = None


def install(config, deadline, stop):
    global _library
    if _library is not None:
        raise RuntimeError('Compatibility shim can be installed once per worker')
    import tantivy.tantivy as extension
    if sha(extension.__file__) != ORIGINAL_PYD:
        raise RuntimeError('Unverified Tantivy extension; no compatibility admission')
    dll = Path(config['dll'])
    if sha(dll) != config['sha256']:
        raise RuntimeError('Compatibility DLL identity mismatch')
    lib = ctypes.WinDLL(str(dll), use_last_error=True)
    lib.ptai_install.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_double]
    lib.ptai_install.restype = ctypes.c_ulong
    module = ctypes.WinDLL(extension.__file__)
    result = lib.ptai_install(module._handle, str(Path(config['root']).resolve()), str(stop), str(config['log']), deadline)
    if result:
        raise OSError(result, 'Failed to install scoped Tantivy atomic compatibility')
    _library = lib  # Keep code alive until process exit, including merge threads.
    return lib


def stats():
    if _library is None:
        return None
    out = (ctypes.c_long * 5)()
    _library.ptai_stats(out)
    return dict(zip(('calls', 'initial_failures', 'recovered', 'exhausted', 'log_failed'), out))
