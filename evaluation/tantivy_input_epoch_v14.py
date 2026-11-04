"""Process-scoped immutable-input lease. No persisted pass-cache admission.

Windows read handles deny write/delete on source, spool and their manifests.
Workers duplicate the actual handles from the live verified controller. Never
place these locks on a native Tantivy index, .managed.json or merge files.
"""
import ctypes
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
import psutil
from rag.tantivy_build import atomic,digest
from rag.tantivy_manifest import sha,IndexIdentityError

class FileInfo(ctypes.Structure):
    _fields_=[('attributes',W.DWORD),('creation',W.FILETIME),('access',W.FILETIME),('write',W.FILETIME),('volume',W.DWORD),('size_high',W.DWORD),('size_low',W.DWORD),('links',W.DWORD),('id_high',W.DWORD),('id_low',W.DWORD)]

def api():
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE];k.CreateFileW.restype=W.HANDLE
    k.GetFileInformationByHandle.argtypes=[W.HANDLE,ctypes.POINTER(FileInfo)]
    k.CloseHandle.argtypes=[W.HANDLE]
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.GetCurrentProcess.restype=W.HANDLE
    k.DuplicateHandle.argtypes=[W.HANDLE,W.HANDLE,W.HANDLE,ctypes.POINTER(W.HANDLE),W.DWORD,W.BOOL,W.DWORD]
    return k

def information(k,h):
    x=FileInfo()
    if not k.GetFileInformationByHandle(h,ctypes.byref(x)):raise ctypes.WinError(ctypes.get_last_error())
    return [x.volume,x.id_high,x.id_low,x.size_high,x.size_low,x.write.dwHighDateTime,x.write.dwLowDateTime,x.attributes]

class Lease:
    def __init__(self):self.k=api();self.handles=[]
    def close(self):
        for h in reversed(self.handles):self.k.CloseHandle(h)
        self.handles=[]
    def pin(self,path):
        p=Path(path).resolve();h=self.k.CreateFileW(str(p),0x80000000,1,None,3,0x80,None)
        if h==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        self.handles.append(h);return {'path':str(p),'handle':h,'info':information(self.k,h)}

class WorkerLease(Lease):
    def __init__(self,receipt):
        super().__init__();self.receipt=receipt;self.last=0;self.parent=None
        try:
            self.check(force=True)
            self.parent=self.k.OpenProcess(0x40,False,receipt['pid'])
            if not self.parent:raise ctypes.WinError(ctypes.get_last_error())
            for row in receipt['files']:
                out=W.HANDLE()
                if not self.k.DuplicateHandle(self.parent,row['handle'],self.k.GetCurrentProcess(),ctypes.byref(out),0,False,2):raise ctypes.WinError(ctypes.get_last_error())
                self.handles.append(out.value)
                if information(self.k,out.value)!=row['info']:raise IndexIdentityError('Pinned file identity mismatch')
            current=Path(receipt['receipt_path']).read_bytes()
            if hashlib.sha256(current).hexdigest()!=receipt['receipt_sha256']:raise IndexIdentityError('Epoch receipt changed')
            self.check(force=True)
        except BaseException:self.close();raise
    def check(self,force=False):
        if not force and time.monotonic()-self.last<.5:return
        self.last=time.monotonic()
        if time.time()>=self.receipt['deadline']:raise TimeoutError('Original epoch deadline expired')
        if (Path(self.receipt['receipt_path']).parent.parent/'stop.json').exists():raise IndexIdentityError('Operator stopped input epoch')
        try:p=psutil.Process(self.receipt['pid'])
        except psutil.NoSuchProcess:raise IndexIdentityError('Input validation controller exited')
        if abs(p.create_time()-self.receipt['created'])>=.001:raise IndexIdentityError('Input validation controller PID reused')
        m=p.memory_info()
        if max(m.rss,getattr(m,'private',m.rss))>64*1024**2:raise MemoryError('Immutable input owner exceeds its reserved64MiB')
        for h,row in zip(self.handles,self.receipt['files']):
            if information(self.k,h)!=row['info']:raise IndexIdentityError('Pinned file changed')
    def close(self):
        super().close()
        if self.parent:self.k.CloseHandle(self.parent);self.parent=None

class InputEpoch(Lease):
    def __init__(self,root,source,knowledge,deadline):
        super().__init__();self.root=Path(root);self.deadline=deadline;self.start=time.time()
        try:
            paths=[Path(source),Path(str(source)+'.manifest.json'),self.root/'spool.sqlite3',self.root/'build-identity.json',self.root/'input-complete.json']
            files=[self.pin(p) for p in paths]
            identity=json.loads(paths[3].read_text());complete=json.loads(paths[4].read_text())
            if [Path(source).stat().st_size,Path(source).stat().st_mtime_ns]!=identity['source_stat']:raise IndexIdentityError('Original source stat identity changed')
            folder=self.root/'input-epochs'/uuid.uuid4().hex;folder.mkdir(parents=True)
            atomic(folder/'state.json',{'state':'validating','pid':os.getpid(),'start':self.start,'deadline':deadline})
            self.folder=folder
            from rag.storage import KnowledgeStore
            from rag.tantivy_members import inventory
            from evaluation.tantivy_medium_measure_v2 import seal_checked
            from unittest.mock import patch
            import evaluation.tantivy_medium_measure_v2 as old
            def check():
                if time.time()>=deadline:raise TimeoutError('Original deadline during input validation')
                if (self.root/'input-epochs/stop.json').exists():raise RuntimeError('Operator stopped input validation')
                now=time.monotonic()
                if now-getattr(self,'_resource_tick',0)<1:return
                self._resource_tick=now
                m=psutil.Process().memory_info()
                if max(m.rss,getattr(m,'private',m.rss))>64*1024**2:raise MemoryError('Input controller exceeds reserved64MiB')
                import shutil
                if shutil.disk_usage(self.root).free<30*1024**3:raise RuntimeError('Original disk reserve violated')
                from evaluation.tantivy_full_controller_v1 import idle
                while not idle() or psutil.virtual_memory().available<512*1024**2:
                    if time.time()>=deadline or (self.root/'input-epochs/stop.json').exists():raise TimeoutError('Stopped/expired during input validation pause')
                    time.sleep(.2)
            with KnowledgeStore(source,readonly=True,validated_pdf_cache=True) as store:
                with patch.object(old,'checkpoint',check):seal_checked(store,knowledge)
                inv=inventory(store,knowledge)
            source_done=time.time();con=sqlite3.connect(paths[2].resolve().as_uri()+'?mode=ro',uri=True)
            atomic(folder/'state.json',{'state':'validating-spool','pid':os.getpid(),'source_seal_seconds':source_done-self.start,'start':self.start,'deadline':deadline})
            try:
                con.execute('pragma cache_size=-4096')
                if con.execute('select identity from meta').fetchone()!=(digest(identity),):raise IndexIdentityError('Spool identity mismatch')
                h=hashlib.sha256();n=0
                for row in con.execute('select * from input order by position'):
                    if n%1000==0:check()
                    if n and n%250000==0:atomic(folder/'state.json',{'state':'validating-spool','pid':os.getpid(),'rows_verified':n,'expected':identity['expected'],'start':self.start,'wall':time.time()})
                    if row[0]!=n or row[1]!=(-(n+1) if n<inv['native'] else n-inv['native']+1) or hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:raise IndexIdentityError('Complete spool order/terms mismatch')
                    h.update(json.dumps(row[:5]).encode());n+=1
                if n!=identity['expected'] or n!=inv['total'] or n!=complete['n'] or h.hexdigest()!=complete['mapping_hash']:raise IndexIdentityError('Complete immutable input digest mismatch')
            finally:con.close()
            for h,row in zip(self.handles,files):
                if information(self.k,h)!=row['info']:raise IndexIdentityError('Input changed during validation')
            receipt={'version':14,'pid':os.getpid(),'created':psutil.Process().create_time(),'deadline':deadline,'files':files,'count':n,'identity':identity,'knowledge':knowledge,'mapping_hash':complete['mapping_hash'],'source_seal_seconds':source_done-self.start,'spool_seconds':time.time()-source_done,'validated_wall':time.time()}
            path=folder/'receipt.json';atomic(path,receipt)
            receipt.update(receipt_path=str(path),receipt_sha256=sha(path));self.receipt=receipt
            atomic(folder/'state.json',{'state':'pinned-validated','validated_wall':time.time(),'pid':os.getpid()})
        except BaseException:self.close();raise

def proof_unchanged(build,proof_path,check):
    build=Path(build);p=json.loads(Path(proof_path).read_text())
    if not p.get('passed'):raise IndexIdentityError('Recovery audit not passed')
    files={build/'mapping.sqlite3':p['mapping_file_sha256'],build/'tantivy/meta.json':p['meta_sha256'],build/'tantivy/.managed.json':p['managed_sha256']}
    if p['journal_sha256']:files[build/'prepared.json']=p['journal_sha256']
    elif (build/'prepared.json').exists():raise IndexIdentityError('Unexpected new journal')
    files.update({build/'tantivy'/n:r['sha256'] for n,r in p['required_files'].items()})
    for f,h in files.items():
        if sha(f,check)!=h:raise IndexIdentityError('Recovery file changed since audit: '+str(f))
    if json.loads((build/'checkpoint.json').read_text())!=p['checkpoint']:raise IndexIdentityError('Checkpoint changed since audit')
    return p
