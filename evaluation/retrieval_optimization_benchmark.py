"""Explicit new diagnostic requests; full bodies compared in memory, never copied."""
import argparse,asyncio,hashlib,json,time,ctypes
from pathlib import Path
from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
from rag.storage import KnowledgeStore
from rag.corpus_index import seal
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.timing import capture_timing

def memory(pid=None):
    if not hasattr(ctypes,'windll'):return None
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ('peak','current','qp','q','qnp','qn','page','peak_page')]
    c=Counters();c.cb=ctypes.sizeof(c)
    if pid is None:handle=ctypes.c_void_p(-1)
    else:
        ctypes.windll.kernel32.OpenProcess.restype=ctypes.c_void_p
        handle=ctypes.windll.kernel32.OpenProcess(0x410,False,pid)
        if not handle:return None
    try:
        if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle if pid is not None else -1),ctypes.byref(c),c.cb):return None
    finally:
        if pid is not None:ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))
    return {'rss':c.current,'process_peak_rss':c.peak}

async def compare(index,freeze,output):
    profiles={p:AsyncSQLiteBM25Retriever(index,execution_profile=p) for p in ('baseline_v1','topic_v3_rank_v1')}
    records=[];comparisons=[];stored={}
    def save():output.write_text(json.dumps({'version':'retrieval-optimization-benchmark-v1','not_historical_replay':True,'measurements':records,'comparisons':comparisons},indent=2)+'\n',encoding='utf-8')
    try:
        for q in freeze['queries']:
            request=RetrievalRequest(q['query'],freeze['scenario_id'],RetrievalPurpose(q['purpose']),freeze['knowledge_version'],freeze['max_results'],ContextOptions(**freeze['context_options']))
            for profile in profiles:
                with capture_timing(retrieval_id=q['id']) as log:
                    start=time.perf_counter();result=await profiles[profile].retrieve(request);await profiles[profile].validate_result(request,result);seconds=time.perf_counter()-start
                stored[(q['id'],profile)]=result
                phases={name:sum(s['seconds'] for s in log.records if s['phase']==name) for name in ('query_prepare','fts_execute_fetch_sort','body_evidence_construct','adjacent_context','result_validation')}
                row={'id':q['id'],'profile':profile,'iteration':0,'seconds':seconds,'segments':phases,'rank_cache_hit':any(s.get('rank_cache_hit') for s in log.records),'core_count':len(result.evidence),'context_count':0 if result.context is None else len(result.context.items),'memory':memory()}
                records.append(row);save();print(json.dumps(row),flush=True)
            old,new=(stored[(q['id'],p)] for p in profiles)
            comparisons.append({'id':q['id'],'core_body_identity_exact':old.evidence==new.evidence,'context_exact':old.context==new.context,'fragment_order_exact':tuple(h.fragment_id for h in old.hits)==tuple(h.fragment_id for h in new.hits),'scores_exact':tuple(h.score for h in old.hits)==tuple(h.score for h in new.hits),'query_sha256':hashlib.sha256(q['query'].encode()).hexdigest()});save()
        slow=sorted(freeze['queries'],key=lambda q:next(r['seconds'] for r in records if r['id']==q['id'] and r['profile']=='baseline_v1'),reverse=True)[:2]
        for q in slow:
            request=RetrievalRequest(q['query'],freeze['scenario_id'],RetrievalPurpose(q['purpose']),freeze['knowledge_version'],freeze['max_results'],ContextOptions(**freeze['context_options']))
            for profile in profiles:
                with capture_timing(retrieval_id=q['id']) as log:
                    start=time.perf_counter();result=await profiles[profile].retrieve(request);await profiles[profile].validate_result(request,result);seconds=time.perf_counter()-start
                assert result==stored[(q['id'],profile)]
                row={'id':q['id'],'profile':profile,'iteration':1,'seconds':seconds,'rank_cache_hit':any(s.get('rank_cache_hit') for s in log.records),'memory':memory()}
                records.append(row);save();print(json.dumps(row),flush=True)
    finally:
        for r in profiles.values():r.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--index',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    f=json.loads(a.freeze.read_text(encoding='utf-8'));start=time.perf_counter()
    with KnowledgeStore(a.index,readonly=True) as store:seal(store,f['knowledge_version'])
    print('Normal complete publication seal checked; startup seconds',time.perf_counter()-start,flush=True)
    asyncio.run(compare(a.index,f,a.output))
if __name__=='__main__':main()
