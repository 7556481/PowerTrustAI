"""Single owned reusable Tantivy worker and bounded source evidence delivery."""
import multiprocessing as mp,time,uuid,hashlib
from pathlib import Path
from rag.tantivy_retriever import AsyncTantivyRetriever,NativeSearchError,UnsupportedQueryError
from rag.tantivy_manifest import IndexIdentityError

def serve(path,identity,pipe):
 try:
  import tantivy
  from rag.tantivy_query import query
  index=tantivy.Index.open(path);index.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());search=index.searcher();pipe.send(('ready',identity,search.num_docs))
  while True:
   msg=pipe.recv()
   if msg[0]=='stop':break
   kind,rid,version,tree,k=msg
   if kind!='search' or version!=identity:raise ValueError('Worker request identity mismatch')
   started=time.monotonic()
   try:
    hits=search.search(query(index,tree),limit=k,count=False).hits;rows=[(search.doc(a)['rowid'][0],float(score)) for score,a in hits];pipe.send(('result',rid,identity,rows,{'query_seconds':time.monotonic()-started}))
   except Exception as e:pipe.send(('error',rid,identity,type(e).__name__,{}))
 except (EOFError,BrokenPipeError):pass
 finally:pipe.close()

class FastTantivyRetriever(AsyncTantivyRetriever):
 def __init__(self,*args,memory_limit=512*1024**2,max_restarts=2,**kwargs):
  if type(memory_limit) is not int or not 64*1024**2<=memory_limit<=2*1024**3:raise ValueError('Bounded worker memory limit required')
  if type(max_restarts) is not int or not 0<=max_restarts<=2:raise ValueError('Worker restart quota must be0..2')
  super().__init__(*args,**kwargs);self.memory_limit=memory_limit;self.max_restarts=max_restarts;self._starts=0;self._pipe=None;self._generation=None
 @property
 def available(self):
  try:live=self._native is not None and self._native.is_alive()
  except ValueError:live=False # process handle just released by its owner
  return not self._closed and (live or self._starts<=self.max_restarts)
 async def _submit(self,*a,**kw):
  from core.validation import ContractError
  try:return await super()._submit(*a,**kw)
  except (IndexIdentityError,ContractError):
   self._closed=True;self._stop();raise
 def _stamps(self):
  for name,stamp in self.manifest['_stamps'].items():
   f=Path(self.manifest['_index_path'])/name
   if (f.stat().st_size,f.stat().st_mtime_ns)!=stamp:self._closed=True;raise IndexIdentityError('Accepted native index changed')
 def _stop(self,graceful=False):
  process=self._native
  if process is None:return
  try:
   if graceful and process.is_alive():
    try:self._pipe.send(('stop',))
    except (OSError,EOFError):pass
    process.join(.5)
   if process.is_alive():process.terminate()
   process.join(2)
   if process.is_alive():process.kill();process.join(2)
   if process.is_alive():self._closed=True;raise NativeSearchError('Owned worker did not release')
  finally:
   if self._pipe:self._pipe.close()
   if not process.is_alive():process.close()
   self._pipe=None;self._native=None;self._generation=None
 def _wait(self,started):
  import psutil
  while True:
   if self._cancel_work.is_set():raise InterruptedError('Reusable search cancelled')
   if time.monotonic()-started>=self.timeout_seconds:raise TimeoutError('Reusable worker request timed out')
   if not self._native.is_alive():raise NativeSearchError('Reusable worker exited')
   try:
    m=psutil.Process(self._native.pid).memory_info()
    if max(m.rss,getattr(m,'private',m.rss))>self.memory_limit:raise NativeSearchError('Worker memory admission exceeded')
   except psutil.NoSuchProcess:raise NativeSearchError('Reusable worker disappeared') from None
   if self._pipe.poll(.02):
    try:return self._pipe.recv()
    except EOFError:raise NativeSearchError('Reusable result channel closed') from None
 def _ensure(self,started):
  if self._native is not None and self._native.is_alive():return False
  self._stop()
  if self._starts>self.max_restarts:raise NativeSearchError('Bounded worker restart quota exhausted')
  context=mp.get_context('spawn');parent,child=context.Pipe();identity=self.manifest['_identity'];self._native=context.Process(target=serve,args=(self.manifest['_index_path'],identity,child),daemon=True);self._pipe=parent;self._native.start();child.close();self._starts+=1;self._generation=uuid.uuid4().hex
  ready=self._wait(started)
  if ready!=('ready',identity,self.manifest['members']['total']):raise IndexIdentityError('Worker loaded wrong index identity or count')
  return True
 def warm(self):
  self._cancel_work.clear();started=time.monotonic()
  try:self._stamps();self._ensure(started)
  except BaseException:self._stop();raise
  return {'seconds':time.monotonic()-started,'pid':self._native.pid,'identity':self.manifest['_identity']}
 def _rank(self,tree,k):
  started=time.monotonic();rid=uuid.uuid4().hex
  try:
   self._stamps();cold=self._ensure(started);self._pipe.send(('search',rid,self.manifest['_identity'],tree,k));msg=self._wait(started)
   if len(msg)!=5 or msg[1]!=rid or msg[2]!=self.manifest['_identity']:raise IndexIdentityError('Late/cross-request result rejected')
   if msg[0]!='result':raise NativeSearchError('Reusable worker search failed')
   self._stamps();self.last_trace={'backend':'tantivy-fast-v1','request_id':rid,'worker_generation':self._generation,'worker_pid':self._native.pid,'worker_starts':self._starts,'worker_cold':cold,'native_seconds':time.monotonic()-started,'worker_metrics':msg[4],'manifest':self.manifest['_identity'],'fallback':False};return msg[3]
  except BaseException:
   self._stop();raise
 def _work(self,request,result,validate):
  if validate:return super()._work(request,result,validate)
  from rag.storage import KnowledgeStore
  from rag.corpus_index import seal,corpus_evidence
  from rag.topic_lanes import plan
  from rag.tantivy_query import ast
  from rag.context import read_adjacent_context
  from rag.contracts import RetrievalRequest,RetrievalResult,RetrievalHit
  from core.validation import validate_types,require
  validate_types(request,RetrievalRequest);require(0<request.max_results<=6 and bool(request.scenario_id.strip()),'Fast delivery requires scenario and at most6 final roots')
  if request.knowledge_version!=self.knowledge_version:raise IndexIdentityError('Fast request source snapshot mismatch')
  try:tree=ast(plan(request.query)[0][1])
  except ValueError as e:raise UnsupportedQueryError(str(e)) from None
  self._certificate=None;rows=self._rank(tree,16);seen=set();evidence=[];hits=[];chars=0;omissions=0;started=time.monotonic()
  with KnowledgeStore(self.path,readonly=True,validated_pdf_cache=True) as store:
   self._connection=store.connection;sealed=seal(store,request.knowledge_version)
   if sealed is None:raise IndexIdentityError('Original sealed source required')
   for rid,score in rows:
    if self._cancel_work.is_set():raise InterruptedError('Fast source read cancelled')
    table='corpus_chunks' if rid>0 else 'corpus_native';row=store.connection.execute('select fragment_id from '+table+' where id=?',(abs(rid),)).fetchone()
    if row is None:raise IndexIdentityError('Native hit missing original source')
    e=corpus_evidence(store,row[0],request.knowledge_version,sealed);key=hashlib.sha256(e.text.encode()).hexdigest()
    if key in seen:omissions+=1;continue
    seen.add(key)
    if chars+len(e.text)>8000:omissions+=1;continue
    evidence.append(e);chars+=len(e.text);hits.append(RetrievalHit(e.evidence_id,row[0],len(hits)+1,score,'tantivy-fast-v1-native-order-exact-body-dedup'))
    if len(evidence)>=request.max_results:break
   self.last_trace.update(body_seconds=time.monotonic()-started,root_chars=chars,candidate_limit=16,final_limit=request.max_results,selection_omissions=omissions)
   start=time.monotonic();context=None if request.context_options is None else read_adjacent_context(store,tuple(evidence),request.knowledge_version,request.context_options);self.last_trace['context_seconds']=time.monotonic()-start
   output=RetrievalResult(tuple(evidence),request.knowledge_version,hits=tuple(hits),context=context);self._certificate=(request,output);return output
 def close(self):
  self.interrupt();self._stop(graceful=True);super().close()
