"""One authorized v2-only fixed-reference run. No resume, v1 send or model tuning."""
import asyncio
from dataclasses import asdict
from evaluation import fact_internal_flow_trial_v1 as shared
from evaluation.fact_internal_flow_materials_v2 import PUBLIC,CASE_IDS,SETTINGS
from services.fact_flow_protocol_v2 import create_agent,PROMPT

ROOT=shared.ROOT
LOCAL=ROOT/'data/retrieval_local/fact-internal-flow-live-v2'
VERSION='fact-internal-flow-v2-fixed-reference-live-v1'
PLAN=PUBLIC/'actual-execution-plan-v1.json'
FREEZE=PUBLIC/'execution-freeze-v1.json'


def validate_plan(plan):
    order=plan['order']
    if [r['case'] for r in order]!=list(CASE_IDS):raise ValueError('Only authorized fixed order allowed')
    if any(r['variant']!='v2' or r['initial_calls']!=1 or r['prompt_version']!=PROMPT for r in order):raise ValueError('Only v2 initial requests allowed')
    if plan['max_sends']!=12 or plan['model']!=asdict(SETTINGS):raise ValueError('Frozen model/call plan required')
    approved={r['case']:r for r in shared.read(PUBLIC/'preparation-v1.json')['order'] if r['variant']=='v2'}
    if any(r!=approved[r['case']] for r in order):raise ValueError('Approved messages changed')


def prepare_plan():
    preparation=shared.read(PUBLIC/'preparation-v1.json')
    selected={r['case']:r for r in preparation['order'] if r['variant']=='v2'}
    shared.write(PLAN,{'version':VERSION,'authorization':'User accepted v2 and six cases, authorized this v2-only DeepSeek run; historical v1 descriptive only, no paid v1 and no strict paired improvement rate.',
        'model':asdict(SETTINGS),'order':[selected[c] for c in CASE_IDS],
        'initial_calls':6,'corrections_per_branch':1,'max_sends':12,
        'budget_per_branch':40,'budget_deadline_seconds':800,'branch_timeout_seconds':110,
        'stop':'First unexpected final structure, execution, cancellation, timeout or storage failure stops all later sends.',
        'no_retry_resume_supplement':True,'production_changed':False,
        'prior_proposal_preserved_sha256':shared.digest(PUBLIC/'revalidation-plan-v1.md'),
        'reference_sha256':shared.digest(PUBLIC/'inputs-and-reference-v1.json'),
        'scoring':'Original and effective support separate; F05 content supported plus explicit objection/fidelity faithful/effective review-required. Fixed six cases/seven components; F05 diagnostic separate. No reduced denominators or paired improvement rates.'})


def freeze():
    plan=shared.read(PLAN);validate_plan(plan)
    old=shared.read(PUBLIC/'source-manifest-v1.json')
    changes=[]
    for r in old['files']:
        actual=shared.digest(ROOT/r['path'])
        if actual!=r['sha256']:
            if r['path']!='evaluation/fact_internal_flow_trial_v1.py':raise ValueError('Accepted semantic implementation changed')
            changes.append({'path':r['path'],'approved_sha256':r['sha256'],'actual_sha256':actual,
                'reason':'Reuse prior sequential archival loop via optional builder/cap/version; persist cancellation, no semantic or default production changes.'})
    paths={r['path'] for r in old['files']}
    paths.update(('evaluation/fact_internal_flow_trial_v2.py','tests/test_fact_internal_flow_trial_v2.py',
        'docs/evaluation/fact-internal-flow-v2/actual-execution-plan-v1.json',
        'docs/evaluation/fact-internal-flow-v2/inputs-and-reference-v1.json',
        'docs/evaluation/fact-internal-flow-v2/preparation-v1.json',
        'docs/evaluation/fact-internal-flow-v2/revalidation-plan-v1.md'))
    shared.write(FREEZE,{'version':VERSION,'plan':plan,'allowed_runner_evolution':changes,
        'files':[{'path':p,'sha256':shared.digest(ROOT/p)} for p in sorted(paths)]})


def preflight():
    if (LOCAL/'attempt.json').exists():raise ValueError('Attempt exists; no resume or rerun')
    f=shared.read(FREEZE);validate_plan(f['plan'])
    for r in f['files']:
        if shared.digest(ROOT/r['path'])!=r['sha256']:raise ValueError('Frozen source or input changed')
    return f


async def batch(plan,root,factory):
    validate_plan(plan)
    return await shared.batch(plan,root,factory,agent_builder=lambda adapter,settings,diagnostics:
        create_agent(adapter,settings,diagnostic_dir=diagnostics),max_sends=12,version=VERSION)


def execute():
    f=preflight()
    from harness.deepseek_trial import load_project_env
    load_project_env()
    from model_adapter.deepseek import create_adapter
    shared.write(LOCAL/'attempt.json',{'version':VERSION,'freeze_sha256':shared.digest(FREEZE),'resume_allowed':False})
    return asyncio.run(batch(f['plan'],LOCAL,lambda:create_adapter(SETTINGS)))

if __name__=='__main__':
    import sys,json
    if sys.argv[1:]==['prepare']:prepare_plan()
    elif sys.argv[1:]==['freeze']:freeze()
    elif sys.argv[1:]==['execute']:
        result=execute();print(json.dumps({'total_sends':result['total_sends'],'branches':[{k:r[k] for k in ('id','status')} for r in result['branches']]}))
    else:raise SystemExit('prepare | freeze | execute')
