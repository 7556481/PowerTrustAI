"""Once-only 16-chain normal HTTP API comparison after frozen offline admission."""
import asyncio,json,time,threading,socket,hashlib,os
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from backend.config import ServiceConfig
from backend.serialization import wire
from backend.api import create_app
from evaluation.tantivy_acceptance_factory_v28 import AcceptanceFactory,HOME,GROUP,SPOOL
from evaluation.tantivy_accounting_v28 import FullBudget,atomic
from evaluation.fast_overlap_replay_v27 import SOURCE
import uvicorn,httpx
K='kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e'
PORTS={'sqlite':8785,'tantivy':8786}

def configure():
    # No secret file is loaded for preparation, offline fixtures or identity checks.
    with patch('backend.config.ROOT',Path('D:/PowerTrustAI')):base=ServiceConfig.from_environment()
    assert base.index_db.resolve()==SOURCE.resolve() and base.knowledge_version==K
    assert base.verification_schema==13 and base.fact_review_execution=='serial_v1' and base.budget.max_revision_rounds==1
    assert base.fact_review_contract==base.fact_internal_flow==base.domain_internal_flow==base.revision_answer_delivery=='production'
    assert base.audit_strategy=='baseline' and base.retrieval_execution_profile=='topic_v4_subject_v1' and base.execution_path=='langgraph_v1'
    return base

def fixture(factory,config):
    from fastapi.testclient import TestClient
    from tests.test_schema14_factory_flow import SyntheticProvider
    provider=SyntheticProvider();headers={'Authorization':'Bearer offline-fixture'}
    with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=provider):
        with TestClient(create_app(config,factory=factory,access_token='offline-fixture')) as client:
            response=client.post('/runs',json={'mode':'question_answer','question':'power factor voltage','engineering_context':{'goal':'conceptual'}},headers=headers);assert response.status_code==202
            rid=response.json()['run_id'];end=time.monotonic()+300
            while time.monotonic()<end:
                state=client.get('/runs/'+rid,headers=headers).json()
                if state['status'] not in ('queued','running'):break
                time.sleep(.1)
            result=client.get('/runs/'+rid+'/result',headers=headers).json();atomic(config.run_db.parent/'fixture-result-private.json',result)
            assert result['execution']['required_stages_complete'],result['execution']
            ids=[]
            for record in result.get('retrieval',[]):ids.extend(record.get('core_evidence_ids',[]))
            checked=0
            # Store payload identity must be readable through the same product endpoint.
            for evidence in result.get('snapshots',{}).get('generation',{}).get('evidence_snapshot',{}).get('evidence',[]):
                assert client.get('/runs/'+rid+'/evidence/'+evidence['evidence_id'],headers=headers).status_code==200;checked+=1
            atomic(HOME/'normal-api-offline.json',{'run_id':rid,'required_stages_complete':True,'external_model_requests':0,'offline_fixture_requests':len(provider.requests),'evidence_endpoint_checks':checked,'semantic_fixture_not_quality_measure':True})

def main():
    assert not (HOME/'live-intent.json').exists(),'No rerun of a frozen live batch'
    base=configure();old=json.loads((HOME.parent/'tantivy-product-v19/freeze.json').read_text(encoding='utf-8'));freeze=json.loads((HOME/'freeze.json').read_text(encoding='utf-8'))
    assert [SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns]==old['source_stat']
    v20=json.loads((HOME.parent/'tantivy-delivery-replay-v20/freeze.json').read_text(encoding='utf-8'));assert [SPOOL.stat().st_size,SPOOL.stat().st_mtime_ns]==v20['spool_stat']
    assert hashlib.sha256(Path('evaluation/tantivy_acceptance_v28.py').read_bytes()).hexdigest()==freeze['source_sha256']
    frozen_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('evaluation').glob('*v28.py')}
    prep=HOME/'normal-api-offline-2';prep.mkdir(exist_ok=False);c=replace(base,run_db=prep/'runs.sqlite3',token_file=prep/'token');factory=AcceptanceFactory(c,True)
    print('Native 90-shard identity/startup preparation; no model',flush=True);tick=time.monotonic();factory.prepare();print('Native prepared',round(time.monotonic()-tick,3),flush=True)
    # Reuse exactly this accepted native reader after zero-paid normal API fixture.
    # TestClient lifespan would close it; temporarily retain the service-owned reader.
    normal_close=factory.close
    async def retain():return None
    factory.close=retain
    fixture(factory,c)
    factory.close=normal_close
    native,reader=factory.native,factory.candidate_reader;factory.native=None
    for port in PORTS.values():
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    gate=FullBudget(HOME/'accounting',cap=240,threshold=4000000);assert not gate.state['calls'];gate.save()
    configs={route:replace(base,run_db=HOME/'live'/route/'runs.sqlite3',token_file=HOME/'live'/route/'token') for route in PORTS}
    factories={route:AcceptanceFactory(configs[route],route=='tantivy',gate) for route in PORTS}
    factories['tantivy'].native=native;factories['tantivy'].candidate_reader=reader
    for c in configs.values():c.run_db.parent.mkdir(parents=True,exist_ok=False)
    admission={'passed':True,'source_selector_unchanged':True,'frozen56_replays':56,'offline24_deliveries':23,'all470_roots_whole_fallback':True,'source_spans_replayed':True,'ISO_complete_paragraph_at_final_boundary':True,'Q6_full_two_device_passage_preserved':True,'Q9_minimum_inputs_not_certified_retrieval_support':'Known gap; keep originals and insufficiency instructions, do not infer a specification from nearby text; judge new model bodies in real batch','character_increase_not_a_veto':True,'normal_api_fixture':True,'same_source_stats':True,'model_requests_before':0}
    atomic(HOME/'admission.json',admission)
    # Existing authorized real entry loads .env without reading/displaying its contents.
    from harness.deepseek_trial import load_project_env
    load_project_env(Path('D:/PowerTrustAI/.env'));assert os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash'
    assert configure()==base,'Real environment changed the frozen baseline configuration'
    atomic(HOME/'live-intent.json',{'started_wall':time.time(),'cases':old['cases'],'configs':{r:wire(c) for r,c in configs.items()},'ports':PORTS,'sources':frozen_files,'budget':{'requests':240,'trusted_tokens':4000000},'model':'deepseek-flash','order':'even sqlite first, odd tantivy first; once each; no refill'})
    servers=[];threads=[];clients={};records=[]
    try:
        for route,port in PORTS.items():
            app=create_app(configs[route],factory=factories[route],access_token='isolated-v28')
            server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False));thread=threading.Thread(target=server.run,daemon=True);thread.start();servers.append(server);threads.append(thread)
            end=time.monotonic()+60
            while not server.started and thread.is_alive() and time.monotonic()<end:time.sleep(.05)
            assert server.started,'Isolated product startup failed'
            clients[route]=httpx.Client(base_url=f'http://127.0.0.1:{port}',headers={'Authorization':'Bearer isolated-v28'},timeout=30,trust_env=False)
        for number,case in enumerate(old['cases']):
            order=('sqlite','tantivy') if number%2==0 else ('tantivy','sqlite')
            for route in order:
                label=case['id']+'-'+route;client=clients[route];tick=time.perf_counter();atomic(HOME/'live'/(label+'-intent.json'),{'wall':time.time(),'case':case['id'],'route':route})
                response=client.post('/runs',json={'mode':'question_answer','question':case['question'],'engineering_context':{'goal':'conceptual'}})
                atomic(HOME/'live'/(label+'-submit.json'),{'status':response.status_code,'body':response.json()});assert response.status_code==202,'Submission shared fault'
                rid=response.json()['run_id'];first=None;observations=[]
                while True:
                    result_response=client.get('/runs/'+rid+'/result');result=result_response.json();stamp=time.perf_counter();execution=result.get('execution',{})
                    versions=(result.get('answer') or {}).get('versions',[])
                    if first is None and versions and any(v.get('version')==1 and v.get('text') for v in versions):first=stamp-tick;observations.append({'kind':'first_draft_api_readable','seconds':first})
                    state=client.get('/runs/'+rid).json()
                    if state['status'] not in ('queued','running'):
                        final_response=client.get('/runs/'+rid+'/result');result=final_response.json();terminal=time.perf_counter()-tick;observations.append({'kind':'terminal_api_readable','seconds':terminal});break
                    if stamp-tick>base.budget.max_duration_seconds+60:raise RuntimeError('Shared task failed to terminate')
                    time.sleep(.1)
                atomic(HOME/'live'/(label+'-result-private.json'),result);atomic(HOME/'live'/(label+'-trace-private.json'),client.get('/runs/'+rid+'/trace').json())
                entry={'case':case['id'],'route':route,'run_id':rid,'submit_to_draft_api_readable_seconds':first,'submit_to_terminal_api_readable_seconds':terminal,'status':state['status'],'complete':bool(result['execution'].get('required_stages_complete')),'observations':observations}
                records.append(entry);atomic(HOME/'live'/'summary.json',records);print(json.dumps(entry),flush=True)
                assert not state.get('service_fault_code') and not state.get('error_code'),'Shared service/storage fault'
                gate.release_drained_chain(rid)
                assert not any(e['inflight'] for e in gate.state['entries'].values()),'Shared resources not drained'
                # Unknown usage retains conservative reservation; original rule stops new chain.
                assert not any(e.get('usage') is None for e in gate.state['entries'].values()),'Unknown usage: conservative reserve retained; batch stopped'
                for p,sha in frozen_files.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha,'Shared source identity changed'
        atomic(HOME/'live-completed.json',{'chains':len(records),'calls':gate.state['calls'],'trusted_tokens':gate.state['trusted_tokens'],'held':gate.held(),'unknown_usage':sum(e.get('usage') is None for e in gate.state['entries'].values())})
    except BaseException as exc:
        atomic(HOME/'stop.json',{'error':type(exc).__name__,'reason':str(exc) if isinstance(exc,AssertionError) else 'controlled run stopped; see private trace','completed_chains':len(records),'calls':gate.state['calls'],'trusted_tokens':gate.state['trusted_tokens'],'held':gate.held()});raise
    finally:
        for client in clients.values():client.close()
        for server in servers:server.should_exit=True
        for thread in threads:thread.join(30)
        if any(thread.is_alive() for thread in threads):atomic(HOME/'release-failure.json',{'service_thread_alive':True})
if __name__=='__main__':main()
