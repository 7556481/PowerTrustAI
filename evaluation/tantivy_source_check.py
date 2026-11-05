"""Read-only source/neighbor acceptance, after ranking timings have ended."""
import json,time
from evaluation.tantivy_bounded_v1 import LOCAL,DB,read,save,digest
from rag.storage import KnowledgeStore
from rag.corpus_index import seal,corpus_evidence
from rag.context import read_adjacent_context
from rag.contracts import ContextOptions

def main():
 f=read(LOCAL/'freeze.json');store=KnowledgeStore(DB,readonly=True);start=time.monotonic();s=seal(store,f['source']['knowledge_version']);startup=time.monotonic()-start;out=[]
 try:
  for population in ['quality','50000']:
   result=read(LOCAL/population/'results.json')
   for row in result['topk']:
    if row['round']!=0:continue
    start=time.monotonic();roots=[]
    for h in row['hits']:
     e=corpus_evidence(store,h['fragment_id'],f['source']['knowledge_version'],s);assert digest(e.text)==h['body_sha'] and e.evidence_id==h['evidence_id'] and e.source_id==h['source_id'] and e.locator==h['locator'];store.verify_evidence(e);roots.append(e)
    body_seconds=time.monotonic()-start;start=time.monotonic();context=read_adjacent_context(store,tuple(roots),f['source']['knowledge_version'],ContextOptions(2400,6,1,True,'storage_order'))
    for item in context.items:store.verify_evidence(item.evidence)
    out.append(dict(population=population,query=row['query'],backend=row['backend'],roots=len(roots),neighbors=len(context.items),body_seconds=body_seconds,context_seconds=time.monotonic()-start,duplicate_bodies=len(roots)-len(set(digest(e.text) for e in roots)),mapping_valid=True))
  save(LOCAL/'source-read-acceptance.json',dict(passed=True,process_seal_seconds=startup,rows=out,model_calls=0));print('48 source groups and bounded neighbor groups verified,0 model')
 finally:store.close()
if __name__=='__main__':main()
