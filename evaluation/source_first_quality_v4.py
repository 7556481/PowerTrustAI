"""One fixed v4 batch on the established atomic usage gate and shared runner."""
import asyncio,json,os,subprocess
from dataclasses import replace
from time import monotonic
from unittest.mock import patch
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation import source_first_real_v3 as prior
from evaluation.source_first_live_v2 import sources
from evaluation.natural_draft_audit_v1 import save,sha
from core.validation import require,validate_request
from core.models import TaskRequest,TaskMode
from evaluation.archive_replay import restore

LOCAL=ROOT/'data/retrieval_local/source-first-quality-ui-release-v4'
class Gate(prior.Gate):
    def __init__(self,root):
        super().__init__(root);self.cap=240;self.threshold=4000000

def material():
    m=json.loads((LOCAL/'materials.json').read_text(encoding='utf-8'))
    identity=json.loads((LOCAL/'materials-identity.json').read_text(encoding='utf-8'))
    require(sha(m)==identity['sha256'] and len(m['cases'])==8,'Frozen v4 material mismatch')
    selected=json.loads((LOCAL/'selection-before-code.json').read_text(encoding='utf-8'))
    require(m['cases'][:4]==selected['old_four'],'Old four materials changed')
    for actual,pinned in zip(m['cases'][4:],selected['new_four']):
        require((actual['request']['question'],actual['request']['existing_answer']['text'],actual['kind'],actual['expected'])==tuple(pinned['spec'][1:]),'New selection changed')
    return m

def rows(m):
    return [dict(id=slot,input=dict(line='B',case=int(slot.split('-')[0][1:])-1,variant=slot.split('-')[1])) for slot in m['order']]

async def execute(c,m,root,provider,gate,*,selected=None):
    return await prior.batch(c,m,root,provider,gate,rows=selected or rows(m),variant_strategy='source_first_audit_v2')

async def offline():
    from tests.test_source_first_quality_v4 import RelationSubstitute
    m=material();c=prior.configuration(m);root=LOCAL/'offline-verified'
    require(not root.exists(),'Preserve offline evidence')
    factory=ComponentFactory(c);start=monotonic();factory.warm_corpus_index();seal=monotonic()-start
    with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):
        s=await execute(c,m,root,lambda *a,**k:RelationSubstitute(),Gate(root),selected=[r for r in rows(m) if r['input']['variant']=='candidate'])
        failure=await execute(c,m,LOCAL/'offline-revision-failure-verified',lambda *a,**k:RelationSubstitute('revision_failure'),Gate(LOCAL/'offline-revision-failure-verified'),selected=[r for r in rows(m) if r['id']=='S2-candidate'])
    require(len(s['outputs'])==8 and all(not x['execution_issues'] for x in s['outputs'].values()),'Real-index v4 deterministic path failed')
    changed=[x for x in s['outputs'].values() if x['answer']['version']==2]
    require(len(changed)>=2 and all(len(x['review_rounds'])==2 for x in changed),'Actual revision/full review not exercised')
    require(any(r['context_evidence_ids'] for x in s['outputs'].values() for r in x['retrieval_records']),'Actual neighbor set empty')
    require(any(x['execution_issues'] for x in failure['outputs'].values()),'Illegal revision was not retained')
    save(root/'acceptance.json',dict(passed=True,actual_index=True,model_responses='deterministic substitutes, not semantic evidence',seal_seconds=seal,sources=sources(),states=[x['state'] for x in s['outputs'].values()]))
    print('Real index eight-path offline acceptance passed',flush=True)

async def live():
    require(not (LOCAL/'live').exists(),'Unique v4 attempt; no resume')
    a=json.loads((LOCAL/'offline-verified/acceptance.json').read_text(encoding='utf-8'))
    require(a['passed'] and a['sources']==sources(),'Offline source freeze changed')
    require((LOCAL/'offline-verified/read-acceptance.json').is_file(),'Ordinary read acceptance required')
    require((LOCAL/'full-offline-passed.json').is_file(),'Final full suite required')
    m=material();c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.audit_strategy,c.verification_schema,c.fact_review_contract,c.fact_review_execution)==('baseline',13,'production','serial_v1'),'Original baseline required')
    c=replace(c,nli_enabled=False,run_db=LOCAL/'live/runs.sqlite3',budget=replace(c.budget,max_model_calls=20,max_revision_rounds=1))
    for case in m['cases']:
        request=replace(restore(case['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
        validate_request(request,c.budget);require(case['snapshot']['knowledge_version']==c.knowledge_version,'Knowledge identity mismatch')
    before=sources();factory=ComponentFactory(c);start=monotonic();factory.preflight();seal=monotonic()-start
    save(LOCAL/'live/freeze.json',dict(start_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=before,material_sha=sha(m),configuration=wire(c),order=m['order'],seal_seconds=seal,limits=m['limits']))
    save(LOCAL/'live/attempt.json',dict(unique=True,no_resume=True))
    from model_adapter.deepseek import create_adapter
    gate=Gate(LOCAL/'live')
    try:
        s=await execute(c,m,LOCAL/'live',create_adapter,gate)
        save(LOCAL/'live/totals.json',dict(requests=gate.calls,tokens=gate.tokens,pending=sorted(gate.pending),stopped=gate.stopped,overshoot=max(0,gate.tokens-gate.threshold)))
        require(sources()==before,'Frozen source changed after paid start')
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],requests=gate.calls,tokens=gate.tokens)),flush=True)
    finally:await factory.close()

if __name__=='__main__':
    import sys
    asyncio.run(offline() if sys.argv[1:]==['offline'] else live())
