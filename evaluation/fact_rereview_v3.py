"""Frozen fact-only replay + fixed semantic development fixtures; no new Harness."""
import argparse
import asyncio
from dataclasses import asdict,replace
import hashlib
import json
import os
import re
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from evaluation.evidence_delivery_trial import ROOT,DB,load,save_new,digest
from evaluation.archive_replay import restore
from agents.contracts import EvidenceVerificationInput,ReliabilityVerificationInput
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.review_templates_v3 import PROMPT_VERSION,CONTRACT_VERSION,INDEPENDENT,ORIGINAL
from core.models import AnswerDraft,Evidence,ObligationClaim,ClaimComponent,TaskRequest,TaskMode
from core.validation import validate_claims,validate_review,merge_evidence
from services.evidence_scope import make_snapshot
from services.scoped_candidates import CandidateScope
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope

SOURCE=ROOT/'data/retrieval_local/deepseek/reliability-v2'
DEFAULT=ROOT/'data/retrieval_local/deepseek/fact-rereview-v3'
FATAL={'MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED'}

def freeze_claim(answer,*,proposition=None,target='technical_content',role='asserted'):
    from services.answer_basis_targets import TARGETS
    from services.claim_obligations import TARGET_OBLIGATIONS
    from services.answer_anchors import anchors
    proposition=proposition or answer.text
    cid='claim-'+hashlib.sha256(json.dumps((answer.answer_id,answer.version,answer.text,proposition),ensure_ascii=False).encode()).hexdigest()[:24]
    category=TARGETS[target]
    return ObligationClaim(cid,answer.answer_id,answer.version,answer.text,0,len(answer.text),category,proposition,
        components=(ClaimComponent(cid+'-part-0',category,proposition),),anchor_group_id=anchors(answer)[0]['anchor_id'],
        assertion_role=role,semantic_origin='program-frozen-fixture-not-model-extraction',component_basis_targets=(target,),
        component_obligations=(TARGET_OBLIGATIONS[target],))

def fixtures(real_evidence,knowledge_version):
    three='This synthetic equipment has three equipment ratings: stator winding rating, field current rating, and terminal voltage rating. Active power output affects capability but is not an equipment rating.'
    four='This synthetic equipment has four equipment ratings: stator winding rating, field current rating, terminal voltage rating, and shaft speed rating. Active power output is a separate operating influence, not another equipment rating.'
    reordered='Active power output is an operating influence, not an equipment rating. The equipment ratings are terminal voltage rating, stator winding rating, and field current rating: three rating categories.'
    semicolons='The synthetic equipment ratings consist of stator winding rating; field current rating; terminal voltage rating. Active power output affects capability and is not another rating category.'
    bullets='Synthetic fixture equipment ratings (three categories):\n- stator winding rating\n- field current rating\n- terminal voltage rating\nActive power output is not a rating category.'
    chinese='合成样例：设备额定值分为三类：定子绕组额定值、励磁电流额定值、端电压额定值。有功输出影响能力，但不属于设备额定值类别。'
    unclear='Synthetic fixture: capability depends on current, voltage, cooling and active power output; this excerpt does not classify equipment rating categories.'
    wrong='There are four equipment ratings: stator winding rating, field current rating, terminal voltage rating, and active power output.'
    correct='There are three equipment ratings: stator winding rating, field current rating, and terminal voltage rating.'
    specs=(
        ('N01',three,wrong,('contradicted',),'asserted',False),
        ('N02',four,'There are four equipment ratings: stator winding rating, field current rating, terminal voltage rating, and shaft speed rating.',('supported',),'asserted',False),
        ('N03',three,correct,('supported',),'asserted',False),
        ('N04',three,'The proposal claims four equipment ratings, but this is incorrect: there are three equipment rating categories and active power output is an operating influence.',('supported',),'correction',False),
        ('N05',reordered,wrong,('contradicted',),'asserted',False),
        ('N06',semicolons,wrong,('contradicted',),'asserted',False),
        ('N07',bullets,correct,('supported',),'asserted',False),
        ('N08',chinese,'设备共有四类额定值，有功输出属于第四类额定值。',('contradicted',),'asserted',False),
        ('N09',unclear,'There are three equipment ratings.',('insufficient_evidence','not_assessable'),'asserted',False),
        ('N10',None,wrong,('contradicted',),'asserted',True),
        ('N11',None,correct,('supported',),'asserted',True),
        ('N12',three,wrong,('not_assessable',),'asserted',False),
    )
    frozen=[];labels=[]
    for name,body,text,expected,role,real in specs:
        answer=AnswerDraft(uuid4().hex,1,text)
        evidence=real_evidence if real else Evidence('synthetic-'+hashlib.sha256(body.encode()).hexdigest()[:24],
            'synthetic_fixture',hashlib.sha256(body.encode()).hexdigest(),f'synthetic_fixture inline original characters [0,{len(body)})',body,'synthetic_fixture')
        c=freeze_claim(answer,role=role,proposition='The answer states that there are four equipment ratings.' if name=='N12' else None,
                       target='answer_text' if name=='N12' else 'technical_content')
        req=TaskRequest(uuid4().hex,TaskMode.ASSESS_EXISTING,'voltage_stability_reactive_support',
            'Check the supplied statement against the supplied excerpt, preserving categories and qualifications.',
            user_context='This is a constructed development statement, not an observed plant state.',existing_answer=answer)
        kv=knowledge_version if real else None
        inp=ReliabilityVerificationInput(req,answer,(c,),(evidence,),knowledge_version=kv,
            generation_snapshot=make_snapshot(answer,(evidence,),kv,request=req,prompt_version='program-frozen-fixture-no-model-generation'))
        validate_claims(inp.claims,answer)
        frozen.append({'case_id':name,'input':asdict(inp),'source_kind':'real_official_excerpt' if real else 'synthetic_fixture',
            'evidence_locator':asdict(evidence.provenance) if evidence.provenance else {'start_offset':0,'end_offset':len(body),'content_sha256':hashlib.sha256(body.encode()).hexdigest()},
            'extraction_evaluated':False,'upstream_fixture':'deliberate_target_conversion' if name=='N12' else 'literal_program_binding'})
        labels.append({'case_id':name,'expected_statuses':expected,'status':'provisional_development_needs_human_review' if real else 'synthetic_logic_development_expectation',
            'basis':'Actual excerpt names three rating labels and distinguishes active-power influence; interpretation is developer-provisional, not an expert label.' if real else
                    'Explicit classifications in synthetic original text; N09 does not determine the count; N12 checks target disagreement, not silent technical support.',
            'is_direct_count_error':name in ('N01','N05','N06','N08','N10'),'not_expert_gold':True})
    return frozen,labels

async def check_index(inputs):
    from rag.retriever import AsyncSQLiteBM25Retriever
    with AsyncSQLiteBM25Retriever(DB) as retriever:
        for inp in inputs:
            evidence=merge_evidence(inp.seed_evidence,inp.original_evidence,inp.generation_snapshot.evidence if inp.generation_snapshot else ())
            await retriever.validate_evidence(evidence,inp.knowledge_version)

async def replay_old(inp,run):
    records=[r for r in run['model_records'] if r['prompt_version']=='evidence-verification-v9.3-target-fidelity']
    responses=[load(r['diagnostic_path']) for r in records]
    class SavedAdapter:
        def __init__(self):self.position=0
        async def complete(self,request):
            if self.position>=len(responses):raise RuntimeError('Archive exhausted; no network fallback')
            r=responses[self.position];self.position+=1
            return ModelResponse(r['response_text'],r['model_id'],finish_reason=r['finish_reason'])
    budget=ModelBudget(1+len(inp.answer.citations)+1);adapter=SavedAdapter()
    with model_scope(budget):out=await ModelEvidenceVerificationAgent(adapter,ModelSettings('deepseek-flash'),schema_version=11).run(inp)
    old={k:v for k,v in run['verification_output'].items() if k!='model_records'}
    actual={k:v for k,v in json.loads(json.dumps(asdict(out))).items() if k!='model_records'}
    return {'source_records':[r['diagnostic_path'] for r in records],'responses_consumed':adapter.position,
        'historical_execution_failed':bool(run['verification_output']['execution_issues']),
        'replay_execution_failed':bool(out.execution_issues),'business_output_exact_match':old==actual,
        'replay_errors':[r.validation_error for r in budget.records if r.validation_error],
        'method':'saved response replay under schema11; simulated requests only; no migration to success'}

def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    frozen=[];restored=[];replays=[]
    for name in ('quantity','missing_engineering'):
        run=load(SOURCE/(name+'-rereview.json'))
        matches=[(p,load(p)['input']) for p in (SOURCE/'actual-inputs-v1').glob('agent-input-verification-*.json') if load(p)['input']['answer']==run['answer']]
        if len(matches)!=1:raise ValueError('Exactly one corresponding actual input required')
        path,wire=matches[0];inp=restore(wire,EvidenceVerificationInput)
        assert json.loads(json.dumps(asdict(inp.answer)))==run['answer'] and json.loads(json.dumps([asdict(c) for c in inp.claims]))==run['extraction_output']['claims']
        validate_claims(inp.claims,inp.answer);restored.append(inp)
        assert all(getattr(c,'component_obligations',()) for c in inp.claims)
        replays.append({'scenario':name,**asyncio.run(replay_old(inp,run))})
        frozen.append({'scenario':name,'input':wire,'source_input_path':str(path),'source_input_sha256':digest(path),
            'source_rereview_sha256':digest(SOURCE/(name+'-rereview.json')),'semantic_adaptation':'none: identical answer, shared claims, snapshot and tools',
            'retrieval_reused':run['retrieval_records'],'retrieval_calls_this_round':0,'candidate_evidence_changed':False,
            'namespace_adaptation':'Only wire IDs change deterministically with new protocol; canonical candidates and source intervals unchanged'})
    asyncio.run(check_index(restored))
    candidates=[e for inp in restored for e in inp.seed_evidence+inp.original_evidence if e.provenance and e.provenance.file_page==8 and
        all(s in re.sub(r'\s+',' ',e.text) for s in ('stator winding rating','field current rating','terminal voltage rating','active power output'))]
    if not candidates:raise ValueError('Required real excerpt not found; refusing invented source')
    real=min(candidates,key=lambda e:len(e.text));semantic,labels=fixtures(real,restored[0].knowledge_version)
    save_new(out/'frozen-stage-inputs-v3.json',frozen);save_new(out/'semantic-inputs-v3.json',semantic);save_new(out/'semantic-expectations-v3.json',labels)
    save_new(out/'historical-replay-v3.json',replays)
    failures=load(SOURCE/'failure-matrix-v2.json')
    diagnosis=[{'scenario':f['scenario'],'phase':f['phase'],'response_path':f['record']['diagnostic_path'],'response_sha256':digest(f['record']['diagnostic_path']),
        'errors':(f['record']['validation_error'] or {}).get('errors',[]),'historical_state_unchanged':True} for f in failures]
    save_new(out/'failure-diagnosis-v3.json',diagnosis)
    source_files=[str(p) for folder in ('agents','core','harness','services','model_adapter','tools','rag') for p in (ROOT/folder).rglob('*.py')]
    source_files+=[str(Path(__file__).resolve()),str(ROOT/'tests/test_fact_rereview_v3.py')]
    old_plan=load(SOURCE/'plan-v1.json')
    plan={'version':'fact-rereview-stability-v3','prompt_version':PROMPT_VERSION,'contract_version':CONTRACT_VERSION,
        'schema_version':12,'model_id':old_plan['model_id'],'knowledge_version':old_plan['knowledge_version'],
        'global_cap':40,'worst_calls':sum(2+len(i.answer.citations) for i in restored)+2*len(semantic),
        'budget_formula':'Two fact stages: independent1 +2 original citations +one stage correction each =8; 12 semantic verifier-only cases*2=24; total32 <=40',
        'semantic_extraction_evaluated':False,'default_retrieval_unchanged':True,
        'source_sha256':{p:digest(p) for p in sorted(source_files)},
        'history_sha256':{str(p):digest(p) for p in SOURCE.rglob('*') if p.is_file()},
        'protected_sha256':old_plan['protected_sha256'],
        'fixture_sha256':{str(out/n):digest(out/n) for n in ('frozen-stage-inputs-v3.json','semantic-inputs-v3.json','semantic-expectations-v3.json')},
        'template_sha256':{'independent':hashlib.sha256(INDEPENDENT.encode()).hexdigest(),'original':hashlib.sha256(ORIGINAL.encode()).hexdigest()},
        'no_model_selection_or_new_retrieval_or_revision':True}
    assert plan['worst_calls']<=40
    save_new(out/'plan-v3.json',plan)
    print(json.dumps({'worst_calls':plan['worst_calls'],'semantic_cases':len(semantic),'old_replay':[(r['scenario'],r['business_output_exact_match']) for r in replays],'index_evidence_verified':True}))

async def live(out,adapter,settings):
    out=Path(out);plan=load(out/'plan-v3.json');gate=load(out/'offline-validated-v3.json')
    assert gate['passed'] and gate['source_sha256']==plan['source_sha256']
    for group in ('source_sha256','history_sha256','protected_sha256','fixture_sha256'):
        assert all(digest(p)==h for p,h in plan[group].items()),'Frozen content changed'
    if settings.model_id!=plan['model_id']:raise ValueError('Model differs from frozen baseline')
    with (out/'started-v3.json').open('x',encoding='utf-8') as f:json.dump({'scope':'one fact-stage validation; no generation/revision/domain run'},f)
    rows=[];records=[];started=perf_counter();used=0;stopped=False
    def reserve():
        nonlocal used
        if used>=plan['global_cap']:
            from model_adapter.contracts import ModelBudgetError
            raise ModelBudgetError()
        used+=1;return used
    def checkpoint():
        value={'scope':'REAL FACT-STAGE REVIEW ONLY NO GLOBAL PASS','runs':rows,'records':records,'actual_requests':used,
            'wall_ms':int((perf_counter()-started)*1000),'stopped_for_service':stopped}
        (out/'progress-v3.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return value
    tasks=[('fact_stage',r['scenario'],r['input']) for r in load(out/'frozen-stage-inputs-v3.json')]+[('semantic_component',r['case_id'],r['input']) for r in load(out/'semantic-inputs-v3.json')]
    checkpoint()
    for kind,name,wire in tasks:
        if stopped:break
        inp=restore(wire,EvidenceVerificationInput);limit=2+len(inp.answer.citations)
        if used+limit>plan['global_cap']:raise ValueError('Insufficient worst-case reserve; no request launched')
        save_new(out/(name+'-actual-input-v3.json'),{'input':asdict(inp),'scope':kind})
        budget=ModelBudget(limit,deadline=perf_counter()+300,reserve=reserve);begin=perf_counter();output=None;error=None
        try:
            with model_scope(budget):output=await ModelEvidenceVerificationAgent(adapter,settings,schema_version=12,diagnostic_dir=out/'response-diagnostics-v3').run(inp)
        except Exception as exc:
            # Do not mislabel a programming failure as a semantic verdict.
            error={'type':type(exc).__name__,'code':getattr(exc,'code',None),'state':'execution_failed_no_semantic_fallback'}
        raw=[asdict(r) for r in budget.records];records.extend(raw)
        stopped=any(r.get('error_code') in FATAL for r in raw)
        row={'kind':kind,'name':name,'output':None if output is None else asdict(output),'error':error,'records':raw,
            'duration_ms':int((perf_counter()-begin)*1000),'model_extraction_run':False}
        rows.append(row);save_new(out/(name+'-result-v3.json'),row);checkpoint()
        print(json.dumps({'name':name,'executed':output is not None and not output.execution_issues,'requests':used,'service_stop':stopped}),flush=True)
    value=checkpoint()
    value['frozen_hashes_unchanged']=all(digest(p)==h for group in ('source_sha256','history_sha256','protected_sha256','fixture_sha256') for p,h in plan[group].items())
    assert value['frozen_hashes_unchanged'] and used<=40
    save_new(out/'live-summary-v3.json',value)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','live'));parser.add_argument('--output-dir',default=str(DEFAULT));args=parser.parse_args()
    if args.phase=='prepare':return prepare(args.output_dir)
    from harness.deepseek_trial import load_project_env
    from model_adapter.deepseek import create_adapter
    load_project_env();model=os.environ.get('DEEPSEEK_MODEL_ID')
    if not model:raise ValueError('Explicit configured model required')
    settings=ModelSettings(model,90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY');adapter=create_adapter(settings)
    try:asyncio.run(live(args.output_dir,adapter,settings))
    finally:adapter.close()

if __name__=='__main__':main()
