"""One 20-slot development batch; real initial audits, no historical review replay."""
import asyncio,json,os,sqlite3,subprocess,hashlib
from pathlib import Path
from dataclasses import replace
from contextlib import closing
from types import SimpleNamespace
from time import monotonic
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from core.models import TaskRequest,TaskMode,EngineeringContext
from core.validation import require
from agents.contracts import GenerationOutput
from evaluation.archive_replay import restore
from evaluation import answer_review_net_benefit_v1 as shared
from evaluation.natural_answer_benefit_v3_materials import N,RULES

VERSION='natural-answer-benefit-v3';BASE='73c25ca0af9ba9fd5143527c6341aae52170fffd'
LOCAL=ROOT/'data/retrieval_local'/VERSION;PUBLIC=ROOT/'docs/evaluation'/VERSION
OLD=ROOT/'data/retrieval_local/literal-review-stage1-v1'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):shared.write(p,wire(v))
def digest(p):
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()

def history():
    s=load(OLD/'batch/summary.json');out={};provenance=[]
    with closing(sqlite3.connect('file:'+(OLD/'batch/runs.sqlite3').as_posix()+'?mode=ro',uri=True)) as db:
        for i in range(4):
            g=next(r for r in s['control'] if r['case_id']==f'G{i+1}')['accepted']['run_id']
            b=next(r for r in s['control'] if r['case_id']==f'B{i+1}-literal_v1')['accepted']['run_id']
            raw=s['outputs'][g];initial=load(OLD/'batch'/b/'input.json')
            for rid in (g,b):require(json.loads(db.execute('SELECT result FROM runs WHERE id=?',(rid,)).fetchone()[0])==s['outputs'][rid],'Historical Store mismatch')
            require(initial['request']['existing_answer']==raw['answer'] and initial['request']['provided_evidence']==raw['evidence'],'Historical initial answer/Evidence mismatch')
            require(initial['generation_snapshot']==raw['generation_output']['evidence_snapshot'],'Historical snapshot mismatch')
            req=restore(initial['request'],TaskRequest);gen=restore(raw['generation_output'],GenerationOutput)
            require(gen.evidence_snapshot is not None and gen.answer==req.existing_answer,'Historical generation identity missing')
            out[8+i]=SimpleNamespace(answer=req.existing_answer,evidence=req.provided_evidence,generation_output=replace(gen,model_records=()),model_records=(),duration_ms=0,retrieval_records=())
            provenance.append(dict(id=f'H{i+1}',old_generation_run=g,old_literal_audit_run=b,initial_input_sha256=shared.sha(initial),answer_sha256=shared.sha(raw['answer']),evidence_sha256=shared.sha(raw['evidence']),snapshot_sha256=shared.sha(initial['generation_snapshot']),knowledge_version=gen.evidence_snapshot.knowledge_version,
                old_generation_background_records=raw['model_records'],historical_cost_recounted=False,no_historical_audit_replay=True,request=wire(req),files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in (OLD/'batch'/b/'input.json',OLD/'batch'/g/'result.json')]))
    return out,provenance

def materials():
    m=load(OLD/'materials.json');_,h=history()
    for i,row in enumerate(h):row['frozen_reference']=m['B'][i]
    h[1]['source_boundary_review']='Voluntary/non-Chinese-standard metadata is separate from technical body and original citation support; coordination important does not establish mandatory duty.'
    h[2]['source_boundary_review']='Source when is not only. N-1 immediate/no-intervention conditions are not all N-2 requirements; source silence is not engineering nonexistence.'
    return dict(version=VERSION,N=N,H=h,rules=RULES,reference_sources={k:m['sources'][k] for k in ('coordination','contingencies','resources','line_model')})

def public_materials(m):
    return dict(version=VERSION,N=m['N'],H=[{k:v for k,v in h.items() if k not in ('request','old_generation_background_records')}|dict(question=h['request']['question']) for h in m['H']],rules=m['rules'],reference_sources={k:{a:e[a] for a in ('evidence_id','source_id','source_version','locator')}|dict(text_sha256=hashlib.sha256(e['text'].encode()).hexdigest(),applicability=e['applicability']) for k,e in m['reference_sources'].items()})

def order(m):
    rows=[]
    for i in range(8):
        rows.extend([dict(id=f'N{i+1}-G',input=dict(line='G',case=i,variant='generation',group='N',id=f'N{i+1}')),dict(id=f'N{i+1}-audit',input=dict(line='B',case=i,variant='candidate',group='N',id=f'N{i+1}'))])
    rows.extend(dict(id=f'H{i+1}-audit',input=dict(line='B',case=8+i,variant='candidate',group='H',id=f'H{i+1}',historical_origin={k:v for k,v in h.items() if k!='request'})) for i,h in enumerate(m['H']))
    return rows

def request(m,i,*,draft=False):
    if i>=8:return replace(restore(m['H'][i-8]['request'],TaskRequest),task_id=f'benefit-v3-H{i-7}')
    return TaskRequest(f'benefit-v3-N{i+1}',TaskMode.QUESTION_ANSWER,'voltage_stability_reactive_support',m['N'][i]['question'],'按所给资料作概念性解释。',engineering_context=EngineeringContext(goal='conceptual'))

def candidate(c,v):return c if v=='generation' else replace(c,fact_review_contract='literal_v1',local_revision_interface='source_actions_v2')
def budget_for(spec,b):return replace(b,max_model_calls=2) if spec['line']=='G' else b
class Factory(ComponentFactory):
    def create(self,rid,observer):return super().create(rid,observer,fixed_evidence_only=self.config.fact_review_contract=='literal_v1')

class SendLimit:
    def __init__(self,root,*,clock=monotonic,cap=304,seconds=7200):self.root=root;self.clock=clock;self.cap=cap;self.seconds=seconds;self.start=None;self.used=0;self.chains={}
    def remaining_seconds(self):return max(.001,self.seconds-(self.clock()-self.start))
    def __call__(self,spec,r,n):
        now=self.clock()
        if self.start is None:self.start=now
        require(r.model_id=='deepseek-flash' and r.max_output_tokens==8000,'Frozen model parameters mismatch')
        key=spec['id']+'-'+spec['line'];limit=2 if spec['line']=='G' else 24
        if self.used>=self.cap or now-self.start>=self.seconds or self.chains.get(key,0)>=limit:
            save(self.root/'global-stop.json',dict(reason='global_or_slot_send_boundary',used=self.used,chains=self.chains,elapsed=now-self.start));raise RuntimeError('Frozen send boundary; no recovery')
        self.used+=1;self.chains[key]=self.chains.get(key,0)+1
        save(self.root/'send-ledger'/f'{self.used:04d}.json',dict(used=self.used,chains=self.chains,elapsed=now-self.start))

class Gate:
    def __call__(self,spec,raw):
        if any(x.get('code') in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CANCELLED','CANCELLED') for x in raw.get('execution_issues',[])):
            return dict(component='harness',code='SERVICE_EXECUTION_FAILED',message='Timeout/unknown acceptance stops the entire batch')

def runner(root):
    async def run(harness,request,budget,**kw):
        if not kw['generation_only']:
            snapshot=kw['generation_snapshot'];require(snapshot is not None,'Actual generation snapshot missing')
            require(kw['knowledge_version']==snapshot.knowledge_version,'Snapshot knowledge identity mismatch')
            require(set(e.evidence_id for e in snapshot.evidence)<=set(e.evidence_id for e in request.provided_evidence),'Actual delivery differs')
            require(harness.retriever is None and not harness.subject_supplement,'Audit must use fixed actual Evidence')
            save(root/kw['run_id']/'audit-origin.json',dict(origin='real_new_initial_audit',request_sha256=shared.sha(wire(request)),evidence_sha256=shared.sha(wire(request.provided_evidence)),snapshot_sha256=shared.sha(wire(snapshot)),knowledge_version=snapshot.knowledge_version,model_budget=budget.max_model_calls,seconds=budget.max_duration_seconds))
        return await harness.run(request,budget,**kw)
    return run

async def batch(c,m,root,provider,*,limit=None):
    h,_=history()
    return await shared.batch(c,m,root,provider,factory_type=Factory,rows=order(m),request_builder=request,variant_config=candidate,initial_generated=h,task_runner=runner(root),result_guard=Gate(),send_guard=limit or SendLimit(root),budget_for=budget_for,local_issue_codes=('MODEL_CALL_BUDGET_EXHAUSTED',),independent_audit_budget=True)

def sources():return [dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in sorted((ROOT/folder).glob('*.py'))]
def require_sources():
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--','agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools'],cwd=ROOT,text=True).strip(),'Commit sources before freezing')
    require(not subprocess.check_output(['git','diff',BASE,'--','agents','backend','core','harness','model_adapter','rag','services','tools'],cwd=ROOT),'Business baseline changed')

async def run():
    require(not LOCAL.exists(),'Unique new batch only; no resume or replacement directory')
    require_sources()
    # The sole authorized real-run entry. Offline preparation never calls this loader.
    c=ServiceConfig.from_environment()
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require((c.profile,c.verification_schema,c.fact_review_contract,c.local_revision_interface,c.execution_path,c.review_result_transport,c.fact_internal_flow,c.domain_internal_flow,c.revision_answer_delivery,c.extraction_message_profile,c.review_message_profile)==('real',13,'production','production','langgraph_v1','json','production','production','production','production','lossless_v1'),'Production baseline mismatch')
    c=replace(c,run_db=LOCAL/'batch/runs.sqlite3',budget=replace(c.budget,max_model_calls=24,max_duration_seconds=800,max_revision_rounds=1,max_transient_retries=0))
    factory=ComponentFactory(c)
    try:
        k=factory.preflight();m=materials();p=public_materials(m)
        require(load(PUBLIC/'materials-reference.json')==p,'Prediction-before reference changed')
        f=dict(version=VERSION,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),business_baseline=BASE,sources=sources(),configuration=wire(c),generation_manifest=factory.manifest(k),candidate_manifest=ComponentFactory(candidate(c,'candidate')).manifest(k,fixed_evidence_only=True),materials_sha256=shared.sha(m),public_materials_sha256=shared.sha(p),order=order(m),budget=dict(generation=2,audit=24,total=304,slot_seconds=800,batch_seconds=7200,output_tokens=8000,business_revisions=1),model='deepseek-flash',scope='8 normal RAG generations each immediately followed by a fresh candidate audit of the exact actual answer/Evidence/snapshot; then 4 archived natural drafts with fresh audits, no review replay. Independent generation/audit quotas, costs separated.',stop='Local final model error/no change/semantic error/clear slot quota continues; shared code/config/source/storage/auth/network/service/timeout/unknown failure stops new sends. No resume/retry batch/second batch or frozen semantic changes.',reference_origin=RULES['origin'])
        save(LOCAL/'materials.json',m);save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
        require(sources()==f['sources'],'Frozen source changed')
        save(LOCAL/'attempt.json',dict(freeze_sha256=shared.sha(f),resume_allowed=False))
        from model_adapter.deepseek import create_adapter
        s=await batch(c,m,LOCAL/'batch',create_adapter)
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],new_requests=len(s['send_log']))),flush=True)
        return s
    finally:await factory.close()

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('run once; offline materials() performs no project requests')
