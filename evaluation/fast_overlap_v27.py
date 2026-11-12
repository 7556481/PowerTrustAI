"""One frozen all-purpose v18 candidate. No production configuration change."""
import collections
import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path
import time
from rag.contracts import RetrievalResult

HOME = Path('D:/PowerTrustAI/data/runtime_local/fast-overlap-v27')

def enable_v18():
    import rag
    archive=Path('D:/PowerTrustAI/data/runtime_local/closeout-v26/frozen-v18-code/rag')
    if str(archive) not in rag.__path__:
        rag.__path__.insert(0,str(archive))

def query_tokens(query):
    enable_v18()
    from rag.topic_lanes import plan
    from rag.tantivy_query import ast
    from rag.tantivy_global_rank_v18 import positive
    return set(positive(ast(plan(query)[0][1])))

def select(query, evidence, max_results=3, root_chars=3600):
    from rag.chinese_terms import terms
    started=time.monotonic()
    targets=query_tokens(query)
    docs=[];seen={}
    for position,item in enumerate(evidence):
        if item.evidence_id in seen:
            if seen[item.evidence_id]!=item:raise ValueError('Conflicting original evidence identity')
            continue
        seen[item.evidence_id]=item
        docs.append((position,item,set(terms(item.text)) & targets))
    count=len(docs)
    frequencies=collections.Counter(token for _,_,tokens in docs for token in tokens)
    weights={token:math.log(1+(count-frequencies[token]+.5)/(frequencies[token]+.5)) for token in targets}
    chosen=[];covered=set();used=0;trace=[]
    while docs and len(chosen)<max_results:
        affordable=[row for row in docs if used+len(row[1].text)<=root_chars]
        if not affordable:break
        def utility(row):
            rank,item,tokens=row
            return sum(weights[t] for t in tokens-covered)/(1+len(item.text)/1200)+.05/(rank+1)
        best=max(affordable,key=lambda row:(utility(row),-row[0]))
        chosen_utility=utility(best)
        docs.remove(best);chosen.append(best[1]);covered.update(best[2]);used+=len(best[1].text)
        trace.append(dict(evidence_id=best[1].evidence_id,pool_rank=best[0]+1,chars=len(best[1].text),utility=chosen_utility))
    return tuple(chosen),dict(version='query-coverage-greedy-v27',selected=trace,root_chars=used,selection_seconds=time.monotonic()-started)

class CandidateRetriever:
    """Wider native pool, whole spans, original bounded adjacency; no extra model."""
    def __init__(self, native):
        self.native=native;self.cache_identity=('fast-overlap-v27',native.cache_identity)
        self.execution_profile=native.execution_profile;self.last_trace={};self._certificate=None
    def __getattr__(self,name):return getattr(self.native,name)
    async def retrieve(self, request):
        started=time.monotonic()
        pool=await self.native.retrieve(replace(request,max_results=6,context_options=None))
        selected,selection=select(request.query,pool.evidence,min(3,request.max_results))
        context=None if request.context_options is None else await self.native.source_context(selected,request.knowledge_version,request.context_options)
        by_id={hit.evidence_id:hit for hit in pool.hits}
        hits=tuple(replace(by_id[e.evidence_id],rank=i+1,scoring_method=by_id[e.evidence_id].scoring_method+';query-coverage-selection-v27') for i,e in enumerate(selected))
        result=RetrievalResult(selected,request.knowledge_version,pool.execution_issues,hits,context)
        self.last_trace=dict(native=dict(self.native.last_trace),selection=selection,total_seconds=time.monotonic()-started)
        self._certificate=(request,result)
        return result
    async def validate_result(self,request,result):
        if self._certificate!=(request,result):raise ValueError('Candidate result identity differs')
        await self.native.validate_evidence(result.evidence+(() if result.context is None else tuple(x.evidence for x in result.context.items)),request.knowledge_version)
    def close(self):self.native.close()
