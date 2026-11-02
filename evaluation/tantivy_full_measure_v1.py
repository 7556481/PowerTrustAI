"""One frozen full-corpus retrieval comparison, actual adapters, no models."""
import asyncio,dataclasses,json,time,hashlib,sqlite3
from pathlib import Path
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.tantivy_fast_v1 import FastTantivyRetriever
from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
from rag.timing import capture_timing
from rag.tantivy_build import atomic
from rag.tantivy_manifest import sha,IndexIdentityError
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K
from evaluation.tantivy_full_controller_v1 import idle

async def run():
 if not (ROOT/'acceptance-complete.json').exists():raise RuntimeError('Full index not accepted; no comparison')
 output=ROOT/'full-measurements.jsonl'
 if output.exists():raise RuntimeError('Comparison already started; no overwrite or second batch')
 plan=json.loads((ROOT/'plan.json').read_text(encoding='utf8'));manifest=ROOT/'accepted/manifest.json'
 from rag.topic_lanes import plan as make_query
 from rag.tantivy_query import ast
 queries=[]
 for q in plan['queries']:
  e=make_query(q['query'])[0][1]
  if q.get('fts_expression') is not None and e!=q['fts_expression']:raise RuntimeError('Original frozen expression changed')
  queries.append(dict(q,fts_expression=e,tantivy_tree=ast(e)))
 files=['rag/tantivy_fast_v1.py','backend/assembly.py','backend/config.py','rag/topic_lanes.py','rag/chinese_terms.py','evaluation/tantivy_full_measure_v1.py']
 frozen={'queries':queries,'implementation_sha256':{f:sha(f) for f in files},'index_manifest_sha256':sha(manifest),'original_source_stat':[SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns],'started_wall':time.time(),'deadline':time.time()+4*3600,'rounds':3,'order':'baseline/fast alternated each round; reverse query order on odd round','cache':'OS not cleared; ranking cache off','budgets':{'baseline_roots':3,'fast_candidates':16,'fast_roots':6,'fast_root_chars':8000,'context_chars':2400},'model_calls':0}
 atomic(ROOT/'offline-freeze.json',frozen);started=time.monotonic();fast=FastTantivyRetriever(SOURCE,manifest,K,isolated=True);warm=fast.warm();baseline=AsyncSQLiteBM25Retriever(SOURCE,execution_profile='topic_v4_subject_v1');baseline.rank_cache=None;atomic(ROOT/'offline-startup.json',{'seconds':time.monotonic()-started,'worker':warm,'source_seal_once':True});records=[]
 try:
  for rd in range(3):
   for q in (queries if rd%2==0 else list(reversed(queries))):
    for name,a in ([('baseline',baseline),('fast',fast)] if rd%2==0 else [('fast',fast),('baseline',baseline)]):
     while not idle():
      if time.time()>=frozen['deadline']:raise TimeoutError('Paused comparison expired')
      await asyncio.sleep(.5)
     if time.time()>=frozen['deadline']:raise TimeoutError('Full comparison expired')
     if any(sha(f)!=h for f,h in frozen['implementation_sha256'].items()):raise RuntimeError('Frozen implementation changed')
     r={'query':q['id'],'backend':name,'round':rd,'started_wall':time.time()};request=RetrievalRequest(q['query'],'voltage_stability_reactive_support',RetrievalPurpose.GENERATION,K,6 if name=='fast' else 3,ContextOptions());tick=time.monotonic()
     try:
      with capture_timing() as timing:
       result=await asyncio.wait_for(a.retrieve(request),110);retrieved=time.monotonic();await asyncio.wait_for(a.validate_result(request,result),110)
      r.update(status='ok',total_seconds=time.monotonic()-tick,retrieve_seconds=retrieved-tick,validation_seconds=time.monotonic()-retrieved,roots=[dataclasses.asdict(e) for e in result.evidence],neighbors=[dataclasses.asdict(e.evidence) for e in result.context.items],hits=[dataclasses.asdict(h) for h in result.hits],context_chars=result.context.char_count,trace=dict(getattr(a,'last_trace',{})),spans=timing.records)
      assert len(result.evidence)<=(6 if name=='fast' else 3) and result.context.char_count<=2400
     except Exception as e:
      if a._active is not None and not a._active.done():
       a.interrupt()
       try:await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(a._active)),10)
       except Exception:pass
      r.update(status='error',error=type(e).__name__,total_seconds=time.monotonic()-tick)
      if a._active is not None and not a._active.done():raise RuntimeError('Unreleased query; stop comparison') from e
     with output.open('a',encoding='utf8') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
     records.append(r);print(q['id'],rd,name,r['status'],round(r['total_seconds'],3),flush=True)
     if r['status']=='error' and r.get('error') in ('IndexIdentityError','DatabaseError','OperationalError','ResourceCleanupError'):raise RuntimeError('Shared identity/storage failure; stop comparison')
 finally:
  fast.close();baseline.close();atomic(ROOT/'offline-receipt.json',{'completed_reads':len(records),'expected_reads':144,'ended':time.time(),'models':0,'worker_released':fast._native is None})
if __name__=='__main__':asyncio.run(run())
