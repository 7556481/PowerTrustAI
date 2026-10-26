"""One frozen staged evaluation, using existing retrieval, Harness and run_fixed.

Only `run` loads project environment. An offline source-first gate file supplies
the predeclared evidence judgment while the same process retains index resources.
"""
import asyncio
from dataclasses import replace, asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

from backend.config import ROOT, ServiceConfig
from backend.assembly import ComponentFactory, Bundle
from backend.serialization import wire
from backend.store import RunStore
from core.validation import require
from core.models import TaskRequest, TaskMode, EngineeringContext
from harness.contracts import RetrievalSettings
from harness.retrieval import RetrievalSession
from rag.storage import KnowledgeStore, canonical
from rag.corpus_index import seal
from rag.contracts import RetrievalRequest, RetrievalPurpose, ContextOptions
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.chinese_first import Catalog, ChineseFirstRetriever, PROFILE
from services.generation_query import GenerationQueryConverter
from model_adapter.contracts import ModelSettings, ModelOutputError
from model_adapter.runtime import ModelBudget, model_scope, model_invocation_scope
from evaluation.batch_control import run_fixed
from evaluation.archive_replay import restore
from evaluation.natural_answer_benefit_v3_materials import N, RULES

VERSION='chinese-first-cross-language-retrieval-v1'
LOCAL=ROOT/'data/retrieval_local'/VERSION
PUBLIC=ROOT/'docs/evaluation'/VERSION
BASE='0eeda99cafeed289acb51b8cb8e275e4b9004935'
OLD=ROOT/'data/retrieval_local/natural-answer-benefit-v3'
EXTRA=[
 dict(id='E1',family='unspecified',question='无功补偿与电压控制有什么关系？请作概念性说明。',required=['没有明确来源，B/C沿原中文路径且不转换，不强定NERC']),
 dict(id='E2',family='ambiguous',question='依据清华大学出版社《无功功率：教材原文小节》，解释无功功率的含义；这份资料对应哪一份样章？',required=['同名标题有两份选段；保留095824与096768来源，不擅选，不转换']),
 dict(id='E3',family='absent',question='请依据《并不存在的跨区域无功资源导则2026-ZZZ》说明动态无功资源的运行方式。',required=['明确未找到所指标题，不用行业或其他资料替代，不转换']),
 dict(id='E4',family='other_institution',question='请依据国家发展和改革委员会《电能质量管理办法（暂行）》说明该资料的适用范围，不要用国外无功规划指南替代。',required=['仅所指国家发展和改革委员会真实文献，中文不转换，不误归NERC'])]

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(v):return hashlib.sha256(canonical(wire(v)).encode()).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(wire(v),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sources():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in sorted((ROOT/folder).glob('*.py'))}
def request(item):
    return TaskRequest(VERSION+'-'+item['id'],TaskMode.QUESTION_ANSWER,'voltage_stability_reactive_support',item['question'],
        '按所给资料作概念性解释。',engineering_context=EngineeringContext(goal='conceptual'))


def prepare():
    require(not (LOCAL/'attempt.json').exists(),'No changes after attempt')
    previous=load(OLD/'freeze.json');cfg=previous['configuration']
    sidecar=load(Path(cfg['index_db']+'.manifest.json'))
    # Small immutable base membership/metadata read only; serving later uses the
    # original full seal before any final query, no trusted sidecar shortcut.
    with KnowledgeStore(cfg['index_db'],readonly=True) as store:
        catalog=Catalog(store.rows(sidecar['base_knowledge_version']))
    original=load(OLD/'materials.json')
    m=dict(version=VERSION,N=N,extra=EXTRA,rules=RULES,reference_sources=original['reference_sources'],catalog_identity=catalog.identity)
    save(LOCAL/'materials.json',m);save(LOCAL/'catalog.json',catalog.documents)
    save(PUBLIC/'materials-reference.json',dict(version=VERSION,N=N,extra=EXTRA,rules=RULES,catalog_identity=catalog.identity,
        reference_sources={k:{x:v[x] for x in ('source_id','source_version','locator')}|dict(text_sha256=hashlib.sha256(v['text'].encode()).hexdigest()) for k,v in original['reference_sources'].items()}))
    save(PUBLIC/'catalog.json',catalog.documents)
    paths=[p[0] for p in sidecar['progress']]
    languages=dict(manifest_revision=sidecar['revision'],published_records=sidecar['records'],published_chunks=sidecar['chunks'],
        valid_shards=len(paths),valid_path_language_counts={key:sum(p.startswith(key+'/') for p in paths) for key in ('chinese','english')},
        processed_input_rows_by_path={key:sum(p[1] for p in sidecar['progress'] if p[0].startswith(key+'/')) for key in ('chinese','english')},
        excluded_shards=sidecar['excluded_shards'],has_english=sidecar['has_english'],
        catalog_documents=len(catalog.documents),catalog_fragments=len(catalog.rows),
        catalog_script_counts={key:sum(d['language']==key for d in catalog.documents) for key in ('chinese','english','mixed','unknown')},
        english_body_documents=sum(d['english_body_available'] for d in catalog.documents),
        note='Manifest shard paths are import partitions, not measured publication/body language proportions. Mixed script includes formulas/acronyms; publisher language/authority not certified. No whole-corpus sample or scan.',
        english_trigger='Existing english_corpus gate: a native body fragment with >=100 Latin letters and zero CJK; no assumption from publisher/title alone.')
    save(PUBLIC/'language-audit.json',languages)
    print(json.dumps(dict(catalog=catalog.identity,fragments=len(catalog.rows),languages=languages['valid_path_language_counts'])))


class SendLedger:
    def __init__(self,root,clock=perf_counter):
        self.root=root;self.clock=clock;self.start=None;self.rows=[];self.slots={};self.fatal=False
    def remaining_seconds(self):return 7200 if self.start is None else max(.001,7200-(self.clock()-self.start))
    def claim(self,r):
        require(not self.fatal,'Shared stop')
        phase='conversion' if r.prompt_version=='generation-cross-language-query-v1' else 'generation'
        require(r.model_id=='deepseek-flash' and r.max_output_tokens==(1000 if phase=='conversion' else 8000),'Frozen model parameters')
        question=None;task_id=None
        for m in r.messages:
            if m.role=='user':
                try:d=json.loads(m.content)
                except ValueError:continue
                if isinstance(d,dict):question=d.get('question',question);task_id=d.get('answer_id',task_id)
        slot=(phase,question if phase=='conversion' else self.current_generation_slot)
        if self.start is None:self.start=self.clock()
        require(len(self.rows)<44 and self.remaining_seconds()>.001,'Global budget exhausted')
        require(self.slots.get(slot,0)<(1 if phase=='conversion' else 2),'Slot request cap')
        require(sum(x['phase']==phase for x in self.rows)<(12 if phase=='conversion' else 32),'Phase cap')
        require(phase!='conversion' or not r.correction,'No query correction')
        self.slots[slot]=self.slots.get(slot,0)+1
        row=dict(sequence=len(self.rows)+1,phase=phase,slot=slot,question=question,correction=r.correction,
            prompt_version=r.prompt_version,model_id=r.model_id,max_output_tokens=r.max_output_tokens,
            elapsed_before_send=self.clock()-self.start,messages_sha256=sha(r.messages))
        save(self.root/'messages'/f"{row['sequence']:04d}.json",dict(row,messages=wire(r.messages)))
        self.rows.append(row);save(self.root/'send-ledger.json',self.rows)
        return row
    # shared.batch supplies its own Guard and requires this compatible boundary;
    # the adapter below is the one global pre-send debit, not a second quota.
    def __call__(self,spec,r,n):
        require(not self.fatal,'Shared stop')
        self.current_generation_slot=(spec['case'],spec['variant'])


class LoggedAdapter:
    def __init__(self,delegate,ledger):self.delegate=delegate;self.ledger=ledger
    @property
    def _active(self):return getattr(self.delegate,'_active',None)
    def close(self):self.delegate.close()
    def validate_request(self,r):return self.delegate.validate_request(r)
    async def complete(self,r):
        self.validate_request(r)
        try:row=self.ledger.claim(r)
        except Exception:self.ledger.fatal=True;raise
        start=perf_counter()
        try:
            response=await asyncio.wait_for(self.delegate.complete(r),self.ledger.remaining_seconds())
            save(self.ledger.root/'responses'/f"{row['sequence']:04d}.json",response)
            row.update(status='response_saved',seconds=perf_counter()-start,usage=wire(response.usage),returned_model=response.model_id,
                response_sha256=hashlib.sha256(response.text.encode()).hexdigest())
            save(self.ledger.root/'send-ledger.json',self.ledger.rows)
            return response
        except BaseException as exc:
            self.ledger.fatal=not isinstance(exc,ModelOutputError)
            row.update(status='local_model_output_error' if isinstance(exc,ModelOutputError) else 'shared_failure_or_acceptance_unknown',exception_type=type(exc).__name__,code=getattr(exc,'code',None),seconds=perf_counter()-start)
            save(self.ledger.root/'send-ledger.json',self.ledger.rows)
            raise


class ReplayRetriever:
    execution_profile='fixed-retrieval-output-replay-v1'
    cache_identity=('fixed-retrieval-output-replay-v1',)
    def __init__(self,variant,results,validator):self.variant=variant;self.results=results;self.validator=validator
    async def retrieve(self,req):
        original,result=self.results[(self.variant,req.query)]
        require(req==original,'Frozen replay request changed');return result
    async def validate_result(self,req,result):
        require(await self.retrieve(req)==result,'Frozen replay result changed')
        items=result.evidence+(() if result.context is None else tuple(x.evidence for x in result.context.items))
        await self.validator.validate_evidence(items,req.knowledge_version)


async def answers(c,m,results,baseline,provider,ledger):
    from evaluation import answer_review_net_benefit_v1 as shared
    class Factory(ComponentFactory):
        def create(self,rid,observer):
            b=super().create(rid,observer,fixed_evidence_only=True)
            variant='C' if self.config.retrieval_execution_profile==PROFILE else 'A'
            b.harness.retriever=ReplayRetriever(variant,results,baseline)
            b.harness.subject_supplement=False;b.harness.generation_query_converter=None
            return b
    rows=[]
    for i in range(8):
        for variant in (('A','C') if i%2==0 else ('C','A')):
            rows.append(dict(id=N[i]['id']+'-'+variant,input=dict(line='G',case=i,variant=variant)))
    result=await shared.batch(c,m,LOCAL/'batch/generation',provider,factory_type=Factory,rows=rows,
        request_builder=lambda mat,i,**kw:request(mat['N'][i]),
        variant_config=lambda cfg,v:replace(cfg,retrieval_execution_profile=PROFILE if v=='C' else c.retrieval_execution_profile),
        send_guard=ledger,budget_for=lambda spec,b:replace(b,max_model_calls=2,max_duration_seconds=min(800,ledger.remaining_seconds()),max_transient_retries=0))
    if ledger.fatal:return result
    require(not any(r.get('stop') for r in result['control']),'Generation shared stop')
    return result


async def run():
    require(not (LOCAL/'attempt.json').exists(),'Unique attempt only; no resume')
    require(not subprocess.check_output(['git','status','--porcelain','--','agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools'],cwd=ROOT,text=True).strip(),'Commit code before freeze')
    m=load(LOCAL/'materials.json');prepared_catalog=load(LOCAL/'catalog.json')
    c=ServiceConfig.from_environment()  # only real entry loads the existing root .env
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    require(c.retrieval_execution_profile=='topic_v4_subject_v1' and c.verification_schema==13 and c.retrieval_mode=='bm25','Baseline differs')
    old_freeze=load(OLD/'freeze.json')
    for key in ('profile','decision_policy','execution_path','fact_review_contract','local_revision_interface',
        'revision_answer_delivery','review_result_transport','fact_internal_flow','domain_internal_flow',
        'extraction_message_profile','review_message_profile','knowledge_version','fact_strategy'):
        require(getattr(c,key)==old_freeze['configuration'][key],'Production baseline field differs: '+key)
    require(ComponentFactory(c).manifest(c.knowledge_version,fixed_evidence_only=True)['prompts']['generation']==old_freeze['generation_manifest']['prompts']['generation'],'Generation prompt differs')
    c=replace(c,run_db=LOCAL/'batch/generation/runs.sqlite3',budget=replace(c.budget,max_duration_seconds=800,step_timeout_seconds=120,max_transient_retries=0))
    ledger=SendLedger(LOCAL/'batch');baseline=AsyncSQLiteBM25Retriever(c.index_db,execution_profile=c.retrieval_execution_profile)
    from model_adapter.deepseek import create_adapter
    provider=lambda settings,**kw:LoggedAdapter(create_adapter(settings,**kw),ledger)
    query_model=provider(ModelSettings('deepseek-flash',90,1000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY'))
    converter=GenerationQueryConverter(query_model,ModelSettings('deepseek-flash',90,1000,96000),LOCAL/'batch/query-diagnostics')
    b=ChineseFirstRetriever(c.index_db,c.knowledge_version,bilingual=False)
    candidate=ChineseFirstRetriever(c.index_db,c.knowledge_version,converter)
    store=RunStore(LOCAL/'batch/retrieval.sqlite3');outputs={};frozen_results={};f=None
    try:
        start=perf_counter()
        with KnowledgeStore(c.index_db,readonly=True) as knowledge:identity=seal(knowledge,c.knowledge_version)
        startup=perf_counter()-start
        cat=await b.prepare();candidate.catalog=cat
        require(cat.documents==prepared_catalog and cat.identity==m['catalog_identity'],'Prepared catalog changed')
        f=dict(version=VERSION,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),baseline=BASE,
            sources=sources(),configuration=wire(c),catalog_identity=cat.identity,materials_sha256=sha(m),
            manifest=ComponentFactory(replace(c,retrieval_execution_profile=PROFILE)).manifest(c.knowledge_version,fixed_evidence_only=True),
            order=[item['id']+'-'+v for item in N+EXTRA for v in ('A','B','C')],
            answer_order=[item['id']+'-'+v for i,item in enumerate(N) for v in (('A','C') if i%2==0 else ('C','A'))],
            limits=dict(query_calls=12,query_output=1000,query_corrections=0,generation_calls=32,generation_output=8000,total_calls=44,slot_seconds=800,batch_seconds=7200,retrieval_seconds=120),
            seal_seconds=startup,knowledge_identity={k:identity[k] for k in ('base_knowledge_version','query_version','revision')},
            gate='C>A >=4 N in >=3 families, no key A loss, E1-E4 no new attribution/version selection, no N C execution failure; source-first semantic assessment, C>B separately',
            stop='Shared code/config/identity/storage/auth/balance/network/rate/service/timeout/acceptance-unknown stops; local invalid model output continues; no resume/second batch/changes after freeze')
        save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
        save(LOCAL/'attempt.json',dict(freeze_sha256=sha(f),no_resume=True))
        async def submit(spec):
            rid=uuid4().hex;store.create(rid,spec,f);return dict(run_id=rid,spec=spec)
        async def collect(accepted):
            spec=accepted['spec'];rid=accepted['run_id'];item=next(x for x in N+EXTRA if x['id']==spec['case']);v=spec['variant']
            r={'A':baseline,'B':b,'C':candidate}[v];req=request(item)
            budget=replace(c.budget,max_model_calls=1,max_duration_seconds=min(800,ledger.remaining_seconds()))
            model_budget=ModelBudget(1,perf_counter()+min(800,ledger.remaining_seconds()))
            session=RetrievalSession(r,c.knowledge_version,RetrievalSettings(),budget,perf_counter()+min(800,ledger.remaining_seconds()),())
            store.mark(rid,'running');start=perf_counter()
            with model_scope(model_budget),model_invocation_scope(rid,'query_conversion',None):
                delivery=await session.retrieve(RetrievalPurpose.GENERATION,req,None,())
            rr=RetrievalRequest(req.question,req.scenario_id,RetrievalPurpose.GENERATION,c.knowledge_version,3,ContextOptions())
            # Use one deterministic validation replay with the same saved query;
            # no paid conversion and no second semantic retrieval attempt.
            retrieval_result=None
            if not delivery.issue:
                if v=='A':retrieval_result=r._corpus_certificate[1]
                else:
                    retrieval_result=r.last_results[rr]
                require(tuple(e.evidence_id for e in retrieval_result.evidence)==delivery.record.core_evidence_ids,'Snapshot/result core mismatch')
                frozen_results[(v,item['question'])]=(rr,retrieval_result)
            raw=dict(case=item['id'],variant=v,delivery=wire(delivery),records=wire(model_budget.records),
                plan=None if v=='A' else wire(r.plans.get(rr)),seconds=perf_counter()-start,
                execution_issues=[] if delivery.issue is None else [wire(delivery.issue)])
            expected_missing=v!='A' and r.catalog.resolve(req.question).status in ('source_not_found','source_conflict')
            if ledger.fatal or delivery.issue and not expected_missing and not any(x.error_code=='MODEL_OUTPUT_ERROR' or x.output_status=='invalid_structure' for x in model_budget.records):
                raw['execution_issues'].append(dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Shared or unknown retrieval failure; stop'))
            outputs[item['id']+'-'+v]=raw;save(LOCAL/'batch/retrieval'/f"{item['id']}-{v}.json",raw)
            store.mark(rid,'finished',result=raw);require(store.get(rid)['result']==raw,'Store readback mismatch')
            print(item['id']+'-'+v+': '+delivery.record.outcome+', calls='+str(len(model_budget.records)),flush=True)
            return raw
        rows=[dict(id=item['id']+'-'+v,input=dict(case=item['id'],variant=v)) for item in N+EXTRA for v in ('A','B','C')]
        control=await run_fixed(rows,submit=submit,collect=collect,persist=lambda ident,kind,value:save(LOCAL/'batch/control'/f'{ident}-{kind}.json',value))
        save(LOCAL/'batch/retrieval-summary.json',dict(control=control,outputs=outputs,planned=rows))
        stopped=ledger.fatal or any(x.get('stop') for x in control)
        if stopped:
            save(LOCAL/'batch/final-status.json',dict(status='shared_stop',sent=len(ledger.rows),no_generation=True));return
        save(LOCAL/'batch/awaiting-evidence-gate.json',dict(freeze_sha256=sha(f),cases=len(outputs)))
        print('AWAITING_FROZEN_SOURCE_FIRST_GATE',flush=True)
        while not (LOCAL/'evidence-gate.json').exists():
            require(ledger.remaining_seconds()>1,'Global time exhausted awaiting gate')
            await asyncio.sleep(.5)
        gate=load(LOCAL/'evidence-gate.json')
        require(sources()==f['sources'] and sha(load(LOCAL/'materials.json'))==f['materials_sha256'],'Frozen identity changed')
        require(gate['freeze_sha256']==sha(f),'Gate identity mismatch')
        save(PUBLIC/'evidence-gate.json',gate)
        if not gate['passed']:
            save(LOCAL/'batch/final-status.json',dict(status='evidence_gate_not_met',sent=len(ledger.rows),no_generation=True));return
        improved=[row for row in gate['N'] if row['C_over_A']]
        require(len(improved)>=4 and len({row['family'] for row in improved})>=3,'Gate numerical threshold')
        require(not any(row['key_A_loss'] for row in gate['N']) and all(row['C_execution_complete'] for row in gate['N']) and all(row['passed'] for row in gate['extra']),'Gate safety/complete condition')
        answer_summary=await answers(c,m,frozen_results,baseline,provider,ledger)
        save(LOCAL/'batch/final-status.json',dict(status='shared_stop' if ledger.fatal else 'completed',sent=len(ledger.rows),answer_slots=len(answer_summary['control'])))
    except BaseException as exc:
        save(LOCAL/'batch/exception.json',dict(type=type(exc).__name__,code=getattr(exc,'code',None),sent=len(ledger.rows),stopped=True))
        raise
    finally:
        save(LOCAL/'batch/send-ledger.json',ledger.rows)
        store.close()
        for r in (baseline,b,candidate,query_model):
            active=getattr(r,'_active',None)
            if active is not None:
                while not active.done():await asyncio.sleep(.1)
            r.close()


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('prepare offline; run exactly once')
