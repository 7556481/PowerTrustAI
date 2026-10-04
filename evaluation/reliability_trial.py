"""One frozen six-case reliability batch, global paid cap60, no hidden retries."""
import argparse
import asyncio
from dataclasses import asdict,fields,replace
import json
import os
from pathlib import Path
from time import perf_counter
from evaluation.evidence_delivery_trial import ROOT,DB,load,save_new,digest,LoggedAgent,SCENARIOS,request
from evaluation.reliability_archive_audit import SOURCE
from evaluation.evidence_delivery_report import stage_complete

DEFAULT_OUT=ROOT/'data/retrieval_local/deepseek/reliability-v1'
CHECKPOINTS={
 'definition':'Preserve QV/contingency scope; normal voltage alone is not a plant-specific stability study.',
 'cross_fragment':'Check cooling, capability ratings, active power and excitation limiter conditions; no implicit cross-page completion.',
 'quantity':'Three explicitly named ratings plus active power is not four ratings; Q in MW warns; 230 kV=230000 V supported by actual scalar tool; quotation of old wrong count is not endorsement.',
 'jurisdiction':'Retain frozen incorrect China mandatory-applicability assertion; review bounded NERC/WECC scope, not all Chinese law.',
 'missing_engineering':'Missing model/operating point/limits/contingencies; limited answer asks concrete inputs, no simulation claim.',
 'insufficient_evidence':'Do not invent Chinese110kV switching setpoint; index applicability is not official PDF text; delivered absence not whole-source nonexistence.'}

def prepare(out, cap=60, reuse=None,claim_protocol=5,verification_protocol=9,prior_calls=0):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    old=load(SOURCE/'summary.json');audit=load(out/'archive-audit-v3.json')
    assert len(audit['responses'])==88 and audit['counts'].get('not_replayed',0)==0
    cases=[]
    for case in SCENARIOS:
        name=case[0];row={'name':name,'request':asdict(request(case)),'expected_development_checkpoints':CHECKPOINTS[name]}
        if case[3]:
            r=next(r for r in old['runs'] if r['scenario']==name and r['mode']=='storage_order')
            g=load(SOURCE/('generation-'+name+'.json'))
            row.update(frozen_answer=r['frozen_answer'],original_evidence=g['generation_output']['evidence_snapshot']['evidence'],draft_origin='synthetic_fixture_existing_frozen_error')
        else:row.update(draft_origin='new_real_generation')
        if reuse and not case[3]:row['reuse_generation_json']=str(Path(reuse)/(name+'-generation.json'))
        cases.append(row)
    files=[ROOT/p for p in ('core/models.py','core/validation.py','core/typed_evidence.py','agents/contracts.py','services/answer_anchors.py','services/claim_extractor.py',
        'services/quantity_checks.py','tools/contracts.py','tools/unit_conversion.py','harness/runtime.py','harness/retrieval.py','harness/contracts.py',
        'agents/verification_contract_v9.py','agents/domain_contract_v3.py','agents/verification_contract_v5.py','agents/evidence_verification.py',
        'agents/power_domain_review.py','agents/generation.py','agents/revision.py','agents/revision_contract_v2.py','harness/policy.py',
        'evaluation/reliability_trial.py')]
    plan={'version':'review-reliability-v1','cases':cases,'model_id':old['model_id'],'knowledge_version':old['knowledge_version'],
        'global_model_cap':cap,'max_format_corrections_per_stage':1,'initial_worst_requests':44,
        'initial_worst_formula':'4 natural generation*2 +6*(extraction2+batched_fact2+domain2)=44',
        'each_revision_and_full_rereview_worst':8,'all_cases_full_worst':92,
        'budget_policy':'Complete all initial stages first; revisions in fixed scenario order, each reserves8. No overrun or retry batch. All-case revision worst92 exceeds cap60, so completion cannot be guaranteed.',
        'versions':{'claim':'atomic-claims-v5','verification':'evidence-verification-output-v9.1','domain':'power-domain-review-output-v3','generation':3,'revision':2,'rules':'power-demo-rules-v1','tool':'scalar-si-conversion-v1'},
        'claim_protocol':claim_protocol,'verification_protocol':verification_protocol,'prior_turn_calls':prior_calls,
        'retrieval':'default BM25/storage_order; no model/ranking/term/context tuning',
        'source_sha256':{str(p):digest(p) for p in files},
        'protected_sha256':load(SOURCE/'plan.json')['protected_sha256'],
        'historical_sha256':audit['source_sha256']}
    if reuse:
        plan['initial_worst_requests']=36;plan['prior_batch_requests']=28;plan['global_total_turn_cap']=60
        plan['initial_worst_formula']='6 initial reviews*6=36; reused frozen successful generations require no new generation calls'
        plan['all_cases_full_worst']=84
        plan['budget_policy']='Remaining cap32 after28 old-version requests. Initial correction-inclusive worst36 cannot be guaranteed; reserve each stage, no overrun. Reuse saved generation unchanged, prioritize all initial stages then fixed-order revisions.'
    if verification_protocol==10:
        extra=['services/answer_basis_targets.py','agents/verification_contract_v9_scoped.py','services/structured_model.py','services/response_diagnostics.py','evaluation/archive_replay.py']
        plan['source_sha256'].update({str(ROOT/p):digest(ROOT/p) for p in extra})
        plan['versions'].update(claim='atomic-claims-v6',verification='evidence-verification-output-v9.2')
        total=0
        for c in cases:
            answer=c.get('frozen_answer') or load(c['reuse_generation_json'])['answer'];c['initial_worst']=6+len(answer['citations']);total+=c['initial_worst']
        plan['initial_worst_requests']=total;plan['each_revision_and_full_rereview_worst']=18;plan['all_cases_full_worst']=total+6*18
        plan['initial_worst_formula']='extraction2 + domain2 + independent1 + each original citation1 + one fact-stage correction; frozen citation counts'
        plan['budget_policy']='New user authorization removes old cap60. One fixed followup batch, cap160 covers frozen initial plus6 revision-and-rereview reserves18. No repeated scenarios, no protocol change within batch.'
        plan['prior_batch_requests']=prior_calls;plan.pop('global_total_turn_cap',None)
    save_new(out/'plan-v1.json',plan);print(json.dumps({'cap':cap,'initial_worst':plan['initial_worst_requests'],'all_full_worst':plan['all_cases_full_worst'],'plan':str(out/'plan-v1.json')}))

async def live(out,adapter,domain_adapter,settings):
    from agents.generation import EvidenceGenerationAgent
    from agents.evidence_verification import ModelEvidenceVerificationAgent
    from agents.power_domain_review import ModelPowerDomainReviewAgent
    from agents.revision import ModelRevisionAgent
    from agents.contracts import RevisionInput
    from services.claim_extractor import ModelClaimExtractor
    from harness.runtime import OfflineHarness
    from harness.contracts import RunBudget,RetrievalSettings
    from harness.policy import LimitedRepairPolicy
    from harness.deepseek_trial import fee_summary
    from rag.retriever import AsyncSQLiteBM25Retriever
    from tools.unit_conversion import UnitConversionTool
    from evaluation.archive_replay import restore
    from core.models import TaskRequest,TaskMode,AnswerDraft,Evidence
    from services.evidence_scope import make_snapshot,validate_snapshot
    from core.validation import validate_answer,validate_revision
    from model_adapter.runtime import ModelBudget,model_scope
    out=Path(out);plan=load(out/'plan-v1.json');offline=load(out/'offline-validated-v1.json')
    assert offline['passed'] and all(digest(p)==h for p,h in plan['source_sha256'].items())
    assert all(digest(p)==h for p,h in plan['protected_sha256'].items())
    if settings.model_id!=plan['model_id']:raise ValueError('Configured model differs from frozen baseline; refusing model change')
    if (out/'live-progress-v1.json').exists():raise FileExistsError('Batch already started; no automatic rerun')
    diag=out/'response-diagnostics-v1';inputs=out/'actual-inputs-v1';diag.mkdir();inputs.mkdir()
    rows=[];records=[];stages=[];started=perf_counter();stopped=False
    def checkpoint():
        value={'scope':'REAL LIMITED REVIEW NO SAFETY CERTIFICATION NO GLOBAL PASS','model_id':settings.model_id,
            'knowledge_version':plan['knowledge_version'],'actual_model_calls':len(records),'cap':plan['global_model_cap'],'model_records':records,'runs':rows,'stages':stages,
            'cost_estimate':fee_summary(records),'wall_ms':int((perf_counter()-started)*1000),'plan_sha256':digest(out/'plan-v1.json')}
        (out/'live-progress-v1.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return value
    def reserve(label,n):
        row={'label':label,'before_calls':len(records),'worst_requests':n,'allowed':len(records)+n<=plan['global_model_cap']};stages.append(row);checkpoint();return row
    def retain(label,result,stage):
        nonlocal stopped
        rs=[asdict(r) for r in result.model_records];records.extend(rs);stage.update(actual_requests=len(rs),state=result.state.value)
        save_new(out/(label+'.json'),asdict(result));checkpoint()
        if plan.get('verification_protocol')==10 and any(i.code in ('EXECUTION_FAILURE','OUTPUT_CONTRACT_ERROR') for i in result.execution_issues):stopped=True
        if any(r.get('error_code') in ('MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED') for r in rs):stopped=True
    async def review(req,answer,evidence,snapshot,label):
        calls=6+len(answer.citations) if plan.get('verification_protocol') in (10,11) else 6
        stage=reserve(label,calls)
        if calls>16:raise ValueError('Frozen followup exceeds reviewed stage request limit16')
        if not stage['allowed']:return None
        with AsyncSQLiteBM25Retriever(DB) as retriever:
            harness=OfflineHarness(None,LoggedAgent(ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=diag,schema_version=plan.get('verification_protocol',9)),inputs,'verification'),
                LoggedAgent(ModelPowerDomainReviewAgent(domain_adapter,settings,diagnostic_dir=diag,protocol_version=plan.get('domain_protocol',3)),inputs,'domain'),None,
                ModelClaimExtractor(adapter,settings,diagnostic_dir=diag,protocol_version=plan.get('claim_protocol',5)),policy=LimitedRepairPolicy(),retriever=retriever,
                retrieval_settings=RetrievalSettings(),unit_tool=UnitConversionTool(version=plan.get('unit_tool_version','scalar-si-conversion-v1')))
            result=await harness.run(replace(req,mode=TaskMode.ASSESS_EXISTING,existing_answer=answer,provided_evidence=evidence),
                RunBudget(max_model_calls=calls,max_revision_rounds=0,max_duration_seconds=500,step_timeout_seconds=180),
                knowledge_version=plan['knowledge_version'],generation_snapshot=snapshot,indexed_reference_ids=tuple(e.evidence_id for e in evidence))
        retain(label,result,stage);stage['execution_complete']=stage_complete(asdict(result));checkpoint();return result
    checkpoint()
    for item in plan['cases']:
        if stopped:break
        name=item['name'];req=restore(item['request'],TaskRequest);row={'scenario':name,'draft_origin':item['draft_origin'],'expected_checks_not_passed_to_model':item['expected_development_checkpoints']};rows.append(row)
        if item.get('frozen_answer'):
            answer=restore(item['frozen_answer'],AnswerDraft);evidence=tuple(restore(e,Evidence) for e in item['original_evidence'])
            snapshot=make_snapshot(answer,evidence,plan['knowledge_version'],request=req,prompt_version='frozen_constructed_error_reliability-v1')
            row['frozen_answer_unchanged']=asdict(answer)==item['frozen_answer']
        elif item.get('reuse_generation_json'):
            saved=load(item['reuse_generation_json']); row['generation']=saved;row['generation_reused_without_API']=True
            answer=restore(saved['answer'],AnswerDraft);evidence=tuple(restore(e,Evidence) for e in saved['evidence']);snapshot=restore(saved['generation_output']['evidence_snapshot'],__import__('core.models',fromlist=['GenerationEvidenceSnapshot']).GenerationEvidenceSnapshot)
        else:
            stage=reserve(name+'-generation',2)
            if not stage['allowed']:row['stop']='generation_budget';continue
            with AsyncSQLiteBM25Retriever(DB) as retriever:
                harness=OfflineHarness(LoggedAgent(EvidenceGenerationAgent(adapter,settings,diagnostic_dir=diag,schema_version=3),inputs,'generation'),None,None,None,None,
                    retriever=retriever,retrieval_settings=RetrievalSettings())
                result=await harness.run(req,RunBudget(max_model_calls=2,max_revision_rounds=0,max_duration_seconds=240,step_timeout_seconds=180),generation_only=True,
                    knowledge_version=plan['knowledge_version'],answer_requirements=('Use at most two short cited answer units, preserve conditions. Index applicability is maintained metadata, not an official PDF quotation.',))
            retain(name+'-generation',result,stage);row['generation']=asdict(result)
            if stopped or result.answer is None or result.execution_issues:row['stop']='generation_failed';continue
            answer=result.answer;evidence=result.evidence;snapshot=result.generation_output.evidence_snapshot
        row['answer']=asdict(answer);row['generation_snapshot']=asdict(snapshot)
        initial=await review(req,answer,evidence,snapshot,name+'-initial');row['initial']=None if initial is None else asdict(initial)
        print(json.dumps({'scenario':name,'initial_complete':stage_complete(row['initial']),'calls':len(records)},ensure_ascii=False),flush=True);checkpoint()
    # All six initial reviews have reserved worst44; revisions spend only remaining cap.
    for row in rows:
        if stopped:break
        case=next(c for c in plan['cases'] if c['name']==row['scenario'])
        if case.get('component_variant'):
            row['required_stages_complete']=stage_complete(row.get('initial'));row['revision_status']='component_variant_no_revision_planned';checkpoint();continue
        if not stage_complete(row.get('initial')):row['stop']=row.get('stop','initial_incomplete');checkpoint();continue
        initial=restore(json.loads(json.dumps(row['initial'])),__import__('harness.contracts',fromlist=['HarnessResult']).HarnessResult)
        decision=LimitedRepairPolicy().decide(initial.verification_output,initial.domain_output,RunBudget(max_revision_rounds=1),0)
        row['initial_policy']=asdict(decision)
        if decision.kind.value!='revise':row['required_stages_complete']=True;row['revision_status']='not_required_by_fixed_policy';checkpoint();continue
        # Reserve correction-inclusive full re-extraction+both reviews before revision.
        stage=reserve(row['scenario']+'-repair-and-rereview',plan.get('each_revision_and_full_rereview_worst',8))
        if not stage['allowed']:row['stop']='insufficient_remaining_budget_for_full_repair';checkpoint();continue
        req=restore(next(c['request'] for c in plan['cases'] if c['name']==row['scenario']),TaskRequest)
        revision_input=RevisionInput(req,initial.answer,initial.verification_output,initial.domain_output,initial.evidence,
            decision.reasons+('Preserve corrected premises and source conditions; do not treat old input error quotations as endorsements. Do not attribute index metadata to official body.',)+
                (() if 'max_revision_citations' not in plan else (f"At most {plan['max_revision_citations']} citation bindings in the revised answer; no raw offsets or old quote IDs.",)),initial.evidence_bindings,plan['knowledge_version'])
        budget=ModelBudget(2,deadline=perf_counter()+180);revised=None
        try:
            with model_scope(budget):revised=await LoggedAgent(ModelRevisionAgent(adapter,settings,diagnostic_dir=diag,protocol_version=2),inputs,'revision').run(revision_input)
            validate_revision(revised,initial.answer,initial.evidence,initial.verification_output.findings+initial.domain_output.findings);validate_snapshot(revised.evidence_snapshot,revised.answer)
            if len(revised.answer.citations)>plan.get('max_revision_citations',1000):raise ValueError('Frozen revision citation budget exceeded; no rereview launched')
        except Exception as exc:
            revised=None;row['stop']='revision_execution_failed';row['revision_error']={'type':type(exc).__name__,'code':getattr(exc,'code',None)}
        records.extend(asdict(r) for r in budget.records);stage['revision_requests']=len(budget.records)
        if any(r.error_code in ('MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED') for r in budget.records):stopped=True
        if revised and not stopped:
            row['revision']=asdict(revised);save_new(out/(row['scenario']+'-revision.json'),asdict(revised))
            rereview=await review(req,revised.answer,initial.evidence,revised.evidence_snapshot,row['scenario']+'-rereview')
            row['rereview']=None if rereview is None else asdict(rereview);row['required_stages_complete']=stage_complete(row['rereview'])
            if rereview and rereview.verification_output and rereview.domain_output:row['final_policy']=asdict(LimitedRepairPolicy().decide(rereview.verification_output,rereview.domain_output,RunBudget(max_revision_rounds=1),1))
        checkpoint();print(json.dumps({'scenario':row['scenario'],'repair_complete':row.get('required_stages_complete',False),'calls':len(records),'stop':row.get('stop')},ensure_ascii=False),flush=True)
    assert len(records)<=plan['global_model_cap'] and all(digest(p)==h for p,h in plan['source_sha256'].items()) and all(digest(p)==h for p,h in plan['historical_sha256'].items())
    save_new(out/'live-summary-v1.json',checkpoint())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('prepare','live'));parser.add_argument('--output-dir',default=str(DEFAULT_OUT));parser.add_argument('--cap',type=int,default=60);parser.add_argument('--reuse-generations');parser.add_argument('--claim-protocol',type=int,default=5);parser.add_argument('--verification-protocol',type=int,default=9);parser.add_argument('--prior-calls',type=int,default=0);args=parser.parse_args()
    if args.phase=='prepare':return prepare(args.output_dir,args.cap,args.reuse_generations,args.claim_protocol,args.verification_protocol,args.prior_calls)
    from harness.deepseek_trial import load_project_env
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    load_project_env();model=os.environ.get('DEEPSEEK_MODEL_ID')
    if not model:raise ValueError('Explicit configured model required')
    settings=ModelSettings(model,90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY');adapter=create_adapter(settings);domain=create_adapter(settings)
    try:asyncio.run(live(args.output_dir,adapter,domain,settings))
    finally:adapter.close();domain.close()

if __name__=='__main__':main()
