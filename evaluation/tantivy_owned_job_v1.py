"""Windows ownership boundary: only explicitly assigned isolated build children."""
import ctypes,os
from ctypes import wintypes as W
class OwnedJob:
 def __init__(self):
  if os.name!='nt':raise RuntimeError('Windows ownership job required')
  class Basic(ctypes.Structure):
   _fields_=[('ProcessTime',ctypes.c_int64),('JobTime',ctypes.c_int64),('Flags',W.DWORD),('MinWorking',ctypes.c_size_t),('MaxWorking',ctypes.c_size_t),('Active',W.DWORD),('Affinity',ctypes.c_size_t),('Priority',W.DWORD),('Scheduling',W.DWORD)]
  class IO(ctypes.Structure):
   _fields_=[(x,ctypes.c_uint64) for x in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
  class Extended(ctypes.Structure):
   _fields_=[('Basic',Basic),('Io',IO),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcess',ctypes.c_size_t),('PeakJob',ctypes.c_size_t)]
  self.api=ctypes.WinDLL('kernel32',use_last_error=True)
  self.api.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];self.api.CreateJobObjectW.restype=W.HANDLE
  self.api.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
  self.api.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE]
  self.api.CloseHandle.argtypes=[W.HANDLE]
  self.handle=self.api.CreateJobObjectW(None,None)
  if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
  limits=Extended();limits.Basic.Flags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
  if not self.api.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
   error=ctypes.get_last_error();self.close();raise ctypes.WinError(error)
 def assign(self,process):
  if not self.api.AssignProcessToJobObject(self.handle,int(process._handle)):raise ctypes.WinError(ctypes.get_last_error())
 def close(self):
  if getattr(self,'handle',None):self.api.CloseHandle(self.handle);self.handle=None
 def __del__(self):self.close()
