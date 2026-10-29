"""One frozen 14-chain v6 run on existing runner and v5 isolation."""
import asyncio,json,os,subprocess
from dataclasses import replace
from time import monotonic
from unittest.mock import patch
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation import source_first_quality_v4 as prior
from evaluation.source_first_live_v2 import sources
from evaluation.failure_isolation_v5 import Gate as PriorGate,Accounted,Isolation,observed_provider
from evaluation.natural_draft_audit_v1 import save,sha
from core.validation import require,validate_request
from core.models import TaskRequest,TaskMode
from evaluation.archive_replay import restore

LOCAL=ROOT/'data/retrieval_local/source-first-modality-release-v6'
class Gate(PriorGate):
    def __init__(self,root):super().__init__(root);self.cap=280;self.threshold=4500000
def material():
    m=json.loads((LOCAL/'materials.json').read_text(encoding='utf-8'));identity=json.loads((LOCAL/'materials-identity.json').read_text(encoding='utf-8'))
    require(sha(m)==identity['sha256'] and len(m['cases'])==10,'Frozen v6 material mismatch')
    require(m['cases'][:8]==prior.material()['cases'],'Original eight changed')
    require(m['order']==prior.material()['order']+['S9-candidate','S10-candidate'],'Frozen order changed')
    return m
async def execute(c,m,root,provider,*,selected=None,gate=None):
    gate=gate or Gate(root)
    s=await prior.prior.batch(c,m,root,provider,gate,rows=selected or prior.rows(m),variant_strategy='source_first_audit_v3',accounted_factory=Accounted,fault_policy=Isolation(gate))
    save(root/'totals.json',dict(request_boundary_entries=gate.calls,known_usage_tokens=gate.tokens,actual_total_tokens=None if gate.unknown else gate.tokens,pending=sorted(gate.pending),unknown=gate.unknown,stopped=gate.stopped,known_overshoot=max(0,gate.tokens-gate.threshold),release_receipts=gate.release_records))
    return s
async def offline():
    from tests.test_source_first_modality_v6 import GroundedSubstitute
    from tools.source_first_v4_read import check
    from model_adapter.contracts import ModelResponse
    m=material();c=prior.prior.configuration(m);root=LOCAL/'offline-verified';require(not root.exists(),'Preserve offline attempt')
    p=ROOT/'data/retrieval_local/source-first-revision-completion-release-v5/live';old=json.loads((p/'summary.json').read_text(encoding='utf-8'))
    rid=next(r['accepted']['run_id'] for r in old['control'] if r['case_id']=='S2-candidate')
    send=next(s for s in old['send_log'] if s['run_id']==rid and s['prompt_version']=='source_first_audit_v2')
    response=restore(json.loads((p/'provider-responses'/f"{send['sequence']:04d}.json").read_text(encoding='utf-8')),ModelResponse)
    class ReplayThenSynthetic(GroundedSubstitute):
        async def complete(self,r):
            d=json.loads(r.messages[1].content)
            if r.prompt_version=='source_first_audit_v3' and not r.correction and d['answer']['answer_id']==m['cases'][1]['request']['existing_answer']['answer_id'] and d['answer']['version']==1:return response
            return await super().complete(r)
    f=ComponentFactory(c);start=monotonic();f.warm_corpus_index();seal=monotonic()-start
    try:
        with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):s=await execute(c,m,root,lambda *a,**k:ReplayThenSynthetic(),selected=[r for r in prior.rows(m) if r['input']['variant']=='candidate'])
        require(len(s['outputs'])==10 and all(not x['execution_issues'] for x in s['outputs'].values()),'Actual-index offline flow incomplete')
        for i in (1,2,9):
            v=list(s['outputs'].values())[i];require(v['answer']['version']==2 and len(v['review_rounds'])==2,'Required synthetic revision/full review missing')
        require('并明确计入' in list(s['outputs'].values())[1]['answer']['text'],'S2 synthetic repair lost adjacent true requirement')
        require('0.90pu' in list(s['outputs'].values())[9]['answer']['text'] and '不得造成电压崩溃' in list(s['outputs'].values())[9]['answer']['text'],'Mixed-unit true obligations lost')
        require(any(r['context_evidence_ids'] for x in s['outputs'].values() for r in x['retrieval_records']),'Actual nonempty adjacency missing')
        check('offline-verified',archive_root=LOCAL,candidate_strategy='source_first_audit_v3',materials=m)
        save(root/'acceptance.json',dict(passed=True,seal_seconds=seal,sources=sources(),material_sha=sha(m),provenance='Exact v5 S2 initial response rejected by v3 literal binding; correction, Revision and later stages explicit deterministic substitutes. Others deterministic; not model quality evidence.'))
        print('Ten real-index offline paths and ordinary reads accepted',flush=True)
    finally:await f.close()
async def live():
    root=LOCAL/'live';require(not root.exists(),'One fixed v6 attempt, no resume')
    a=json.loads((LOCAL/'offline-verified/acceptance.json').read_text(encoding='utf-8'));require(a['passed'] and a['sources']==sources(),'Offline source freeze changed')
    require((LOCAL/'full-offline-passed.json').is_file(),'Final full suite required')
    from harness.deepseek_trial import load_project_env
    load_project_env();m=material();c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.audit_strategy,c.verification_schema,c.fact_review_contract,c.fact_review_execution)==('baseline',13,'production','serial_v1'),'Original production baseline required')
    c=replace(c,nli_enabled=False,run_db=root/'runs.sqlite3',budget=replace(c.budget,max_model_calls=20,max_revision_rounds=1))
    for row in m['cases']:
        r=replace(restore(row['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING);validate_request(r,c.budget);require(row['snapshot']['knowledge_version']==c.knowledge_version,'Knowledge identity mismatch')
    before=sources();f=ComponentFactory(c);start=monotonic();f.preflight();seal=monotonic()-start
    save(root/'freeze.json',dict(start_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=before,configuration=wire(c),material_sha=sha(m),order=m['order'],seal_seconds=seal,limits=m['limits'],timeouts='unchanged model/socket90, stage110, run800'))
    save(root/'attempt.json',dict(unique=True,no_resume=True))
    from model_adapter.deepseek import create_adapter
    gate=Gate(root)
    try:
        s=await execute(c,m,root,observed_provider(gate,create_adapter),gate=gate);require(sources()==before,'Frozen business changed after paid start')
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],requests=gate.calls,known_tokens=gate.tokens,unknown=len(gate.unknown))),flush=True)
    finally:await f.close()
if __name__=='__main__':
    import sys
    require(sys.argv[1:] in (['offline'],['live']),'Explicit offline/live action required')
    asyncio.run(offline() if sys.argv[1:]==['offline'] else live())
