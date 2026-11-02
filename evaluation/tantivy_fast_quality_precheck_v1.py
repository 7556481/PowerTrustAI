"""Single non-model development check on existing674, not full-corpus timing."""
import asyncio,dataclasses,json,time
from pathlib import Path
from rag.tantivy_fast_v1 import FastTantivyRetriever
from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
from rag.tantivy_build import atomic
from rag.tantivy_manifest import sha
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K
async def run():
 output=ROOT/'quality674-fast-precheck.json'
 if output.exists():raise RuntimeError('Precheck already recorded; no overwrite')
 plan=json.loads((ROOT/'plan.json').read_text(encoding='utf8'));queries=[q for q in plan['queries'] if q['id'] in ('Q10','E3','E4')];manifest=ROOT.parent/'tantivy-product-v1/quality674/manifest.json'
 atomic(ROOT/'quality674-fast-precheck-freeze.json',{'queries':queries,'manifest_sha256':sha(manifest),'implementation_sha256':sha('rag/tantivy_fast_v1.py'),'scope':'existing674 only, development check, no full-corpus/performance claim','models':0})
 started=time.monotonic();a=FastTantivyRetriever(SOURCE,manifest,K,isolated=True);warm=a.warm();rows=[]
 try:
  startup=time.monotonic()-started
  for q in queries:
   req=RetrievalRequest(q['query'],'voltage_stability_reactive_support',RetrievalPurpose.GENERATION,K,6,ContextOptions());tick=time.monotonic();r=await a.retrieve(req);await a.validate_result(req,r)
   rows.append({'id':q['id'],'seconds':time.monotonic()-tick,'roots':[dataclasses.asdict(e) for e in r.evidence],'neighbors':[dataclasses.asdict(x.evidence) for x in r.context.items],'trace':a.last_trace});atomic(output,{'startup_seal_seconds':startup,'warm':warm,'rows':rows,'models':0,'scope':'674, not full-corpus, no speed comparison'})
 finally:a.close()
if __name__=='__main__':asyncio.run(run())
