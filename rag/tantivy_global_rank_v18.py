"""Opt-in global token-IDF scoring of the bounded native candidate union."""
import math,time,sqlite3,hashlib,collections
from pathlib import Path
from rag.tantivy_diagnostic_v18 import DiagnosticRetriever
from rag.tantivy_manifest import IndexIdentityError

def positive(tree):
 if tree is None:return []
 if tree[0]=='phrase':return tree[1]
 return positive(tree[1])+(positive(tree[2]) if tree[0]!='not' else [])

def score(tf,weights):return sum(w*tf[t]/(tf[t]+1) for t,w in weights.items() if tf[t])

class GlobalIDFRetriever(DiagnosticRetriever):
 def __init__(self,*args,spool_path,**kw):
  self.collect_statistics=True;self.spool=Path(spool_path);self.spool_stamp=(self.spool.stat().st_size,self.spool.stat().st_mtime_ns);super().__init__(*args,**kw)
 def _rank(self,tree,k):
  started=time.monotonic();super()._rank(tree,k);metrics=self.last_trace['worker_metrics'];n=self.manifest['members']['total'];df=metrics['global_token_df'];weights={t:math.log(1+(n-df[t]+.5)/(df[t]+.5)) for t in set(positive(tree))}
  if (self.spool.stat().st_size,self.spool.stat().st_mtime_ns)!=self.spool_stamp:raise IndexIdentityError('Frozen input changed')
  tick=time.monotonic();rows=[]
  con=sqlite3.connect(self.spool.as_uri()+'?mode=ro',uri=True)
  try:
   for local in metrics['per_shard_candidates']:
    for rid,old in local:
     if self._cancel_work.is_set():raise InterruptedError('Candidate scoring cancelled')
     if time.monotonic()-started>=self.timeout_seconds:raise TimeoutError('Candidate scoring timed out')
     row=con.execute('select rowid,terms_sha,terms from input where position=?',(-rid-1 if rid<0 else rid+673,)).fetchone()
     if row is None or row[0]!=rid or hashlib.sha256(row[2].encode()).hexdigest()!=row[1]:raise IndexIdentityError('Candidate input identity/hash differs')
     rows.append((rid,score(collections.Counter(row[2].split()),weights)))
  finally:con.close()
  result=sorted(rows,key=lambda z:(-z[1],z[0]))[:k];self.last_trace.update(backend='tantivy-global-idf-v18',score_scope='global exact token DF; saturated TF; no length normalization; bounded union only',merged_candidates=result,rerank_seconds=time.monotonic()-tick);return result
 def _work(self,*args):
  result=super()._work(*args)
  if not args[2]:
   from dataclasses import replace
   result=replace(result,hits=tuple(replace(h,scoring_method='global-token-idf-saturated-tf-v18') for h in result.hits));self._certificate=(args[0],result)
  return result
