"""Independent one-case repair validation after a stopped batch; remaining cap9."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
from evaluation.reliability_trial import ROOT,DB,load,save_new,digest,LoggedAgent

OUT=ROOT/'data/retrieval_local/deepseek/reliability-v1-repair1'
PREVIOUS=OUT.parent/'reliability-v1-patch1'

def prepare():
    OUT.mkdir(exist_ok=True)
    first=load(OUT.parent/'reliability-v1/live-summary-v1.json');previous=load(PREVIOUS/'live-progress-v1.json')
    assert first['actual_model_calls']+previous['actual_model_calls']==51
    row=next(r for r in previous['runs'] if r['scenario']=='jurisdiction')
    assert not row['initial']['execution_issues']
    plan=load(PREVIOUS/'plan-v1.json');paths=list(plan['source_sha256'])+[str(Path(__file__).resolve())]
    save_new(OUT/'plan-v1.json',{'scope':'INDEPENDENT REPAIR ONLY; NO INITIAL RERUN','prior_calls':51,'cap':9,'worst':8,
        'knowledge_version':plan['knowledge_version'],'model_id':plan['model_id'],'source_sha256':{p:digest(p) for p in paths},
        'original_initial':str(PREVIOUS/'jurisdiction-initial.json'),'frozen_case':next(c for c in plan['cases'] if c['name']=='jurisdiction')})

async def live(adapter,domain,settings):
    from evaluation.archive_replay import restore
    from harness.contracts import HarnessResult,RunBudget,RetrievalSettings
    from core.models import TaskRequest,TaskMode
    from agents.contracts import RevisionInput
    from agents.revision import ModelRevisionAgent
    from agents.evidence_verification import ModelEvidenceVerificationAgent
    from agents.power_domain_review import ModelPowerDomainReviewAgent
    from services.claim_extractor import ModelClaimExtractor
    from harness.runtime import OfflineHarness
    from harness.policy import LimitedRepairPolicy
    from core.validation import validate_revision
    from services.evidence_scope import validate_snapshot
    from model_adapter.runtime import ModelBudget,model_scope
    from rag.retriever import AsyncSQLiteBM25Retriever
    from tools.unit_conversion import UnitConversionTool
    from harness.deepseek_trial import fee_summary
    from evaluation.evidence_delivery_report import stage_complete
    plan=load(OUT/'plan-v1.json');gate=load(OUT/'offline-validated-v1.json')
    assert gate['passed'] and settings.model_id==plan['model_id'] and all(digest(p)==h for p,h in plan['source_sha256'].items())
    if (OUT/'live-progress-v1.json').exists():raise FileExistsError('No automatic repeat')
    # Read canonical persisted JSON, not asdict tuples in memory. Strict archive restoration stays unchanged.
    initial=restore(load(plan['original_initial']),HarnessResult);req=restore(plan['frozen_case']['request'],TaskRequest)
    decision=LimitedRepairPolicy().decide(initial.verification_output,initial.domain_output,RunBudget(max_revision_rounds=1),0)
    row={'scenario':'jurisdiction','initial_policy':asdict(decision),'revision_status':'not_started'};records=[];start=perf_counter()
    diag=OUT/'response-diagnostics-v1';inputs=OUT/'actual-inputs-v1';diag.mkdir();inputs.mkdir()
    def checkpoint():
        value={'model_id':settings.model_id,'knowledge_version':plan['knowledge_version'],'cap':9,'actual_model_calls':len(records),'prior_calls':51,'model_records':records,'runs':[row],
            'cost_estimate':fee_summary(records),'wall_ms':int((perf_counter()-start)*1000)}
        (OUT/'live-progress-v1.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return value
    checkpoint()
    if decision.kind.value!='revise':row['stop']='policy_does_not_require_revision';save_new(OUT/'live-summary-v1.json',checkpoint());return
    budget=ModelBudget(2,deadline=perf_counter()+180);revised=None
    try:
        with model_scope(budget):
            revised=await LoggedAgent(ModelRevisionAgent(adapter,settings,diagnostic_dir=diag,protocol_version=2),inputs,'revision').run(
                RevisionInput(req,initial.answer,initial.verification_output,initial.domain_output,initial.evidence,
                    decision.reasons+('Retain source qualifications and distinguish quoted user errors from corrected assertions.',),initial.evidence_bindings,plan['knowledge_version']))
        validate_revision(revised,initial.answer,initial.evidence,initial.verification_output.findings+initial.domain_output.findings)
        validate_snapshot(revised.evidence_snapshot,revised.answer)
    except Exception as exc:row['stop']='revision_failed';row['safe_error']={'type':type(exc).__name__,'code':getattr(exc,'code',None)}
    records.extend(asdict(r) for r in budget.records);checkpoint()
    if revised:
        row['revision']=asdict(revised);save_new(OUT/'jurisdiction-revision.json',asdict(revised))
        with AsyncSQLiteBM25Retriever(DB) as retriever:
            harness=OfflineHarness(None,LoggedAgent(ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=diag,schema_version=9),inputs,'verification'),
                LoggedAgent(ModelPowerDomainReviewAgent(domain,settings,diagnostic_dir=diag,protocol_version=3),inputs,'domain'),None,
                ModelClaimExtractor(adapter,settings,diagnostic_dir=diag,protocol_version=5),policy=LimitedRepairPolicy(),retriever=retriever,retrieval_settings=RetrievalSettings(),unit_tool=UnitConversionTool())
            from dataclasses import replace
            result=await harness.run(replace(req,mode=TaskMode.ASSESS_EXISTING,existing_answer=revised.answer,provided_evidence=initial.evidence),
                RunBudget(max_model_calls=6,max_revision_rounds=0,max_duration_seconds=500,step_timeout_seconds=180),knowledge_version=plan['knowledge_version'],
                generation_snapshot=revised.evidence_snapshot,indexed_reference_ids=tuple(e.evidence_id for e in initial.evidence))
        row['rereview']=asdict(result);records.extend(asdict(r) for r in result.model_records);save_new(OUT/'jurisdiction-rereview.json',asdict(result))
        row['required_stages_complete']=stage_complete(row['rereview'])
        if result.verification_output and result.domain_output:row['final_policy']=asdict(LimitedRepairPolicy().decide(result.verification_output,result.domain_output,RunBudget(max_revision_rounds=1),1))
    assert len(records)<=9 and all(digest(p)==h for p,h in plan['source_sha256'].items())
    save_new(OUT/'live-summary-v1.json',checkpoint());print(json.dumps({'calls':len(records),'complete':row.get('required_stages_complete',False),'stop':row.get('stop')}))

if __name__=='__main__':
    import sys,os
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['live']:
        from harness.deepseek_trial import load_project_env
        from model_adapter.contracts import ModelSettings
        from model_adapter.deepseek import create_adapter
        load_project_env();settings=ModelSettings(os.environ['DEEPSEEK_MODEL_ID'],90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')
        adapter=create_adapter(settings);domain=create_adapter(settings)
        try:asyncio.run(live(adapter,domain,settings))
        finally:adapter.close();domain.close()
    else:raise ValueError('Use prepare or live')
