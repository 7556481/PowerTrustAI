"""Single fixed product API acceptance; no alternate scheduler or audit policy."""
import asyncio,json,hashlib,os,secrets,sqlite3,subprocess,time
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.api import create_app
from backend.serialization import wire
from evaluation.source_first_real_v3 import Gate
from evaluation.source_first_live_v2 import Accounted
from evaluation.natural_draft_audit_v1 import save,sha
LOCAL=ROOT/'data/runtime_local/stable-product-ten-v1'
def freeze():
    assert not LOCAL.exists(),'No overwrite or resume'
    conn=sqlite3.connect('file:'+str((ROOT/'data/runtime_local/runs.sqlite3').resolve()).replace('\\','/')+'?mode=ro',uri=True)
    history=[json.loads(r[0]) for r in conn.execute('select request from runs order by created desc')];conn.close()
    prefixes=['什么是无功功率？为什么电力系统','电压稳定性下降的表现','什么是功率因数？功率因数低','为什么远距离输电通常要提高电压','SVC和STATCOM','熔断器和断路器有什么区别','我只有新工厂的建筑面积','我家未提供型号、线路参数']
    goals=[['解释无功与电场磁场能量交换及电压支撑','补偿就地供无功，不能称其产生有功能量'],['电压持续不可控下降与崩溃风险','负荷无功需求和无功限制，区别一般瞬态波动'],['P/S；正弦条件下cosφ','同有功电压条件下低功率因数增大电流及损耗'],['同功率及功率因数时升压降流','相同线路电阻下I平方R损耗减小，不保证无条件更经济'],['SVC通过电抗/电纳调节，STATCOM电压源变流器','电压下降时能力差异须有额定和限流条件，不保证具体性能'],['熔断器熔体熔断一般需更换，断路器可分合并配保护','不作任何情况下动作快慢的普遍判断'],['建筑面积不能确定容量','设备功率、需用/同时率、运行备用及功率因数等输入'],['不能给具体无功数值并保证合格','需设备能力、线路参数、运行测量及并网约束']]
    cases=[]
    for prefix,g in zip(prefixes,goals):
        r=next(x for x in history if x.get('question','').startswith(prefix))
        cases.append(dict(question=r['question'],origin='existing product run request; seen development material',goals=g,critical_errors='反转关系、删失必要条件、无据数值或工程保证',allowed_gap='允许说明检索或来源不足；不足本身不计有用答案'))
    from evaluation.source_first_modality_v6 import material
    m=material()
    for idx,g in [(0,['TO/DP边界负荷用MW/Mvar显式表示','高压侧或变压器/等效配电阻抗之后两种位置']),(4,['GOP向TOP通知两类无功能力变化','两种情况均保留超过30分钟条件'])]:
        cases.insert(6+int(idx!=0),dict(question=m['cases'][idx]['request']['question'],origin='archived source-explanation original; seen development material',goals=g,critical_errors='来源错配、通知主体/时间/建模位置颠倒或遗漏',allowed_gap='无足够NERC原文则明确不足；不能凭一般常识算文献回答',source_required='NERC archived original document'))
    for i,r in enumerate(cases,1):r.update(id=f'Q{i}',category='概念' if i<=4 else '条件/设备区别' if i<=6 else '文献依据' if i<=8 else '缺少输入')
    c=ServiceConfig.from_environment();assert os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash'
    assert (c.verification_schema,c.audit_strategy,c.fact_review_contract,c.fact_review_execution,c.retrieval_execution_profile)==(13,'baseline','production','serial_v1','topic_v4_subject_v1')
    c=replace(c,run_db=LOCAL/'runs.sqlite3',token_file=LOCAL/'access-token')
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ('backend','agents','harness','services','rag','model_adapter','core') for p in (ROOT/d).glob('*.py')}
    identity=dict(version='stable-product-ten-v1',base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),configuration=wire(c),sources=sources,index_stat=dict(bytes=c.index_db.stat().st_size,mtime_ns=c.index_db.stat().st_mtime_ns),cases=cases,budget=dict(requests=160,trusted_usage_stop=3000000,per_chain_existing_gate=20,per_task=wire(c.budget),unknown_usage='stop new requests; preserve pending; no fabricated billing bound'),scoring='AI辅助、用户监督的开发复核；非专家金标准、非独立保留集。执行完整与有用有据分别逐项评分。每题一次，无补槽。',stop='共享存储/身份/资源未释放/未知usage预算不可控停批；局部合同失败释放后继续')
    LOCAL.mkdir(parents=True);save(LOCAL/'freeze.json',identity)
    print('Frozen 10 original questions; no submissions',flush=True)
    return c,identity
async def execute(c,f):
    import uvicorn,httpx
    assert not (LOCAL/'attempt.json').exists(),'No replay'
    save(LOCAL/'attempt.json',dict(freeze_sha=sha(f),start=time.time(),no_resume=True))
    gate=Gate(LOCAL/'accounting');gate.cap=160;gate.threshold=3000000
    from model_adapter.deepseek import create_adapter as provider
    class Factory(ComponentFactory):
        def create(self,rid,observer):
            def build(settings,**kw):
                delegate=Accounted(provider(settings,**kw),gate)
                class Boundary:
                    @property
                    def _active(self):return delegate._active
                    def close(self):return delegate.close()
                    async def complete(self,r):
                        gate(dict(case=rid,variant='product'),r,gate.calls+1)
                        return await delegate.complete(r)
                return Boundary()
            with patch('model_adapter.deepseek.create_adapter',side_effect=build):return super().create(rid,observer)
    token=secrets.token_hex(32);factory=Factory(c);server=None
    app=create_app(c,factory=factory,access_token=token,shutdown=lambda:setattr(server,'should_exit',True))
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8775,access_log=False,log_level='warning'))
    start=time.monotonic();task=asyncio.create_task(server.serve());rows=[]
    try:
        while not server.started:
            if task.done():await task;raise RuntimeError('Service failed before acceptance')
            await asyncio.sleep(.1)
        save(LOCAL/'startup.json',dict(seconds=time.monotonic()-start,process_seal_separate=True,manifest=factory.manifest(c.knowledge_version)))
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8775',headers={'Authorization':'Bearer '+token},timeout=30,trust_env=False) as client:
            for case in f['cases']:
                for p,h in f['sources'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'Frozen source changed'
                assert c.index_db.stat().st_mtime_ns==f['index_stat']['mtime_ns'],'Index changed'
                health=(await client.get('/health')).json()
                assert health['status']=='ready' and not health['active_run'] and not health['queued'],'Shared lifecycle fault'
                if gate.stopped:break
                t=time.monotonic();save(LOCAL/(case['id']+'-submission-intent.json'),dict(case=case['id'],time=time.time()))
                response=await client.post('/runs',json=dict(mode='question_answer',question=case['question'],engineering_context=dict(goal='conceptual')))
                save(LOCAL/(case['id']+'-submission.json'),dict(status=response.status_code,response=response.json()))
                response.raise_for_status();rid=response.json()['run_id'];first=None
                while True:
                    result=(await client.get('/runs/'+rid+'/result')).json()
                    if first is None and (result.get('answer',{}).get('final') or result.get('answer',{}).get('original')):first=time.monotonic()-t
                    state=(await client.get('/runs/'+rid)).json()
                    if state['status'] not in ('queued','running'):break
                    await asyncio.sleep(.5)
                ended=time.monotonic()-t
                for _ in range(220):
                    h=(await client.get('/health')).json()
                    if not h['active_run']:break
                    await asyncio.sleep(.5)
                assert not h['active_run'] and h['status']=='ready' and not h['queued'],'Release/storage fault'
                result=(await client.get('/runs/'+rid+'/result')).json();save(LOCAL/(case['id']+'-result.json'),result)
                raw=app.state.service.store.get(rid);save(LOCAL/(case['id']+'-stored.json'),raw)
                row=dict(id=case['id'],run_id=rid,first_answer_observed_seconds=first,terminal_observed_seconds=ended,total_seconds=time.monotonic()-t,observation='0.5s polling; actual browser paint unknown',execution=state,calls=gate.calls,tokens=gate.tokens,pending=sorted(gate.pending));rows.append(row);save(LOCAL/'progress.json',rows)
                print(case['id']+': '+state['status']+'; calls='+str(gate.calls)+' tokens='+str(gate.tokens),flush=True)
                if gate.pending or gate.stopped:break
    finally:
        save(LOCAL/'totals.json',dict(rows=rows,calls=gate.calls,trusted_tokens=gate.tokens,pending=sorted(gate.pending),stopped=gate.stopped,unsubmitted=[x['id'] for x in f['cases'] if x['id'] not in {r['id'] for r in rows}],billing_amount=None))
        server.should_exit=True;await task
if __name__=='__main__':
    c,f=freeze();asyncio.run(execute(c,f))
