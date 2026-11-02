"""One frozen two-port product API comparison; no alternate Harness or replay."""
import asyncio,hashlib,json,os,secrets,subprocess,time
from dataclasses import replace
from pathlib import Path
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from backend.api import create_app
from backend.serialization import wire
from model_adapter.call_budget_v1 import shared_gate,BudgetStop
from rag.tantivy_build import atomic
from rag.tantivy_manifest import sha
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K

LOCAL=Path('D:/PowerTrustAI/data/runtime_local/tantivy-full-fast-v1/comparison')
CODE=Path(__file__).resolve().parents[1]
def code_identity():
 return {str(p.relative_to(CODE)):sha(p) for d in ('backend','agents','harness','services','rag','model_adapter','core') for p in (CODE/d).rglob('*') if p.is_file() and p.suffix in ('.py','.js','.html','.css')}
def freeze():
 if LOCAL.exists():raise RuntimeError('Comparison directory exists; no repeat freeze')
 approval_file=ROOT/'offline-approved.json';approval=json.loads(approval_file.read_text(encoding='utf8'));manifest=ROOT/'accepted/manifest.json'
 if not approval.get('known_critical_coverage_addressed') or not approval.get('no_new_critical_regression') or not approval.get('engineering_passed') or approval.get('wide_median_ratio',0)<1.5 or approval.get('manifest_sha256')!=sha(manifest) or approval.get('measurements_sha256')!=sha(ROOT/'full-measurements.jsonl'):raise RuntimeError('Offline release prerequisite not satisfied')
 if approval.get('implementation_sha256')!=code_identity():raise RuntimeError('Review applies to different implementation')
 plan=json.loads((ROOT/'plan.json').read_text(encoding='utf8'))
 # Existing authorized loader only; no environment or credentials are serialized.
 from harness.deepseek_trial import load_project_env
 load_project_env(Path('D:/PowerTrustAI/.env'))
 if os.environ.get('DEEPSEEK_MODEL_ID')!='deepseek-flash':raise RuntimeError('Explicit Flash environment required')
 from unittest.mock import patch
 with patch('backend.config.ROOT',Path('D:/PowerTrustAI')):c=ServiceConfig.from_environment()
 if c.index_db.resolve()!=SOURCE.resolve() or c.knowledge_version!=K or c.execution_path!='langgraph_v1' or c.tantivy_manifest is not None or c.model_budget_dir is not None:raise RuntimeError('Original managed service identity changed')
 c=replace(c,index_db=SOURCE,knowledge_version=K,nli_enabled=False,tantivy_manifest=None,tantivy_isolated=False,tantivy_worker_mode='oneshot',model_budget_dir=LOCAL/'accounting',model_budget_question_sha256=None,model_budget_owner_file=None)
 if (c.verification_schema,c.audit_strategy,c.fact_review_contract,c.fact_review_execution,c.fact_internal_flow,c.domain_internal_flow,c.local_revision_interface,c.revision_answer_delivery,c.review_result_transport,c.fact_strategy,c.retrieval_mode,c.retrieval_execution_profile,c.decision_policy,c.budget.max_revision_rounds)!=(13,'baseline','production','serial_v1','production','production','production','production','json','aggregate','bm25','topic_v4_subject_v1','product-v1',1):raise RuntimeError('Production configuration differs from authorized comparison')
 configs={name:replace(c,run_db=LOCAL/name/'runs.sqlite3',token_file=LOCAL/name/'access-token',tantivy_manifest=manifest if name=='fast' else None,tantivy_isolated=name=='fast',tantivy_worker_mode='fast_v1' if name=='fast' else 'oneshot') for name in ('baseline','fast')}
 f={'version':'full-fast-product-comparison-v1','commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'sources':code_identity(),'source_stat':[SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns],'index_manifest_sha256':sha(manifest),'offline_approval_sha256':sha(approval_file),'cases':plan['real_questions'],'smoke_question':plan['smoke_question'],'configs':{k:wire(v) for k,v in configs.items()},'ports':{'baseline':8775,'fast':8776},'budget':plan['model'],'order':'even pair baseline first, odd pair fast first; each once','poll_seconds':.5,'speed_formula':'same complete pair set: baseline terminal median minus candidate terminal median; divide by baseline median; report per-pair savings too',
 'review':'AI辅助、用户监督的开发复核；已见材料，非专家金标准或独立保留集','gates':plan['gates']}
 LOCAL.mkdir(parents=True);atomic(LOCAL/'freeze.json',f);return configs,f

async def execute(configs,f):
 import uvicorn,httpx
 if (LOCAL/'attempt.json').exists():raise RuntimeError('Batch already started; no replay or supplement')
 atomic(LOCAL/'attempt.json',{'freeze_sha256':sha(LOCAL/'freeze.json'),'started_wall':time.time()});gate=shared_gate(LOCAL/'accounting');servers={};tasks={};clients={};apps={};rows=[];stopping=None
 try:
  # Both startups complete before any paid submission, separate from per-question time.
  for name,c in configs.items():
   token=secrets.token_hex(32);factory=ComponentFactory(c);app=create_app(c,factory=factory,access_token=token);apps[name]=app
   server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=f['ports'][name],access_log=False,log_level='warning'));servers[name]=server
   started=time.monotonic();task=asyncio.create_task(server.serve());tasks[name]=task
   while not server.started:
    if task.done():await task;raise RuntimeError('Isolated service failed before comparison')
    if time.monotonic()-started>600:raise TimeoutError('Isolated startup exceeded allowance')
    await asyncio.sleep(.1)
   atomic(LOCAL/(name+'-startup.json'),{'seconds':time.monotonic()-started,'configuration':factory.manifest(K),'health_model_requests':0})
   clients[name]=httpx.AsyncClient(base_url='http://127.0.0.1:'+str(f['ports'][name]),headers={'Authorization':'Bearer '+token},timeout=30,trust_env=False)
  for i,case in enumerate(f['cases']):
   for name in (('baseline','fast') if i%2==0 else ('fast','baseline')):
    if f['sources']!=code_identity() or f['source_stat']!=[SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns] or f['index_manifest_sha256']!=sha(ROOT/'accepted/manifest.json'):raise RuntimeError('Frozen code/source/index changed')
    if gate.state['calls']>=240 or gate.state['trusted_tokens']>=4000000:raise BudgetStop('Global allowance reached')
    if any(e['inflight'] for e in gate.state['entries'].values()):raise RuntimeError('Prior model resources not proven drained')
    for client in clients.values():
     h=(await client.get('/health')).json()
     if h['status']!='ready' or h['active_run'] or h['queued'] or not h['storage_healthy']:raise RuntimeError('Shared service/store admission failed')
    label=case['id']+'-'+name;client=clients[name];tick=time.monotonic();atomic(LOCAL/(label+'-submission-intent.json'),{'case':case['id'],'backend':name,'wall':time.time()})
    response=await client.post('/runs',json={'mode':'question_answer','question':case['question'],'engineering_context':{'goal':'conceptual'}})
    atomic(LOCAL/(label+'-submission.json'),{'status':response.status_code,'response':response.json()});response.raise_for_status();rid=response.json()['run_id'];first=None
    while True:
     result=(await client.get('/runs/'+rid+'/result')).json();state=(await client.get('/runs/'+rid)).json()
     if first is None and (result.get('answer',{}).get('original') or result.get('answer',{}).get('final')):first=time.monotonic()-tick
     if state['status'] not in ('queued','running'):break
     if time.monotonic()-tick>1000:raise RuntimeError('Task not terminal within original run budget; no further submissions')
     await asyncio.sleep(.5)
    terminal=time.monotonic()-tick
    for _ in range(240):
     h=(await client.get('/health')).json()
     if not h['active_run']:break
     await asyncio.sleep(.5)
    if h['active_run'] or h['queued'] or h['status']!='ready' or not h['storage_healthy']:raise RuntimeError('Unproven drain or shared lifecycle fault')
    gate.release_drained_chain(rid)
    result=(await client.get('/runs/'+rid+'/result')).json();atomic(LOCAL/(label+'-result.json'),result);atomic(LOCAL/(label+'-trace.json'),(await client.get('/runs/'+rid+'/trace')).json());atomic(LOCAL/(label+'-stored.json'),apps[name].state.service.store.get(rid))
    fatal={'TANTIVY_IDENTITY_ERROR','RETRIEVAL_CONTRACT_ERROR','RUN_STORAGE_FAILED'}
    if any(issue.get('code') in fatal for issue in result['execution'].get('execution_issues',[])) or any(str(record.get('reason','')).startswith(('IndexIdentityError:','ContractError:','DatabaseError:','OperationalError:')) for record in result.get('retrieval',[])):raise RuntimeError('Shared source/identity/storage fault; no further submissions')
    row={'case':case['id'],'backend':name,'run_id':rid,'status':state['status'],'complete':result['execution']['required_stages_complete'],'first_answer_observed_seconds':first,'terminal_observed_seconds':terminal,'total_including_drain_seconds':time.monotonic()-tick,'observation':'0.5s API polling, browser first frame unknown','requests_admitted_cumulative':gate.state['calls'],'trusted_tokens_cumulative':gate.state['trusted_tokens'],'unknown_usage_reservation':gate.held()};rows.append(row);atomic(LOCAL/'progress.json',rows);print(label,state['status'],round(terminal,3),flush=True)
 except BaseException as e:
  stopping=type(e).__name__;raise
 finally:
  atomic(LOCAL/'totals.json',{'rows':rows,'admissions':gate.state['calls'],'trusted_tokens':gate.state['trusted_tokens'],'unknown_usage_reservation':gate.held(),'inflight':[i for i,e in gate.state['entries'].items() if e['inflight']],'stopped':stopping,'billing_amount':None,'expected_chains':16})
  for client in clients.values():await client.aclose()
  for server in servers.values():server.should_exit=True
  # Original lifecycle performs physical resource drain. Never force user/model processes.
  if tasks:await asyncio.gather(*tasks.values())
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--execute-single-authorized-batch',action='store_true',required=True);p.parse_args();c,f=freeze();asyncio.run(execute(c,f))
