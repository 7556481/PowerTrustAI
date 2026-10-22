"""Exactly six authorized service runs, single admission each, no resume."""
import argparse,json,hashlib,os,time,secrets,sqlite3
from pathlib import Path
from dataclasses import replace,asdict
from unittest.mock import patch
from contextlib import closing
from backend.config import ServiceConfig,ROOT
from backend.assembly import ComponentFactory
from backend.api import create_app
from backend.store import RunStore
from backend.serialization import wire
from fastapi.testclient import TestClient
from evaluation.public_review_validation_trial_v1 import write,read,sha,assert_no_evaluator_keys

PUBLIC=ROOT/'docs/evaluation/langgraph-service-integration-v1'
LOCAL=ROOT/'data/evaluation_local/langgraph-service-integration-v1/batch-v1'
PRIVATE=ROOT/'data/retrieval_local/langgraph-service-integration-v1/batch-v1'
ORDER=(('LSI-01-S','LSI-01','sequential'),('LSI-01-G','LSI-01','langgraph_v1'),
       ('LSI-02-G','LSI-02','langgraph_v1'),('LSI-02-S','LSI-02','sequential'),
       ('LSI-03-S','LSI-03','sequential'),('LSI-03-G','LSI-03','langgraph_v1'))

def tasks():
    old=read(ROOT/'docs/evaluation/generation-mapping-comparison-v1/tasks-v1.json')
    source=old['tasks'][0]['evidence'][0]
    common={'local_nli_enabled':False,'engineering_context':{'goal':'conceptual'},'user_context':'只解释给定归档文献，不判断实际天气。',
        'references':[{'label':source['locator'],'text':source['text']}],
        'answer_requirements':['请用中文直接回答，正文不超过120字；保留必要条件，不附加无关保证。']}
    return {
      'LSI-01':{**common,'mode':'question_answer','question':'根据给定NWS文献，可测降水的阈值是多少？保留原单位，仅解释该定义。'},
      'LSI-02':{'mode':'question_answer','question':'某匿名厂站未提供网络模型、当前运行点及限值。能否据此确定该厂站无功补偿容量？请简洁说明必要资料缺口，不编造参数或具体容量。',
          'user_context':'没有提供厂站记录、网络模型或工况数据，只询问当前资料是否足够。','local_nli_enabled':False,
          'engineering_context':{'goal':'plant_assessment'},'answer_requirements':['中文正文不超过120字；明确说明缺口，不编造数值或保证。']},
      'LSI-03':{**common,'mode':'assess_existing','question':'根据给定NWS文献，指出并修正下面可测降水阈值中的局部错误，保留文献定义范围。',
          'existing_answer':'给定NWS文献将可测降水定义为达到或超过0.1英寸；这里仅指文献定义，不判断实际天气。'}}

def config_identity(c):
    value=wire(c)
    for k in ('run_db','token_file'):value.pop(k,None)
    return value

def saved_result(database,run_id):
    """Collection-only: a separate read-only connection, never the worker handle."""
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        row=db.execute('SELECT result FROM runs WHERE id=?',(run_id,)).fetchone()
        if row is None:raise ValueError('Accepted run not found')
        return None if row[0] is None else json.loads(row[0])

def prepare():
    if LOCAL.exists() or (PUBLIC/'execution-freeze-v1.json').exists():raise ValueError('Fresh fixed batch only')
    c=ServiceConfig.from_environment();factory=ComponentFactory(c);k=factory.preflight();m=factory.manifest(k)
    if c.profile!='real' or c.verification_schema!=13 or c.decision_policy!='product-v1':raise ValueError('Confirmed production configuration required')
    paths=set()
    for name in ('backend','agents','core','harness','rag','services','model_adapter','tools'):
        paths.update((ROOT/name).glob('*.py'))
    paths.update((ROOT/'backend/static').glob('*'))
    paths.update((Path(__file__).resolve(),ROOT/'evaluation/batch_control.py',ROOT/'evaluation/public_review_validation_trial_v1.py',ROOT/'evaluation/public_review_validation_materials_v1.py',ROOT/'tests/test_langgraph_service_integration_v1.py',ROOT/'tests/test_langgraph_service_trial_v1.py'))
    frozen={'version':'langgraph-real-service-integration-v1','owner_authorized':True,'source_base_commit':'1779b157fe78f333762b5bdb0a41cea88e87c0c4',
        'order':[{'id':ident,'task_id':task,'execution_path':path,'payload_sha256':sha(tasks()[task])} for ident,task,path in ORDER],
        'configuration':config_identity(c),'manifest':m,'model_id':os.environ.get('DEEPSEEK_MODEL_ID'),
        'budget':wire(c.budget),'extra_batch_cap':None,'max_revision_rounds':1,
        'semantic_scope':'Existing development material, not independent eval; live differences not orchestration causality.',
        'stop':'First final execution, required audit, storage/config failure stops further paid sends; no resubmit/resume.',
        'bound_files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths) if p.is_file()]}
    write(PUBLIC/'execution-freeze-v1.json',frozen);write(LOCAL/'freeze.json',frozen)
    write(LOCAL/'payloads.json',tasks())
    print('Six service payload/config identities frozen; no paid attempt yet',flush=True)

def execute():
    freeze=read(PUBLIC/'execution-freeze-v1.json')
    if freeze!=read(LOCAL/'freeze.json') or (LOCAL/'attempt.json').exists():raise ValueError('No resume or changed freeze')
    for x in freeze['bound_files']:
        if hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']:raise ValueError('Frozen file mismatch')
    c=ServiceConfig.from_environment()
    if config_identity(c)!=freeze['configuration'] or os.environ.get('DEEPSEEK_MODEL_ID')!=freeze['model_id']:raise ValueError('Frozen production config mismatch')
    if tasks()!=read(LOCAL/'payloads.json'):raise ValueError('Payload identity changed')
    write(LOCAL/'attempt.json',{'authorization':'Explicit user six-run DeepSeek authorization; no added cases','freeze_sha256':hashlib.sha256((PUBLIC/'execution-freeze-v1.json').read_bytes()).hexdigest()})
    from model_adapter.deepseek import create_adapter as provider_factory
    from model_adapter.runtime import current_model_invocation
    result=[];stopped=False
    for ident,tid,path in ORDER:
        if stopped:
            result.append({'id':ident,'status':'unexecuted','execution_path':path,'reason':'stopped_after_previous_final_failure'});continue
        started=time.perf_counter();state={'sent':[],'fatal':False};run_id=None;raw=None
        directory=LOCAL/ident
        class Guard:
            def __init__(self,delegate):self.delegate=delegate
            @property
            def _active(self):return self.delegate._active
            def close(self):self.delegate.close()
            async def complete(self,request):
                if state['fatal']:raise RuntimeError('Pre-send storage/gate failed')
                rows=[asdict(m) for m in request.messages]
                try:
                    if request.model_id!=freeze['model_id'] or request.max_output_tokens!=8000:raise ValueError('Model changed')
                    if any(s in request.prompt_version for s in ('premise-boundary','object-boundary','generation-map')):raise ValueError('Development candidate forbidden')
                    for row in rows:
                        if row['role']=='user':
                            try:value=json.loads(row['content'])
                            except ValueError:continue
                            assert_no_evaluator_keys(value)
                    number=len(state['sent'])+1
                    item={'id':ident,'sequence':number,'prompt_version':request.prompt_version,'correction':request.correction,
                          'invocation':current_model_invocation(),'messages':rows,'messages_sha256':sha(rows),'elapsed_before_send':time.perf_counter()-started}
                    write(PRIVATE/ident/f'before-send-{number:03d}.json',item)
                    state['sent'].append({k:v for k,v in item.items() if k!='messages'})
                except Exception:
                    state['fatal']=True
                    from evaluation.public_review_validation_trial_v1 import PreSendStorageFailure
                    raise PreSendStorageFailure({'stage':'pre_send','field_path':'messages','constraint':'frozen_gate_or_storage_failure'}) from None
                return await self.delegate.complete(request)
        try:
            cfg=replace(c,execution_path=path,run_db=LOCAL/'runs.sqlite3',token_file=LOCAL/'unused-token')
            factory=ComponentFactory(cfg);token=secrets.token_urlsafe(32)
            with patch('model_adapter.deepseek.create_adapter',side_effect=lambda settings:Guard(provider_factory(settings))):
                with TestClient(create_app(cfg,factory=factory,access_token=token)) as client:
                    h={'Authorization':'Bearer '+token}
                    response=client.post('/runs',json=tasks()[tid],headers=h)
                    if response.status_code!=202:raise RuntimeError('Service admission failed')
                    run_id=response.json()['run_id'];write(directory/'accepted.json',{'run_id':run_id,'id':ident,'execution_path':path})
                    print(ident+': accepted '+run_id,flush=True)
                    while True:
                        progress=client.get('/runs/'+run_id,headers=h).json()
                        if progress['status'] not in ('queued','running'):break
                        time.sleep(.2)
                    projected=client.get('/runs/'+run_id+'/result',headers=h).json()
                    raw=saved_result(cfg.run_db,run_id)
                    write(directory/'raw-result.json',raw);write(directory/'api-result.json',projected)
                    write(directory/'trace.json',client.get('/runs/'+run_id+'/trace',headers=h).json())
                    if not raw or raw['execution_issues'] or raw['state'] in ('failed','cancelled','execution_incomplete') or projected['execution']['error_code'] or state['fatal']:
                        stopped=True
                    for output in ('verification_output','domain_output'):
                        if (raw.get(output) or {}).get('execution_issues'):stopped=True
                    # Drain already sent work before another admission; never repeat a request.
                    while client.app.state.service.active is not None:time.sleep(.1)
            item={'id':ident,'task_id':tid,'execution_path':path,'run_id':run_id,'status':'execution_failed' if stopped else 'complete',
                  'elapsed_seconds':time.perf_counter()-started,'sent':state['sent'],'result':raw}
            write(directory/'observations.json',{k:v for k,v in item.items() if k!='result'});result.append(item)
            print(ident+': '+item['status']+', sent='+str(len(state['sent'])),flush=True)
        except BaseException as exc:
            stopped=True;item={'id':ident,'execution_path':path,'run_id':run_id,'status':'execution_failed','exception_type':type(exc).__name__,'result':raw,'sent':state['sent']}
            write(directory/'entry-failure.json',{k:v for k,v in item.items() if k!='result'});result.append(item)
    write(LOCAL/'summary.json',{'version':'langgraph-real-service-integration-v1','branches':result})
    print(json.dumps([{k:b.get(k) for k in ('id','status','run_id')} for b in result]),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','execute'));a=p.parse_args()
    prepare() if a.action=='prepare' else execute()
