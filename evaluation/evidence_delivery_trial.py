"""Paired evidence-delivery development trial; reuse existing Harness/four Agents."""
import argparse
import asyncio
from dataclasses import asdict,replace
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from core.models import TaskRequest,TaskMode,EngineeringContext,EngineeringQuantity,AnswerDraft,CitationBinding
from harness.contracts import RunBudget,RetrievalSettings
from rag.contracts import ContextOptions,RetrievalRequest,RetrievalPurpose

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/retrieval_local/semantic'
DB=BASE/'corpus.sqlite3'
MODES=('storage_order','cross_page_next_first')
SCENARIOS=(
 ('definition','How does the NERC guideline define voltage stability, and does normal bus voltage alone prove stability?',EngineeringContext(),None),
 ('cross_fragment','Which ratings and operating conditions limit synchronous generator reactive capability? Include cooling, excitation limiters and active power output.',EngineeringContext(),None),
 ('quantity','Review a synthetic proposal claiming four equipment ratings including active power output. Its reactive power is Q=30 MW and the same bus has 230 kV and 230 V. Identify inconsistencies without claiming a study.',EngineeringContext(quantities=(EngineeringQuantity('q','reactive_power',30.,'MW','synthetic-plant'),EngineeringQuantity('v1','voltage',230.,'kV','synthetic-bus'),EngineeringQuantity('v2','voltage',230.,'V','synthetic-bus'))),
  'There are four equipment ratings: stator winding rating, field current rating, terminal voltage rating, and active power output. Reactive power Q=30 MW has the correct unit, and 230 kV equals 230 V at the same bus.'),
 ('jurisdiction','Does NERC VAR-001-5 establish mandatory voltage and reactive control requirements for a distribution plant in China? State the applicable jurisdiction.',EngineeringContext(),
  'NERC VAR-001-5 establishes mandatory voltage and reactive control requirements for this distribution plant in China.'),
 ('missing_engineering','Can this plant safely add 30 MVAr reactive support and guarantee voltage stability without a network model, operating point, equipment limits or contingency study?',EngineeringContext(goal='plant_assessment',quantities=(EngineeringQuantity('q-proposal','reactive_power',30.,'MVAr','synthetic-plant'),)),None),
 ('insufficient_evidence','What exact capacitor-bank switching setpoint is mandatory for a 110 kV plant in China according to these sources? No plant-specific data or local grid code was supplied.',EngineeringContext(goal='plant_assessment'),None),
)
REQUIREMENTS=('Use at most two cited answer units and at most 100 words. Preserve qualifications; ask specific missing-input questions when evidence is insufficient.',)

def save_new(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def request(case):
    name,question,engineering,error=case
    return TaskRequest('delivery-'+name,TaskMode.QUESTION_ANSWER,'voltage_stability_reactive_support',question,
        'synthetic_fixture development scenario; no actual engineering study or simulation executed.',engineering_context=engineering)
def settings_for(mode):return RetrievalSettings(3,ContextOptions(2400,6,1,True,mode))
def review_worst(answer,shared=False):return 2*(3+len(answer.citations))-(2 if shared else 0)

def plan(out):
    from rag.storage import KnowledgeStore
    from rag.retriever import BM25Retriever
    out=Path(out)
    if out.exists():raise FileExistsError('New experiment directory required')
    out.mkdir(parents=True);kv=load(BASE/'dataset-v1.json')['knowledge_version'];rows=[]
    with KnowledgeStore(DB,readonly=True) as store:
        retriever=BM25Retriever(store)
        for case in SCENARIOS:
            req=request(case);modes={}
            for mode in MODES:
                rr=RetrievalRequest(req.question,req.scenario_id,RetrievalPurpose.GENERATION,kv,3,settings_for(mode).context_options)
                result=retriever._retrieve(rr);retriever._validate_result(rr,result)
                modes[mode]=asdict(result)
            rows.append({'scenario':case[0],'request':asdict(req),'constructed_error':case[3],'modes':modes,
                'different_context_ids':[e['evidence']['evidence_id'] for e in modes[MODES[0]]['context']['items']]!=[e['evidence']['evidence_id'] for e in modes[MODES[1]]['context']['items']]})
    # With <=2 initial citations and <=4 revised citations: generation2 +
    # shared extraction2 + two*(initial independent/citations+domain8 + revision2 + full rereview14)=52 per case.
    value={'version':'evidence-delivery-paired-v1','knowledge_version':kv,'modes':MODES,'scenarios':rows,
        'global_request_cap':312,'worst_case_derivation':'6 * (generation2 + shared extraction2 + 2*(initial facts/citations+domain8 + revision2 + complete rereview14))',
        'max_initial_citations':2,'max_revised_citations':4,'requirements':REQUIREMENTS,
        'review_protocols':{'generation':3,'evidence':8,'domain':2,'revision':2,'policy':'limited-repair-policy-v1'},
        'paired_design':'One baseline real generation per scenario; shared frozen initial draft/extraction. Only review/rereview adjacency priority differs. Quantity/jurisdiction have explicit synthetic replacement drafts; natural generation retained unchanged.',
        'scope':'development comparison; no semantic gold standard, engineering safety certificate or global real pass',
        'protected_sha256':{str(p):digest(p) for p in (DB,BASE/'vectors.sqlite3',BASE/'annotations/term-expansion-27-final-v1/merged-annotations.json')},
        'source_sha256':{str(p):digest(p) for p in (ROOT/'agents/generation.py',ROOT/'agents/verification_contract_v8.py',ROOT/'agents/domain_contract_v2.py',ROOT/'agents/revision_contract_v2.py',ROOT/'harness/policy.py')},
        'retrieval_chars_per_call':16000,'retrieval_chars_total':160000,'context_chars':2400,'context_fragments':6}
    save_new(out/'plan.json',value)
    print(json.dumps({'output':str(out),'changed_preview_contexts':[r['scenario'] for r in rows if r['different_context_ids']],
        'cap':value['global_request_cap']},ensure_ascii=False))

class LoggedAgent:
    def __init__(self,agent,path,label):self.agent,self.path,self.label=agent,Path(path),label
    def __getattr__(self,key):return getattr(self.agent,key)
    async def run(self,inputs):
        save_new(self.path/f'agent-input-{self.label}-{uuid4().hex}.json',{'agent':self.label,'input':asdict(inputs)})
        return await self.agent.run(inputs)

class FrozenExtraction:
    uses_model_adapter=False
    def __init__(self,answer,extracted):self.answer,self.extracted=answer,extracted
    async def extract(self,answer):
        if answer!=self.answer:raise ValueError('Frozen extraction answer/version mismatch')
        return self.extracted

async def live(out,adapter,domain_adapter,settings):
    from agents.generation import EvidenceGenerationAgent
    from agents.evidence_verification import ModelEvidenceVerificationAgent
    from agents.power_domain_review import ModelPowerDomainReviewAgent
    from agents.revision import ModelRevisionAgent
    from agents.contracts import RevisionInput
    from core.validation import validate_revision,validate_answer
    from services.claim_extractor import ModelClaimExtractor
    from services.evidence_scope import make_snapshot,validate_snapshot
    from model_adapter.runtime import ModelBudget,model_scope
    from harness.deepseek_trial import fee_summary
    from harness.policy import LimitedRepairPolicy
    from harness.runtime import OfflineHarness
    from rag.retriever import AsyncSQLiteBM25Retriever
    out=Path(out);frozen=load(out/'plan.json');kv=frozen['knowledge_version'];cap=frozen['global_request_cap'];records=[];runs=[];stages=[]
    if (out/'summary.json').exists() or any(out.glob('generation-*.json')):raise FileExistsError('Live trial already started; no automatic reruns')
    assert all(digest(p)==h for p,h in frozen['protected_sha256'].items())
    assert all(digest(p)==h for p,h in frozen['source_sha256'].items())
    diagnostics=out/'response-diagnostics';diagnostics.mkdir();inputs_dir=out/'agent-inputs';inputs_dir.mkdir()
    def checkpoint():
        value={'scope':frozen['scope'],'max_requests':cap,'actual_model_calls':len(records),'model_records':records,
            'cost_summary_saved_price_estimate':fee_summary(records),'model_id':settings.model_id,'knowledge_version':kv,
            'stages':stages,'runs':runs,'plan_sha256':digest(out/'plan.json')}
        (out/'progress.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return value
    def reserve(label,n):
        row={'label':label,'used':len(records),'worst_requests':n,'allowed':len(records)+n<=cap};stages.append(row);checkpoint()
        return row
    def complete(result):
        return bool(result.extraction_output and result.verification_output and result.domain_output and not result.execution_issues
            and not result.verification_output.execution_issues and not result.domain_output.execution_issues)
    async def review(req,answer,evidence,snapshot,mode,label,shared=None):
        row=reserve(label,review_worst(answer,shared is not None))
        if not row['allowed']:return None
        extractor=FrozenExtraction(answer,shared) if shared else ModelClaimExtractor(adapter,settings,diagnostic_dir=diagnostics,typed_components=True)
        with AsyncSQLiteBM25Retriever(DB) as retriever:
            harness=OfflineHarness(None,
                LoggedAgent(ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=diagnostics,schema_version=8),inputs_dir,'verification'),
                LoggedAgent(ModelPowerDomainReviewAgent(domain_adapter,settings,diagnostic_dir=diagnostics,protocol_version=2),inputs_dir,'domain'),
                None,extractor,policy=LimitedRepairPolicy(),retriever=retriever,retrieval_settings=settings_for(mode))
            result=await harness.run(replace(req,mode=TaskMode.ASSESS_EXISTING,existing_answer=answer,provided_evidence=evidence),
                RunBudget(max_model_calls=row['worst_requests'],max_revision_rounds=0,max_duration_seconds=700,step_timeout_seconds=180,
                    max_retrieval_chars_total=160000),knowledge_version=kv,indexed_reference_ids=tuple(e.evidence_id for e in evidence),generation_snapshot=snapshot)
        records.extend(asdict(r) for r in result.model_records);row.update(actual_requests=len(result.model_records),execution_complete=complete(result))
        save_new(out/(label+'.json'),asdict(result));checkpoint();return result
    for case in SCENARIOS:
        name=case[0];req=request(case)
        if cap-len(records)<52:
            stages.append({'label':name,'status':'not_started_full_case_worst_reserve'});checkpoint();break
        genrow=reserve(name+':generation',2)
        with AsyncSQLiteBM25Retriever(DB) as retriever:
            harness=OfflineHarness(LoggedAgent(EvidenceGenerationAgent(adapter,settings,diagnostic_dir=diagnostics,schema_version=3),inputs_dir,'generation'),None,None,None,None,
                retriever=retriever,retrieval_settings=settings_for(MODES[0]))
            gen=await harness.run(req,RunBudget(max_model_calls=2,max_revision_rounds=0,step_timeout_seconds=180,max_duration_seconds=240),
                knowledge_version=kv,generation_only=True,answer_requirements=REQUIREMENTS)
        records.extend(asdict(r) for r in gen.model_records);save_new(out/('generation-'+name+'.json'),asdict(gen));genrow.update(actual_requests=len(gen.model_records),state=gen.state.value);checkpoint()
        if gen.answer is None or gen.execution_issues:
            runs.append({'scenario':name,'generation_failed':True});checkpoint();continue
        answer=gen.answer;snapshot=gen.generation_output.evidence_snapshot;evidence=gen.evidence
        if case[3]:
            citations=() if not evidence else (CitationBinding(0,len(case[3]),(evidence[0].evidence_id,)),)
            answer=AnswerDraft(req.task_id+'-synthetic-error',1,case[3],citations=citations)
            snapshot=make_snapshot(answer,evidence,kv,request=req,answer_requirements=REQUIREMENTS,
                prompt_version='explicit-synthetic-replacement-after-real-generation',evidence_bindings=gen.evidence_bindings)
        validate_answer(answer,evidence);validate_snapshot(snapshot,answer)
        if len(answer.citations)>2:
            runs.append({'scenario':name,'stop_reason':'initial citations exceed prepaid comparison limit','generated_record_retained':True});checkpoint();continue
        shared=None
        for mode in MODES:
            label=name+'-'+mode;run={'scenario':name,'mode':mode,'draft_origin':'synthetic_fixture_after_real_generation' if case[3] else 'real_generated_draft',
                'frozen_answer':asdict(answer),'shared_initial_extraction':shared is not None,'initial':None,'revision':None,'rereview':None};runs.append(run)
            initial=await review(req,answer,evidence,snapshot,mode,label+'-initial',shared)
            if initial is None:run['stop_reason']='initial review budget';checkpoint();continue
            run['initial']=asdict(initial)
            if shared is None and initial.extraction_output:shared=initial.extraction_output
            if not complete(initial):run['stop_reason']='execution incomplete; valid peer findings retained';checkpoint();continue
            decision=LimitedRepairPolicy().decide(initial.verification_output,initial.domain_output,RunBudget(max_revision_rounds=1),0)
            if decision.kind.value!='revise':run['revision_status']='not_required_by_fixed_policy';run['loop_execution_complete']=True;checkpoint();continue
            row=reserve(label+':revision',2)
            if not row['allowed']:run['stop_reason']='revision budget';checkpoint();continue
            inputs=RevisionInput(req,answer,initial.verification_output,initial.domain_output,initial.evidence,
                decision.reasons+('Use at most four cited answer units. Do not remove conditions to meet the limit.',),initial.evidence_bindings,kv)
            agent=LoggedAgent(ModelRevisionAgent(adapter,settings,diagnostic_dir=diagnostics,protocol_version=2),inputs_dir,'revision')
            budget=ModelBudget(limit=2,deadline=perf_counter()+180)
            revised=None
            try:
                with model_scope(budget):revised=await agent.run(inputs)
                validate_revision(revised,answer,initial.evidence,initial.verification_output.findings+initial.domain_output.findings)
                validate_snapshot(revised.evidence_snapshot,revised.answer)
            except Exception as exc:
                revised=None
                row.update(status='execution_failed',error_type=type(exc).__name__,code=getattr(exc,'code',None));run['stop_reason']='revision execution failed, no identical retry'
            records.extend(asdict(r) for r in budget.records);row['actual_requests']=len(budget.records)
            if revised is not None:
                run['revision']=asdict(revised);save_new(out/(label+'-revision.json'),asdict(revised))
                if len(revised.answer.citations)>4:run['stop_reason']='revised citations exceed preflight bound; new answer retained, no full-loop claim'
                else:
                    reviewed=await review(req,revised.answer,initial.evidence,revised.evidence_snapshot,mode,label+'-rereview')
                    if reviewed:
                        run['rereview']=asdict(reviewed);run['loop_execution_complete']=complete(reviewed)
                        if reviewed.verification_output and reviewed.domain_output:
                            run['final_decision']=asdict(LimitedRepairPolicy().decide(reviewed.verification_output,reviewed.domain_output,RunBudget(max_revision_rounds=1),1))
            checkpoint()
            print(json.dumps({'scenario':name,'mode':mode,'requests_used':len(records),'loop_complete':run.get('loop_execution_complete',False),'stop':run.get('stop_reason')},ensure_ascii=False),flush=True)
    assert len(records)<=cap and all(digest(p)==h for p,h in frozen['protected_sha256'].items())
    save_new(out/'summary.json',checkpoint())

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('plan','live'));p.add_argument('--output-dir',required=True);a=p.parse_args()
    if a.phase=='plan':return plan(a.output_dir)
    from harness.deepseek_trial import load_project_env
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    load_project_env();model=os.environ.get('DEEPSEEK_MODEL_ID')
    if not model:raise ValueError('Configured DEEPSEEK_MODEL_ID required; not guessed')
    settings=ModelSettings(model,90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')
    adapter,domain=create_adapter(settings),create_adapter(settings)
    try:asyncio.run(live(a.output_dir,adapter,domain,settings))
    finally:adapter.close();domain.close()

if __name__=='__main__':main()
