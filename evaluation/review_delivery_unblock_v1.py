"""One Flash-only mechanism change; existing Factory/graph/run_fixed execution."""
import asyncio,json,os
from dataclasses import replace
from pathlib import Path
from evaluation import answer_review_net_benefit_v1 as shared
from evaluation import production_review_v2 as base
from evaluation.fact_review_model_fit_v1 import ComparisonAdapter
from evaluation.strict_interface_probe_v1 import ROOT,load,save,digest
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from services.review_bound_answer_v1 import specification as bound_spec

PUBLIC=ROOT/'docs/evaluation/review-delivery-unblock-v1'
LOCAL=ROOT/'data/retrieval_local/review-delivery-unblock-v1'
VERSION='review-delivery-unblock-v1'


def materials():
    old=load(ROOT/'data/retrieval_local/production-review-net-benefit-v2/materials.json')
    return dict(**{k:v for k,v in old.items() if k not in ('A','B','version')},version=VERSION,
        A=[old['A'][i] for i in (4,5,2,6)],B=[old['B'][i] for i in (0,1,2)],
        original_A_ids=['A5','A6','A3','A7'],reference_revision='unchanged-source-reviewed-v1',
        boundary='Development regression. Source silence is insufficient, not proof of the opposite. Whole-task requirements separate. Natural extra claims beyond pre-reviewed sources may remain unjudgeable.')


def order():
    a=[dict(id=f'A{i+1}-{v}',input=dict(line='A',case=i,variant=v)) for i in range(4) for v in (('before','bound') if i%2==0 else ('bound','before'))]
    b=[]
    for i in range(3):
        b.append(dict(id=f'G{i+1}',input=dict(line='G',case=i,variant='production')))
        for v in (('before','bound') if i%2==0 else ('bound','before')):b.append(dict(id=f'B{i+1}-{v}',input=dict(line='B',case=i,variant=v)))
    return a+b


def variants(c,v):
    return c if v=='production' else replace(c,fact_review_contract='simple_bound_v1' if v=='bound' else 'simple_v1',review_result_transport='strict_tool_v1')


def provider(settings,*,review_contract='production'):
    if settings.model_id!='deepseek-flash':raise ValueError('Flash-only; no model fallback')
    return ComparisonAdapter(settings,diagnostic_tool=bound_spec() if review_contract=='simple_bound_v1' else None)


class Gate:
    def __init__(self,m):self.materials=m;self.candidate={}
    def __call__(self,spec,raw):
        if any(x.get('code') in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CALL_BUDGET_EXHAUSTED','BUDGET_EXHAUSTED','MODEL_CANCELLED','CANCELLED') for x in raw.get('execution_issues',[])):
            return dict(component='harness',code='SERVICE_EXECUTION_FAILED',message='Unknown acceptance, timeout or shared budget boundary; stop remaining sends.')
        if spec['line']=='A' and spec['variant']=='bound':
            out=raw.get('verification_output') or {};refs=self.materials['A'][spec['case']]['reference']
            self.candidate[spec['case']]=raw
            for kind,items in [('fact',out.get('findings',[])),('citation',out.get('citation_reviews',[]))]:
                for i,item in enumerate(items):
                    if refs[i]!='supported' and item['status']=='supported':
                        return dict(component='evidence_verification',code='SERVICE_EXECUTION_FAILED',message='Candidate supports a pre-frozen protected counterexample; stop dependent delivery validation.',protected=dict(case=spec['case'],interface=kind,unit=i,reference=refs[i]))
        return None


def freeze(c,m,manifest):
    if (LOCAL/'freeze.json').exists() or (LOCAL/'attempt.json').exists():raise ValueError('No resume or overwrite')
    paths=sorted(p for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in (ROOT/folder).glob('*.py'))
    f=dict(version=VERSION,model='deepseek-flash',order=order(),configuration=shared.frozen_config(c),manifest=manifest,materials_sha256=shared.sha(m),sources=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p.read_bytes())) for p in paths],
        plan=dict(mechanism_tasks=8,natural_generation=3,paired_delivery_branches=6),comparison='before=simple_v1 strict tool; bound=simple_bound_v1 strict tool; no new Pro requests',
        immutable_inputs='Each natural question generated once, same draft/evidence/snapshot; per-branch variable budgets independently deduct generation records/time.',
        retrieval='Normal Factory retriever retained for generation AND full audits. No fixed-delivery shortcut in B; post-draft extraction/retrieval may differ between branches and is recorded, not attributed solely to projection.',
        admission='Candidate protected counterexample supported stops B; all shared faults/unknown state stop. Local malformed output retained; no retries/resume.',
        budget='Existing40 calls/800s,90s request,110s stage,one shared fact correction and at most oneRevision. No arbitrary batch cap.',
        references='Old source-reviewed references unchanged; AI-assisted supervised development materials, not independent holdout.')
    save(LOCAL/'materials.json',m);save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
    save(PUBLIC/'materials-reference.json',{k:v for k,v in m.items() if k!='sources'}|dict(source_identities={k:{q:e[q] for q in ('evidence_id','source_id','source_version','locator')} for k,e in m['sources'].items()}))
    return f


async def run():
    from harness.deepseek_trial import load_project_env
    load_project_env();c=ServiceConfig.from_environment()
    assert os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash'
    assert c.fact_review_contract=='production' and c.review_result_transport=='json' and c.verification_schema==13
    assert c.execution_path=='langgraph_v1'
    if (LOCAL/'attempt.json').exists():raise ValueError('No resume')
    factory=ComponentFactory(c)
    try:
        print('Read-only normal Factory preflight; zero model calls.',flush=True)
        k=factory.preflight();m=materials();f=freeze(c,m,factory.manifest(k))
        assert all(digest((ROOT/x['path']).read_bytes())==x['sha256'] for x in f['sources'])
        save(LOCAL/'attempt.json',dict(freeze_sha256=shared.sha(f),resume_allowed=False))
        result=await shared.batch(c,m,LOCAL/'batch',provider,rows=order(),request_builder=base.request,variant_config=variants,task_runner=base.task_runner,result_guard=Gate(m),fixed_audit_delivery=False)
        print(json.dumps(dict(executed=len(result['control']),unexecuted=result['unexecuted'],calls=len(result['send_log']))),flush=True)
        return result
    finally:await factory.close()


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('run once only; no resume')
