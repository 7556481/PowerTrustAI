"""Frozen natural-input regression; reuses the existing bounded batch controller."""
import asyncio
import hashlib
import json
import os
from types import SimpleNamespace
from collections import Counter
from dataclasses import replace
from pathlib import Path
from backend.config import ROOT, ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from core.models import Evidence, TaskRequest, TaskMode, EngineeringContext
from harness.contracts import HarnessResult
from evaluation.archive_replay import restore
from evaluation import answer_review_net_benefit_v1 as shared
from evaluation.review_delivery_unblock_v1 import provider
from evaluation.strict_interface_probe_v1 import load, save, digest
from services.claim_message_v1 import system, VERSION as MESSAGE_VERSION

VERSION='natural-review-seam-v1'
LOCAL=ROOT/'data/retrieval_local'/VERSION
PUBLIC=ROOT/'docs/evaluation'/VERSION
OLD=ROOT/'data/retrieval_local/review-delivery-unblock-v1/batch'


def old_records():
    s=load(OLD/'summary.json')
    return {r['case_id']:(s['outputs'][r['accepted']['run_id']],
        load(OLD/r['accepted']['run_id']/'input.json')) for r in s['control']}


def generations():
    records=old_records()
    from agents.contracts import GenerationOutput
    from harness.evidence_review_demo import restore_answer,restore_evidence
    result={}
    for i in range(3):
        raw=records[f'G{i+1}'][0]
        # Minimal read-only view of saved fields the existing collector uses.
        # Do not reconstruct an old trace using today's generic tuple decoder.
        result[i]=SimpleNamespace(answer=restore_answer(raw['answer']),
            evidence=tuple(restore_evidence(e) for e in raw['evidence']),
            generation_output=restore(raw['generation_output'],GenerationOutput),
            model_records=tuple(raw['model_records']),duration_ms=raw['duration_ms'],
            retrieval_records=tuple(SimpleNamespace(**r) for r in raw['retrieval_records']))
    for i,g in result.items():
        assert wire(g.generation_output)==records[f'G{i+1}'][0]['generation_output']
        for variant in ('before','bound'):
            saved=records[f'B{i+1}-{variant}'][1]
            assert saved['request']['existing_answer']==wire(g.answer)
            assert saved['generation_snapshot']==wire(g.generation_output.evidence_snapshot)
            assert saved['request']['provided_evidence']==wire(g.evidence)
    return result


def diagnosis():
    records=old_records(); rows=[]
    for case,(r,inp) in records.items():
        if not case.startswith('B'):continue
        findings=(r.get('verification_output') or {})
        rows.append(dict(case=case,run_id=r['run_id'],question=inp['request']['question'],
            answer=r['answer'],input_sha256=shared.sha(inp),
            source_identities=[{k:e[k] for k in ('evidence_id','source_id','source_version','locator')} |
                dict(text_sha256=digest(e['text'].encode())) for e in inp['request']['provided_evidence']],
            extraction=r['extraction_output'],
            fact=public_findings(findings.get('findings',[])),
            citations=public_findings(findings.get('citation_reviews',[])),
            domain=[{k:f.get(k) for k in ('finding_id','category','check_status','rationale','missing_prerequisites')} for f in (r.get('domain_output') or {}).get('findings',[])],
            decision=r['report']['decision'],state=r['state'],execution_issues=r['execution_issues'],
            revision_outputs=r['revision_outputs'],
            calls=[{k:c.get(k) for k in ('call_number','component','prompt_version','correction','output_status','validation_error')} for c in r['model_records']]))
    s=load(OLD/'summary.json'); calls=[c for r in s['outputs'].values() for c in r.get('model_records',[])]
    erratum=dict(total=len(calls),initial=sum(not c['correction'] for c in calls),corrections=sum(c['correction'] for c in calls),
        correction_owners=dict(Counter(c['component'] for c in calls if c['correction'])),
        explanation='12 is fact-stage corrections only; total13 includes one extraction correction. Historical responses/results unchanged.',
        generation_retrieval_patch='ebb6fb974655406b73a87d1a64d84f49b52d275f is post-batch offline only; old allowance is not retroactively equivalent.')
    messages=[]
    for p in sorted((OLD/'messages').glob('*.json')):
        m=load(p)
        if not m['prompt_version'].startswith('atomic-claims'):continue
        text=m['messages'][0]['content']
        messages.append(dict(sequence=m['sequence'],task=m['task'],correction=m['correction'],
            messages_sha256=m['messages_sha256'],system_chars=len(text),
            obsolete_two_field_example='{category,proposition}' in text,
            obsolete_three_field_shape='EXACT category,proposition,basis_target' in text,
            mandatory_fourth_field='every component ALSO requires verification_obligation' in text))
    save(PUBLIC/'previous-breakpoints.json',dict(erratum=erratum,rows=rows,actual_extraction_messages=messages))
    return rows


def public_findings(rows):
    # Preserve model judgments/reasons, omit duplicated private source bodies.
    out=[]
    for row in rows:
        row=dict(row);row.pop('bases',None)
        def clean(v):
            if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in ('bases','evidence')}
            if isinstance(v,list):return [clean(x) for x in v]
            if isinstance(v,str) and ' [compact-support-assessment-v1] ' in v:
                reason,tail=v.rsplit(' [compact-support-assessment-v1] ',1)
                try:
                    a=json.loads(tail)
                    for u in a.get('program_source_units',[]):
                        if 'text' in u:u['text_sha256']=digest(u.pop('text').encode())
                    return reason+' [compact-support-assessment-v1] '+json.dumps(a,ensure_ascii=False)
                except ValueError:raise ValueError('Cannot publish unsanitized source annotation')
            return v
        out.append(clean(row))
    return out


def materials():
    m=load(ROOT/'data/retrieval_local/review-delivery-unblock-v1/materials.json')
    cards=ROOT/'data/evaluation_local/evidence-bound-v1'
    sw=load(cards/'SW-001.owner-confirmed-v1.json');rc=load(cards/'RC-001.offline-card-v2.json')
    sources={}
    for e in sw['evidence']:
        # Use original extracted text, not the historical normalized display.
        text=e['raw_text']; key=e['evidence_id']
        page=cards/'sources/SW-001'/e['raw_extracted_page_file']
        raw=page.read_text(encoding='utf-8');start,end=e['raw_text_span']
        assert raw[start:end]==text
        sources[key]=wire(Evidence('seam-'+key,'abb-fixed-2006',sw['source_pdf_sha256'],
            f"PDF page{e['pdf_page_1based']};original pypdf chars[{start}:{end})",text,'official_document',('fixed2006 LV definitions, not current compliance',)))
    for e in rc['evidence']:
        text=e['text'];key=e['id']
        assert digest(text.encode())==e['text_sha256_utf8']
        sources[key]=wire(Evidence('seam-'+key,e['url'],e['local_file_sha256'],
            e['locator']+';historical browser-visible manually recorded derivative',text,'official_document',('US Subpart S fixed excerpt; not Chinese regulation or site certification',)))
        for scope in e.get('scope_context',[]):
            key=scope['id'];text=scope['text']
            sources[key]=wire(Evidence('seam-'+key,scope['url'],scope['local_file_sha256'],scope['locator']+';historical recorded derivative',text,'official_document'))
    new=[dict(question='根据给定ABB低压手册，隔离开关在什么位置满足怎样的功能要求？这一定义本身能否证明其可以开断任意故障电流？只解释资料含义，不给操作步骤。',
        sources=['SW-001-E1'],requirements=['分闸位置满足规定隔离功能','定义不足以证明任意故障开断能力；不自动断言所有电流都不能开断'],
        reference='E1原文明确in the open position及isolating function；未定义完整开断能力。不作现行标准或现场安全判断。'),
        dict(question='只按给定OSHA固定条文解释：live parts指什么？1910.303(g)(2)(iii)对哪类场所的什么位置提出何种标志要求？请保留上位电压范围，不把它推广为所有电气场所，也不作现场合规结论。',
        sources=['RC-001-E1','RC-001-E2','RC-001-SCOPE'],requirements=['已带电导电部件定义','含外露live parts的房间及其他有防护场所入口、醒目标志、禁止不合格人员进入','对地标称600V及以下；仅给定美国条文理解，不等于所有场所或现场认证'],
        reference='E1完整术语；E2完整编号段；SCOPE完整上位范围。无需推断匿名实例或新增规定，标志不构成安全保证。')]
    return dict(version=VERSION,B=m['B'][:3]+new,sources=m['sources']|sources,
        reference_origin='AI-assisted supervised development checks. Old sources reused; no independent holdout, no expert gold.',
        source_cards=[dict(path=str(p.relative_to(ROOT)),sha256=digest(p.read_bytes())) for p in (cards/'SW-001.owner-confirmed-v1.json',cards/'RC-001.offline-card-v2.json')])


def request(m,i,*,draft=False):
    if i<3:
        return restore(old_records()[f'B{i+1}-bound'][1]['request'],TaskRequest)
    from harness.evidence_review_demo import restore_evidence
    c=m['B'][i]
    return TaskRequest('seam-new-'+str(i+1),TaskMode.QUESTION_ANSWER,'electrical_document_understanding',c['question'],
        user_context='仅解释交付的固定版本原文；不作现场认证或操作步骤。',
        provided_evidence=tuple(restore_evidence(m['sources'][k]) for k in c['sources']),engineering_context=EngineeringContext(goal='conceptual'))


def order():
    rows=[]
    for i in range(5):
        if i>=3:rows.append(dict(id=f'G{i+1}',input=dict(line='G',case=i,variant='production')))
        for v in (('before','seam') if i%2==0 else ('seam','before')):
            rows.append(dict(id=f'B{i+1}-{v}',input=dict(line='B',case=i,variant=v)))
    return rows


def variants(c,v):
    if v=='production':return c
    return replace(c,fact_review_contract='simple_bound_v1',review_result_transport='strict_tool_v1',
        extraction_message_profile='unified_v1' if v=='seam' else 'production')


class Gate:
    def __call__(self,spec,raw):
        if any(x.get('code') in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CALL_BUDGET_EXHAUSTED','BUDGET_EXHAUSTED','MODEL_CANCELLED','CANCELLED') for x in raw.get('execution_issues',[])):
            return dict(component='harness',code='SERVICE_EXECUTION_FAILED',message='Timeout/cancellation/budget/unknown acceptance stops subsequent sends.')
        # Business admission is reviewed from the persisted first-line results,
        # before any new generation; it is not a keyword-based semantic judge.
        return None


async def run():
    from harness.deepseek_trial import load_project_env
    load_project_env();c=ServiceConfig.from_environment()
    assert os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash'
    assert c.fact_review_contract=='production' and c.extraction_message_profile=='production' and c.execution_path=='langgraph_v1'
    if (LOCAL/'attempt.json').exists():raise ValueError('No resume or second batch')
    g=generations();m=materials();factory=ComponentFactory(c)
    try:
        print('Normal Factory read-only preflight; no sends.',flush=True)
        k=factory.preflight()
        f=dict(version=VERSION,order=order(),configuration=shared.frozen_config(c),
            manifest=factory.manifest(k),candidate_manifest=ComponentFactory(variants(c,'seam')).manifest(k),
            model='deepseek-flash',materials_sha256=shared.sha(m),message_version=MESSAGE_VERSION,
            sources=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p.read_bytes())) for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in sorted((ROOT/folder).glob('*.py'))],
            historical_generation=[dict(case=i,sha256=shared.sha(old_records()[f'G{i+1}'][0]),calls=len(x.model_records),duration_ms=x.duration_ms,retrieval=vars(x.retrieval_records[-1]) if x.retrieval_records else None) for i,x in g.items()],
            plan=dict(old_chains=6,new_generation=2,new_chains=4),
            timing='Old generation excluded from new wall clock, but calls/time/retrieval counts and chars independently charged to each branch. Normal later extraction/retrieval randomness retained.',
            stop='Single output failure continues; shared/unknown fault stops. No retry/resume. Before G4, explicit source-text admission of first6 chains required.',
            budget='Original40 calls/800s,90s request/110s step,shared finite correction,oneRevision. No additional batch cap.')
        save(LOCAL/'materials.json',m);save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
        save(PUBLIC/'materials-reference.json',{k:v for k,v in m.items() if k!='sources'} | dict(sources={k:{q:v[q] for q in ('evidence_id','source_id','source_version','locator')} | dict(text_sha256=digest(v['text'].encode())) for k,v in m['sources'].items()}))
        save(LOCAL/'attempt.json',dict(freeze_sha256=shared.sha(f),resume_allowed=False))
        for x in f['sources']:assert digest((ROOT/x['path']).read_bytes())==x['sha256']
        # Same immutable freeze and stop ledger, no alternate controller.
        # The shared collector accepts a pre-submit boundary callback below.
        result=await shared.batch(c,m,LOCAL/'batch',provider,rows=order(),request_builder=request,
            variant_config=variants,result_guard=Gate(),fixed_audit_delivery=False,initial_generated=g,
            before_submit=admit_new_line)
        print(json.dumps(dict(executed=len(result['control']),unexecuted=result['unexecuted'],calls=len(result['send_log']))),flush=True)
        return result
    finally:await factory.close()


async def admit_new_line(spec,outputs):
    if spec['line']=='G' and spec['case']==3:
        save(LOCAL/'line1-review-input.json',dict(outputs=outputs))
        # Intentionally requires a local, already written human/AI source-text
        # review within this active authorized turn, never a model call.
        p=LOCAL/'line1-admission.json'
        print('First6 chains persisted. New-theme sends gated on source-text analysis in this turn.',flush=True)
        while not p.exists():await asyncio.sleep(1)
        a=load(p)
        assert a['outputs_sha256']==shared.sha(outputs) and a['continue'] is True


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['diagnose']:diagnosis();print('Read-only diagnosis saved; zero model requests.')
    elif sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('diagnose | run once; no resume')
