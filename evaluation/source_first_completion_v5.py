"""Fixed v5 validation, unchanged v4 materials/semantics; one bounded unknown."""
import asyncio,json,os,subprocess
from dataclasses import replace
from time import monotonic
from unittest.mock import patch
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation import source_first_quality_v4 as prior
from evaluation.source_first_live_v2 import sources
from evaluation.failure_isolation_v5 import Gate,Accounted,Isolation,observed_provider
from evaluation.natural_draft_audit_v1 import save,sha
from core.validation import require,validate_request
from core.models import TaskRequest,TaskMode
from evaluation.archive_replay import restore

LOCAL=ROOT/'data/retrieval_local/source-first-revision-completion-release-v5'
async def execute(c,m,root,provider,*,selected=None,budget_for=None,gate=None,policy=None):
    gate=gate or Gate(root);policy=policy or Isolation(gate)
    s=await prior.prior.batch(c,m,root,provider,gate,rows=selected or prior.rows(m),variant_strategy='source_first_audit_v2',accounted_factory=Accounted,fault_policy=policy,budget_for=budget_for)
    save(root/'totals.json',dict(request_boundary_entries=gate.calls,known_usage_tokens=gate.tokens,actual_total_tokens=None if gate.unknown else gate.tokens,pending=sorted(gate.pending),unknown=gate.unknown,stopped=gate.stopped,known_overshoot=max(0,gate.tokens-gate.threshold),release_receipts=gate.release_records))
    return s

async def offline():
    from tests.test_source_first_completion_v5 import ArchivedThenSynthetic
    from tools.source_first_v4_read import check
    m=prior.material();c=prior.prior.configuration(m);root=LOCAL/'offline-verified'
    require(not root.exists(),'Preserve offline evidence')
    factory=ComponentFactory(c);start=monotonic();factory.warm_corpus_index();seal=monotonic()-start
    with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):
        s=await execute(c,m,root,lambda *a,**k:ArchivedThenSynthetic(),selected=[r for r in prior.rows(m) if r['input']['variant']=='candidate'])
    require(len(s['outputs'])==8 and all(not x['execution_issues'] for x in s['outputs'].values()),'Actual-index offline flow failed')
    second=list(s['outputs'].values())[1]
    require(second['answer']['version']==2 and len(second['review_rounds'])==2,'Archived S2 initial review did not reach complete synthetic revision/reviews')
    require('并明确计入' in second['answer']['text'],'Synthetic repair weakened unrelated correct requirement')
    require(any(r['context_evidence_ids'] for x in s['outputs'].values() for r in x['retrieval_records']),'Nonempty actual adjacency required')
    check('offline-verified',archive_root=LOCAL)
    save(root/'acceptance.json',dict(passed=True,seal_seconds=seal,sources=sources(),models='Exact archived v4 S1/S2 initial responses; missing Revision and post-revision extraction/reviews are explicit deterministic substitutes; others deterministic. No paid calls',material_sha=sha(m)))
    print('v5 real index archived/synthetic paths and ordinary reads accepted',flush=True)

async def live():
    root=LOCAL/'live';require(not root.exists(),'Only one v5 live attempt; never resume')
    a=json.loads((LOCAL/'offline-verified/acceptance.json').read_text())
    require(a['passed'] and a['sources']==sources(),'Offline implementation changed')
    require((LOCAL/'full-offline-passed.json').is_file() and (LOCAL/'isolation-acceptance.json').is_file(),'Full suite and real-entry failure isolation required')
    m=prior.material();c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.audit_strategy,c.verification_schema,c.fact_review_contract,c.fact_review_execution)==('baseline',13,'production','serial_v1'),'Unchanged baseline required')
    c=replace(c,nli_enabled=False,run_db=root/'runs.sqlite3',budget=replace(c.budget,max_model_calls=20,max_revision_rounds=1))
    for row in m['cases']:
        r=replace(restore(row['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING);validate_request(r,c.budget)
        require(row['snapshot']['knowledge_version']==c.knowledge_version,'Knowledge mismatch')
    before=sources();factory=ComponentFactory(c);start=monotonic();factory.preflight();seal=monotonic()-start
    save(root/'freeze.json',dict(start_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=before,configuration=wire(c),material_sha=sha(m),order=m['order'],seal_seconds=seal,limits=dict(chain_calls=20,total_calls=240,known_usage_stop=4000000,allowed_released_unknowns=1),timeouts='unchanged model/socket90, stage110, run800'))
    save(root/'attempt.json',dict(unique=True,no_resume=True))
    from model_adapter.deepseek import create_adapter
    gate=Gate(root)
    try:
        s=await execute(c,m,root,observed_provider(gate,create_adapter),gate=gate)
        require(sources()==before,'Frozen business changed after start')
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],requests=gate.calls,known_tokens=gate.tokens,unknown=len(gate.unknown))),flush=True)
    finally:await factory.close()

if __name__=='__main__':
    import sys
    asyncio.run(offline() if sys.argv[1:]==['offline'] else live())
