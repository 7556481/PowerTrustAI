"""Real read-only index acceptance and one new fixed live batch; shared execution."""
import asyncio,json,os,subprocess,hashlib
from dataclasses import replace
from time import monotonic
from types import SimpleNamespace as NS
from unittest.mock import patch
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from backend.store import RunStore
from core.models import TaskMode,TaskRequest,ClaimExtractionOutput
from core.validation import require,validate_request,validate_extraction
from model_adapter.contracts import ModelResponse
from evaluation.archive_replay import restore
from evaluation import source_first_live_v2 as old
from evaluation.natural_draft_audit_v1 import save,sha

VERSION='source-first-real-path-acceptance-v3'
LOCAL=ROOT/'data/retrieval_local'/VERSION

class Gate(old.UsageGate):
    def __init__(self,root):super().__init__(root,threshold=3000000,cap=160)
    def __call__(self,spec,r,n):
        with self.lock:
            key=f"{spec['case']}-{spec['variant']}"
            if self.stopped or self.calls>=self.cap or self.tokens>=self.threshold or self.remaining_seconds()<=.001:
                self.stopped=True;raise RuntimeError('Global v3 budget stop')
            require(self.chains.get(key,0)<20,'Per-chain20 limit')
            require(r.model_id=='deepseek-flash' and r.max_output_tokens==8000,'Frozen Flash parameters')
            index=self.calls+1;chars=sum(len(m.content) for m in r.messages)
            self.event('send',dict(id=index,chain=key,usage_before=self.tokens,inflight_before=len(self.pending),message_chars=chars,
                message_utf8_bytes=sum(len(m.content.encode()) for m in r.messages),rough_tokens=chars*.6+8000,
                estimate_basis='Official character heuristic .3English/.6Chinese; .6all chars warning only, not exact or a hard upper bound'))
            self.calls=index;self.chains[key]=self.chains.get(key,0)+1;self.pending.add(index);old.OWNER.set(index)

def configuration(m):
    frozen=json.loads((ROOT/'data/retrieval_local/source-first-audit-live-validation-v2/freeze.json').read_text(encoding='utf-8'))['configuration']
    return ServiceConfig(index_db=ROOT/frozen['index_db'],knowledge_version=m['cases'][0]['snapshot']['knowledge_version'],execution_path='langgraph_v1')

async def batch(c,m,root,provider,gate,*,rows=None,variant_strategy='source_first_audit_v1',accounted_factory=old.Accounted,fault_policy=None,budget_for=None):
    generated=old.inputs(m)
    def request(m,i,**kw):return replace(restore(m['cases'][i]['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
    def variant(cfg,v):return replace(cfg,audit_strategy=variant_strategy,fact_review_contract='literal_v1',local_revision_interface='source_actions_v2') if v=='candidate' else cfg
    async def runner(h,req,budget,**kw):
        i=next(i for i,x in generated.items() if x.answer.answer_id==req.existing_answer.answer_id)
        fixed=restore(m['cases'][i]['extraction'],ClaimExtractionOutput);delegate=h.extractor
        class Frozen:
            uses_model_adapter=True
            async def extract(self,a):return await self.extract_for_task(a,req)
            async def extract_for_task(self,a,r):
                if a.version==fixed.answer_version:validate_extraction(fixed,a);return fixed
                return await delegate.extract(a)
        h.extractor=Frozen()
        from rag.timing import capture_timing
        with capture_timing(run_id=kw['run_id']) as timing:
            result=await h.run(req,budget,indexed_reference_ids=tuple(e.evidence_id for e in req.provided_evidence),**kw)
        save(root/kw['run_id']/'retrieval-timing.json',timing.records)
        from rag.topic_lanes import plan
        save(root/kw['run_id']/'query-expressions.json',[dict(retrieval_id=r.retrieval_id,query=r.query,
            expression=plan(r.query) if r.query else None,method=r.query_method) for r in result.retrieval_records])
        return result
    rows=rows or [dict(id=f'S{i+1}-{v}',input=dict(line='B',case=i,variant=v)) for i in range(4) for v in (('baseline','candidate') if i%2==0 else ('candidate','baseline'))]
    def guard(spec,raw):
        if gate.stopped:return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Global usage/call/connection stop')
        # The established structured parser can report its local final contract
        # failure as OUTPUT_CONTRACT_ERROR; do not misclassify it as shared code.
    return await old.shared.batch(c,m,root,lambda settings,**opts:accounted_factory(provider(settings,**opts),gate),rows=rows,
        request_builder=request,variant_config=variant,task_runner=runner,result_guard=guard,initial_generated=generated,
        fixed_audit_delivery=False,independent_audit_budget=True,send_guard=gate,
        local_issue_codes=('MODEL_CALL_BUDGET_EXHAUSTED',),
        fault_policy=fault_policy,budget_for=budget_for or (lambda spec,b:replace(b,max_model_calls=20,max_revision_rounds=1,max_transient_retries=0)))

async def replay(label):
    m=old.material();c=configuration(m);root=LOCAL/label
    require(not root.exists(),'Never overwrite replay evidence')
    source=ROOT/'data/retrieval_local/source-first-audit-live-validation-v2/batch'
    records=json.loads((source/'summary.json').read_text(encoding='utf-8'))
    original=list(records['outputs'].values())[1]
    responses={row['prompt_version']:restore(json.loads((source/'provider-responses'/f'{i:04d}.json').read_text(encoding='utf-8')),ModelResponse)
        for i,row in enumerate(records['send_log'],1) if row['task']['variant']=='candidate'}
    class Replay:
        def close(self):pass
        async def complete(self,r):return responses[r.prompt_version]
    f=ComponentFactory(c);start=monotonic();f.warm_corpus_index();seal=monotonic()-start
    gate=Gate(root)
    with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):
        s=await batch(c,m,root,lambda *a,**k:Replay(),gate,rows=[dict(id='S1-candidate',input=dict(line='B',case=0,variant='candidate'))])
    result=next(iter(s['outputs'].values()))
    save(root/'acceptance.json',dict(state=result['state'],issues=result['execution_issues'],seal_seconds=seal,
        actual_index=True,response_origin='Exact archived v2 S1 candidate2 responses; new paid calls0',
        added_adjacent_ids=[eid for r in result['retrieval_records'] if r['outcome']=='source_scope' for eid in r['context_evidence_ids']],
        original_v2_state=original['state']))
    print(json.dumps(dict(label=label,state=result['state'],issues=result['execution_issues'],seal_seconds=seal),ensure_ascii=False))
    return result

async def offline():
    result=await replay('replay-after-verified')
    require(result['report'] is not None and not result['execution_issues'],'Archived-response replay failed')
    m=old.material();c=configuration(m);root=LOCAL/'real-paths-verified'
    require(not root.exists(),'Do not overwrite real path evidence')
    from tests.test_source_first_real_v3 import ActualInputSubstitute
    from rag.timing import capture_timing
    with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),capture_timing(run_id='v3-offline-real-index') as timing:
        s=await batch(c,m,root,lambda *a,**k:ActualInputSubstitute(),Gate(root),rows=[dict(id=f'S{i+1}-candidate',input=dict(line='B',case=i,variant='candidate')) for i in range(4)])
        save(root/'timing.json',timing.records)
        # One independent reachability probe uses the exact first frozen S4
        # component query and original retrieval/session budgets; not a new query.
        from harness.fact_retrieval import objects
        from harness.retrieval import RetrievalSession
        from rag.retriever import AsyncSQLiteBM25Retriever
        from harness.contracts import RetrievalSettings
        from rag.contracts import RetrievalPurpose
        req=replace(restore(m['cases'][3]['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
        claims=restore(m['cases'][3]['extraction'],ClaimExtractionOutput).claims
        query=next(x[4] for x in objects(claims) if x[3] in ('document_body','technical_content'))
        retriever=AsyncSQLiteBM25Retriever(c.index_db,execution_profile=c.retrieval_execution_profile)
        session=RetrievalSession(retriever,c.knowledge_version,RetrievalSettings(),c.budget,monotonic()+800,req.provided_evidence,tuple(e.evidence_id for e in req.provided_evidence))
        try:
            reachable=await session.retrieve(RetrievalPurpose.VERIFICATION,req,req.existing_answer,claims,query_override=query,fact_query=True)
            save(root/'s4-reachability.json',wire(reachable))
        finally:
            from backend.assembly import Bundle
            await Bundle(None,(retriever,)).drain();retriever.close()
        failure_root=LOCAL/'revision-failure-verified'
        fail=await batch(c,m,failure_root,lambda *a,**k:ActualInputSubstitute('revision_failure'),Gate(failure_root),rows=[dict(id='S2-candidate',input=dict(line='B',case=1,variant='candidate'))])
    states=[dict(slot=row['case_id'],state=s['outputs'][row['accepted']['run_id']]['state'],issues=s['outputs'][row['accepted']['run_id']]['execution_issues']) for row in s['control']]
    acceptance=dict(passed=False,actual_index=True,models='deterministic substitutes; no paid calls',states=states,
        reachability_status=reachable.record.outcome,revision_failure_states=[v['state'] for v in fail['outputs'].values()])
    save(root/'acceptance.json',acceptance)
    require(len(s['outputs'])==4 and all(not v['execution_issues'] for v in s['outputs'].values()),'Real-index deterministic paths incomplete; inspect archive')
    require(all(v['answer']['version']==2 and len(v['review_rounds'])==2 for v in list(s['outputs'].values())[1:3]),'Revision/full rereview not exercised')
    require(any(v['execution_issues'] for v in fail['outputs'].values()),'Revision failure not exercised')
    require(any(e['component']=='source_first_domain_recheck' for v in s['outputs'].values() for e in v['trace']['events']),'Expanded domain supply not rechecked')
    acceptance.update(passed=True,sources=old.sources())
    save(root/'acceptance.json',acceptance)
    print(json.dumps(dict(real_path_states=states,reachability=reachable.record.outcome),ensure_ascii=False))

async def run():
    require(not (LOCAL/'live').exists(),'Unique live attempt; no resume')
    for p in ('replay-after-verified/acceptance.json','real-paths-verified/acceptance.json',
              'replay-after-verified/projection-acceptance.json','real-paths-verified/projection-acceptance.json'):
        require((LOCAL/p).is_file(),'Required real-index offline acceptance absent: '+p)
    require(json.loads((LOCAL/'replay-after-verified/acceptance.json').read_text(encoding='utf-8'))['state']!='failed','Replay not accepted')
    acceptance=json.loads((LOCAL/'real-paths-verified/acceptance.json').read_text(encoding='utf-8'))
    require(acceptance['passed'] and acceptance['sources']==old.sources(),'Real-path acceptance incomplete or source changed')
    m=old.material()
    from harness.deepseek_trial import load_project_env
    load_project_env();c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.audit_strategy,c.verification_schema,c.fact_review_contract,c.fact_review_execution)==('baseline',13,'production','serial_v1'),'Frozen original production baseline required')
    c=replace(c,nli_enabled=False,run_db=LOCAL/'live/runs.sqlite3',budget=replace(c.budget,max_model_calls=20,max_revision_rounds=1))
    for row in m['cases']:
        req=replace(restore(row['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
        validate_request(req,c.budget);require(row['snapshot']['knowledge_version']==c.knowledge_version,'Knowledge mismatch')
    before=old.sources();start=monotonic();f=ComponentFactory(c);f.preflight();seal=monotonic()-start
    save(LOCAL/'live/freeze.json',dict(start_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources=before,material_sha=sha(m),configuration=wire(c),order=m['order'],seal_seconds=seal,limits=dict(total_calls=160,chain_calls=20,usage_threshold=3000000)))
    save(LOCAL/'live/attempt.json',dict(unique=True,no_resume=True))
    from model_adapter.deepseek import create_adapter
    gate=Gate(LOCAL/'live')
    try:
        s=await batch(c,m,LOCAL/'live',create_adapter,gate)
        save(LOCAL/'live/totals.json',dict(requests=gate.calls,tokens=gate.tokens,pending=sorted(gate.pending),stopped=gate.stopped,overshoot=max(0,gate.tokens-3000000)))
        require(old.sources()==before,'Source changed after freeze')
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],requests=gate.calls,tokens=gate.tokens)))
    finally:await f.close()

if __name__=='__main__':
    import sys
    asyncio.run(offline() if sys.argv[1:]==['offline'] else replay(sys.argv[1]) if sys.argv[1:] and sys.argv[1].startswith('replay-') else run())
