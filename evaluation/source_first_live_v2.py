"""Unique usage_threshold_v2 batch on existing Factory/Harness/Store paths."""
import asyncio,json,os,threading,subprocess,hashlib
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from time import monotonic
from types import SimpleNamespace as NS
from backend.config import ROOT,ServiceConfig
from backend.serialization import wire
from backend.assembly import ComponentFactory
from core.models import TaskRequest,TaskMode,GenerationEvidenceSnapshot,ClaimExtractionOutput
from core.validation import validate_request,validate_extraction,require
from evaluation.archive_replay import restore
from evaluation import answer_review_net_benefit_v1 as shared
from evaluation.source_first_materials_v1 import LOCAL as MATERIALS
from evaluation.natural_draft_audit_v1 import sha,save
from model_adapter.contracts import ModelConnectionError

VERSION='source-first-audit-live-validation-v2'
LOCAL=ROOT/'data/retrieval_local'/VERSION
OWNER=ContextVar('usage_threshold_v2_send',default=None)

class UsageGate:
    def __init__(self,root,threshold=1200000,cap=96):
        self.root=Path(root);self.threshold=threshold;self.cap=cap;self.calls=0;self.tokens=0
        self.chains={};self.pending=set();self.lock=threading.Lock();self.stopped=False;self.started=monotonic()
    def remaining_seconds(self):return max(.001,5400-(monotonic()-self.started))
    def event(self,kind,data):
        try:save(self.root/'ledger'/f'{len(list((self.root/"ledger").glob("*.json"))) if (self.root/"ledger").exists() else 0:04d}-{kind}.json',data)
        except BaseException:self.stopped=True;raise
    def __call__(self,spec,r,n):
        with self.lock:
            key=f"{spec['case']}-{spec['variant']}"
            if self.stopped or self.calls>=self.cap or self.tokens>=self.threshold or self.remaining_seconds()<=.001:
                self.stopped=True;raise RuntimeError('usage_threshold_v2 global stop')
            require(r.model_id=='deepseek-flash' and r.max_output_tokens==8000,'Frozen Flash parameters')
            require(self.chains.get(key,0)<12,'Chain12 cap')
            index=self.calls+1
            self.event('send',dict(id=index,chain=key,usage_before=self.tokens,inflight_before=len(self.pending),
                message_chars=sum(len(m.content) for m in r.messages),message_utf8_bytes=sum(len(m.content.encode()) for m in r.messages),
                token_estimate='not exact; bytes recorded for warning only, no hidden-template guarantee',max_output_tokens=8000))
            self.calls=index;self.chains[key]=self.chains.get(key,0)+1;self.pending.add(index);OWNER.set(index)
    def received(self,index,response):
        with self.lock:
            save(self.root/'provider-responses'/f'{index:04d}.json',wire(response))
            u=response.usage
            valid=u is not None and all(type(n) is int and n>=0 for n in (u.input_tokens,u.output_tokens,u.total_tokens)) and u.input_tokens+u.output_tokens==u.total_tokens
            if valid and (u.cache_hit_tokens is not None or u.cache_miss_tokens is not None):
                valid=all(type(n) is int and n>=0 for n in (u.cache_hit_tokens,u.cache_miss_tokens)) and u.cache_hit_tokens+u.cache_miss_tokens==u.input_tokens
            if not valid:
                self.stopped=True;self.event('unknown_usage',dict(id=index,pending=sorted(self.pending)));raise ModelConnectionError()
            self.tokens+=u.total_tokens;self.pending.remove(index)
            if self.tokens>=self.threshold:self.stopped=True
            self.event('usage',dict(id=index,usage=wire(u),cumulative=self.tokens,threshold_triggered=self.stopped,
                inflight_at_threshold=len(self.pending),overshoot=max(0,self.tokens-self.threshold)))

class Accounted:
    def __init__(self,delegate,gate):self.delegate=delegate;self.gate=gate
    @property
    def _active(self):return getattr(self.delegate,'_active',None)
    def close(self):self.delegate.close()
    async def complete(self,r):
        index=OWNER.get();require(index in self.gate.pending,'No boundary admission: refuse send')
        try:
            response=await self.delegate.complete(r)
            self.gate.received(index,response);return response
        except BaseException:
            with self.gate.lock:
                self.gate.stopped=True;self.gate.event('uncertain_or_failed',dict(id=index,pending=sorted(self.gate.pending)))
            raise

def material():
    m=json.loads((MATERIALS/'materials-v1.1.json').read_text(encoding='utf-8'))
    require(sha(m)=='346ba9d1c3e72a3ecdbee01825368a92d344b42be203786f683d26370dedadfc','Frozen material changed')
    return m

def inputs(m):
    generated={}
    for i,row in enumerate(m['cases']):
        req=restore(row['request'],TaskRequest);snapshot=restore(row['snapshot'],GenerationEvidenceSnapshot)
        generated[i]=NS(answer=req.existing_answer,evidence=req.provided_evidence,generation_output=NS(evidence_snapshot=snapshot,substantive_answer=True),
            model_records=(),duration_ms=0,retrieval_records=())
    return generated

async def batch(c,m,root,provider,*,gate=None):
    gate=gate or UsageGate(root);generated=inputs(m)
    def request(m,i,**kw):return replace(restore(m['cases'][i]['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
    def variant(cfg,v):
        return replace(cfg,audit_strategy='source_first_audit_v1',fact_review_contract='literal_v1',local_revision_interface='source_actions_v2') if v=='candidate' else cfg
    async def runner(h,req,budget,**kw):
        i=next(i for i,x in generated.items() if x.answer.answer_id==req.existing_answer.answer_id)
        fixed=restore(m['cases'][i]['extraction'],ClaimExtractionOutput);delegate=h.extractor
        class FirstFrozen:
            uses_model_adapter=True
            async def extract(self,answer):return await self.extract_for_task(answer,req)
            async def extract_for_task(self,answer,request):
                if answer.version==fixed.answer_version:
                    validate_extraction(fixed,answer);return fixed
                return await delegate.extract_for_task(answer,request) if hasattr(delegate,'extract_for_task') else await delegate.extract(answer)
        h.extractor=FirstFrozen()
        return await h.run(req,budget,indexed_reference_ids=tuple(e.evidence_id for e in req.provided_evidence),**kw)
    rows=[dict(id=f'S{i+1}-{v}',input=dict(line='B',case=i,variant=v)) for i in range(4)
        for v in (('baseline','candidate') if i%2==0 else ('candidate','baseline'))]
    def guard(spec,raw):
        if gate.stopped:return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='usage_threshold_v2 global stop; no new slots')
    return await shared.batch(c,m,root,lambda settings,**opts:Accounted(provider(settings,**opts),gate),
        rows=rows,request_builder=request,variant_config=variant,task_runner=runner,result_guard=guard,
        initial_generated=generated,fixed_audit_delivery=False,independent_audit_budget=True,send_guard=gate,
        budget_for=lambda spec,b:replace(b,max_model_calls=12,max_revision_rounds=1,max_transient_retries=0))

def sources():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for d in ('agents','backend','core','harness','rag','services','model_adapter','evaluation') for p in (ROOT/d).glob('*.py')}

async def run():
    require(not LOCAL.exists(),'Unique new attempt only; no resume')
    m=material()
    from harness.deepseek_trial import load_project_env
    load_project_env();c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.verification_schema,c.fact_review_contract,c.local_revision_interface,c.fact_review_execution,c.audit_strategy)==(13,'production','production','serial_v1','baseline'),'Original baseline required')
    c=replace(c,run_db=LOCAL/'batch/runs.sqlite3',nli_enabled=False,budget=replace(c.budget,max_model_calls=12,max_revision_rounds=1))
    for row in m['cases']:
        req=replace(restore(row['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
        validate_request(req,c.budget)
        validate_extraction(restore(row['extraction'],ClaimExtractionOutput),req.existing_answer)
        require(row['snapshot']['knowledge_version']==c.knowledge_version,'Frozen knowledge differs from configuration')
    before=sources();start=monotonic();factory=ComponentFactory(c);factory.preflight();seal_seconds=monotonic()-start
    freeze=dict(version=VERSION,start_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources=before,
        material_sha=sha(m),configuration=wire(c),order=m['order'],seal_seconds=seal_seconds,token_policy='usage_threshold_v2; inflight overshoot accepted')
    save(LOCAL/'freeze.json',freeze);save(LOCAL/'attempt.json',dict(unique=True,resume=False))
    from model_adapter.deepseek import create_adapter
    gate=UsageGate(LOCAL/'batch')
    try:
        summary=await batch(c,m,LOCAL/'batch',create_adapter,gate=gate)
        save(LOCAL/'totals.json',dict(requests=gate.calls,tokens=gate.tokens,pending=sorted(gate.pending),stopped=gate.stopped,overshoot=max(0,gate.tokens-1200000)))
        require(sources()==before,'Frozen source changed during batch')
        print(json.dumps(dict(executed=len(summary['control']),unexecuted=summary['unexecuted'],requests=gate.calls,tokens=gate.tokens)))
    finally:await factory.close()
if __name__=='__main__':asyncio.run(run())
