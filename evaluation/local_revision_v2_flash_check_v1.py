"""Four fixed historical first rounds -> new revision and real re-audit. No resume."""
import asyncio,json,os,sqlite3,subprocess
from contextlib import closing
from dataclasses import dataclass,replace
from pathlib import Path
from time import monotonic
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from agents.contracts import RevisionInput
from core.models import EvidenceBinding,ClaimExtractionOutput
from core.validation import require,validate_review,validate_extraction
from harness.contracts import ReviewRound
from evaluation.archive_replay import restore
from evaluation.local_revision_offline_v1 import old_input,OLD,SEQUENCES,sha,load
from evaluation import answer_review_net_benefit_v1 as shared
from services.local_revision_v2 import plan

VERSION='local-revision-v2-flash-check-v1'
LOCAL=ROOT/'data/retrieval_local'/VERSION
PUBLIC=ROOT/'docs/evaluation'/VERSION
INITIAL=(10,15,37,42)
BUSINESS=('services/local_revision_v2.py','services/literal_review_v1.py','services/literal_policy_v1.py','services/structured_model.py','services/validation_diagnostics.py','services/claim_extractor.py','services/claim_obligations.py','agents/power_domain_review.py','harness/product_policy.py')

def save(path,value):shared.write(path,wire(value))


@dataclass(frozen=True)
class History:
    revision: RevisionInput
    extraction: ClaimExtractionOutput
    decision: object
    provenance: dict


def recover():
    summary=load(OLD/'batch/summary.json');result=[]
    with closing(sqlite3.connect('file:'+(OLD/'batch/runs.sqlite3').as_posix()+'?mode=ro',uri=True)) as db:
        for n in INITIAL:
            partial,msg,_,_=old_input(n);rid=msg['run_id'];raw=summary['outputs'][rid]
            stored=json.loads(db.execute('SELECT result FROM runs WHERE id=?',(rid,)).fetchone()[0]);assert stored==raw
            initial=load(OLD/'batch'/rid/'input.json');rr=restore(raw['review_rounds'][0],ReviewRound)
            assert wire(rr.answer)==wire(partial.answer) and wire(rr.verification)==wire(partial.verification) and wire(rr.domain_review)==wire(partial.domain_review)
            assert raw['extraction_output']==wire(rr.extraction) and raw['evidence']==wire(partial.allowed_evidence)
            assert initial['generation_snapshot'] is None and raw['generation_output'] is None and not raw['retrieval_records'] and not raw['tool_results']
            assert all(e['knowledge_version'] is None for e in raw['trace']['events'])
            assert rr.report.decision.kind.value=='revise' and rr.report.decision.reason_codes==('LITERAL_SOURCE_BOUND_REPAIR',)
            v=replace(rr.verification,model_records=());d=replace(rr.domain_review,model_records=())
            bindings=tuple(restore(x,EvidenceBinding) for x in raw['evidence_bindings'])
            rev=replace(partial,verification=v,domain_review=d,evidence_bindings=bindings,knowledge_version=None,revision_instructions=rr.report.decision.reasons)
            validate_extraction(rr.extraction,rev.answer);validate_review(v,rev.answer,rr.extraction.claims,rev.allowed_evidence,True)
            validate_review(d,rev.answer,rr.extraction.claims,rev.allowed_evidence,False)
            historical=[c for c in raw['model_records'] if c['component'] in ('claim_extraction','evidence_verification','power_domain_review') and c['answer_version']==rev.answer.version]
            paths=[OLD/'batch'/rid/'input.json',OLD/'batch/messages'/f'{n:04d}.json',OLD/'batch/responses'/f'{n:04d}.json']
            provenance=dict(origin='historical_replay',case='A'+str(len(result)+1),source_revision_request_sequence=n,source_run_id=rid,
                source_input_sha256=shared.sha(initial),initial_review_sha256=shared.sha(raw['review_rounds'][0]),
                message_sha256=msg['messages_sha256'],restored_revision_sha256=shared.sha(wire(rev)),new_projection_sha256=shared.sha(plan(rev).payload),
                bindings_origin='original runs.result.evidence_bindings',instructions_origin='review_rounds[0].report.decision.reasons',
                knowledge_version=None,knowledge_origin='all original trace events; fixed A runner',generation_snapshot=None,snapshot_origin='original input.json explicit null; no generation_output',
                historical_background_records=historical,count_historical_as_new=False,
                files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p.read_bytes())) for p in paths])
            result.append(History(rev,rr.extraction,rr.report.decision,provenance))
    return result


def config(c):
    return replace(c,fact_review_contract='literal_v1',local_revision_interface='source_actions_v2',run_db=LOCAL/'batch/runs.sqlite3',
        budget=replace(c.budget,max_model_calls=12,max_duration_seconds=800,max_revision_rounds=1,max_transient_retries=0))


def verify_policy(c,history):
    policy=ComponentFactory(c).product_policy()
    for h in history:
        r=h.revision
        decision=policy.decide_context(r.verification,r.domain_review,c.budget,0,request=r.request,answer=r.answer,claims=h.extraction.claims,extraction=h.extraction,issues=(),retrieval=None)
        require(wire(decision)==wire(h.decision),'Historical revision eligibility differs; cannot force REVISE')


class FixedFactory(ComponentFactory):
    def create(self,rid,observer):return super().create(rid,observer,fixed_evidence_only=True)


class ReplayExtractor:
    uses_model_adapter=True
    def __init__(self,delegate,history):self.delegate,self.history=delegate,history
    async def extract(self,answer):return await self.extract_for_task(answer,self.history.revision.request)
    async def extract_for_task(self,answer,request):
        if answer.version==self.history.revision.answer.version:
            require(answer==self.history.revision.answer and request==self.history.revision.request,'Replay extraction binding mismatch')
            return self.history.extraction
        if hasattr(self.delegate,'extract_for_task'):return await self.delegate.extract_for_task(answer,request)
        return await self.delegate.extract(answer)


class ReplayReview:
    uses_model_adapter=True
    def __init__(self,delegate,history,kind):self.delegate,self.history,self.kind=delegate,history,kind
    def __getattr__(self,name):return getattr(self.delegate,name)
    async def run(self,inputs):
        h=self.history;r=h.revision
        if inputs.answer.version==r.answer.version:
            require(inputs.answer==r.answer and inputs.request==r.request and inputs.claims==h.extraction.claims,'Replay review input mismatch')
            require(inputs.evidence_bindings==r.evidence_bindings and inputs.knowledge_version==r.knowledge_version,'Replay origin binding mismatch')
            if self.kind=='fact':
                require(inputs.seed_evidence==r.allowed_evidence and inputs.generation_snapshot is None,'Replay factual delivery differs')
                return r.verification
            require(inputs.evidence==r.allowed_evidence,'Replay domain delivery differs');return r.domain_review
        return await self.delegate.run(inputs)


class BoundRevision:
    uses_model_adapter=True
    bounded_real_revision=True
    def __init__(self,delegate,history):self.delegate,self.history=delegate,history
    async def run(self,inputs):
        require(wire(inputs)==wire(self.history.revision),'Restored normal RevisionInput differs from archive; no send')
        return await self.delegate.run(inputs)


def runner(history,root):
    by_answer={h.revision.answer.answer_id:h for h in history}
    async def run(harness,request,budget,**kw):
        h=by_answer[request.existing_answer.answer_id]
        require(kw.get('knowledge_version') is None and kw.get('generation_snapshot') is None,'Historical null scope changed')
        harness.extractor=ReplayExtractor(harness.extractor,h)
        harness.verification=ReplayReview(harness.verification,h,'fact')
        harness.domain_review=ReplayReview(harness.domain_review,h,'domain')
        harness.revision=BoundRevision(harness.revision,h)
        original=harness.observer
        def observe(value):
            event=value['event'];replay=event.answer_version==h.revision.answer.version and event.component in ('claim_extraction','evidence_verification','power_domain_review') and value.get('stage_output') is not None
            original(dict(value,first_round_provenance=h.provenance,stage_origin='historical_replay' if replay else 'normal_current_execution'))
        harness.observer=observe
        shared.write(root/kw['run_id']/'historical-replay.json',h.provenance)
        result=await harness.run(request,budget,**kw)
        require(bool(result.review_rounds) and wire(result.review_rounds[0].report.decision)==wire(h.decision),'Normal replay policy differs: '+repr(result.execution_issues))
        require(not result.retrieval_records,'Unexpected new retrieval')
        return result
    return run


class SendLimit:
    def __init__(self,root,*,clock=monotonic,max_calls=48,max_seconds=3600):self.root=root;self.clock=clock;self.limit=max_calls;self.seconds=max_seconds;self.started=None;self.used=0;self.chains={};self.stop_reason=None
    def remaining_seconds(self):return max(.001,self.seconds-(self.clock()-self.started))
    def __call__(self,spec,request,n):
        now=self.clock()
        if self.started is None:self.started=now
        require(request.model_id=='deepseek-flash' and request.max_output_tokens==8000,'Frozen Flash parameters differ')
        if self.used>=self.limit or now-self.started>=self.seconds:
            self.stop_reason='global_request_limit' if self.used>=self.limit else 'global_time_limit'
            shared.write(self.root/'global-stop.json',dict(reason=self.stop_reason,used=self.used,elapsed=now-self.started));raise RuntimeError(self.stop_reason)
        key=str(spec['case']);require(self.chains.get(key,0)<12,'Per-chain send cap exceeded')
        self.used+=1;self.chains[key]=self.chains.get(key,0)+1
        save(self.root/'send-ledger'/f'{self.used:04d}.json',dict(used=self.used,chains=self.chains,elapsed=now-self.started,global_limit=self.limit))


class Gate:
    def __call__(self,spec,raw):
        if any(x['code'] in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CANCELLED','CANCELLED') for x in raw['execution_issues']):return dict(component='harness',code='SERVICE_EXECUTION_FAILED',message='Timeout/cancel or unknown acceptance: global stop, no recovery')


def order(history):return [dict(id='A'+str(i+1),input=dict(line='A',case=i,variant='source_actions_v2',historical_source=h.provenance)) for i,h in enumerate(history)]
def request(history,i,*,draft=False):return history[i].revision.request
def sources():return [dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p.read_bytes())) for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in sorted((ROOT/folder).glob('*.py'))]

def require_committed_sources():
    status=subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--','agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools'],cwd=ROOT,text=True)
    require(not status.strip(),'Commit reviewed source changes before the unique batch')


async def batch(c,history,root,provider,*,limit=None):
    limit=limit or SendLimit(root)
    return await shared.batch(c,history,root,provider,factory_type=FixedFactory,rows=order(history),request_builder=request,
        variant_config=lambda c,_:c,task_runner=runner(history,root),result_guard=Gate(),send_guard=limit,local_issue_codes=('MODEL_CALL_BUDGET_EXHAUSTED',))


async def run():
    if LOCAL.exists():raise ValueError('Unique new batch only; no resume or replacement freeze')
    require_committed_sources()
    from harness.deepseek_trial import load_project_env
    load_project_env();production=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((production.profile,production.verification_schema,production.fact_review_contract,production.local_revision_interface,production.execution_path)==('real',13,'production','production','langgraph_v1'),'Production baseline differs')
    require((production.extraction_message_profile,production.review_message_profile,production.review_result_transport,production.fact_internal_flow,production.domain_internal_flow,production.revision_answer_delivery)==('production','lossless_v1','json','production','production','production'),'Frozen business profiles differ')
    for path in BUSINESS:
        base=subprocess.check_output(['git','show','a6a42df8186b31d7e23319d3d0fe118964ff9b63:'+path],cwd=ROOT)
        require(base.replace(b'\r\n',b'\n')==(ROOT/path).read_bytes().replace(b'\r\n',b'\n'),'Business implementation changed')
    from harness.graph_runtime_v1 import validate_versions,build_graph
    validate_versions();build_graph()
    c=config(production);history=recover();verify_policy(c,history)
    f=dict(version=VERSION,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),baseline='a6a42df8186b31d7e23319d3d0fe118964ff9b63',sources=sources(),configuration=wire(c),
        manifest=ComponentFactory(c).manifest(None,fixed_evidence_only=True),fixed_evidence_only=True,index_resources_opened=False,knowledge_version=None,order=order(history),model='deepseek-flash',
        input_sha256=shared.sha([wire(h) for h in history]),references_sha256=sha((ROOT/'docs/evaluation/literal-review-stage1-v1/materials-reference.json').read_bytes()),
        budget=dict(per_chain_new=12,total_new=48,chain_seconds=800,batch_seconds=3600,output_tokens=8000,business_revisions=1),
        boundary='Historical first extraction/fact/domain exact business outputs replayed with no new cost; current revision and all new-version checks real. Fixed actual Evidence, no retrieval. No resume/rerun/second batch.',
        stop='Local malformed output or clear chain quota continues; any shared/config/program/storage/service/network/timeout/unknown failure stops all new sends. No semantic editing after first send.')
    save(LOCAL/'restored-inputs.json',[wire(h) for h in history]);save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
    require(sources()==f['sources'],'Freeze source mismatch')
    save(LOCAL/'attempt.json',dict(freeze_sha256=shared.sha(f),resume_allowed=False))
    from model_adapter.deepseek import create_adapter
    result=await batch(c,history,LOCAL/'batch',create_adapter)
    print(json.dumps(dict(executed=len(result['control']),unexecuted=result['unexecuted'],new_requests=len(result['send_log']))),flush=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('run once; historical recovery is available through recover(), zero sends')
