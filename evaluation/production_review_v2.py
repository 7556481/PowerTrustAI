"""Single fixed v2 batch, reusing v1 run library and fixed submission controller."""
import asyncio,json,hashlib,os
from pathlib import Path
from dataclasses import replace
from time import perf_counter
from datetime import datetime,timezone
from uuid import uuid4
from backend.config import ServiceConfig,ROOT
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation.answer_review_net_benefit_v1 import batch
from evaluation.public_review_validation_trial_v1 import read,write,sha
from evaluation.langgraph_service_trial_v1 import config_identity
from core.models import TaskRequest,TaskMode,EngineeringContext,RunTrace,TraceEvent,ExecutionStatus
from services.answer_units import assemble
from services.answer_anchors import anchors
from services.claim_obligations import parse
from harness.evidence_review_demo import restore_evidence
from harness.contracts import HarnessResult
from harness.states import RunState
from agents.contracts import ReliabilityVerificationInput
from model_adapter.runtime import ModelBudget,model_scope,model_invocation_scope

PUBLIC=ROOT/'docs/evaluation/production-review-net-benefit-v2'
LOCAL=ROOT/'data/retrieval_local/production-review-net-benefit-v2'


def materials():
    archive=ROOT/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json'
    all_e=read(archive)['runs'][0]['result']['evidence']
    prefix={'resources':'e-5144faa1','contingencies':'e-38d427eb','coordination':'e-052ea023','line_model':'e-9d1e06ec','locality':'e-54b969cc'}
    sources={k:next(e for e in all_e if e['evidence_id'].startswith(v)) for k,v in prefix.items()}
    A=[
        dict(id='A1',family='local_citation',question='按给定NERC资料分别解释动态资源的调节方式及静态资源的输出与投切方式。',
             units=[('resources','动态无功资源在规定电压带宽内随电网电压变化自动实时连续调节输出，可维持电压设定点或按电压下垂模式运行。'),('resources','静态无功资源在额定电压下输出固定，其能力随电压平方变化，并可按系统条件手动或自动投切。')],reference=['supported','supported']),
        dict(id='A2',family='local_citation',question='按给定NERC资料说明输配边界负荷的建模方式，以及双方无功支撑依赖应注意什么。',
             units=[('coordination','资料将输配边界负荷显式建模为MW和Mvar，可放在母线高压侧，也可放在降压变压器或等效配电阻抗之后。'),('coordination','资料指出负荷不应过度依赖大电力系统的无功支撑，反过来大电力系统也不应单纯依赖负荷的无功支撑。')],reference=['supported','supported']),
        dict(id='A3',family='condition_scope',question='按资料核对N-1与选定N-2的工况要求，区分无操作员干预这一限定的归属。',
             units=[('contingencies','资料对单一N-1故障要求系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内。'),('contingencies','资料明确要求所有选定N-2故障也必须在无操作员干预下立即满足相同限值。')],reference=['supported','insufficient_evidence']),
        dict(id='A4',family='condition_scope',question='核对资料中短线路无功传输表达式的建模前提和线路适用范围。',
             units=[('line_model','给定资料的无功传输表达式明确保留了线路电阻R和电容B。'),('line_model','资料明确声明该表达式适用于任意长度的所有输电线路。')],reference=['contradicted','insufficient_evidence']),
        dict(id='A5',family='near_correct',question='只解释给定资料的单一N-1故障分析要求。',
             units=[('contingencies','资料要求N-1失去一个元件后，系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内，且N-1条件适用于稳态与稳定要求。')],reference=['supported']),
        dict(id='A6',family='near_correct',question='只说明给定资料中短线路无功传输关系的前提和相关量，不计算数值。',
             units=[('line_model','在忽略线路电阻R和电容B的短输电线路模型中，资料把无功传输表示为两端电压、相角差与线路电抗相关的关系。')],reference=['supported']),
        dict(id='A7',family='mixed_insufficient',question='按资料解释动态资源特性，并核对是否能据此保证匿名厂站所有故障后均电压稳定。',
             units=[('resources','资料中的动态无功资源可在规定电压带宽内随电网电压变化自动实时连续调节。'),('resources','因此匿名厂站只要采用动态无功资源，就能保证所有故障后电压稳定。')],reference=['supported','insufficient_evidence']),
        dict(id='A8',family='mixed_insufficient',question='按资料说明输配边界负荷建模，并核对某匿名变压器的额定容量是否可由此确定。',
             units=[('coordination','输配边界负荷在资料中显式建模为MW与Mvar。'),('coordination','因此该匿名变压器的实际额定容量确定为100MVA。')],reference=['supported','insufficient_evidence']),
    ]
    B=[
        dict(question='按给定NERC资料比较动态与静态无功资源的调节方式、运行方式和电压依赖。',sources=['resources'],requirements=['动态在规定带宽内实时连续自动调节、设定点或下垂','静态额定电压固定贡献、平方依赖、按系统条件投切；不写恒定实际出力']),
        dict(question='按给定NERC资料解释输配边界负荷怎样建模，以及负荷功率因数与双方无功支撑协调有什么关系。',sources=['coordination'],requirements=['MW/Mvar显式建模及两类位置','负荷功率因数影响电压/无功，双方不应过度单向依赖、需协调']),
        dict(question='按给定NERC资料分别说明N-1与选定N-2的要求；无操作员干预这一限定在所给段落中具体绑定哪种工况？',sources=['contingencies'],requirements=['N-1立即、无操作员干预、限值/稳态稳定','选定N-2等另外说明，不把N-1限定无据扩展至N-2']),
        dict(question='按给定NERC资料说明短线路无功传输关系用了哪些建模前提、受哪些量影响；不要做数值计算或推广到任意长线路。',sources=['line_model'],requirements=['忽略R和B、短线路','电压/相角/电抗相关及相对影响，保持来源范围']),
        dict(question='按给定NERC资料，正常母线电压是否就能证明电压稳定？解释资料能够支持的判断及故障分析边界。',sources=['locality','contingencies'],requirements=['正常电压不能单独作为完整稳定证明','正常/故障工况及足够无功资源，保留所需研究边界，不编造已完成研究']),
        dict(question='按给定NERC资料，动态资源的调节特性是否足以确定匿名厂站的补偿容量并保证故障后电压稳定？给出有据解释和具体资料缺口。',sources=['resources','contingencies'],requirements=['解释动态特性','不能仅据类型确定容量或稳定保证；具体缺口和未执行分析保留，不拒掉有用解释']),
    ]
    return dict(version='production-review-v2-materials',sources=sources,A=A,B=B,
        source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        reference_origin='AI-assisted direct-source development references under user supervision; not expert gold, independent holdout or general accuracy',
        coverage_rule='Whole answer coverage scored separately against question requirements; each citation evaluated only against its bound substring, each fact against complete frozen proposition.',
        ambiguity_rule='Source silence about N-2 no-operator condition means insufficient support, not opposite engineering truth. A4 preserves-R/B contradicts explicit neglecting; arbitrary length is insufficient. No labels changed after prediction.')


def order():
    rows=[]
    for i in range(8):
        for v in (('production','scope_v2') if i%2==0 else ('scope_v2','production')):rows.append(dict(id=f'A{i+1}-{v}',input=dict(line='A',case=i,variant=v)))
    for i in range(6):
        rows.append(dict(id=f'G{i+1}',input=dict(line='G',case=i,variant='production')))
        for v in (('production','scope_v2') if i%2==0 else ('scope_v2','production')):rows.append(dict(id=f'B{i+1}-{v}',input=dict(line='B',case=i,variant=v)))
    return rows


def request(m,i,*,draft=False):
    case=m['A' if draft else 'B'][i]
    keys=list(dict.fromkeys(x[0] for x in case['units'])) if draft else case['sources']
    evidence=tuple(restore_evidence(m['sources'][k]) for k in keys)
    answer=None
    if draft:
        value=dict(answer_units=[dict(kind='technical',text=text,evidence_ids=[m['sources'][source]['evidence_id']]) for source,text in case['units']],assumptions=[],missing_information=[])
        answer=assemble(value,'fixed-review-v2-'+str(i+1),1,evidence)
    return TaskRequest(('fixed-' if draft else 'natural-')+str(i+1),TaskMode.ASSESS_EXISTING if draft else TaskMode.QUESTION_ANSWER,
        'voltage_stability_reactive_support',case['question'],user_context='仅依据实际给定资料解释，不将未提供的匿名厂站记录当作已知输入。',existing_answer=answer,provided_evidence=evidence,engineering_context=EngineeringContext(goal='conceptual'))


def fixed_input(req):
    claims=parse(dict(claims=[dict(anchor_id=a['anchor_id'],proposition=a['text'],claim_type='technical_fact',components=[dict(category='technical_fact',proposition=a['text'],basis_target='technical_content',verification_obligation='technical_truth')],assertion_role='asserted',semantic_qualifiers=[]) for a in anchors(req.existing_answer)],non_claims=[]),req.existing_answer).claims
    return ReliabilityVerificationInput(req,req.existing_answer,claims,req.provided_evidence,original_evidence=req.provided_evidence)


async def task_runner(h,req,budget,**kw):
    if not req.task_id.startswith('fixed-'):return await h.run(req,budget,**kw)
    start=perf_counter();rid=kw['run_id'];inp=fixed_input(req);events=[]
    def event(component,elapsed,output=None):
        failed=bool(output and output.execution_issues)
        e=TraceEvent(uuid4().hex,datetime.now(timezone.utc).isoformat(),component,ExecutionStatus.FAILED if failed else ExecutionStatus.SUCCEEDED,(),(),elapsed,answer_version=1,state='execution_incomplete' if failed else 'completed' if output else 'validated');events.append(e)
        if h.observer:h.observer(dict(run_id=rid,state=e.state,event=e,answer=inp.answer,claims=inp.claims,stage_output=output,verification_output=output))
    event('fixed_audit_input',0)
    b=ModelBudget(budget.max_model_calls,deadline=start+budget.max_duration_seconds)
    with model_scope(b),model_invocation_scope(rid,'evidence_verification',1):out=await asyncio.wait_for(h.verification.run(inp),min(budget.max_duration_seconds,budget.step_timeout_seconds))
    elapsed=round((perf_counter()-start)*1000);event('evidence_verification',elapsed,out)
    return HarnessResult(rid,RunState.EXECUTION_INCOMPLETE if out.execution_issues else RunState.COMPLETED,RunTrace(rid,req.task_id,tuple(events)),
        termination_reason='Fixed fact/citation interfaces only; completed is execution, not approval or whole-task coverage.',execution_issues=out.execution_issues,evidence=out.evidence,duration_ms=elapsed,answer=inp.answer,model_records=out.model_records,verification_output=out)


def variants(c,v):return replace(c,fact_review_contract=v)


def freeze(*,public=None,local=None,materials_factory=None,order_factory=None,version='production-review-net-benefit-v2',additional_identity=None):
    public=public or PUBLIC;local=local or LOCAL
    rows=(order_factory or order)()
    if (public/'freeze.json').exists() or (local/'attempt.json').exists():raise ValueError('Fresh fixed batch only')
    c=ServiceConfig.from_environment()
    if any((c.verification_schema!=13,c.fact_internal_flow!='production',c.fact_review_contract!='production',c.domain_internal_flow!='production',c.revision_answer_delivery!='production')):raise ValueError('Production baseline required')
    if os.environ.get('DEEPSEEK_MODEL_ID')!='deepseek-flash':raise ValueError('Confirmed model required')
    f=ComponentFactory(c);k=f.preflight();m=(materials_factory or materials)()
    for i in range(8):fixed_input(request(m,i,draft=True))
    paths=sorted(p for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in (ROOT/folder).glob('*.py'))
    frozen=dict(version=version,owner_authorized=True,no_resume=True,configuration=config_identity(c),manifest=f.manifest(k),model='deepseek-flash',order=rows,materials_sha256=sha(m),
        files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
        budget='Original shared40/800s, finite correction and oneRevision. Each B independently deducts actual G calls/time. A fact/citation interface only; whole-task coverage separate.',
        evaluation_scope='A fixed current authored targets, no model extraction/domain/revision. B production RAG generation once then isolated complete double-review/revision on same actual delivery, no further audit retrieval. No production configuration change.',
        stop='Single final model output failure continues; shared/unknown program/config/identity/budget ownership/connection/storage stops. No replay/resume/resubmit.')
    if additional_identity is not None:frozen['additional_identity']=additional_identity
    write(local/'materials.json',m);write(local/'freeze.json',frozen);write(public/'freeze.json',frozen)
    write(public/'materials-reference.json',{k:v for k,v in m.items() if k!='sources'} | dict(sources={k:{f:e.get(f) for f in ('evidence_id','source_id','source_version','locator','provenance')} | dict(text_sha256=sha(e['text'])) for k,e in m['sources'].items()}))
    print(f'Frozen {len(rows)} slots; zero sends.',flush=True)


def execute(*,public=None,local=None,order_factory=None,variants_factory=None,result_guard=None):
    public=public or PUBLIC;local=local or LOCAL
    f=read(public/'freeze.json')
    if f!=read(local/'freeze.json') or (local/'attempt.json').exists():raise ValueError('No changed freeze or resume')
    for x in f['files']:
        if hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']:raise ValueError('Frozen source mismatch')
    m=read(local/'materials.json');c=ServiceConfig.from_environment()
    if sha(m)!=f['materials_sha256'] or config_identity(c)!=f['configuration'] or os.environ.get('DEEPSEEK_MODEL_ID')!=f['model']:raise ValueError('Frozen inputs/configuration mismatch')
    ComponentFactory(c).preflight()
    from model_adapter.deepseek import create_adapter
    write(local/'attempt.json',dict(freeze_sha256=sha(f),resume_allowed=False))
    s=asyncio.run(batch(c,m,local/'batch',create_adapter,rows=(order_factory or order)(),request_builder=request,variant_config=variants_factory or variants,task_runner=task_runner,result_guard=result_guard))
    print(json.dumps(dict(accepted=len(s['control']),unexecuted=s['unexecuted'],sends=len(s['send_log']))),flush=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['freeze']:freeze()
    elif sys.argv[1:]==['execute']:execute()
    else:raise SystemExit('freeze | execute')
