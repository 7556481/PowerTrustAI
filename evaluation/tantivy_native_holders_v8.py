"""Read-only Restart Manager query for exact isolated-index file holders.

Never calls RmShutdown/RmRestart and never enumerates other processes' content.
An empty result is a point observation, not proof of no future/exotic handles.
"""
import ctypes
from ctypes import wintypes as W


def holders(files):
    class Unique(ctypes.Structure):
        _fields_ = [('pid', W.DWORD), ('start', W.FILETIME)]

    class Process(ctypes.Structure):
        _fields_ = [('process', Unique), ('app', W.WCHAR*256), ('service', W.WCHAR*64),
                    ('type', W.UINT), ('status', W.ULONG), ('session', W.DWORD), ('restartable', W.BOOL)]

    api = ctypes.WinDLL('rstrtmgr', use_last_error=True)
    session = W.DWORD()
    key = ctypes.create_unicode_buffer(33)
    rc = api.RmStartSession(ctypes.byref(session), 0, key)
    if rc:
        return {'error': rc, 'stage': 'RmStartSession'}
    try:
        names = (W.LPCWSTR*len(files))(*[str(p) for p in files])
        rc = api.RmRegisterResources(session, len(files), names, 0, None, 0, None)
        if rc:
            return {'error': rc, 'stage': 'RmRegisterResources'}
        required, count, reason = W.UINT(), W.UINT(), W.DWORD()
        rc = api.RmGetList(session, ctypes.byref(required), ctypes.byref(count), None, ctypes.byref(reason))
        if rc == 0:
            return {'holders': [], 'registered_files': len(files)}
        if rc != 234 or required.value > 256:
            return {'error': rc, 'required': required.value, 'stage': 'RmGetList size'}
        rows = (Process*required.value)()
        count.value = required.value
        rc = api.RmGetList(session, ctypes.byref(required), ctypes.byref(count), rows, ctypes.byref(reason))
        if rc:
            return {'error': rc, 'stage': 'RmGetList'}
        return {'registered_files': len(files), 'holders': [
            {'pid': row.process.pid, 'created': ((row.process.start.dwHighDateTime << 32) + row.process.start.dwLowDateTime) / 1e7 - 11644473600,
             'application': row.app} for row in rows[:count.value]]}
    finally:
        api.RmEndSession(session)
