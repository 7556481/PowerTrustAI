"""Frozen ranking investigation; real adapters, source reads, zero models/builds."""
import asyncio,dataclasses,hashlib,json,sqlite3,time,sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from rag.tantivy_retriever import AsyncTantivyRetriever
from rag.tantivy_manifest import sha,IndexIdentityError
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
from rag.timing import capture_timing
from rag.tantivy_build import atomic
ROOT=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-ranking-v1')
SOURCE=Path('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3')
PACKAGES=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-product-v1')
SCOPES={'quality674':Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/quality'),'million':Path('D:/PowerTrustAI/data/retrieval_local/tantivy-supervision-v3/million')}

@contextmanager
def readonly(path):
 c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
 try:yield c
 finally:c.close()
def stat(path):s=Path(path).stat();return [s.st_size,s.st_mtime_ns]

class BoundedOriginalBM25(AsyncTantivyRetriever):
 """Only research candidate: T32 -> original FTS BM25 -> K<=3. No fallback."""
 def __init__(self,*a,reference,reference_sha,**kw):
  self.reference=Path(reference);self.reference_stamp=stat(reference);self.reference_sha=reference_sha
  if sha(reference)!=reference_sha:raise IndexIdentityError('Ranking reference file identity mismatch')
  super().__init__(*a,**kw)
  with readonly(reference) as c:
   if c.execute('select count(*) from corpus_fts').fetchone()[0]!=self.manifest['members']['total']:raise IndexIdentityError('Ranking reference population mismatch')
 def _rank(self,tree,k):
  if not 0<k<=3:raise ValueError('Frozen candidate only supports original final K<=3')
  if stat(self.reference)!=self.reference_stamp:raise IndexIdentityError('Ranking reference changed')
  start=time.monotonic();rows=super()._rank(tree,32);ids=[r[0] for r in rows]
  if not ids:return []
  from rag.tantivy_query import ast
  from rag.topic_lanes import plan
  # _work captures the exact original expression, not a special-case rewrite.
  with readonly(self.reference) as c:
   c.set_progress_handler(lambda:int(self._cancel_work.is_set() or time.monotonic()-start>=self.timeout_seconds),1000)
   t=time.monotonic()
   try:ranked=list(c.execute('select rowid,-bm25(corpus_fts) score from corpus_fts where rowid in ('+','.join('?'*len(ids))+') and corpus_fts match ? order by bm25(corpus_fts),rowid limit ?',(*ids,self.expression,k)))
   except sqlite3.OperationalError:
    if self._cancel_work.is_set():raise InterruptedError('Bounded ranking cancelled') from None
    if time.monotonic()-start>=self.timeout_seconds:raise TimeoutError('Bounded ranking deadline') from None
    raise
  self.last_trace.update(rerank_seconds=time.monotonic()-t,candidate_count=len(ids),candidate_limit=32,ranking_rule='original SQLite BM25 ascending, rowid ascending',reference_sha256=self.reference_sha)
  if stat(self.reference)!=self.reference_stamp:raise IndexIdentityError('Ranking reference changed during query')
  return ranked
 def _work(self,request,result,validate):
  if not validate:
   from rag.topic_lanes import plan
   self.expression=plan(request.query)[0][1]
  output=super()._work(request,result,validate)
  if not validate:
   output=dataclasses.replace(output,hits=tuple(dataclasses.replace(h,scoring_method='T32-original-FTS-BM25-v1') for h in output.hits));self._certificate=(request,output)
  return output
 @property
 def reference_sha(self):return self._reference_sha
 @reference_sha.setter
 def reference_sha(self,v):self._reference_sha=v

async def measure():
 freeze=json.loads((ROOT/'freeze.json').read_text(encoding='utf8'));config=json.loads((ROOT/'implementation-freeze.json').read_text(encoding='utf8'));output=ROOT/'measurements.jsonl'
 if output.exists():raise RuntimeError('Frozen measurement already started; no overwrite/retry')
 for file,digest in config['implementation_sha256'].items():
  if sha(file)!=digest:raise RuntimeError('Implementation changed after freeze: '+file)
 from rag.topic_lanes import plan
 for q in freeze['queries']:
  if plan(q['query'])[0][1]!=q['fts_expression']:raise RuntimeError('Frozen expression changed: '+q['id'])
 start=time.monotonic();deadline=start+3600;records=[]
 # Startup identity hashing is measured separately and never charged per query.
 for scope,folder in SCOPES.items():
  t=time.monotonic();manifest=PACKAGES/scope/'manifest.json';knowledge=json.loads(manifest.read_text(encoding='utf8'))['knowledge_version'];native=AsyncTantivyRetriever(SOURCE,manifest,knowledge,isolated=True)
  candidate=BoundedOriginalBM25(SOURCE,manifest,knowledge,isolated=True,reference=folder/'fts.sqlite3',reference_sha=config['references'][scope]['sha256']);candidate.reference_sha=config['references'][scope]['sha256']
  baseline=AsyncSQLiteBM25Retriever(SOURCE,execution_profile='topic_v4_subject_v1');baseline.rank_cache=None
  atomic(ROOT/(scope+'-startup.json'),{'seconds':time.monotonic()-t,'includes_source_seal_once_per_process':True,'not_per_query':True})
  adapters={'fts':baseline,'tantivy':native,'protected':candidate};names=list(adapters)
  def sample_rank(unused,raw,k):
   from rag.topic_lanes import plan
   with readonly(folder/'fts.sqlite3') as c:
    c.row_factory=sqlite3.Row;c.set_progress_handler(lambda:int(time.monotonic()>=deadline),10000)
    return c.execute('select rowid,bm25(corpus_fts) score from corpus_fts where corpus_fts match ? order by score,rowid limit ?',(plan(raw)[0][1],k)).fetchall()
  try:
   for rd in range(3):
    queries=freeze['queries'] if rd%2==0 else list(reversed(freeze['queries']))
    for q in queries:
     for backend in names[rd:]+names[:rd]:
      if time.monotonic()>=deadline:raise TimeoutError('Frozen batch deadline; no more submissions')
      adapter=adapters[backend];request=RetrievalRequest(q['query'],'synthetic_fixture',RetrievalPurpose.GENERATION,knowledge,3,ContextOptions())
      wall=time.monotonic();record={'scope':scope,'query':q['id'],'round':rd,'backend':backend,'status':'unknown'}
      try:
       with capture_timing() as timing:
        if backend=='fts':
         with patch('rag.topic_lanes.rank',sample_rank):result=await adapter.retrieve(request)
        else:result=await adapter.retrieve(request)
       record.update(seconds=time.monotonic()-wall,spans=timing.records,trace=dict(getattr(adapter,'last_trace',{})))
       t=time.monotonic();await adapter.validate_result(request,result);record['validation_seconds']=time.monotonic()-t
       assert len(result.evidence)<=3
       assert result.context is not None and result.context.char_count<=2400 and len(result.context.items)<=6
       assert getattr(adapter,'_native',None) is None
       record.update(status='ok',hits=[dataclasses.asdict(h) for h in result.hits],roots=[dataclasses.asdict(e) for e in result.evidence],neighbors=[dataclasses.asdict(e.evidence) for e in result.context.items],context_chars=result.context.char_count,resource_released=True)
      except Exception as e:
       record.update(status='error',error=type(e).__name__,seconds=time.monotonic()-wall)
       if getattr(adapter,'_native',None) is not None or (adapter._active is not None and not adapter._active.done()):raise RuntimeError('Unreleased request; stop batch') from e
      with output.open('a',encoding='utf8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
      records.append(record);print(scope,q['id'],rd,backend,record['status'],round(record['seconds'],3),flush=True)
  finally:
   for a in adapters.values():a.close()
 atomic(ROOT/'measurement-receipt.json',{'n':len(records),'completed':True,'wall_seconds':time.monotonic()-start,'model_calls':0,'full_build':False})
if __name__=='__main__':asyncio.run(measure())
