"""Single ten-candidate Flash validation using original SQL and v5 isolation."""
import asyncio,json,os,subprocess
from dataclasses import replace
from time import monotonic
from unittest.mock import patch
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation import source_first_modality_v6 as prior
from evaluation.source_first_live_v2 import sources
from evaluation.failure_isolation_v5 import Gate as PriorGate,Accounted,Isolation,observed_provider
from evaluation.natural_draft_audit_v1 import save,sha
from core.validation import require,validate_request
from core.models import TaskRequest,TaskMode
from evaluation.archive_replay import restore
LOCAL=ROOT/'data/retrieval_local/retrieval-rank-and-audit-reference-v7/audit'
class Gate(PriorGate):
    def __init__(self,root):super().__init__(root);self.cap=200;self.threshold=3500000
def material():return prior.material()
def rows(m):return [r for r in prior.prior.rows(m) if r['input']['variant']=='candidate']
async def execute(c,m,root,provider,*,gate=None):
    gate=gate or Gate(root)
    s=await prior.prior.prior.batch(c,m,root,provider,gate,rows=rows(m),variant_strategy='source_first_audit_v4',accounted_factory=Accounted,fault_policy=Isolation(gate))
    save(root/'totals.json',dict(request_boundary_entries=gate.calls,known_usage_tokens=gate.tokens,actual_total_tokens=None if gate.unknown else gate.tokens,pending=sorted(gate.pending),unknown=gate.unknown,stopped=gate.stopped,known_overshoot=max(0,gate.tokens-gate.threshold),release_receipts=gate.release_records))
    return s
async def offline():
    from tests.test_audit_reference_v7 import ReferenceSubstitute
    from tools.source_first_v4_read import check
    from model_adapter.contracts import ModelResponse
    m=material();c=prior.prior.prior.configuration(m);root=LOCAL/'offline-verified';require(not root.exists(),'Preserve offline attempt')
    p=prior.LOCAL/'live';old=json.loads((p/'summary.json').read_text(encoding='utf-8'));archive={}
    for entry in old['control']:
        if entry['case_id'] not in ('S2-candidate','S3-candidate','S4-candidate','S10-candidate'):continue
        rid=entry['accepted']['run_id'];raw=old['outputs'][rid];sends=[s for s in old['send_log'] if s['run_id']==rid]
        for rec in raw['model_records']:
            if not rec.get('validation_error'):continue
            send=sends[rec['call_number']-1];key=(raw['answer']['answer_id'],rec['answer_version'],'fact' if rec['component']=='evidence_verification' else 'domain')
            archive.setdefault(key,restore(json.loads((p/'provider-responses'/f"{send['sequence']:04d}.json").read_text(encoding='utf-8')),ModelResponse))
    class ReplayThenSynthetic(ReferenceSubstitute):
        async def complete(self,r):
            d=json.loads(r.messages[1].content)
            kind='fact' if r.prompt_version=='source_first_audit_v4' else 'domain' if r.prompt_version=='power-domain-review-reference-v7' else None
            key=(d.get('answer',{}).get('answer_id'),d.get('answer',{}).get('version'),kind)
            if kind and key in archive and not r.correction:return archive.pop(key)
            return await super().complete(r)
    f=ComponentFactory(c);start=monotonic();f.warm_corpus_index();seal=monotonic()-start
    try:
        with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):s=await execute(c,m,root,lambda *a,**k:ReplayThenSynthetic())
        require(len(s['outputs'])==10 and all(not v['execution_issues'] for v in s['outputs'].values()),'Real-index candidate path incomplete')
        for i in (1,2,9):
            v=list(s['outputs'].values())[i];require(v['answer']['version']==2 and len(v['review_rounds'])==2,'Revision/reextraction/double review missing')
        require(any(r['context_evidence_ids'] for v in s['outputs'].values() for r in v['retrieval_records']),'Nonempty actual adjacency missing')
        check('offline-verified',archive_root=LOCAL,candidate_strategy='source_first_audit_v4',materials=m)
        save(root/'acceptance.json',dict(passed=True,sources=sources(),seal_seconds=seal,material_sha=sha(m),provenance='Exact invalid v6 raw responses rejected, not transformed into successful predictions; all new/corrective responses are explicit synthetic substitutes. Old citation scope rejection also unit-tested; no semantic model score.'))
        print('Ten actual-index candidate paths, archived failures and ordinary reads accepted',flush=True)
    finally:await f.close()
async def live():
    root=LOCAL/'live';require(not root.exists(),'Single v7 batch; no resume')
    a=json.loads((LOCAL/'offline-verified/acceptance.json').read_text(encoding='utf-8'));require(a['passed'] and a['sources']==sources(),'Offline source freeze changed');require((LOCAL/'full-offline-passed.json').is_file(),'Full offline required')
    from harness.deepseek_trial import load_project_env
    load_project_env();m=material();c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.audit_strategy,c.verification_schema,c.fact_review_contract,c.fact_review_execution,c.retrieval_execution_profile)==('baseline',13,'production','serial_v1','topic_v4_subject_v1'),'Original audit and SQL baseline required')
    c=replace(c,nli_enabled=False,run_db=root/'runs.sqlite3',budget=replace(c.budget,max_model_calls=20,max_revision_rounds=1))
    for case in m['cases']:
        req=replace(restore(case['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING);validate_request(req,c.budget);require(case['snapshot']['knowledge_version']==c.knowledge_version,'Knowledge mismatch')
    before=sources();f=ComponentFactory(c);start=monotonic();f.preflight();seal=monotonic()-start
    save(root/'freeze.json',dict(start_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=before,configuration=wire(c),material_sha=sha(m),order=[r['id'] for r in rows(m)],seal_seconds=seal,limits=dict(chain_calls=20,total_calls=200,known_usage_stop=3500000,allowed_released_unknowns=1),ranking='original score,rowid SQL; independent of A',timeouts='unchanged model/socket90, stage110, run800'))
    save(root/'attempt.json',dict(unique=True,no_resume=True));gate=Gate(root)
    from model_adapter.deepseek import create_adapter
    try:
        s=await execute(c,m,root,observed_provider(gate,create_adapter),gate=gate);require(sources()==before,'Frozen business changed after paid start')
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],requests=gate.calls,known_tokens=gate.tokens,unknown=len(gate.unknown))),flush=True)
    finally:await f.close()
if __name__=='__main__':
    import sys
    require(sys.argv[1:] in (['offline'],['live']),'Explicit offline/live required');asyncio.run(offline() if sys.argv[1:]==['offline'] else live())
