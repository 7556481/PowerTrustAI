"""New generation-only diagnosis over complete archived deliveries; no search.

The adapter supplies old Delivery objects to the existing Harness stage. It does
not reconstruct ranking/context, load knowledge stores, or resume the old batch.
"""
import asyncio
from contextlib import closing
from dataclasses import fields, replace
import hashlib
import os
import sqlite3
import subprocess
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from agents.contracts import GenerationInput
from agents.generation import messages_for
from backend.assembly import ComponentFactory
from backend.config import ROOT, ServiceConfig
from backend.serialization import wire
from core.models import Evidence, EvidenceBinding, ExecutionStatus
from core.validation import require, validate_types
from harness.contracts import RetrievalRecord, RetrievalRequestOptions
from harness.retrieval import Delivery
from rag.contracts import RetrievalHit, RetrievalPurpose
from evaluation.archive_replay import restore
from evaluation import chinese_first_cross_language_v1 as old
from evaluation import answer_review_net_benefit_v1 as shared

VERSION='retrieval-evidence-answer-check-v1'
BASE='99b93497cb78bf3f040f1874ad07cb525be6d64b'
LOCAL=ROOT/'data/retrieval_local'/VERSION
PUBLIC=ROOT/'docs/evaluation'/VERSION
OLD=old.LOCAL
load,save,sha,sources=old.load,old.save,old.sha,old.sources


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def restore_delivery(value):
    require(value['issue'] is None and not value['issues'],'Archived delivery did not succeed')
    record=dict(value['record'])
    require(set(record)=={f.name for f in fields(RetrievalRecord)},'Archived record fields differ')
    record['status']=ExecutionStatus(record['status'])
    record['hits']=tuple(restore(h,RetrievalHit) for h in record['hits'])
    record['request_options']=restore(record['request_options'],RetrievalRequestOptions)
    for name in ('core_evidence_ids','context_evidence_ids','omitted_evidence_ids','context_omissions'):
        record[name]=tuple(record[name])
    require(not record['fact_bindings'],'Generation archive cannot gain fact retrieval bindings')
    record['fact_bindings']=()
    record['omission_reasons']=tuple(tuple(row) for row in record['omission_reasons'])
    record['offered_context_links']=tuple((eid,tuple(ids)) for eid,ids in record['offered_context_links'])
    restored=Delivery(tuple(restore(e,Evidence) for e in value['evidence']),
        tuple(restore(b,EvidenceBinding) for b in value['bindings']),None,RetrievalRecord(**record),())
    # The existing general validator treats heterogeneous tuple items as the
    # first type. Preserve these two archived tuple fields explicitly here;
    # do not change the shared business validator for an evaluation reader.
    validate_types(restored.record.request_options,RetrievalRequestOptions)
    for hit in restored.record.hits:validate_types(hit,RetrievalHit)
    for eid,ids in restored.record.offered_context_links:
        require(type(eid) is str and all(type(i) is str for i in ids),'Invalid archived context links')
    require(restored.record.core_evidence_ids==tuple(b.evidence_id for b in restored.bindings if b.origin=='index_core_hit'),'Core binding mismatch')
    require(restored.record.context_evidence_ids==tuple(b.evidence_id for b in restored.bindings if b.origin=='index_adjacent_context'),'Context binding mismatch')
    require(wire(restored)==value,'Restored delivery is not byte-content/field equivalent')
    return restored


def recover():
    previous=load(OLD/'freeze.json');gate=load(OLD/'evidence-gate.json')
    require(gate['passed'] is False and 'N6' in gate['semantic_failure_cases'],'Old failure must remain')
    builder=ROOT/'evaluation/chinese_first_cross_language_v1.py'
    require(previous['sources'][str(builder.relative_to(ROOT))]==digest(builder),'Original request builder changed')
    require(sha(load(OLD/'materials.json'))==previous['materials_sha256'],'Previous reference changed')
    with closing(sqlite3.connect((OLD/'batch/retrieval.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        stored={r['case']+'-'+r['variant']:v for request,result in db.execute('SELECT request,result FROM runs')
            for r,v in [(old.json.loads(request),old.json.loads(result))]}
    public=load(old.PUBLIC/'retrieval-results.json');result={};origins=[]
    for i,item in enumerate(old.N):
        for variant in ('A','C'):
            ident=item['id']+'-'+variant;path=OLD/'batch/retrieval'/f'{ident}.json';raw=load(path)
            require(raw==stored[ident],'Archived file/Store mismatch')
            d=restore_delivery(raw['delivery']);rec=d.record
            require(rec.query==item['question'] and rec.knowledge_version==previous['configuration']['knowledge_version'],'Original question/knowledge changed')
            require(rec.request_options.max_results==3 and rec.request_options.context_options==old.ContextOptions(),'Original context options changed')
            require(rec.accepted_chars==sum(len(e.text) for e in d.evidence),'Delivery character mismatch')
            expected=next(row for row in public['cases'] if row['id']==item['id'])['variants'][variant]
            require([e.evidence_id for e in d.evidence]==[e['evidence_id'] for e in expected['delivered']],'Public delivery order mismatch')
            for e,summary in zip(d.evidence,expected['delivered']):
                require(hashlib.sha256(e.text.encode()).hexdigest()==summary['text_sha256'],'Archived body hash mismatch')
            result[(i,variant)]=d
            origins.append(dict(id=ident,path=path.relative_to(ROOT).as_posix(),file_sha256=digest(path),delivery_sha256=sha(d),
                evidence_sha256=sha(d.evidence),bindings_sha256=sha(d.bindings),record_sha256=sha(rec),
                knowledge_version=rec.knowledge_version,archived_retrieval_id=rec.retrieval_id,evidence_count=len(d.evidence),chars=rec.accepted_chars))
    return result,origins


def request(m,i,**kw):return replace(old.request(m['N'][i]),task_id=VERSION+'-'+m['N'][i]['id'])


def prepare():
    require(not (LOCAL/'attempt.json').exists(),'No overwrite after attempt')
    recovered,origins=recover();materials=load(OLD/'materials.json')
    m=dict(version=VERSION,N=materials['N'],rules=materials['rules'],reference_sources=materials['reference_sources'],
        source_trial=old.VERSION,old_gate_passed=False,old_N6_conversion='substantive_unfaithfulness',
        group_definitions=dict(all_8=[r['id'] for r in materials['N']],faithful_7=[r['id'] for r in materials['N'] if r['id']!='N6'],N6=['N6']),
        origin='Seen fixed-output development diagnosis; faithful subset is already-known post hoc stratification, not holdout')
    pairs=[]
    for i in range(8):
        inputs=[GenerationInput(request(m,i),recovered[(i,v)].evidence,recovered[(i,v)].bindings,recovered[(i,v)].record.knowledge_version,()) for v in ('A','C')]
        messages=[messages_for(inp,3,product_guidance=True) for inp in inputs]
        require(messages[0][0:2]==messages[1][0:2],'Same-question prompt changed between branches')
        require(all(old.json.loads(msgs[1].content)['question']==m['N'][i]['question'] for msgs in messages),'Original Chinese question missing')
        pairs.append(dict(id=m['N'][i]['id'],same_system_and_question_messages=True,
            message_shape=[msg.role for msg in messages[0]],input_sha256={v:sha(inp) for v,inp in zip(('A','C'),inputs)},
            document_message_fields=sorted(old.json.loads(messages[0][-1].content)),query_plan_in_message=False))
    save(LOCAL/'materials.json',m);save(LOCAL/'origins.json',origins)
    save(PUBLIC/'input-recovery.json',dict(origins=origins,pairs=pairs,old_gate_passed=False,old_gate_unchanged=True,new_retrieval_calls=0,
        scope='All sixteen actual complete deliveries restored and matched to old Store/file/public body hashes; no index or seal opened'))
    ref=load(old.PUBLIC/'materials-reference.json')
    save(PUBLIC/'materials-reference.json',{k:m[k] for k in ('version','N','rules','group_definitions','origin','old_gate_passed','old_N6_conversion')}|dict(reference_sources=ref['reference_sources']))
    print('Recovered 16 complete deliveries; paired messages differ only in Evidence and original bindings; no model/index access',flush=True)


class ArchivedSession:
    def __init__(self,delivery,question):
        self.delivery=delivery;self.question=question;self.records=[];self.calls=self.chars=0
    async def retrieve(self,purpose,request,answer,claims,**kw):
        require(not self.records and purpose==RetrievalPurpose.GENERATION and answer is None and not claims and not kw.get('query_override'),'Only one archived generation delivery allowed')
        require(request.question==self.question==self.delivery.record.query,'Archive question mismatch')
        record=replace(self.delivery.record,query_method='archived_retrieval',duration_ms=0,calls_used=0,cumulative_chars=0,
            reason='Previously validated actual delivery; no new search, conversion, seal or ranking. Original record retained in archive-origin.json.')
        self.records.append(record)
        return replace(self.delivery,record=record)


class SendLimit:
    def __init__(self,root,clock=monotonic):self.root=root;self.clock=clock;self.start=None;self.used=0;self.slots={}
    def remaining_seconds(self):return 3600 if self.start is None else max(.001,3600-(self.clock()-self.start))
    def __call__(self,spec,r,n):
        now=self.clock()
        if self.start is None:self.start=now
        require(r.model_id=='deepseek-flash' and r.max_output_tokens==8000 and r.prompt_version.startswith('evidence-bound-generation'),'Generation parameters/type changed')
        key=str(spec['case'])+'-'+spec['variant']
        require(self.used<32 and self.slots.get(key,0)<2 and now-self.start<3600,'Global or slot send cap')
        self.used+=1;self.slots[key]=self.slots.get(key,0)+1
        save(self.root/'send-ledger'/f'{self.used:04d}.json',dict(used=self.used,slot=key,slots=self.slots,elapsed=now-self.start))


async def batch(c,m,recovered,origins,root,provider,*,limit=None):
    current={};limit=limit or SendLimit(root)
    class Factory(ComponentFactory):
        def create(self,rid,observer):
            b=super().create(rid,observer,fixed_evidence_only=True)
            b.harness.retriever=SimpleNamespace(archive_only=True)
            b.harness.subject_supplement=False;b.harness.generation_query_converter=None
            b.harness.archived_delivery=recovered[(current['case'],current['variant'])]
            return b
    async def before(spec,outputs):current.clear();current.update(spec)
    async def runner(harness,req,budget,**kw):
        d=harness.archived_delivery;origin=next(r for r in origins if r['id']==m['N'][current['case']]['id']+'-'+current['variant'])
        require(sha(d)==origin['delivery_sha256'],'Restored input changed before execution')
        save(root/kw['run_id']/'archive-origin.json',dict(origin=origin,original_record=wire(d.record),
            restored_evidence_sha256=sha(d.evidence),restored_bindings_sha256=sha(d.bindings),new_run_id=kw['run_id'],
            classification='archived_retrieval',new_retrieval_calls=0,historical_conversion_cost_recounted=False))
        session=ArchivedSession(d,req.question)
        with patch('harness.execution.RetrievalSession',return_value=session):
            return await harness.run(req,budget,**kw)
    def guard(spec,raw):
        d=recovered[(spec['case'],spec['variant'])]
        if raw['evidence']!=wire(d.evidence) or raw['evidence_bindings']!=wire(d.bindings):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Archived input identity mismatch')
        if any(x['code'] in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CANCELLED','CANCELLED') for x in raw['execution_issues']):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Timeout/unknown acceptance stops batch')
        if any(not r['prompt_version'].startswith('evidence-bound-generation') for r in raw['model_records']):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Non-generation model invocation')
    rows=[dict(id=m['N'][i]['id']+'-'+v,input=dict(id=m['N'][i]['id']+'-'+v,line='G',case=i,variant=v))
        for i in range(8) for v in (('A','C') if i%2==0 else ('C','A'))]
    return await shared.batch(c,m,root,provider,factory_type=Factory,rows=rows,request_builder=request,
        variant_config=lambda cfg,v:cfg,task_runner=runner,result_guard=guard,before_submit=before,
        send_guard=limit,budget_for=lambda spec,b:replace(b,max_model_calls=2,max_duration_seconds=min(800,limit.remaining_seconds()),max_transient_retries=0),
        local_issue_codes=('MODEL_CALL_BUDGET_EXHAUSTED',))


async def run():
    require(not (LOCAL/'attempt.json').exists(),'Unique new attempt only; no resume')
    require(not subprocess.check_output(['git','status','--porcelain','--','agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools'],cwd=ROOT,text=True).strip(),'Commit sources first')
    require(not subprocess.check_output(['git','diff',BASE,'--','agents','backend','core','harness','model_adapter','rag','services','tools'],cwd=ROOT),'Business semantics changed')
    m=load(LOCAL/'materials.json');recovered,origins=recover();require(origins==load(LOCAL/'origins.json'),'Prepared origins changed')
    original_materials=load(OLD/'materials.json')
    for key in ('N','rules','reference_sources'):
        require(m[key]==original_materials[key],'Frozen original reference changed: '+key)
    c=ServiceConfig.from_environment()  # sole real-run root .env loader
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    previous=load(OLD/'freeze.json')
    for key in ('profile','decision_policy','execution_path','verification_schema','retrieval_mode','retrieval_execution_profile',
        'fact_strategy','fact_review_contract','local_revision_interface','revision_answer_delivery','review_result_transport',
        'fact_internal_flow','domain_internal_flow','extraction_message_profile','review_message_profile','knowledge_version'):
        require(getattr(c,key)==previous['configuration'][key],'Original configuration differs: '+key)
    c=replace(c,run_db=LOCAL/'batch/runs.sqlite3',budget=replace(c.budget,max_model_calls=2,max_duration_seconds=800,max_transient_retries=0))
    manifest=ComponentFactory(c).manifest(c.knowledge_version,fixed_evidence_only=True)
    require(manifest['prompts']['generation']==previous['manifest']['prompts']['generation'],'Generation prompt differs')
    f=dict(version=VERSION,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),baseline=BASE,
        sources=sources(),configuration=wire(c),generation_manifest=manifest,materials_sha256=sha(m),origins_sha256=sha(origins),
        old_gate_passed=False,old_N6_conversion='failed and unchanged',classification='new fixed archived Evidence generation diagnosis, not old trial continuation',
        order=[r['id']+'-'+v for i,r in enumerate(m['N']) for v in (('A','C') if i%2==0 else ('C','A'))],
        limits=dict(slots=16,per_slot=2,total=32,corrections_per_slot=1,slot_seconds=800,total_seconds=3600,max_output=8000),
        stop='Persisted final model format failure/local quota continues; shared code/config/input/storage/auth/balance/rate/service/network/timeout/unknown acceptance stops. No repair/resume/second batch.',
        scope='No knowledge store/seal/search/conversion/verification/domain/Revision; existing generation-only/Store over exact archived deliveries')
    save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
    save(LOCAL/'attempt.json',dict(freeze_sha256=sha(f),resume_allowed=False))
    from model_adapter.deepseek import create_adapter
    s=await batch(c,m,recovered,origins,LOCAL/'batch',create_adapter)
    require(sources()==f['sources'],'Frozen source changed')
    print(old.json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],new_requests=len(s['send_log']))),flush=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('prepare offline; run exactly once')
