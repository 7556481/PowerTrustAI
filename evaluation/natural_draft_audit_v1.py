"""One fresh audit of eight archived natural C drafts; no generation/search."""
import asyncio
from contextlib import closing
from dataclasses import replace
import hashlib,json,os,sqlite3,subprocess
from time import monotonic
from types import SimpleNamespace

from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from core.models import TaskRequest
from core.validation import require
from services.evidence_scope import validate_snapshot
from agents.contracts import GenerationOutput
from evaluation.archive_replay import restore
from evaluation import retrieval_evidence_answer_check_v1 as previous
from evaluation import answer_review_net_benefit_v1 as shared

VERSION='natural-draft-audit-v1';BASE='1a92d03da49ae25f311e950373003d6ab32d09f5'
LOCAL=ROOT/'data/retrieval_local'/VERSION;PUBLIC=ROOT/'docs/evaluation'/VERSION
OLD=previous.LOCAL
load,save,sha,sources=previous.load,previous.save,previous.sha,previous.sources
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def recover():
    summary=load(OLD/'batch/summary.json');generated={};origins=[]
    with closing(sqlite3.connect((OLD/'batch/runs.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        for i in range(8):
            ident=f'N{i+1}-C';control=next(r for r in summary['control'] if r['case_id']==ident);rid=control['accepted']['run_id']
            raw=summary['outputs'][rid];path=OLD/'batch'/rid/'result.json';inp=load(OLD/'batch'/rid/'input.json')
            require(load(path)==raw and json.loads(db.execute('SELECT result FROM runs WHERE id=?',(rid,)).fetchone()[0])==raw,'Historical result/Store mismatch')
            req=restore(inp['request'],TaskRequest);gen=restore(raw['generation_output'],GenerationOutput)
            validate_snapshot(gen.evidence_snapshot,gen.answer)
            require(wire(gen.answer)==raw['answer'] and wire(gen.evidence_snapshot.evidence)==raw['evidence'],'Historical natural draft/snapshot mismatch')
            require(wire(gen.evidence_snapshot.evidence_bindings)==raw['evidence_bindings'],'Historical role/binding mismatch')
            require(gen.evidence_snapshot.question==req.question and gen.evidence_snapshot.user_context==req.user_context and gen.evidence_snapshot.engineering_context==req.engineering_context,'Historical question/context mismatch')
            generated[i]=SimpleNamespace(answer=gen.answer,evidence=gen.evidence_snapshot.evidence,generation_output=replace(gen,model_records=()),model_records=(),duration_ms=0,retrieval_records=())
            origins.append(dict(id=f'N{i+1}',old_run_id=rid,request=wire(req),answer_sha256=sha(raw['answer']),evidence_sha256=sha(raw['evidence']),
                bindings_sha256=sha(raw['evidence_bindings']),snapshot_sha256=sha(raw['generation_output']['evidence_snapshot']),
                knowledge_version=gen.evidence_snapshot.knowledge_version,old_generation_records=raw['model_records'],historical_cost_recounted=False,
                origin='archived_natural_generation_only; all initial extraction/fact/domain audits must be fresh',
                files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in (path,OLD/'batch'/rid/'input.json')]))
    return generated,origins


def prepare():
    require(not (LOCAL/'attempt.json').exists(),'No preparation changes after attempt')
    generated,origins=recover();m=load(OLD/'materials.json');results=load(previous.PUBLIC/'cases.json')
    references=[]
    for i,row in enumerate(results['cases']):
        references.append(dict(id=row['id'],question=row['question'],family=row['family'],required=row['required'],critical=row['critical'],
            initial_correct_slots=row['variants']['C']['complete_correct_required_slots'],initial_partial=row['variants']['C']['partial_coverage'],
            prior_source_first_judgment=row['source_first_judgment'],prior_critical_error=row['C_new_critical_error'],
            review_scope='Full original answer including citations/assumptions/missing_information; no expert gold',
            N6_ambiguity='Conservative planning-to-daily scope error; alternative unmarked-planning-supplement reading retained' if i==5 else None))
    material=dict(version=VERSION,N=m['N'],references=references,reference_sources=m['reference_sources'],origins=origins,
        criterion='N2 and N4 both fully corrected; no new critical errors/key required loss elsewhere; >=2 complete traceable improvements. N6 conservative/disputed interpretations separate.',
        supervision='Seen AI-assisted/user-supervised references; not expert gold or independent holdout')
    save(LOCAL/'materials.json',material)
    save(PUBLIC/'materials-reference.json',{k:v for k,v in material.items() if k not in ('reference_sources','origins')}|dict(
        reference_sources=load(previous.PUBLIC/'materials-reference.json')['reference_sources'],
        origins=[{k:v for k,v in row.items() if k not in ('request','old_generation_records')} for row in origins]))
    print('Recovered8 complete natural C drafts/Evidence/roles/knowledge/snapshots; no index/env/model access',flush=True)


class Factory(ComponentFactory):
    def create(self,rid,observer):return super().create(rid,observer,fixed_evidence_only=True)


class SendLimit:
    def __init__(self,root,clock=monotonic):self.root=root;self.clock=clock;self.start=None;self.used=0;self.chains={}
    def remaining_seconds(self):return 5400 if self.start is None else max(.001,5400-(self.clock()-self.start))
    def __call__(self,spec,r,n):
        now=self.clock()
        if self.start is None:self.start=now
        require(r.model_id=='deepseek-flash' and r.max_output_tokens==8000,'Frozen model parameters')
        require(not r.prompt_version.startswith(('evidence-bound-generation','generation-cross-language-query')),'No generation/conversion')
        key=str(spec['case']);require(self.used<192 and self.chains.get(key,0)<24 and now-self.start<5400,'Global/chain send cap')
        self.used+=1;self.chains[key]=self.chains.get(key,0)+1
        save(self.root/'send-ledger'/f'{self.used:04d}.json',dict(used=self.used,chains=self.chains,elapsed=now-self.start))


def request(m,i,**kw):return replace(restore(m['origins'][i]['request'],TaskRequest),task_id=VERSION+f'-N{i+1}')


async def batch(c,m,generated,root,provider,*,limit=None):
    limit=limit or SendLimit(root)
    async def runner(h,req,budget,**kw):
        i=next(i for i,row in enumerate(m['origins']) if row['request']['question']==req.question);origin=m['origins'][i]
        require(req.existing_answer==generated[i].answer and req.provided_evidence==generated[i].evidence,'Fixed natural input differs')
        require(sha(kw['generation_snapshot'])==origin['snapshot_sha256'],'Real generation snapshot differs')
        require(h.retriever is None and not h.subject_supplement and kw['knowledge_version']==origin['knowledge_version'],'Unexpected retrieval/snapshot scope')
        save(root/kw['run_id']/'audit-origin.json',dict(origin=origin,new_run_id=kw['run_id'],initial_audits='all_fresh',
            archived_generation_bindings_preserved_in_snapshot=True,current_provided_evidence_roles='normal fixed-evidence Harness user_reference; distinct from archived generation core/adjacent roles',
            no_historical_audit_replay=True,historical_cost_recounted=False))
        return await h.run(req,budget,**kw)
    def guard(spec,raw):
        if any(x['code'] in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CANCELLED','CANCELLED') for x in raw.get('execution_issues',[])):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Shared timeout/unknown acceptance; stop new sends')
        if raw.get('generation_output') or raw.get('retrieval_records'):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Unexpected generation/retrieval')
    rows=[dict(id=f'N{i+1}',input=dict(id=f'N{i+1}',line='B',case=i,variant='candidate')) for i in range(8)]
    return await shared.batch(c,m,root,provider,factory_type=Factory,rows=rows,request_builder=request,variant_config=lambda cfg,v:cfg,
        initial_generated=generated,task_runner=runner,result_guard=guard,send_guard=limit,independent_audit_budget=True,
        budget_for=lambda spec,b:replace(b,max_model_calls=24,max_duration_seconds=min(800,limit.remaining_seconds()),max_revision_rounds=1,max_transient_retries=0),
        local_issue_codes=('MODEL_CALL_BUDGET_EXHAUSTED',))


async def run():
    require(not (LOCAL/'attempt.json').exists(),'Unique batch only; no resume')
    require(not subprocess.check_output(['git','status','--porcelain','--','agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools'],cwd=ROOT,text=True).strip(),'Commit source before freeze')
    require(not subprocess.check_output(['git','diff',BASE,'--','agents','backend','core','harness','model_adapter','rag','services','tools'],cwd=ROOT),'Business baseline changed')
    generated,origins=recover();m=load(LOCAL/'materials.json');require(origins==m['origins'],'Prepared origin changed')
    require(m['N']==load(OLD/'materials.json')['N'],'Original question/reference changed')
    require(m['reference_sources']==load(OLD/'materials.json')['reference_sources'],'Original source reference changed')
    c=ServiceConfig.from_environment();require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    old_config=load(OLD/'freeze.json')['configuration']
    for key in ('profile','decision_policy','execution_path','verification_schema','retrieval_mode','retrieval_execution_profile',
        'fact_strategy','fact_review_contract','local_revision_interface','revision_answer_delivery','review_result_transport',
        'fact_internal_flow','domain_internal_flow','extraction_message_profile','review_message_profile','knowledge_version'):
        require(getattr(c,key)==old_config[key],'Production baseline differs: '+key)
    c=replace(c,fact_review_contract='literal_v1',local_revision_interface='source_actions_v2',run_db=LOCAL/'batch/runs.sqlite3',
        budget=replace(c.budget,max_model_calls=24,max_duration_seconds=800,max_revision_rounds=1,max_transient_retries=0))
    f=dict(version=VERSION,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),baseline=BASE,
        sources=sources(),configuration=wire(c),manifest=Factory(c).manifest(c.knowledge_version,fixed_evidence_only=True),materials_sha256=sha(m),origins_sha256=sha(origins),
        order=[f'N{i+1}' for i in range(8)],limits=dict(chains=8,per_chain=24,total=192,chain_seconds=800,total_seconds=5400,revision_attempts=1,max_output=8000),
        initial_audits='all new actual model requests, no historical review replay',historical_generation_and_conversion_recounted=False,
        stop='Local final format/semantic/no-change failure continues; shared code/config/input/storage/auth/balance/rate/service/network/timeout/unknown acceptance stops. No repair/resume/second batch.')
    save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f);save(LOCAL/'attempt.json',dict(freeze_sha256=sha(f),resume_allowed=False))
    from model_adapter.deepseek import create_adapter
    summary=await batch(c,m,generated,LOCAL/'batch',create_adapter)
    require(sources()==f['sources'],'Frozen source changed')
    print(json.dumps(dict(executed=len(summary['control']),unexecuted=summary['unexecuted'],requests=len(summary['send_log']))),flush=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('prepare offline, run once')
