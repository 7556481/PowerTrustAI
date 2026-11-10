"""Isolated two-shard product evidence reader; production defaults unchanged."""
import asyncio,hashlib,json,sqlite3,time
from pathlib import Path
from rag.tantivy_fast_v1 import FastTantivyRetriever
from rag.tantivy_manifest import package_manifest,sha
from rag.tantivy_build import atomic
from evaluation.tantivy_shard_v16 import HOME,OLD,START,END,read

class ShardedReader(FastTantivyRetriever):
 def __init__(self,source,manifests,k):
  super().__init__(source,manifests[0],k,isolated=True)
  self.other=FastTantivyRetriever(source,manifests[1],k,isolated=True)
 def _rank(self,tree,k):
  a=super()._rank(tree,k);ta=dict(self.last_trace)
  b=self.other._rank(tree,k);tb=dict(self.other.last_trace)
  assert not set(r for r,s in a)&set(r for r,s in b),'Overlapping shards'
  merged=sorted(a+b,key=lambda x:(-x[1],x[0]))[:k]
  self.last_trace={'backend':'isolated-sharded-fast-v16','shards':[ta,tb],'merge':'score desc, signed rowid asc','candidate_limit_per_shard':k,'global_candidate_limit':k}
  return merged
 def close(self):
  try:self.other.close()
  finally:super().close()

async def run():
 from evaluation.tantivy_full_build_v1 import SOURCE,K
 from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
 from rag.storage import KnowledgeStore
 from rag.chinese_terms import terms
 proof=read(OLD/'checkpoint-recovery-v10/user-manual-once-17/after-audit.json');assert proof['passed'] and proof['checkpoint']==read(OLD/'build/checkpoint.json')
 new=read(HOME/'shard-01/acceptance.json');assert new['passed']
 for f,h in [(OLD/'build/mapping.sqlite3',proof['mapping_file_sha256']),(OLD/'build/tantivy/meta.json',proof['meta_sha256']),(OLD/'build/tantivy/.managed.json',proof['managed_sha256'])]+[(OLD/'build/tantivy'/n,v['sha256']) for n,v in proof['required_files'].items()]:
  assert sha(f)==h, 'Read-only first shard changed since audit: '+str(f)
 manifests=[]
 for ordinal,(root,count) in enumerate([(OLD/'build',START),(HOME/'shard-01',250000)]):
  accepted=HOME/f'reader-proof-{ordinal}.json';atomic(accepted,{'passed':True,'complete_id_set':True,'n':count,'origin':'existing complete checkpoint audit' if ordinal==0 else 'new process full shard audit'})
  target=HOME/f'reader-manifest-{ordinal}.json'
  package_manifest(root/'tantivy',accepted,target,knowledge_version=K,source_total=24620947,scope='isolated',build={'kind':'shards-v16','range':[0,START] if ordinal==0 else [START,END]},source_identity={'audit':str(OLD/'checkpoint-recovery-v10/user-manual-once-17/after-audit.json') if ordinal==0 else str(HOME/'shard-01/acceptance.json')})
  manifests.append(target)
 adapter=ShardedReader(SOURCE,manifests,K);results=[]
 sp=sqlite3.connect((OLD/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
 try:
  # Fixed membership probes: direct native query through the same merged rank,
  # then normal product source/context validation; no model or answer scoring.
  from rag.tantivy_query import ast
  for label,lo,hi in [('old',674,START),('new',START,END)]:
   row=sp.execute('select * from input where position=?',(lo,)).fetchone()
   query=' '.join(row[5].split()[:8]);req=RetrievalRequest(query,'isolated-two-shard-v16',RetrievalPurpose.GENERATION,K,6,ContextOptions())
   started=time.time();result=await adapter.retrieve(req);await adapter.validate_result(req,result)
   ids=[]
   with KnowledgeStore(SOURCE,readonly=True,validated_pdf_cache=True) as store:
    for e in result.evidence:
     store.verify_evidence(e)
     r=store.connection.execute('select id,text_hash from corpus_chunks where fragment_id=?',(e.provenance.fragment_id,)).fetchone()
     if r:r=(r[0]+673,r[0],r[1])
     else:
      rid=store.connection.execute('select id from corpus_native where fragment_id=?',(e.provenance.fragment_id,)).fetchone();assert rid
      r=(rid[0]-1,-rid[0],hashlib.sha256(e.text.encode()).hexdigest())
     assert hashlib.sha256(e.text.encode()).hexdigest()==r[2];ids.append(r[:2])
    if result.context:
     for ctx in result.context.items:store.verify_evidence(ctx.evidence)
   assert any(lo<=p<hi for p,rid in ids),(label,query,ids)
   results.append({'label':label,'query':query,'positions_and_ids':ids,'context_count':len(result.context.items) if result.context else 0,'seconds':time.time()-started,'trace':adapter.last_trace})
  atomic(HOME/'two-shard-read.json',{'passed':True,'results':results,'models':0,'ranking_limit':'Shard-local BM25 stats; deterministic merge is not global BM25 equivalence or quality acceptance'})
 finally:sp.close();adapter.close()

if __name__=='__main__':asyncio.run(run())
