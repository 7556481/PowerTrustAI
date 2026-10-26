"""One authorized fixed Flash batch. Reuses shared.batch/run_fixed, no resumption."""
import asyncio,json,os,subprocess
from dataclasses import replace
from pathlib import Path
from time import monotonic
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation import answer_review_net_benefit_v1 as shared
from evaluation import production_review_v2 as old
from evaluation.strict_interface_probe_v1 import load,save,digest

VERSION='literal-review-stage1-v1'
LOCAL=ROOT/'data/retrieval_local'/VERSION
PUBLIC=ROOT/'docs/evaluation'/VERSION


def materials():
    m=old.materials()
    cases=[
        dict(id='LR-A1-v1',family='obligation',question='按给定资料说明输配边界负荷的建模位置、双方无功支撑关系，以及确定关键负荷水平的建议负荷功率因数时协调的地位。',
            units=[('coordination','输配边界负荷通常显式建模为MW和Mvar，可位于母线高压侧，或降压变压器及等效配电阻抗之后。'),('coordination','资料明确规定：在确定峰荷和轻载等关键负荷水平的建议负荷功率因数时，TO与DP之间的协调是必须履行的强制义务。负荷不应过度依赖BES的无功支撑，BES也不应仅依赖负荷提供无功支撑。')],
            target='important被增强为强制义务；仅纠正该义务强度，不否定协调的重要性或擅自认定无需协调',requirements=['MW/Mvar及两类位置','协调对关键负荷水平的建议LPF重要','双方不应过度单向依赖'],preserve=['两种建模位置','双向依赖限制'],kind='repairable_error'),
        dict(id='LR-A2-v1',family='condition_owner',question='按给定资料分别解释N-1、选定N-2及极端扰动要求，明确无操作员干预限定的归属。',
            units=[('contingencies','N-1指失去一个元件，要求系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内，且用于稳态与稳定要求。'),('contingencies','资料又要求系统承受选定的N-2故障；这里的每一种选定N-2故障，均被原文明确要求在无操作员干预下立即满足上述紧急热额定值和电压限值。系统还应承受更严重但较不可能的极端扰动，避免电压崩溃、级联或失稳。')],
            target='明确把N-1的无干预/立即限值移给每个选定N-2；应删除该无据扩张，保留选定N-2与极端扰动并列要求',requirements=['N-1立即/无干预/限值/稳态稳定','选定N-2','极端扰动及避免崩溃级联失稳'],preserve=['首单元N-1','选定N-2及极端扰动'],kind='repairable_error',parent_note='旧B3有主语歧义，本稿另立身份，明确每一种选定N-2；不改旧标签'),
        dict(id='LR-A3-v1',family='necessary_qualifier',question='按给定资料解释动态无功资源调节的电压适用范围、方式及两种运行方式。',
            units=[('resources','动态无功资源在任何电网电压下都能响应电压变化，自动、实时、连续调节无功输出，不受指定电压带宽限制；可维持电压设定点或按电压下垂模式运行。'),('resources','静态无功资源在额定电压下贡献固定，其能力随电压平方变化，可按系统条件手动或自动投切。')],
            target='指定电压带宽是必要限定，不能改成任何电压且不受带宽限制',requirements=['指定电压带宽','自动实时连续','设定点或下垂'],preserve=['两种运行方式','静态资源正确解释'],kind='repairable_error'),
        dict(id='LR-A4-v1',family='causal_dependence',question='解释给定短线路无功传输关系的前提、相关量及相角差与电压差/阻抗的相对影响，并据此说明资料为何将电压与无功控制紧密联系。不要数值计算。',
            units=[('line_model','在忽略线路电阻R和电容B的短输电线路模型中，无功传输与两端电压、相角差和线路电抗有关。'),('line_model','资料指出相角差是最强的驱动量，而电压差和阻抗的影响相对很小。'),('line_model','因此，该资料把无功控制主要归结为相角差控制，电压控制与无功控制并不紧密耦合。')],
            target='相对影响颠倒，及由此前提推出不紧密耦合的直接依赖结论；二者须同时纠正',requirements=['短线路/忽略R和B','相关量','相角差相对小而电压差/阻抗更强','电压与无功控制紧密耦合'],preserve=['首单元模型前提与变量'],kind='repairable_error'),
        dict(id='LR-A5-v1',family='correct_equivalence',question='按给定资料概括动态与静态无功资源的特性。',
            units=[('resources','在规定电压带宽内，动态无功资源能随电网电压改变而自动、实时地连续调整输出；它可以守住电压设定点，也可以按电压下垂方式运行。'),('resources','静态无功资源在额定电压下给出固定的额定贡献，能力则随电压平方变化；按系统条件手动或自动接入、退出。')],target=None,requirements=['带宽/自动实时连续/两种方式','静态额定贡献/平方/投切'],preserve=['全部正确含义和必答点'],kind='correct_protection'),
        dict(id='LR-A6-v1',family='distributed_context',question='只解释资料中的短线路模型前提及其无功关系，不推广到任意长度线路。',
            units=[('line_model','以下解释仅限给定资料忽略线路电阻R和电容B的短输电线路模型。'),('line_model','在上述模型中，无功传输与电压差、相角差及电气阻抗有关；相角差影响相对较小，电压差与阻抗则是更强的驱动量，因此电压控制与无功控制紧密耦合。')],target=None,requirements=['上下文明确绑定短线路及忽略R/B','相关量与相对影响','耦合'],preserve=['跨句前提的正确归属'],kind='correct_protection'),
        dict(id='LR-A7-v1',family='multiunit_correct',question='按给定资料说明输配边界负荷的建模、负荷功率因数的影响与双方支撑协调。',
            units=[('coordination','边界通常用MW和Mvar显式负荷建模，可放在母线高压侧，或降压变压器及等效配电阻抗之后。'),('coordination','边界建模采用的负荷功率因数会影响BES的电压与无功表现；在峰荷、轻载等关键负荷水平确定建议LPF时，TO与DP间的协调很重要。'),('coordination','负荷不应过度依赖BES的无功支撑，反向而言BES也不应仅依赖负荷的无功支撑。')],target=None,requirements=['两类位置','LPF影响电压和无功','协调重要','双方依赖限制'],preserve=['全部三个单元'],kind='correct_protection'),
        dict(id='LR-A8-v1',family='insufficient',question='按资料解释动态无功资源的调节特性；另核验所给资料是否足以确定匿名变压器的实际额定容量。',
            units=[('resources','动态无功资源在指定电压带宽内响应电网电压变化，自动实时连续调节，可维持设定电压或按电压下垂方式运行。'),('resources','该匿名变压器的实际额定容量为100MVA。')],target='没有匿名设备资料，100MVA无支持但不存在可据此确定实际容量的反证或可填数值；保留有用资源解释并合理未解决',requirements=['动态特性','不能据此确定匿名容量，不编数值'],preserve=['第一单元完整解释'],kind='insufficient'),
    ]
    # Prediction-before clarifications, new identities only; old references untouched.
    cases[1]['units'][1]=('contingencies',cases[1]['units'][1][1].replace('资料又要求系统承受选定的N-2故障；','在确定稳定极限时，资料又要求系统承受选定的N-2故障；'))
    cases[1]['requirements'][1]='确定稳定极限时的选定N-2'
    cases[4]['units'][0]=('resources',cases[4]['units'][0][1].replace('它可以守住电压设定点','它可以以维持电压设定点为运行目标'))
    natural=[dict(m['B'][i]) for i in (0,1,2,3)]
    natural[1]['requirements']=['MW/Mvar显式建模及两类位置','负荷功率因数影响电压/无功，双方不应过度单向依赖；协调很重要，不增强为强制义务']
    return dict(version=VERSION,sources=m['sources'],A=cases,B=natural,
        reference_origin='AI-assisted construction and direct source review under user supervision; NOT individually owner-confirmed labels, expert gold or independent holdout',
        identities='New authored drafts, no historical generation snapshot; old references/results unchanged.',
        source_archive_sha256=m['source_archive_sha256'],allowed='Equivalent correct expression, no fixed-answer string score. Correct content/required points preserved; mixed results separate.')


def order():
    rows=[]
    for line,n in (('A',8),('B',4)):
        for i in range(n):
            if line=='B':rows.append(dict(id=f'G{i+1}',input=dict(line='G',case=i,variant='production')))
            for v in (('production','literal_v1') if i%2==0 else ('literal_v1','production')):rows.append(dict(id=f'{line}{i+1}-{v}',input=dict(line=line,case=i,variant=v)))
    return rows


def request(m,i,*,draft=False):
    r=old.request(m,i,draft=draft)
    return replace(r,task_id='literal-stage1-'+r.task_id,existing_answer=replace(r.existing_answer,answer_id='literal-stage1-A'+str(i+1)) if draft else None)


def variants(c,v):return replace(c,fact_review_contract='literal_v1') if v=='literal_v1' else c
def budget_for(spec,b):return replace(b,max_model_calls=2) if spec['line']=='G' else b


class SendLimit:
    def __init__(self,path,*,clock=monotonic):self.path=path;self.clock=clock;self.started=None;self.used=0;self.by_chain={}
    def remaining_seconds(self):return max(.001,21600-(self.clock()-self.started))
    def __call__(self,spec,r,n):
        now=self.clock()
        if self.started is None:self.started=now
        if r.model_id!='deepseek-flash' or r.max_output_tokens>8000:raise ValueError('Frozen Flash settings mismatch')
        key=spec['line']+str(spec['case'])+'-'+spec['variant'];used=self.by_chain.get(key,0)
        cap=2 if spec['line']=='G' else 24
        if self.used>=584 or now-self.started>=21600 or used>=cap:raise RuntimeError('Frozen batch send boundary reached')
        self.used+=1;self.by_chain[key]=used+1
        save(self.path.parent/self.path.stem/f'{self.used:04d}.json',dict(used=self.used,by_chain=self.by_chain,elapsed_seconds=now-self.started,maximum=584))


class Gate:
    def __call__(self,spec,raw):
        if any(x.get('code') in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CANCELLED','CANCELLED') for x in raw.get('execution_issues',[])):
            return dict(component='harness',code='SERVICE_EXECUTION_FAILED',message='Timeout/cancellation: conservative shared stop; no paid recovery.')
        return None


def source_files():return [dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p.read_bytes())) for folder in ('agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools') for p in sorted((ROOT/folder).glob('*.py'))]


async def run():
    from harness.deepseek_trial import load_project_env
    load_project_env();c=ServiceConfig.from_environment()
    assert os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash'
    assert (c.verification_schema,c.fact_review_contract,c.review_result_transport,c.fact_internal_flow,c.domain_internal_flow,c.revision_answer_delivery,c.extraction_message_profile,c.execution_path)==(13,'production','json','production','production','production','production','langgraph_v1')
    assert not (LOCAL/'attempt.json').exists() and not (LOCAL/'freeze.json').exists(),'No resume, replacement freeze or second batch'
    # Dedicated per-run caps; saved production config remains unchanged.
    c=replace(c,budget=replace(c.budget,max_model_calls=24,max_duration_seconds=800,max_revision_rounds=1))
    fct=ComponentFactory(c)
    try:
        k=fct.preflight();m=materials()
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        f=dict(version=VERSION,code_commit=commit,source_base_commit='b6c73daf1ba9b18ce8d9dc951ee3c5c1d77af9fe',sources=source_files(),
            configuration=shared.frozen_config(c),production_manifest=fct.manifest(k),candidate_manifest=ComponentFactory(variants(c,'literal_v1')).manifest(k),
            materials_sha256=shared.sha(m),order=order(),model='deepseek-flash',plan=dict(A=16,G=4,B=8,logical_slots=28,audit_chains=24),
            budget=dict(audit=24,generation=2,total=584,chain_seconds=800,batch_seconds=21600,output_tokens=8000,business_revision=1),
            evidence='Same authored draft or single generated draft and its actual delivery for both branches; fixed audit seam, no later retrieval. Original citation scopes separate.',
            messages='Constructors/parsers frozen; every actual initial/correction/rereview message is hashed before its send, never predict dynamic hashes.',
            failures=dict(local='Final MODEL_OUTPUT_ERROR or clear per-chain quota: retain, continue independent slots',shared='Configuration/input/parser bug/ownership/storage/auth/service/network/timeout/unknown: stop all new sends',business='Bad semantics or retained/unresolved: retain and continue; no admission selection',global_limit='stop new sends; all remaining slots retained unexecuted'),
            no_resume=True,references='AI-assisted supervised development, no paid judge, no post-prediction changes')
        save(LOCAL/'materials.json',m);save(LOCAL/'freeze.json',f);save(PUBLIC/'freeze.json',f)
        save(PUBLIC/'materials-reference.json',{q:v for q,v in m.items() if q!='sources'}|dict(sources={q:{k:e[k] for k in ('evidence_id','source_id','source_version','locator')}|dict(text_sha256=digest(e['text'].encode())) for q,e in m['sources'].items()}))
        assert source_files()==f['sources']
        save(LOCAL/'attempt.json',dict(freeze_sha256=shared.sha(f),resume_allowed=False))
        from model_adapter.deepseek import create_adapter
        s=await shared.batch(c,m,LOCAL/'batch',create_adapter,rows=order(),request_builder=request,variant_config=variants,
            result_guard=Gate(),fixed_audit_delivery=True,budget_for=budget_for,send_guard=SendLimit(LOCAL/'send-ledger.json'),local_issue_codes=('MODEL_CALL_BUDGET_EXHAUSTED',))
        print(json.dumps(dict(executed=len(s['control']),unexecuted=s['unexecuted'],sends=len(s['send_log']))),flush=True)
        return s
    finally:await fct.close()


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['run']:asyncio.run(run())
    else:raise SystemExit('run once; no resume')
