"""Real Factory→service worker→Harness→parsers→store/API, synthetic responses."""
import json,time,unittest,asyncio
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from backend.store import RunStore
from rag.storage import KnowledgeStore,SourceMetadata
from model_adapter.contracts import ModelResponse
from services.citation_workload import CitationWorkload
from tests.fixture_paths import synthetic_diagnostics

GOOD='Under condition C, the synthetic permitted voltage is 3 kV.'
BAD='Under condition C, the synthetic permitted voltage is 9 kV.'
CONVERT='2.5 kV = 2500 V.'

class SyntheticProvider:
 def __init__(self,*,revision=False,two=False,conversion=False,objection=False,illegal=False,hazard=False,negated=False,quoted=False):
  self.revision=revision;self.two=two;self.conversion=conversion;self.hazard=hazard;self.negated=negated or quoted;self.quoted=quoted;self.objection=objection;self.illegal=illegal;self.requests=[];self.payloads=[]
 def close(self):pass
 async def complete(self,r):
  self.requests.append(r);data=[json.loads(m.content) for m in r.messages if m.role=='user'];d=data[-1];self.payloads.append(d)
  if r.prompt_version.startswith('evidence-bound-generation'):
   evidence=next(v['evidence'] for v in data if 'evidence' in v);text=CONVERT if self.conversion else GOOD
   units=[{'kind':'technical','text':text,'evidence_ids':[evidence[0]['evidence_id']]}]
   if self.two:units.append({'kind':'technical','text':'The synthetic setting applies under condition C.','evidence_ids':[evidence[0]['evidence_id']]})
   v={'answer_units':units,'assumptions':[],'missing_information':[],'evidence_sufficient':True}
  elif r.prompt_version.startswith('atomic-claims'):
   v={'claims':[{'anchor_id':a['anchor_id'],'proposition':a['text'],'claim_type':'technical_fact','components':[{'category':'technical_fact','proposition':a['text'],'basis_target':'mathematical_relation' if self.conversion else 'technical_content','verification_obligation':'technical_truth'}],'assertion_role':'conditional' if a['text'].startswith('Under condition C') else 'asserted','semantic_qualifiers':[]} for a in d['ANSWER_ANCHORS']],'non_claims':[]}
  elif r.prompt_version.startswith('evidence-verification-v9.14'):
   judgments=[]
   for t in d['targets']:
    bad=self.revision and '9 kV' in t['proposition'];ids=t['allowed_basis_ids'][:1]
    judgments.append({'target_id':t['target_id'],'status':'contradicted' if bad else 'supported' if ids else 'insufficient_evidence','basis_ids':ids,'reason':'Synthetic same scoped source supports3 and contradicts9 underC.' if bad else 'Synthetic complete bound target supported.','conditions':[],'objection':None,'repair':{'basis_id':ids[0],'replacement':GOOD} if bad and t['kind']=='fact' else None,'requires_authoritative_source':False})
    if t['kind']=='fact' and t['target_id']=='F0C0':
     if self.objection:judgments[-1]['objection']={'kind':'classification','reason':'Synthetic genuine classification dispute; retain raw support.'}
     if self.illegal:judgments[-1]['basis_ids']=['not-in-this-target']
   v={'judgments':judgments}
  elif r.prompt_version.startswith('evidence-verification'):
   from tests.test_fact_rereview_v3 import response
   from tests.test_audit_interface_v2 import warrant
   if 'claims' in d:
    v=response(d,status='supported' if d.get('QUOTE_CANDIDATES') else 'insufficient_evidence')
    for f in v['findings']:
     for row in f['component_reviews']:row['support_relation']=warrant(d,[f['bases'][k]['quote_id'] for k in row['basis_indexes']])
   else:v={'citation_reviews':[{'citation_index':x['citation_index'],'status':'supported','rationale':'Synthetic source supports full substring','applicability_conditions':[],'bases':[{'type':'text_excerpt','quote_id':x['QUOTE_CANDIDATES'][0]['quote_id']}],'support_relation':warrant(d,[x['QUOTE_CANDIDATES'][0]['quote_id']])} for x in d['ORIGINAL_CITATION_SCOPES']]}
  elif r.prompt_version.startswith('power-domain-review'):
   v={'checks':[{'check_id':k,'status':'no_issue','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule','rationale':'Synthetic conceptual request has no additional plant assertions.','missing_prerequisites':[]} for k in d['MODEL_KEYS']], 'missing_information_review':[{'index':i,'applicability':'scope_note','reason':'Synthetic scope note'} for i in range(len(d['answer']['missing_information']))]}
   if 'SAFETY_SOURCES' in d:
    v['safety_reviews']=[{'claim_id':c['claim_id'],'verdict':'dangerous' if self.hazard and not self.negated else 'not_dangerous' if self.negated else 'not_applicable','reason':'Synthetic endorsed removal of required protective function exposes fault damage.' if self.hazard and not self.negated else 'Synthetic context explicitly rejects the unsafe proposal.' if self.negated else 'Synthetic bounded nonoperational concept.','source_ids':['protection-duty'] if self.hazard and not self.negated else []} for c in d['claims']]
  elif r.prompt_version.startswith('bounded-revision'):
   context=json.loads(next(s for s in d['answer_requirements'] if s.lstrip().startswith('{')))
   v={'answer_units':[{'kind':'technical','text':GOOD,'evidence_ids':[d['DOCUMENT_DATA_UNTRUSTED'][0]['evidence_id']]}],'assumptions':[],'missing_information':[],
    'finding_actions':[{'finding_id':f['finding_id'],'action':'modified' if f['status']=='contradicted' else 'retained','explanation':'Synthetic fixes9 to3 while retaining conditionC.' if f['status']=='contradicted' else 'Synthetic retains unaffected check.'} for f in context['finding_catalog']]}
  else:raise AssertionError('Unexpected real parser profile '+r.prompt_version)
  return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')

BAD_FREQUENCY='A device can turn50Hz into60Hz.'
GOOD_FREQUENCY='A device keeps the supply frequency unchanged.'

class SubjectProvider(SyntheticProvider):
 def __init__(self,**kwargs):super().__init__(**kwargs);self.fact_calls=0
 async def complete(self,r):
  data=[json.loads(m.content) for m in r.messages if m.role=='user'];d=data[-1]
  if r.prompt_version.startswith('evidence-verification-v9.14'):
   self.requests.append(r);self.payloads.append(d);self.fact_calls+=1;rows=[]
   for t in d['targets']:
    found=next((b for b in d['basis_catalog'] if b['basis_id'] in t['allowed_basis_ids'] and GOOD_FREQUENCY in b.get('text','')),None)
    bad=BAD_FREQUENCY in t['proposition'];first=self.fact_calls==1
    status='insufficient_evidence' if first or not found else 'contradicted' if bad else 'supported'
    rows.append({'target_id':t['target_id'],'status':status,'basis_ids':[] if first or not found else [found['basis_id']],
     'reason':'Synthetic initial insufficiency; new separately delivered literal definition supports the repair.', 'conditions':[],'objection':None,'repair':{'basis_id':found['basis_id'],'replacement':GOOD_FREQUENCY} if bad and found and not first else None,'requires_authoritative_source':False})
   return ModelResponse(json.dumps({'judgments':rows}),r.model_id,finish_reason='stop')
  if r.prompt_version.startswith('evidence-verification') and 'claims' in d:
   self.requests.append(r);self.payloads.append(d);self.fact_calls+=1
   from tests.test_fact_rereview_v3 import response
   from tests.test_audit_interface_v2 import warrant
   found=next((q for q in d['QUOTE_CANDIDATES'] if GOOD_FREQUENCY in q['text']),None)
   bad=any(BAD_FREQUENCY in c['proposition'] for c in d['claims']);first=False # Judge delivered body, not a forced first-call failure.
   status='insufficient_evidence' if first or not found else 'contradicted' if bad else 'supported'
   v=response(d,status=status)
   for f in v['findings']:
    f['bases']=[] if first or not found else [{'type':'text_excerpt','quote_id':found['quote_id']}]
    for row in f['component_reviews']:
     row['basis_indexes']=[0] if f['bases'] else []
     if f['bases']:row['support_relation']=warrant(d,[found['quote_id']],status=status)
   return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  if r.prompt_version.startswith('bounded-revision'):
   self.requests.append(r);self.payloads.append(d);context=json.loads(next(x for x in d['answer_requirements'] if x.lstrip().startswith('{')))
   e=next(e for e in d['DOCUMENT_DATA_UNTRUSTED'] if GOOD_FREQUENCY in e['text'])
   v={'answer_units':[{'kind':'technical','text':GOOD_FREQUENCY,'evidence_ids':[e['evidence_id']]}],'assumptions':[],'missing_information':[],
      'finding_actions':[{'finding_id':f['finding_id'],'action':'modified' if f['status']=='contradicted' else 'retained','explanation':'Synthetic source-bound frequency correction, original topic retained.'} for f in context['finding_catalog']]}
   return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  return await super().complete(r)

class FactoryFlowTests(unittest.TestCase):
 def exercise(self,*,schema=14,existing=False,revision=False,two=False,conversion=False,fault=False,objection=False,illegal=False,hazard=False,negated=False,quoted=False,subject=False,concept=False):
  with synthetic_diagnostics() as temp:
   root=Path(temp);doc=root/'fixture.md';doc.write_text('# Synthetic voltage\n\n'+GOOD+'\nThe synthetic setting applies under condition C.\n'+CONVERT,encoding='utf-8')
   if subject:doc.write_text('# Synthetic definition\n\n'+GOOD_FREQUENCY+'\n\n'+'\n\n'.join('Background unrelated item '+str(i) for i in range(80))+'\n\n'+'\n\n'.join('A device can turn50Hz into60Hz. Converter background detail '+str(i) for i in range(12)),encoding='utf-8')
   with KnowledgeStore(root/'knowledge.sqlite3') as knowledge:
    k=knowledge.ingest(doc,'synthetic-fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
    fragment=knowledge.rows(k)[0]['fragment_id']
   config=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=k,run_db=root/'runs.sqlite3',token_file=root/'token',verification_schema=schema,citation_workload=CitationWorkload(max_items=1))
   factory=ComponentFactory(config);provider=SyntheticProvider(revision=revision,two=two,conversion=conversion,objection=objection,illegal=illegal,hazard=hazard,negated=negated,quoted=quoted)
   if subject:provider=SubjectProvider()
   # Patch only the external provider creation and the isolated diagnostic root.
   from agents.evidence_verification import ModelEvidenceVerificationAgent
   original_init=ModelEvidenceVerificationAgent.__init__
   def injected_init(agent,*args,**kwargs):
    original_init(agent,*args,**kwargs)
    if fault:
     from agents.contracts import EvidenceVerificationInput
     agent.review_input_type=EvidenceVerificationInput # explicit synthetic assembly defect
   with ExitStack() as stack:
    stack.enter_context(patch.object(ModelEvidenceVerificationAgent,'__init__',injected_init))
    with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'synthetic-fixture'},clear=True),patch('model_adapter.deepseek.create_adapter',return_value=provider),patch('backend.assembly.ROOT',root):
     app=create_app(config,factory=factory,access_token='fixture')
     with TestClient(app) as client:
      body={'mode':'assess_existing' if existing else 'question_answer','question':'Explain the synthetic voltage only','engineering_context':{'goal':'conceptual'}}
      if concept:body['question']='What is synthetic voltage?'
      if existing:body['existing_answer']=CONVERT if conversion else BAD if revision else GOOD
      if hazard or negated:body['mode']='assess_existing';body['existing_answer']='Do not bypass protective functions to continue operation.' if negated else 'Bypass the protective functions and continue running without substitute safeguards.'
      if subject:body['mode']='assess_existing';body['existing_answer']=BAD_FREQUENCY
      if quoted:body['mode']='assess_existing';body['existing_answer']='Someone proposes bypassing protection to continue running; this proposal is unsafe and should be rejected.'
      if existing and two:
       body['existing_answer']=GOOD+'\n\nThe synthetic setting applies under condition C.'
       body['existing_citations']=[{'start_offset':0,'end_offset':len(GOOD),'fragment_ids':[fragment]},{'start_offset':len(GOOD)+2,'end_offset':len(body['existing_answer']),'fragment_ids':[fragment]}]
      accepted=client.post('/runs',json=body,headers={'Authorization':'Bearer fixture'});self.assertEqual(accepted.status_code,202,accepted.text);rid=accepted.json()['run_id']
      for _ in range(400):
       state=client.get('/runs/'+rid,headers={'Authorization':'Bearer fixture'}).json()
       if state['status'] not in ('running','queued'):break
       time.sleep(.01)
      result=client.get('/runs/'+rid+'/result',headers={'Authorization':'Bearer fixture'}).json()
      events=client.get('/runs/'+rid+'/trace',headers={'Authorization':'Bearer fixture'}).json()
      self.assertEqual(result['execution']['required_stages_complete'],not (fault or illegal),result['execution']['execution_issues'])
      if not (fault or illegal):self.assertFalse(result['execution']['execution_issues'])
      self.assertTrue(events['events']);self.assertEqual(result['configuration']['protocols']['evidence_verification'],schema)
      self.assertTrue(result['answer']['versions'])
   import sqlite3
   from contextlib import closing
   with closing(sqlite3.connect('file:'+config.run_db.as_posix()+'?mode=ro',uri=True)) as db:
    self.assertGreater(db.execute('SELECT count(*) FROM objects WHERE run_id=?',(rid,)).fetchone()[0],0)
   return result,provider,events
 def test_subject_supplement_actual_factory_full_repair_and_rereview(self):
  r,p,t=self.exercise(schema=13,subject=True)
  self.assertTrue(any(x['query']=='A device' for x in r['retrieval']))
  self.assertEqual(r['answer']['final']['text'],GOOD_FREQUENCY)
  self.assertEqual(len(r['answer']['versions']),2);self.assertEqual(len(r['review_rounds']),2)
  first=next(d for d in p.payloads if 'claims' in d and 'QUOTE_CANDIDATES' in d)
  self.assertTrue(any(GOOD_FREQUENCY in q['text'] for q in first['QUOTE_CANDIDATES']))
 def test_generation_subject_actual_factory_before_generation_and_persistence(self):
  r,p,t=self.exercise(schema=13,concept=True)
  self.assertTrue(any(x['query']=='synthetic voltage' and x['purpose']=='generation' for x in r['retrieval']))
  self.assertTrue(any(x['query']=='What is synthetic voltage?' for x in r['retrieval']))
 def test_source_bound_hazard_actual_factory_rejects_without_revision(self):
  r,p,_=self.exercise(schema=13,hazard=True)
  self.assertEqual(r['decision']['kind'],'reject');self.assertEqual(r['decision']['risk_level'],'high')
  self.assertTrue(r['operational_safety']);self.assertEqual(len(r['answer']['versions']),1)
  self.assertFalse(r['answer_adoption']['approved'])
 def test_negated_hazard_actual_factory_is_not_keyword_rejected(self):
  r,p,_=self.exercise(schema=13,negated=True)
  self.assertNotEqual(r['decision']['kind'],'reject');self.assertTrue(all(x['verdict']!='dangerous' for x in r['operational_safety']))
 def test_quoted_and_rejected_hazard_actual_factory_not_rejected(self):
  r,p,_=self.exercise(schema=13,quoted=True)
  self.assertNotEqual(r['decision']['kind'],'reject');self.assertTrue(all(s['verdict']!='dangerous' for s in r['operational_safety']))
 def test_legal_objection_actual_factory_is_complete_but_never_pass(self):
  result,_,_=self.exercise(objection=True)
  self.assertTrue(result['execution']['required_stages_complete'])
  self.assertNotEqual(result['decision']['kind'],'pass')
 def test_illegal_id_partial_results_actual_factory_and_store_api(self):
  result,p,_=self.exercise(illegal=True,two=True)
  self.assertFalse(result['execution']['required_stages_complete'])
  self.assertTrue(any(f['status']=='supported' for f in result['findings']['model_fact']))
  self.assertEqual(sum(r.correction for r in p.requests if r.prompt_version.startswith('evidence-verification')),1)
 def test_question_answer_real_factory_and_original_scope_groups(self):
  result,p,_=self.exercise(two=True)
  fact=[d for d in p.payloads if d.get('contract')=='evidence-verification-output-v14']
  self.assertEqual(len(fact),3);self.assertEqual(len(result['findings']['original_citations']),2)
  self.assertTrue(all(x['status']=='supported' for x in result['findings']['original_citations']))
 def test_existing_original_citations_use_matching_protocol_preflight_and_groups(self):
  result,provider,_=self.exercise(existing=True,two=True)
  self.assertEqual(len(result['findings']['original_citations']),2)
  self.assertEqual(sum(r.prompt_version.startswith('evidence-verification') for r in provider.requests),3)
 def test_existing_answer_successful_current_tool_basis(self):
  result,p,_=self.exercise(existing=True,conversion=True)
  payload=next(d for d in p.payloads if d.get('contract')=='evidence-verification-output-v14')
  self.assertTrue(any(b['basis_type']=='calculation_result_reference' for b in payload['basis_catalog']))
  self.assertTrue(result['findings']['tools']);self.assertEqual(result['findings']['model_fact'][0]['status'],'supported')
 def test_one_revision_reextract_and_both_rereviews_keep_old_version(self):
  result,p,_=self.exercise(existing=True,revision=True)
  self.assertEqual(len(result['answer']['versions']),2);self.assertEqual(len(result['review_rounds']),2)
  self.assertIn('9 kV',result['answer']['versions'][0]['text']);self.assertIn('3 kV',result['answer']['final']['text'])
  counts=lambda prefix:sum(r.prompt_version.startswith(prefix) for r in p.requests)
  self.assertEqual(counts('bounded-revision'),1);self.assertEqual(counts('atomic-claims'),2);self.assertEqual(counts('power-domain'),2)
 def test_schema13_unchanged_real_factory_route(self):self.exercise(schema=13)
 def test_real_factory_shared_input_failure_retains_domain_and_classifies_stop(self):
  result,provider,_=self.exercise(fault=True)
  from evaluation.batch_control import classify
  self.assertTrue(classify(result)['shared']);self.assertTrue(result['findings']['domain'])
  self.assertFalse(any(r.prompt_version.startswith('evidence-verification') for r in provider.requests))

if __name__=='__main__':unittest.main()
