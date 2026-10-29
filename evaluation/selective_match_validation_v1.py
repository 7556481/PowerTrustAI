"""One fixed real-library retrieval validation. Zero model/env entry points."""
import asyncio,json,time,subprocess,statistics
from pathlib import Path
from dataclasses import asdict
from backend.assembly import ComponentFactory
from backend.serialization import wire
from core.models import TaskRequest,TaskMode
from harness.retrieval import RetrievalSession
from harness.contracts import RunBudget,RetrievalSettings
from rag.contracts import ContextOptions,RetrievalPurpose
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.selective_match import plan
from evaluation.archive_replay import restore
from evaluation.selective_match_diagnosis_v1 import LOCAL,read
from evaluation.source_first_modality_v6 import material
from evaluation.source_first_real_v3 import configuration
from evaluation.source_first_live_v2 import sources
from evaluation.retrieval_rank_v7 import idle
from evaluation.natural_draft_audit_v1 import save,sha

async def run():
    root=LOCAL/'validation';assert not root.exists(),'Unique validation; no resume/refill'
    assert idle(),'User work active'
    assert read(LOCAL/'diagnosis/complete.json')['df_queries']==24
    sel=read(LOCAL/'selection-before-code.json');assert sha(sel)==read(LOCAL/'selection-identity.json')['sha256']
    mats=read(LOCAL/'materials.json');assert sha(mats)==read(LOCAL/'materials-identity.json')['sha256']
    c=configuration(material());f=ComponentFactory(c);t=time.perf_counter();f.warm_corpus_index();seal=time.perf_counter()-t
    frozen_sources=sources()
    save(root/'freeze.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=frozen_sources,selection_sha=sha(sel),materials_sha=sha(mats),candidate_plans={q['id']:plan(q['query']) for q in sel['cases']},seal_seconds=seal,cap_groups=72,cap_seconds=3600,model_calls=0,cache='Fresh adapter and session each group; no ranking cache reuse; OS cache not cleared',baseline='topic_v4_subject_v1 original SQL',candidate='selective_match_v1',production_switched=False))
    began=time.perf_counter();records=[];stopped=None
    try:
        for slot in sel['schedule']:
            q=next(x for x in sel['cases'] if x['id']==slot['query'])
            for path in slot['order']:
                assert idle(),'User work became active; stop without refill'
                if len(records)>=72 or time.perf_counter()-began>=3600:
                    stopped='execution cap';break
                n=len(records)+1;save(root/'admissions'/f'{n:02d}.json',dict(slot=slot,path=path,elapsed=time.perf_counter()-began))
                profile='topic_v4_subject_v1' if path=='baseline' else 'selective_match_v1'
                r=AsyncSQLiteBM25Retriever(c.index_db,execution_profile=profile)
                budget=restore(q['budget'],RunBudget);opts=q['settings']
                settings=RetrievalSettings(opts['max_results'],restore(opts['context_options'],ContextOptions) if opts['context_options'] else None)
                request=TaskRequest('selective-fixed-'+q['id'],TaskMode.ASSESS_EXISTING,opts['scenario_id'],q['query'])
                start=time.perf_counter()
                session=RetrievalSession(r,c.knowledge_version,settings,budget,min(start+budget.max_duration_seconds,began+3600),())
                session.calls=q['initial_calls'];session.chars=q['initial_chars']
                delivery=None
                try:
                    delivery=await session.retrieve(RetrievalPurpose.VERIFICATION,request,None,(),query_override=q['query'],fact_query=True)
                finally:
                    # Original baseline keeps its production cancellation behavior.
                    # This experiment must nevertheless physically drain its own
                    # timed-out connection before admitting the next group.
                    if r._active is not None and not r._active.done():
                        r.interrupt()
                        try:await asyncio.shield(asyncio.wrap_future(r._active))
                        except Exception:pass
                    r.close()
                row=dict(number=n,query=q['id'],round=slot['round'],path=path,seconds=time.perf_counter()-start,delivery=wire(delivery),selective_work=None if r.last_selective_work is None else wire(r.last_selective_work),physical_worker_released=r._active is None or r._active.done())
                records.append(row);save(root/'groups'/f'{n:02d}.json',row)
                save(root/'progress.json',dict(groups=len(records),seconds=time.perf_counter()-began))
                print(q['id'],slot['round'],path,delivery.record.outcome,round(row['seconds'],3),flush=True)
            if stopped:break
        assert sources()==frozen_sources,'Source changed during fixed batch'
        comparisons=[]
        for q in sel['cases']:
            rows=[x for x in records if x['query']==q['id']];pairs=[]
            for rnd in (1,2,3):
                a=next((x for x in rows if x['round']==rnd and x['path']=='baseline'),None);b=next((x for x in rows if x['round']==rnd and x['path']=='candidate'),None)
                if a and b:pairs.append(dict(round=rnd,baseline=a['seconds'],candidate=b['seconds'],saving=a['seconds']-b['seconds'],reduction=1-b['seconds']/a['seconds']))
            if len(pairs)==3:
                a=statistics.median(x['baseline'] for x in pairs);b=statistics.median(x['candidate'] for x in pairs)
                comparisons.append(dict(query=q['id'],baseline_median=a,candidate_median=b,saving=a-b,reduction=1-b/a,improving_rounds=sum(x['saving']>0 for x in pairs),material_regression_rounds=sum(x['candidate']>x['baseline']*1.2 and -x['saving']>1 for x in pairs),pairs=pairs))
        perf=len(comparisons)==12 and all(x['saving']>=5 and x['reduction']>=.5 and x['improving_rounds']>=2 for x in comparisons[:2]) and all(x['material_regression_rounds']<2 for x in comparisons[2:])
        save(root/'summary.json',dict(groups=len(records),seconds=time.perf_counter()-began,seal_seconds=seal,stopped=stopped,comparisons=comparisons,performance_gate=perf,quality_gate='pending manual full-body review',model_calls=0,source_unchanged=True))
    except BaseException as exc:
        save(root/'stopped.json',dict(error=type(exc).__name__,reason=str(exc),groups=len(records),seconds=time.perf_counter()-began,no_refill=True));raise

if __name__=='__main__':asyncio.run(run())
