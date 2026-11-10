"""Explicit isolated shard reader: one reusable process, finite fanout, no fallback."""
import hashlib,json,multiprocessing as mp,time,uuid
from rag.tantivy_fast_v1 import FastTantivyRetriever
from rag.tantivy_manifest import load_manifest,IndexIdentityError

def serve_shards(paths,identity,pipe):
 try:
  import tantivy
  from rag.tantivy_query import query
  opened=[];count=0
  for path in paths:
   index=tantivy.Index.open(path);index.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());search=index.searcher();opened.append((index,search));count+=search.num_docs
  pipe.send(('ready',identity,count))
  while True:
   msg=pipe.recv()
   if msg[0]=='stop':break
   kind,rid,version,tree,k=msg
   if kind!='search' or version!=identity or not 0<k<=16:raise ValueError('Shard request identity/budget mismatch')
   started=time.monotonic();candidates=[];segments=[]
   for index,search in opened:
    t=time.monotonic();hits=search.search(query(index,tree),limit=k,count=False).hits
    candidates.extend((search.doc(a)['rowid'][0],float(score)) for score,a in hits);segments.append(time.monotonic()-t)
   t=time.monotonic();ids=[r for r,s in candidates]
   if len(ids)!=len(set(ids)):raise ValueError('Overlapping shard member IDs')
   rows=sorted(candidates,key=lambda x:(-x[1],x[0]))[:k]
   pipe.send(('result',rid,identity,rows,{'query_seconds':time.monotonic()-started,'shard_seconds':segments,'merge_seconds':time.monotonic()-t,'candidate_count':len(candidates),'shard_count':len(paths)}))
 except (EOFError,BrokenPipeError):pass
 except BaseException as e:
  try:pipe.send(('fatal',type(e).__name__))
  except (EOFError,BrokenPipeError):pass
 finally:pipe.close()

class ShardedTantivyRetriever(FastTantivyRetriever):
 def __init__(self,source,manifests,k,*,memory_limit=512*1024**2):
  if not 1<=len(manifests)<=90:raise IndexIdentityError('Bounded1..90 shards required')
  super().__init__(source,manifests[0],k,isolated=True,memory_limit=memory_limit)
  self._shards=[self.manifest]+[load_manifest(p,k,isolated=True) for p in manifests[1:]]
  total=sum(m['members']['total'] for m in self._shards)
  identity=hashlib.sha256(json.dumps([m['_identity'] for m in self._shards]).encode()).hexdigest()
  self.manifest=dict(self.manifest,_identity=identity,members={'total':total,'source_total':self._shards[0]['members']['source_total']})
  self.cache_identity=('tantivy-sharded-v17',identity)
 def _stamps(self):
  from pathlib import Path
  for m in self._shards:
   for name,stamp in m['_stamps'].items():
    f=Path(m['_index_path'])/name
    if (f.stat().st_size,f.stat().st_mtime_ns)!=stamp:self._closed=True;raise IndexIdentityError('Accepted shard changed')
 def _ensure(self,started):
  if self._native is not None and self._native.is_alive():return False
  self._stop()
  if self._starts>self.max_restarts:raise IndexIdentityError('Shard worker restart quota exhausted')
  ctx=mp.get_context('spawn');parent,child=ctx.Pipe();identity=self.manifest['_identity']
  self._native=ctx.Process(target=serve_shards,args=([m['_index_path'] for m in self._shards],identity,child),daemon=True);self._pipe=parent;self._native.start();child.close();self._starts+=1;self._generation=uuid.uuid4().hex
  if self._wait(started)!=('ready',identity,self.manifest['members']['total']):raise IndexIdentityError('Shard identity/count mismatch')
  return True
 def _rank(self,tree,k):
  rows=super()._rank(tree,k)
  self.last_trace.update(backend='tantivy-sharded-v17',score_scope='per-shard BM25; score desc, signed rowid asc',shard_count=len(self._shards))
  return rows
 def _work(self,request,result,validate):
  output=super()._work(request,result,validate)
  if not validate:
   from dataclasses import replace
   output=replace(output,hits=tuple(replace(h,scoring_method='tantivy-sharded-v17-local-bm25-merge-exact-body-dedup') for h in output.hits))
   self._certificate=(request,output)
  return output
