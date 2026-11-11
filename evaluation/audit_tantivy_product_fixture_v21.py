"""Real API/Factory/Harness/Store, real frozen index; synthetic model responses."""
import json,time,sqlite3
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.serialization import wire
from evaluation.audit_tantivy_v21 import AuditFactory,expand
from evaluation.tantivy_product_v19 import configs
from tests.test_schema14_factory_flow import SyntheticProvider,GOOD,BAD
from tests.test_fact_rereview_v3 import response
from tests.test_audit_interface_v2 import warrant
from model_adapter.contracts import ModelMessage,ModelResponse
from services.request_metrics import measure
HOME=Path('D:/PowerTrustAI/data/runtime_local/audit-tantivy-v21/product-fixture-v2')

def unpack(p):
 if p.get('TRANSPORT_VERSION')=='review-lossless-shared-values-v1':
  from services.review_transport import expand as old_expand
  p=old_expand(p)
 return expand(p) if 'EVIDENCE_TEXTS' in p else p

class Provider(SyntheticProvider):
 def __init__(self):super().__init__(revision=True);self.boundary=[]
 async def complete(self,r):
  self.boundary.append(dict(prompt=r.prompt_version,correction=r.correction,metrics=measure(r.messages)))
  decoded=[ModelMessage(m.role,json.dumps(unpack(json.loads(m.content)),ensure_ascii=False)) if m.role=='user' else m for m in r.messages]
  r=replace(r,messages=tuple(decoded));data=[json.loads(m.content) for m in r.messages if m.role=='user'];d=data[0]
  if r.prompt_version.startswith('evidence-bound-generation'):
   e=next(e for p in data for e in p.get('evidence',[]) if e['text']==GOOD)
   v={'answer_units':[{'kind':'technical','text':BAD,'evidence_ids':[e['evidence_id']]}],'assumptions':[],'missing_information':[],'evidence_sufficient':True}
  elif r.prompt_version.startswith('evidence-verification'):
   bad=d.get('answer',{}).get('version',d.get('answer_version'))==1;status='contradicted' if bad else 'supported'
   if 'claims' in d:
    q=next(q for q in d['QUOTE_CANDIDATES'] if q['text']==GOOD);v=response(d,status=status)
    for f in v['findings']:
     f['bases']=[{'type':'text_excerpt','quote_id':q['quote_id']}]
     for row in f['component_reviews']:
      row['basis_indexes']=[0]
      cid=next(x['condition_id'] for x in d['SOURCE_CONDITION_CANDIDATES']['candidates'] if x['quote_id']==q['quote_id'])
      row['support_relation']=warrant(d,[q['quote_id']],status=status,repair={'replacement':GOOD,'condition_id':cid} if bad else None)
   else:
    v={'citation_reviews':[]}
    for s in d['ORIGINAL_CITATION_SCOPES']:
     q=next(q for q in s['QUOTE_CANDIDATES'] if q['text']==GOOD)
     v['citation_reviews'].append(dict(citation_index=s['citation_index'],status=status,rationale='Synthetic supplied literal3 conflicts with9 under the same C; version2 is faithful.',applicability_conditions=[],bases=[{'type':'text_excerpt','quote_id':q['quote_id']}],support_relation=warrant(d,[q['quote_id']],status=status)))
  elif r.prompt_version.startswith('bounded-revision'):
   context=json.loads(next(s for s in d['answer_requirements'] if s.lstrip().startswith('{')));e=next(e for e in d['DOCUMENT_DATA_UNTRUSTED'] if e['text']==GOOD)
   v={'answer_units':[{'kind':'technical','text':GOOD,'evidence_ids':[e['evidence_id']]}],'assumptions':[],'missing_information':[],'finding_actions':[{'finding_id':f['finding_id'],'action':'modified' if f['status']=='contradicted' else 'retained','explanation':'Synthetic source-bound9 to3, conditionC preserved.'} for f in context['finding_catalog']]}
  else:return await super().complete(r)
  self.requests.append(r);self.payloads.append(d);return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')

class ProbedFactory(AuditFactory):
 def create(self,*a,**kw):
  b=super().create(*a,**kw);self.last=b;return b

def main():
 HOME.mkdir(parents=True,exist_ok=False);c=configs(HOME)['fast'];factory=ProbedFactory(c);provider=Provider();started=time.monotonic()
 with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=provider):
  with TestClient(create_app(c,factory=factory,access_token='fixture')) as client:
   h={'Authorization':'Bearer fixture'}
   r=client.post('/runs',headers=h,json={'mode':'question_answer','question':'Explain power factor voltage using only the supplied synthetic statement.','references':[{'text':GOOD,'label':'synthetic_fixture'}],'engineering_context':{'goal':'conceptual'}});assert r.status_code==202,r.text;rid=r.json()['run_id']
   deadline=time.monotonic()+800
   while time.monotonic()<deadline:
    state=client.get('/runs/'+rid,headers=h).json()
    if state['status'] not in ('queued','running'):break
    time.sleep(.1)
   result=client.get('/runs/'+rid+'/result',headers=h).json();trace=client.get('/runs/'+rid+'/trace',headers=h).json()
   (HOME/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');(HOME/'trace.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding='utf8')
   routes=factory.last.harness.retriever.trace
   (HOME/'routes.json').write_text(json.dumps(routes,indent=2),encoding='utf8');(HOME/'model-boundary.json').write_text(json.dumps(provider.boundary,indent=2),encoding='utf8')
   assert result['execution']['required_stages_complete'],result['execution']
   assert len(result['answer']['versions'])==2 and len(result['review_rounds'])==2
   assert result['answer']['versions'][0]['text']==BAD and result['answer']['final']['text']==GOOD
   again=client.get('/runs/'+rid+'/result',headers=h).json();assert again==result
   for e in result['evidence']:assert client.get('/runs/'+rid+'/evidence/'+e['evidence_id'],headers=h).status_code==200
   assert any(x['purpose']=='generation' and x['backend']=='AsyncSQLiteBM25Retriever' for x in routes)
   assert all(x['backend']=='GlobalIDFRetriever' and x['trace']['backend']=='tantivy-global-idf-v18' and x['trace']['fallback'] is False for x in routes if x['purpose'] in ('verification','domain_review'))
   db=sqlite3.connect('file:'+str(c.run_db)+'?mode=ro',uri=True)
   raw=json.loads(db.execute('select result from runs where id=?',(rid,)).fetchone()[0]);objects=[(r[0],r[1],r[2]) for r in db.execute('select kind,version,id from objects where run_id=?',(rid,))];db.close()
   assert len(raw['review_rounds'])==2 and len(raw['revision_outputs'])==1
   assert {x[1] for x in objects if x[0]=='answer'}=={1,2}
   summary=dict(status=state['status'],complete=True,versions=2,review_rounds=2,revisions=1,stored_object_count=len(objects),routing=routes,seconds=time.monotonic()-started,model_calls_real=0,revision_retrieval_note='Existing Harness revise constructs RevisionInput from the allowed evidence pool; it issues NO revision-purpose retrieval. Do not invent one. Generation-purpose reads use SQLite; both audit rounds use v18.',boundary=provider.boundary)
   (HOME/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print('Normal product v2/re-extraction/full dual reviews/Store verified',flush=True)
if __name__=='__main__':main()
