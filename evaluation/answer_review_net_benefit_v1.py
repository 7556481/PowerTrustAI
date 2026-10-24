"""Fixed paired development validation. Uses run_fixed, Factory, Harness and RunStore.

No HTTP resubmission, resume, alternative scheduler or production configuration writes.
Generation uses the normal frozen index; paired audits use its immutable delivery.
"""
import asyncio
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4
from backend.assembly import ComponentFactory
from backend.config import ROOT, ServiceConfig
from backend.serialization import wire
from backend.store import RunStore
from evaluation.batch_control import run_fixed
from evaluation.langgraph_service_trial_v1 import saved_result, config_identity
from evaluation.public_review_validation_trial_v1 import write, read, sha, assert_no_evaluator_keys, PreSendStorageFailure
from harness.evidence_review_demo import restore_answer, restore_evidence, restore_snapshot
from core.models import TaskRequest, TaskMode, EngineeringContext, AnswerDraft, CitationBinding

PUBLIC=ROOT/'docs/evaluation/answer-review-net-benefit-v1'
LOCAL=ROOT/'data/retrieval_local/answer-review-net-benefit-v1'


def materials():
    archive=ROOT/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json'
    s=read(archive)
    all_e=s['runs'][0]['result']['evidence']
    ids=('e-5144faa1d672ad26585556a4d64b78cebf248f80c4a6f18ec52a7fd5470d36c5',
         'e-38d427eb90b5026a4ccac127c04b5b11c0e211aac700421c01638df034e35bde')
    evidence=[next(e for e in all_e if e['evidence_id']==i) for i in ids]
    questions=[
        '按给定NERC资料解释动态无功资源如何调节输出，以及两种运行方式。',
        '按给定NERC资料解释静态无功资源在额定电压下的输出及其电压依赖，并说明如何投切。',
        '按给定NERC资料解释静态无功资源的电压依赖；这些资料能否给出某匿名厂站所需补偿容量？',
        '按给定NERC资料比较动态与静态无功资源的调节方式，并说明这一区别能否单独保证某厂站在故障后电压稳定。',
    ]
    drafts=[
        '动态无功资源一旦并网就固定输出，不能随电网电压变化连续调节；它只采用固定电压设定点运行。',
        '按该资料，静态无功资源在额定电压下有固定的无功输出，其能力随电压平方变化；可根据系统条件手动或自动投切，接入后提供固定的额定无功贡献。',
        '按该资料，静态无功资源的能力随电压平方变化。给定资料没有该匿名厂站的网络模型、运行点与补偿目标，不能据此给出具体补偿容量。',
        '动态无功资源输出固定，静态无功资源能实时连续自动调节。因此只要选用静态无功资源，就能保证匿名厂站故障后电压稳定。',
    ]
    refs=[
        ['动态：响应电网电压变化、在规定电压带宽内实时自动连续调节','运行方式：维持电压设定点或电压下垂模式'],
        ['额定电压下固定输出','能力随电压平方变化','按系统条件手动或自动投切；接入后额定贡献固定'],
        ['静态能力随电压平方变化','未给该厂站数据不能确定具体容量；具体缺口不得变成已完成计算'],
        ['动态自动连续调节与静态投切/固定额定贡献分别说明','能力的电压依赖保留','不能单凭类型保证厂站故障后稳定，需相应工况/故障分析，未执行不得声称完成'],
    ]
    return dict(version='answer-review-materials-v1',source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                evidence=evidence,questions=questions,drafts=drafts,reference=refs,
                reference_origin='AI-assisted source reading under user supervision; development validation, not expert gold or independent holdout',
                allowed='Equivalent correct expressions; no exact wording score. Technical comparisons allowed; revision history is not requested.',
                boundaries='No universal response-time guarantee, plant capacity or safety certification. Missing input and unexecuted analysis remain gaps.')


def order():
    rows=[]
    for i in range(4):
        for v in (('production','answer_only_v1') if i%2==0 else ('answer_only_v1','production')):
            rows.append(dict(id=f'A{i+1}-{v}',input=dict(line='A',case=i,variant=v)))
    for i in range(4):
        rows.append(dict(id=f'G{i+1}',input=dict(line='G',case=i,variant='production')))
        for v in (('production','answer_only_v1') if i%2==0 else ('answer_only_v1','production')):
            rows.append(dict(id=f'B{i+1}-{v}',input=dict(line='B',case=i,variant=v)))
    return rows


def initial_request(m,i,*,draft=False):
    e=tuple(restore_evidence(e) for e in m['evidence'])
    text=m['drafts'][i]
    answer=AnswerDraft(f'fixed-A{i+1}',1,text,citations=(CitationBinding(0,len(text),(e[0].evidence_id,)),)) if draft else None
    return TaskRequest(f'net-v1-{i+1}',TaskMode.ASSESS_EXISTING if draft else TaskMode.QUESTION_ANSWER,
        'voltage_stability_reactive_support',m['questions'][i],
        '仅解释给定资料的适用范围，不作厂站安全认证。匿名厂站没有另附工程记录。',answer,e,EngineeringContext(goal='conceptual'))


def frozen_config(c):
    return config_identity(c)


def freeze():
    if (LOCAL/'attempt.json').exists() or (PUBLIC/'freeze.json').exists():raise ValueError('New batch only')
    from harness.deepseek_trial import load_project_env
    load_project_env()
    c=ServiceConfig.from_environment()
    if c.verification_schema!=13 or c.fact_internal_flow!='production' or c.domain_internal_flow!='production' or c.revision_answer_delivery!='production':raise ValueError('Production baseline mismatch')
    if os.environ.get('DEEPSEEK_MODEL_ID')!='deepseek-flash':raise ValueError('Confirmed model required')
    f=ComponentFactory(c);k=f.preflight();m=materials()
    # Materials/references are frozen before any prediction; references never enter request.
    write(LOCAL/'materials.json',m)
    paths=[p for name in ('agents','backend','core','harness','model_adapter','services','rag','evaluation','tests','tools') for p in (ROOT/name).glob('*.py')]
    value=dict(version='answer-review-net-benefit-v1',source_base_commit='865a7e8a82a7557caa7c74f042a7b412256b4052',
        configuration=frozen_config(c),manifest=f.manifest(k),materials_sha256=sha(m),order=order(),
        source_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(paths)],
        owner_authorized=True,no_resume=True,model='deepseek-flash',plan=dict(A=8,generation=4,B=8),
        budget='40 shared calls /800s per original flow. B deducts its immutable generation calls/time independently. One Revision, existing corrections; no new node allowance.',
        scope='A fixed authored electrical development drafts; B current RAG generation once, paired audits of identical actual delivery. Audit retrieval disabled for fixed-delivery comparison only; production retrieval unchanged.',
        stop='Shared/unknown program, identity, connection, storage or ownership failure stops all subsequent sends. Local final model structure failure continues. No resubmit/resume.',
        adoption='Keep candidate unless complete-answer benefit without critical new error/required-point loss is evidenced. Four pairs cannot establish general accuracy.')
    write(LOCAL/'freeze.json',value);write(PUBLIC/'freeze.json',value)
    write(PUBLIC/'materials-reference.json',{k:v for k,v in m.items() if k!='evidence'} | {'sources':[dict(evidence_id=e['evidence_id'],source_id=e['source_id'],source_version=e['source_version'],locator=e['locator'],text_sha256=sha(e['text'])) for e in m['evidence']]})
    print('Frozen 8 capability + 4 generation + 8 natural audit tasks; zero sends.',flush=True)


async def batch(c,m,root,provider_factory,*,factory_type=ComponentFactory,rows=None,request_builder=None,variant_config=None,task_runner=None,result_guard=None,fixed_audit_delivery=True):
    """Submission/persistence/stop is exclusively run_fixed; collection runs Harness."""
    rows=rows or order();generated={};outputs={};send_log=[];fatal=False
    store=RunStore(root/'runs.sqlite3')
    async def submit(spec):
        rid=uuid4().hex
        if fatal:raise RuntimeError('Shared stop')
        store.create(rid,spec,dict(configuration=frozen_config(c),variant=spec['variant']))
        return dict(run_id=rid,spec=spec)
    async def collect(a):
        nonlocal fatal
        rid=a['run_id'];spec=a['spec'];i=spec['case'];line=spec['line'];start=perf_counter();directory=root/rid
        if line=='B' and (i not in generated or not generated[i].generation_output or not generated[i].generation_output.substantive_answer):
            result=dict(run_id=rid,execution_issues=[],state='unexecuted',reason='no_substantive_natural_draft')
            store.mark(rid,'finished',result=result);outputs[rid]=result;return result
        req=(request_builder or initial_request)(m,i,draft=line=='A');snapshot=None;budget=c.budget
        if line=='B':
            g=generated[i];snapshot=g.generation_output.evidence_snapshot
            req=replace(req,mode=TaskMode.ASSESS_EXISTING,existing_answer=g.answer,provided_evidence=g.evidence)
            generation_retrieval=g.retrieval_records[-1] if g.retrieval_records else None
            budget=replace(budget,max_model_calls=budget.max_model_calls-len(g.model_records),
                           max_duration_seconds=max(.001,budget.max_duration_seconds-g.duration_ms/1000),
                           max_retrieval_calls=budget.max_retrieval_calls-(generation_retrieval.calls_used if generation_retrieval else 0),
                           max_retrieval_chars_total=budget.max_retrieval_chars_total-(generation_retrieval.cumulative_chars if generation_retrieval else 0))
        cfg=variant_config(c,spec['variant']) if variant_config else replace(c,revision_answer_delivery=spec['variant'])
        factory=factory_type(cfg);bundle=None
        observations={'first_answer_saved_ms':None,'browser_first_paint_ms':None}
        def observe(value):
            store.checkpoint(rid,value)
            if value.get('answer') is not None and observations['first_answer_saved_ms'] is None:
                observations['first_answer_saved_ms']=round((perf_counter()-start)*1000,3)
        class Guard:
            def __init__(self,delegate):self.delegate=delegate
            @property
            def _active(self):return getattr(self.delegate,'_active',None)
            def close(self):self.delegate.close()
            async def complete(self,r):
                nonlocal fatal
                if fatal:raise PreSendStorageFailure({'constraint':'shared_stop'})
                validate=getattr(self.delegate,'validate_request',None)
                if validate is not None:validate(r)
                try:
                    if r.model_id!=os.environ.get('DEEPSEEK_MODEL_ID') or r.max_output_tokens!=8000:raise ValueError('Frozen model mismatch')
                    for msg in r.messages:
                        if msg.role=='user':
                            try:v=json.loads(msg.content)
                            except ValueError:continue
                            assert_no_evaluator_keys(v)
                    n=len(send_log)+1
                    row=dict(sequence=n,run_id=rid,task=spec,prompt_version=r.prompt_version,correction=r.correction,
                             messages=wire(r.messages),messages_sha256=sha(wire(r.messages)),parameters=dict(model_id=r.model_id,max_output_tokens=r.max_output_tokens),elapsed_before_send=perf_counter()-start)
                    if r.result_tool is not None:row['parameters'].update(result_tool=r.result_tool,endpoint='https://api.deepseek.com/beta/chat/completions',tool_choice={'type':'function','function':{'name':'submit_review_result'}},thinking={'type':'disabled'})
                    write(root/'messages'/f'{n:04d}.json',row)
                    send_log.append({k:v for k,v in row.items() if k!='messages'})
                except Exception:
                    fatal=True;raise PreSendStorageFailure({'constraint':'frozen_identity_or_message_storage'}) from None
                try:response=await self.delegate.complete(r)
                except Exception as exc:
                    if getattr(exc,'code',None) in ('MODEL_REQUEST_REJECTED','MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED','MODEL_RATE_LIMITED'):fatal=True
                    raise
                try:write(root/'responses'/f'{n:04d}.json',dict(text=response.text,model_id=response.model_id,usage=wire(response.usage),finish_reason=response.finish_reason,**({'result_transport':wire(response.result_transport)} if response.result_transport is not None else {})))
                except Exception:fatal=True;raise PreSendStorageFailure({'constraint':'response_storage'}) from None
                return response
        try:
            store.mark(rid,'running')
            with patch('model_adapter.deepseek.create_adapter',side_effect=lambda settings,**options:Guard(provider_factory(settings,**options))):
                bundle=factory.create(rid,observe)
            if line=='A' or line=='B' and fixed_audit_delivery:
                # Fixed-evidence evaluation seam, never saved to production configuration.
                bundle.harness.retriever=None
                bundle.harness.subject_supplement=False
            run=task_runner if task_runner else lambda h,*args,**kw:h.run(*args,**kw)
            result=await run(bundle.harness,req,budget,knowledge_version=c.knowledge_version if line in ('G','B') else None,
                generation_only=line=='G',generation_snapshot=snapshot,run_id=rid)
            raw=wire(result)
            if fatal:raw['execution_issues'].append(dict(component='harness',code='DIAGNOSTIC_STORAGE_FAILED',message='pre-send or response persistence failed'))
            known={'MODEL_OUTPUT_ERROR','MODEL_TIMEOUT','TIMEOUT','BUDGET_EXHAUSTED','CANCELLED'}
            # Unknown errors stop; never discover sharedness by spending again.
            if any(x['code'] not in known for x in raw['execution_issues']):
                raw['execution_issues'].append(dict(component='harness',code='SERVICE_EXECUTION_FAILED',message='Unknown or shared issue stops remaining sends'))
            if result_guard is not None:
                stop_issue=result_guard(spec,raw)
                if stop_issue:raw['execution_issues'].append(stop_issue);fatal=True
            outputs[rid]=raw
            write(directory/'input.json',dict(request=wire(req),generation_snapshot=wire(snapshot),budget=wire(budget)))
            write(directory/'result.json',raw)
            write(directory/'observations.json',observations | {'collect_elapsed_ms':round((perf_counter()-start)*1000,3)})
            store.mark(rid,'finished',result=raw)
            saved=saved_result(root/'runs.sqlite3',rid)
            if saved!=raw:raise ValueError('Independent collector mismatch')
            if line=='G':generated[i]=result
            print(f'{line}{i+1}-{spec["variant"]}: {raw["state"]}, calls={len(result.model_records)}',flush=True)
            return raw
        finally:
            if bundle:
                await bundle.drain();bundle.close()
            await factory.close()
    try:
        control=await run_fixed(rows,submit=submit,collect=collect,persist=lambda ident,kind,value:write(root/'control'/f'{ident}-{kind}.json',value))
        summary=dict(control=control,outputs=outputs,send_log=send_log,planned=rows,
                     unexecuted=[x['id'] for x in rows if x['id'] not in {r['case_id'] for r in control}])
        write(root/'summary.json',summary)
        return summary
    finally:store.close()


def execute():
    f=read(PUBLIC/'freeze.json')
    if f!=read(LOCAL/'freeze.json') or (LOCAL/'attempt.json').exists():raise ValueError('No changed freeze or resume')
    for row in f['source_files']:
        if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Frozen source changed')
    m=read(LOCAL/'materials.json')
    if sha(m)!=f['materials_sha256']:raise ValueError('Materials changed')
    c=ServiceConfig.from_environment()
    if frozen_config(c)!=f['configuration'] or os.environ.get('DEEPSEEK_MODEL_ID')!=f['model']:raise ValueError('Configuration changed')
    ComponentFactory(c).preflight()
    from model_adapter.deepseek import create_adapter
    write(LOCAL/'attempt.json',dict(freeze_sha256=sha(f),resume_allowed=False))
    s=asyncio.run(batch(c,m,LOCAL/'batch',create_adapter))
    print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],sends=len(s['send_log']))),flush=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['freeze']:freeze()
    elif sys.argv[1:]==['execute']:execute()
    else:raise SystemExit('freeze | execute')
