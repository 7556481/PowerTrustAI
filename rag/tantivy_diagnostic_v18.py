"""Opt-in diagnostics for the existing isolated shard reader. No default wiring."""
import json,time,traceback,multiprocessing as mp,uuid
from pathlib import Path
from rag.tantivy_sharded_v17 import ShardedTantivyRetriever
from rag.tantivy_retriever import NativeSearchError

def event(path,kind,**fields):
 try:
  with Path(path).open('a',encoding='utf8') as f:f.write(json.dumps(dict(wall=time.time(),kind=kind,**fields))+'\n')
 except OSError:pass # diagnostics must not replace the primary error

def serve(paths,identity,pipe,log,statistics=False):
 import tantivy
 from rag.tantivy_query import query
 stage='open';rid=None
 try:
  opened=[]
  for path in paths:
   idx=tantivy.Index.open(path);idx.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());opened.append((idx,idx.searcher()))
  pipe.send(('ready',identity,sum(s.num_docs for i,s in opened)))
  while True:
   msg=pipe.recv()
   if msg[0]=='stop':return
   stage='request_validation'
   kind,rid,version,tree,k=msg
   if kind!='search' or version!=identity or not 0<k<=16:raise ValueError('Request identity/budget')
   started=time.monotonic();rows=[];parts=[];seconds=[]
   for n,(idx,s) in enumerate(opened):
    stage='search';event(log,'worker_phase',request=rid,stage=stage,shard=n)
    t=time.monotonic();hits=s.search(query(idx,tree),limit=k,count=False).hits
    stage='stored_read';local=[(s.doc(a)['rowid'][0],float(score)) for score,a in hits];rows+=local;parts.append(local);seconds.append(time.monotonic()-t)
   stage='merge';t=time.monotonic()
   if len({r for r,s in rows})!=len(rows):raise ValueError('Overlapping IDs')
   selected=sorted(rows,key=lambda z:(-z[1],z[0]))[:k];stage='send'
   metrics={'query_seconds':time.monotonic()-started,'merge_seconds':time.monotonic()-t,'shard_seconds':seconds,'per_shard_candidates':parts}
   if statistics:
    from rag.tantivy_global_rank_v18 import positive
    t=time.monotonic();metrics['global_token_df']={word:sum(s.doc_freq('terms',word) for idx,s in opened) for word in set(positive(tree))};metrics['statistics_seconds']=time.monotonic()-t
   pipe.send(('result',rid,identity,selected,metrics))
 except BaseException as e:
  event(log,'worker_exception',request=rid,stage=stage,type=type(e).__name__,message=str(e),chain=traceback.format_exc())
  try:pipe.send(('error',rid,identity,str(e),{'stage':stage,'exception':type(e).__name__}))
  except (EOFError,OSError):pass
 finally:pipe.close()

class DiagnosticRetriever(ShardedTantivyRetriever):
 def __init__(self,*args,diagnostic_path,trim_owned_working_set=False,**kw):self.trim_owned_working_set=trim_owned_working_set;self.diagnostic_path=str(diagnostic_path);self.stop_initiator='normal_close';super().__init__(*args,**kw)
 def _rank(self,*args):
  self._trim_used=False;return super()._rank(*args)
 def trim(self):
  import ctypes,psutil
  from ctypes import wintypes
  if psutil.Process(self._native.pid).create_time()!=self._born:raise NativeSearchError('Worker creation identity changed')
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE;k.K32EmptyWorkingSet.argtypes=[wintypes.HANDLE];k.K32EmptyWorkingSet.restype=wintypes.BOOL;k.CloseHandle.argtypes=[wintypes.HANDLE]
  h=k.OpenProcess(0x1000|0x100,False,self._native.pid)
  if not h:raise ctypes.WinError(ctypes.get_last_error())
  try:
   if not k.K32EmptyWorkingSet(h):raise ctypes.WinError(ctypes.get_last_error())
  finally:k.CloseHandle(h)
 def _ensure(self,started):
  if self._native is not None and self._native.is_alive():return False
  self._stop()
  if self._starts>self.max_restarts:raise NativeSearchError('Bounded restart quota exhausted')
  ctx=mp.get_context('spawn');parent,child=ctx.Pipe();identity=self.manifest['_identity'];self._pipe=parent
  self._native=ctx.Process(target=serve,args=([m['_index_path'] for m in self._shards],identity,child,self.diagnostic_path,getattr(self,'collect_statistics',False)),daemon=True);self._native.start();child.close();self._starts+=1;self._generation=uuid.uuid4().hex
  import psutil
  self._born=psutil.Process(self._native.pid).create_time()
  if self._wait(started)!=('ready',identity,self.manifest['members']['total']):raise NativeSearchError('Worker initialization failed')
  return True
 def _wait(self,started):
  try:
   import psutil
   while True:
    if self._cancel_work.is_set():raise InterruptedError('Reusable search cancelled')
    if time.monotonic()-started>=self.timeout_seconds:raise TimeoutError('Reusable worker request timed out')
    if not self._native.is_alive():raise NativeSearchError('Reusable worker exited: '+str(self._native.exitcode))
    m=psutil.Process(self._native.pid).memory_info();value=max(m.rss,getattr(m,'private',m.rss))
    if getattr(self,'trim_owned_working_set',False) and not getattr(self,'_trim_used',False) and m.rss>self.memory_limit//2 and getattr(m,'private',value)<=self.memory_limit:
     self._trim_used=True;t=time.monotonic();self.trim();after=psutil.Process(self._native.pid).memory_info();event(self.diagnostic_path,'owned_working_set_reclaim',reclaim_threshold=self.memory_limit//2,rss_before=m.rss,rss_after=after.rss,seconds=time.monotonic()-t);continue
    if value>self.memory_limit:
     event(self.diagnostic_path,'memory_limit',value=value,threshold=self.memory_limit,rss=m.rss,private=getattr(m,'private',None))
     raise NativeSearchError('Worker memory admission exceeded')
    if self._pipe.poll(.02):result=self._pipe.recv();break
   if result[0]=='error':
    self.stop_initiator='worker_response_error';event(self.diagnostic_path,'worker_response_error',response=result)
   return result
  except BaseException as e:
   import psutil
   sample={}
   try:
    m=psutil.Process(self._native.pid).memory_info();sample={'rss':m.rss,'private':getattr(m,'private',None)}
   except (psutil.Error,AttributeError):pass
   self.stop_initiator='parent_wait_failure'
   event(self.diagnostic_path,'parent_wait_error',type=type(e).__name__,message=str(e),threshold=self.memory_limit,elapsed=time.monotonic()-started,**sample)
   raise
 def _stop(self,graceful=False):
  p=self._native
  if p is None:return
  try:
   event(self.diagnostic_path,'stop_before',pid=p.pid,initiator=self.stop_initiator,already_exited=not p.is_alive(),exitcode=p.exitcode)
   if graceful and p.is_alive():
    try:self._pipe.send(('stop',))
    except (OSError,EOFError):pass
    p.join(.5)
   if p.is_alive():event(self.diagnostic_path,'terminate',initiator=self.stop_initiator,pid=p.pid);p.terminate()
   p.join(2)
   if p.is_alive():event(self.diagnostic_path,'kill',pid=p.pid);p.kill();p.join(2)
   event(self.diagnostic_path,'stop_after',pid=p.pid,exitcode=p.exitcode)
   if p.is_alive():self._closed=True;raise NativeSearchError('Owned worker did not release')
  finally:
   if self._pipe:self._pipe.close()
   if not p.is_alive():p.close()
   self._pipe=None;self._native=None;self._generation=None;self.stop_initiator='normal_close'
