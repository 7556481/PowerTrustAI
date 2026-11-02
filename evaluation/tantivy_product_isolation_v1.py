"""Explicit isolated product acceptance. Real indexes, offline provider only; no network."""
import json,time,hashlib,sqlite3
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from backend.api import create_app
from rag.storage import KnowledgeStore
from rag.tantivy_members import inventory
from rag.tantivy_manifest import package_manifest,sha
from rag.tantivy_build import atomic
from tests.test_schema14_factory_flow import SyntheticProvider
from model_adapter.contracts import ModelResponse

ROOT=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-product-v1')
DB=Path('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3')
K='kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e'
class OfflineProvider(SyntheticProvider):
 async def complete(self,r):
  data=[json.loads(m.content) for m in r.messages if m.role=='user'];d=next((x for x in data if x.get('section')!='FORMAT_CORRECTION_DATA_UNTRUSTED'),data[-1])
  if r.prompt_version.startswith('evidence-verification') and 'claims' in d:
   from tests.test_fact_rereview_v3 import response
   from tests.test_audit_interface_v2 import warrant
   bad=any('SYNTHETIC_WRONG' in c['proposition'] for c in d['claims']);status='contradicted' if bad else 'supported' if d.get('QUOTE_CANDIDATES') else 'insufficient_evidence'
   v=response(d,status=status)
   for f in v['findings']:
    for row in f['component_reviews']:row['support_relation']=warrant(d,[f['bases'][i]['quote_id'] for i in row['basis_indexes']],status=status)
   self.requests.append(r);self.payloads.append(d);return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  return await super().complete(r)

def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 with KnowledgeStore(DB,readonly=True) as s:inv=inventory(s,K)
 atomic(ROOT/'source-inventory.json',inv)
 summary={'model_calls_real':0,'source_total':inv['total'],'cases':[]}
 for name,index,proof_path,n in [('million',Path('D:/PowerTrustAI/data/retrieval_local/tantivy-supervision-v3/million/tantivy'),Path('D:/PowerTrustAI/data/retrieval_local/tantivy-supervision-v3/million/acceptance.json'),1000000),('quality674',Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/quality/tantivy'),Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/extended-source-check.json'),674)]:
  dest=ROOT/name;dest.mkdir(exist_ok=True);prior=json.loads(proof_path.read_text());assert prior['passed']
  if n==674:assert prior['quality_complete_members']==674 and prior['matches_v1_all_fid_body_terms']
  else:assert prior['complete_id_set'] and prior['n']==n
  proof={'passed':True,'complete_id_set':True,'n':n,'prior_proof':str(proof_path),'prior_proof_sha256':sha(proof_path),'reuse':'Historical complete ID/body/terms acceptance; current files freshly hashed, no repeat timing batch'}
  atomic(dest/'acceptance.json',proof)
  selection={'kind':'industry affine prefix','modulus':24620273,'offset':12345,'step':48271,'n':n} if n==1000000 else {'kind':'all 674 original negative-ID native literature members'}
  package_manifest(index,dest/'acceptance.json',dest/'manifest.json',knowledge_version=K,source_total=inv['total'],scope='isolated',build={'code_base':'b385e55','selection':selection},source_identity={'knowledge_version':K,'selection':selection,'source_bytes':DB.stat().st_size,'source_mtime_ns':DB.stat().st_mtime_ns})
  config=ServiceConfig(index_db=DB,knowledge_version=K,run_db=dest/'runs-r4.sqlite3',token_file=dest/'token',tantivy_manifest=dest/'manifest.json',tantivy_isolated=True)
  provider=OfflineProvider();factory=ComponentFactory(config)
  with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'synthetic-fixture'},clear=False),patch('model_adapter.deepseek.create_adapter',return_value=provider):
   app=create_app(config,factory=factory,access_token='fixture')
   with TestClient(app) as client:
    headers={'Authorization':'Bearer fixture'}
    for label,body in [('ordinary',{'mode':'question_answer','question':'power factor voltage'}),('insufficient',{'mode':'question_answer','question':'zzzzxxyyunknown987654'}),('revision',{'mode':'assess_existing','question':'power factor voltage','existing_answer':'SYNTHETIC_WRONG voltage is 9 kV.'}),('invalid_reference',{'mode':'assess_existing','question':'power factor voltage','existing_answer':'voltage','existing_citations':[{'start_offset':0,'end_offset':7,'fragment_ids':['not-a-real-source']} ]})]:
     body['engineering_context']={'goal':'conceptual'};started=time.monotonic();accepted=client.post('/runs',json=body,headers=headers)
     if label=='invalid_reference':
      assert accepted.status_code==422,accepted.text;summary['cases'].append({'scope':name,'case':label,'status':422});continue
     assert accepted.status_code==202,accepted.text;rid=accepted.json()['run_id']
     while time.monotonic()-started<180:
      state=client.get('/runs/'+rid,headers=headers).json()
      if state['status'] not in ('running','queued'):break
      time.sleep(.05)
     assert state['status'] not in ('running','queued'),state
     result=client.get('/runs/'+rid+'/result',headers=headers).json();trace=client.get('/runs/'+rid+'/trace',headers=headers).json()
     atomic(dest/(label+'-result-r4.json'),result);atomic(dest/(label+'-trace-r4.json'),trace)
     record={'scope':name,'case':label,'state':state['status'],'seconds':time.monotonic()-started,'execution':result.get('execution'),'versions':len(result.get('answer',{}).get('versions',[])),'review_rounds':len(result.get('review_rounds',[])),'retrievals':len(result.get('retrieval',[]))}
     history=client.get('/runs/page/0',headers=headers);assert history.status_code==200
     evidence=[]
     for e in result.get('evidence',[]):
      if isinstance(e,dict) and e.get('evidence_id'):evidence.append(e['evidence_id'])
     record['history_read']=True;record['evidence_endpoint_checks']=0
     for eid in set(evidence):
      assert client.get('/runs/'+rid+'/evidence/'+eid,headers=headers).status_code==200;record['evidence_endpoint_checks']+=1
     assert result['execution']['required_stages_complete'],record
     if label=='revision':assert record['versions']==2 and record['review_rounds']==2,record
     record['offline_fixture_requests']=len(result.get('model_usage',[]))
     summary['cases'].append(record);atomic(ROOT/'summary.json',summary);print(name,label,json.dumps(record),flush=True)
 summary['offline_model_fixture_requests']=sum(c.get('offline_fixture_requests',0) for c in summary['cases']);atomic(ROOT/'summary.json',summary)
if __name__=='__main__':main()
