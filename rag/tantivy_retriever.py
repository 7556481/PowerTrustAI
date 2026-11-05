"""Default-off Tantivy adapter; native query is an owned killable process."""
import multiprocessing as mp,time
from pathlib import Path
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.contracts import RetrievalResult,RetrievalHit
from rag.tantivy_manifest import load_manifest,IndexIdentityError

class NativeSearchError(RuntimeError):code='TANTIVY_SEARCH_ERROR'
class UnsupportedQueryError(RuntimeError):code='TANTIVY_UNSUPPORTED_QUERY'

def search_worker(path,tree,k,pipe):
 try:
  import tantivy
  from rag.tantivy_query import query
  started=time.monotonic();idx=tantivy.Index.open(path);idx.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());search=idx.searcher();opened=time.monotonic()
  hits=search.search(query(idx,tree),limit=k,count=False).hits;queried=time.monotonic();rows=[(search.doc(a)['rowid'][0],float(score)) for score,a in hits];finished=time.monotonic()
  pipe.send(('ok',rows,{'index_open_seconds':opened-started,'query_seconds':queried-opened,'stored_hit_seconds':finished-queried}))
 except Exception as e:pipe.send(('error',type(e).__name__))
 finally:pipe.close()

class AsyncTantivyRetriever(AsyncSQLiteBM25Retriever):
 def __init__(self,path,manifest,knowledge_version,*,isolated=False,timeout_seconds=30):
  self.manifest=load_manifest(manifest,knowledge_version,isolated=isolated);self.knowledge_version=knowledge_version;self.timeout_seconds=float(timeout_seconds)
  if not 0<self.timeout_seconds<=300:raise ValueError('Bounded positive search timeout required')
  from rag.storage import KnowledgeStore
  from rag.corpus_index import seal
  with KnowledgeStore(path,readonly=True) as source:
   source_seal=seal(source,knowledge_version)
   if source_seal is None:raise IndexIdentityError('Sealed source corpus required at initialization')
   total=source.connection.execute('select count(*) from corpus_native').fetchone()[0]+(source_seal['chunks'] if 'chunks' in source_seal else source.connection.execute('select count(*) from corpus_chunks').fetchone()[0])
   if total!=self.manifest['members']['source_total']:raise IndexIdentityError('Source member scope mismatch')
  super().__init__(path,execution_profile='topic_v4_subject_v1');self.cache_identity=('tantivy',self.manifest['_identity']);self._certificate=None;self.last_trace={};self._native=None
 def _rank(self,tree,k):
  for name,stamp in self.manifest['_stamps'].items():
   f=Path(self.manifest['_index_path'])/name
   if (f.stat().st_size,f.stat().st_mtime_ns)!=stamp:raise IndexIdentityError('Accepted index changed')
  ctx=mp.get_context('spawn');parent,child=ctx.Pipe(duplex=False);process=ctx.Process(target=search_worker,args=(self.manifest['_index_path'],tree,k,child),daemon=True);started=time.monotonic();process.start();launched=time.monotonic();child.close();self._native=process
  try:
   while not parent.poll(.02):
    if self._cancel_work.is_set():raise InterruptedError('Tantivy request cancelled')
    if time.monotonic()-started>=self.timeout_seconds:raise TimeoutError('Tantivy native search timeout')
    if not process.is_alive():raise NativeSearchError('Native process exited without result')
   try:
    payload=parent.recv();status,rows=payload[:2];metrics=payload[2] if len(payload)>2 else {}
   except EOFError:raise NativeSearchError('Native process closed result channel') from None
   for name,stamp in self.manifest['_stamps'].items():
    f=Path(self.manifest['_index_path'])/name
    if (f.stat().st_size,f.stat().st_mtime_ns)!=stamp:raise IndexIdentityError('Accepted index changed during search')
   if status!='ok':raise NativeSearchError('Native index/search failure: '+rows)
   self.last_trace={'backend':'tantivy','manifest':self.manifest['_identity'],'scope':self.manifest['scope'],'native_seconds':time.monotonic()-started,'process_start_seconds':launched-started,'worker_metrics':metrics,'fallback':False};return rows
  finally:
   release_started=time.monotonic()
   if process.is_alive():process.terminate()
   process.join(2)
   if process.is_alive():process.kill();process.join(2)
   parent.close();self._native=None
   self.last_trace.update(release_seconds=time.monotonic()-release_started,native_total_seconds=time.monotonic()-started)
   if process.is_alive():self._closed=True;raise NativeSearchError('Native process resource release failed')
 def _work(self,request,result,validate):
  # Reuse the existing source-only/citation replay paths; they never rank.
  if validate in ('saved_evidence','source_context'):
   version=request if validate=='saved_evidence' else request[0]
   if version!=self.knowledge_version:raise IndexIdentityError('Source replay snapshot mismatch')
   return super()._work(request,result,validate)
  from rag.storage import KnowledgeStore
  from rag.corpus_index import seal,corpus_evidence
  from rag.topic_lanes import plan
  from rag.tantivy_query import ast
  from rag.context import read_adjacent_context
  from core.validation import validate_types,require
  from rag.contracts import RetrievalRequest
  validate_types(request,RetrievalRequest);require(request.max_results>0 and bool(request.scenario_id.strip()),'Positive K and scenario required')
  if request.knowledge_version!=self.knowledge_version:raise IndexIdentityError('Request knowledge snapshot mismatch')
  with KnowledgeStore(self.path,readonly=True,validated_pdf_cache=True) as store:
   self._connection=store.connection;sealed=seal(store,request.knowledge_version)
   if sealed is None:raise IndexIdentityError('Sealed original corpus required')
   if validate:
    if self._certificate is None or self._certificate!=(request,result):raise IndexIdentityError('Result differs from preceding certified Tantivy request')
    for e in result.evidence+(() if result.context is None else tuple(x.evidence for x in result.context.items)):store.verify_evidence(e)
    return None
   try:tree=ast(plan(request.query)[0][1])
   except ValueError as e:raise UnsupportedQueryError(str(e)) from None
   self._certificate=None;rows=self._rank(tree,request.max_results);evidence=[];hits=[];body_started=time.monotonic()
   for rank,(rid,score) in enumerate(rows,1):
    table='corpus_chunks' if rid>0 else 'corpus_native';row=store.connection.execute('select fragment_id from '+table+' where id=?',(abs(rid),)).fetchone()
    if not row:raise IndexIdentityError('Native row has no original source member')
    e=corpus_evidence(store,row[0],request.knowledge_version,sealed);evidence.append(e);hits.append(RetrievalHit(e.evidence_id,row[0],rank,score,'tantivy-0.27.0-bm25;topic_v4_subject_v1;'+self.manifest['_identity']))
   self.last_trace['body_seconds']=time.monotonic()-body_started;context_started=time.monotonic()
   context=None if request.context_options is None else read_adjacent_context(store,tuple(evidence),request.knowledge_version,request.context_options)
   self.last_trace['context_seconds']=time.monotonic()-context_started
   output=RetrievalResult(tuple(evidence),request.knowledge_version,hits=tuple(hits),context=context);self._certificate=(request,output);return output
 async def _submit(self,*a,**kw):
  import asyncio
  try:return await super()._submit(*a,**kw)
  except asyncio.CancelledError:
   self.interrupt()
   if self._active is not None:
    try:await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(self._active)),5)
    except Exception:pass
   raise
 def interrupt(self):
  import sqlite3
  self._cancel_work.set()
  if self._connection is not None:
   try:self._connection.interrupt()
   except sqlite3.ProgrammingError:self._connection=None # the owning worker already closed it
 def close(self):self.interrupt();super().close()
