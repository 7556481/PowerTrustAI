"""Use the existing two-port product batch with explicit v18 factory wiring."""
import json,time,os,hashlib,subprocess,asyncio
from pathlib import Path
from dataclasses import replace
from backend.assembly import ComponentFactory
from backend.config import ServiceConfig
from backend.serialization import wire
from rag.tantivy_build import atomic
from rag.tantivy_manifest import sha
from evaluation.tantivy_full_build_v1 import ROOT as ORIGINAL,SOURCE,K
from evaluation.tantivy_shard_continuous_v17 import HOME
from model_adapter.call_budget_v1 import shared_gate
LOCAL=Path('D:/PowerTrustAI/data/runtime_local/tantivy-product-v19')
V18=HOME.parent/'tantivy-query-repair-v18'

class ProbedFactory(ComponentFactory):
 def create(self,rid,*a,**kw):
  bundle=super().create(rid,*a,**kw);retriever=bundle.harness.retriever
  if retriever is None:raise RuntimeError('Full product retriever required')
  retriever._probe_run=rid
  if not getattr(retriever,'_probe_installed',False):
   original= retriever.retrieve
   async def retrieve(request):
    started=time.monotonic();item={'run_id':retriever._probe_run,'purpose':request.purpose.value,'query_sha256':hashlib.sha256(request.query.encode()).hexdigest(),'retriever_class':type(retriever).__name__}
    try:
     result=await original(request);trace=dict(getattr(retriever,'last_trace',{}))
     if self.config.tantivy_worker_mode=='sharded_v18':
      if trace.get('backend')!='tantivy-global-idf-v18' or trace.get('fallback') is not False or trace.get('shard_count')!=90:raise RuntimeError('V18 retrieval routing or fallback mismatch')
     item.update(status='ok',trace=trace,evidence_ids=[e.evidence_id for e in result.evidence]);return result
    except BaseException as e:item.update(status='error',error=type(e).__name__);raise
    finally:
     item['seconds']=time.monotonic()-started
     with (self.config.run_db.parent/'retriever-routing.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(item)+'\n')
   retriever.retrieve=retrieve;retriever._probe_installed=True
  return bundle

def configs(root,*,load_real=False):
 from unittest.mock import patch
 if load_real:
  from harness.deepseek_trial import load_project_env
  load_project_env(Path('D:/PowerTrustAI/.env'))
  if os.environ.get('DEEPSEEK_MODEL_ID')!='deepseek-flash':raise RuntimeError('Explicit Flash required')
  with patch('backend.config.ROOT',Path('D:/PowerTrustAI')):c=ServiceConfig.from_environment()
  if c.index_db.resolve()!=SOURCE.resolve() or c.knowledge_version!=K or c.execution_path!='langgraph_v1' or c.tantivy_manifest is not None or c.model_budget_dir is not None:raise RuntimeError('Managed baseline identity changed')
 else:c=ServiceConfig(index_db=SOURCE,knowledge_version=K,execution_path='langgraph_v1')
 fields=('verification_schema','audit_strategy','fact_review_contract','fact_review_execution','fact_internal_flow','domain_internal_flow','local_revision_interface','revision_answer_delivery','review_result_transport','fact_strategy','retrieval_mode','retrieval_execution_profile','decision_policy')
 if tuple(getattr(c,x) for x in fields)!=(13,'baseline','production','serial_v1','production','production','production','production','json','aggregate','bm25','topic_v4_subject_v1','product-v1') or c.budget.max_revision_rounds!=1 or c.nli_enabled:raise RuntimeError('Production contract/configuration differs')
 c=replace(c,model_budget_dir=root/'accounting' if load_real else None)
 return {name:replace(c,run_db=root/name/'runs.sqlite3',token_file=root/name/'access-token',tantivy_manifest=HOME/'accepted-shard-group.json' if name=='fast' else None,tantivy_isolated=name=='fast',tantivy_worker_mode='sharded_v18' if name=='fast' else 'oneshot',tantivy_spool=ORIGINAL/'spool.sqlite3' if name=='fast' else None) for name in ['baseline','fast']}

def freeze():
 import evaluation.tantivy_full_product_batch_v1 as old
 if (LOCAL/'freeze.json').exists():raise RuntimeError('Frozen batch already exists; no replay')
 if not (LOCAL/'offline-routing-proof.json').exists():raise RuntimeError('Offline product routing proof required')
 proof=json.loads((LOCAL/'offline-routing-proof.json').read_text())
 if proof['index_manifest_sha256']!=sha(HOME/'accepted-shard-group.json'):raise RuntimeError('Offline routing proof index changed')
 group=json.loads((HOME/'accepted-shard-group.json').read_text())
 if not group['complete'] or group['count']!=24620947 or len(group['manifests'])!=90:raise RuntimeError('Full90 accepted group required')
 if Path('D:/PowerTrustAI/data/runtime_local/tantivy-full-fast-v1/comparison/accounting/state.json').exists():raise RuntimeError('Prior shared accounting exists; reconcile before any requests')
 summary=json.loads((V18/'full-summary-v18.json').read_text());assert summary['slots']==144 and not summary['errors'] and summary['wide_ratio_median']>=1.5
 measured=json.loads((V18/'comparison/offline-freeze.json').read_text())['implementation_sha256']
 for f in ['rag/tantivy_global_rank_v18.py','rag/tantivy_diagnostic_v18.py','rag/tantivy_sharded_v17.py','rag/tantivy_fast_v1.py']:
  if sha(f)!=measured[f]:raise RuntimeError('Measured v18 retrieval code changed')
 cs=configs(LOCAL,load_real=True);plan=json.loads((ORIGINAL/'plan.json').read_text());gate=shared_gate(LOCAL/'accounting')
 if gate.state['calls'] or gate.state['entries']:raise RuntimeError('Existing admissions; cannot repeat batch')
 gate.save()
 f={'version':'v18-real-product-v19','commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'retrieval_measured_commit':'eb7ab40','sources':old.code_identity(),'source_stat':[SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns],'index_manifest_sha256':sha(HOME/'accepted-shard-group.json'),'cases':plan['real_cases'],'configs':{n:wire(c) for n,c in cs.items()},'ports':{'baseline':8775,'fast':8776},'budget':plan['model'],'model_calls_before':0,'gates':{'complete_pairs':6,'candidate_completes_not_lower':True,'terminal_median_saving_fraction':.15,'terminal_median_saving_seconds':3,'no_new_critical_quality_regression':True},'order':'even pair baseline first, odd pair candidate first; each once','review':'AI辅助、用户监督的开发复核；已见开发材料，非专家金标准','offline_routing_sha256':sha(LOCAL/'offline-routing-proof.json')}
 atomic(LOCAL/'freeze.json',f);return cs,f

def offline():
 from fastapi.testclient import TestClient
 from backend.api import create_app
 from unittest.mock import patch
 from evaluation.tantivy_product_isolation_v1 import OfflineProvider
 root=LOCAL/'offline';cs=configs(root);proof=[]
 for name,c in cs.items():
  if (c.run_db.parent/'result.json').exists():
   result=json.loads((c.run_db.parent/'result.json').read_text());rows=[json.loads(l) for l in (c.run_db.parent/'retriever-routing.jsonl').read_text().splitlines()];purposes={x['purpose'] for x in rows};assert {'generation','verification','domain_review'}<=purposes
   proof.append({'backend':name,'execution':result['execution'],'purposes':sorted(purposes),'classes':sorted({x['retriever_class'] for x in rows}),'reuse':'completed offline API fixture; prior assertion used incorrect purpose labels; no submission replay','external_model_requests':0});continue
  c.run_db.parent.mkdir(parents=True,exist_ok=False);factory=ProbedFactory(c);provider=OfflineProvider()
  with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=provider):
   started=time.monotonic()
   with TestClient(create_app(c,factory=factory,access_token='fixture')) as client:
    response=client.post('/runs',headers={'Authorization':'Bearer fixture'},json={'mode':'question_answer','question':'synthetic voltage','engineering_context':{'goal':'conceptual'}});assert response.status_code==202;rid=response.json()['run_id']
    for _ in range(16000):
     state=client.get('/runs/'+rid,headers={'Authorization':'Bearer fixture'}).json()
     if state['status'] not in ['queued','running']:break
     time.sleep(.05)
    result=client.get('/runs/'+rid+'/result',headers={'Authorization':'Bearer fixture'}).json();atomic(c.run_db.parent/'result.json',result)
    rows=[json.loads(l) for l in (c.run_db.parent/'retriever-routing.jsonl').read_text().splitlines()];purposes={x['purpose'] for x in rows};assert {'generation','verification','domain_review'}<=purposes,purposes
    proof.append({'backend':name,'status':state['status'],'execution':result['execution'],'purposes':sorted(purposes),'classes':sorted({x['retriever_class'] for x in rows}),'startup_and_chain_seconds':time.monotonic()-started,'external_model_requests':0})
 results=[json.loads((root/name/'result.json').read_text()) for name in ['baseline','fast']]
 for key in ['prompts','contracts','protocols','policy','template_sha256']:
  assert results[0]['configuration'][key]==results[1]['configuration'][key],key
 assert all(x['execution']['required_stages_complete'] for x in results)
 prior=LOCAL/'offline-routing-proof.json'
 if prior.exists():
  n=0
  while (LOCAL/f'offline-routing-proof-history-{n}.json').exists():n+=1
  (LOCAL/f'offline-routing-proof-history-{n}.json').write_bytes(prior.read_bytes())
 atomic(LOCAL/'offline-routing-proof.json',{'proof':proof,'models':0,'index_manifest_sha256':sha(HOME/'accepted-shard-group.json'),'same_contract_fields':['prompts','contracts','protocols','policy','template_sha256']})

if __name__=='__main__':
 import sys
 LOCAL.mkdir(parents=True,exist_ok=True)
 if sys.argv[1]=='offline':offline()
 elif sys.argv[1]=='execute':
  import evaluation.tantivy_full_product_batch_v1 as old
  original_identity=old.code_identity
  def identity():
   d=original_identity()
   for file in ['evaluation/tantivy_product_v19.py','evaluation/tantivy_full_product_batch_v1.py']:d[file]=sha(file)
   return d
  old.code_identity=identity;old.LOCAL=LOCAL;old.ROOT=V18/'comparison';old.ComponentFactory=ProbedFactory;cs,f=freeze();asyncio.run(old.execute(cs,f))
