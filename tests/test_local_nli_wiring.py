"""Actual Harness/schema13 output -> conversion -> sidecar -> append/API."""
import json,time,tempfile
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import unittest
from fastapi.testclient import TestClient
from agents.fakes import make_fake_harness
from agents.evidence_verification import ModelEvidenceVerificationAgent
from backend.assembly import ComponentFactory,Bundle
from backend.config import ServiceConfig
from backend.api import create_app
from harness.contracts import RetrievalSettings,RunBudget
from model_adapter.contracts import ModelSettings,ModelResponse
from rag.storage import KnowledgeStore,SourceMetadata
from rag.retriever import AsyncSQLiteBM25Retriever
from services.answer_anchors import anchors
from services.claim_obligations import parse
from tests.test_fact_rereview_v3 import response
from tests.test_local_nli import FakeProcess

class WiringTests(unittest.TestCase):
 def exercise(self,kind,*,enabled=True,fail=False,selection=None):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);doc=root/'synthetic_fixture.md';doc.write_text('Alpha supports voltage.\n',encoding='utf-8')
   db=root/'knowledge.sqlite3'
   with KnowledgeStore(db) as store:k=store.ingest(doc,'synthetic_fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
   retriever=AsyncSQLiteBM25Retriever(db)
   outer=self
   class Adapter:
    async def complete(self,request):
     data=json.loads(request.messages[1].content)
     v=response(data,status='insufficient_evidence' if kind=='unsupported' else 'supported')
     return ModelResponse(json.dumps(v),request.model_id,finish_reason='stop')
   class Extractor:
    async def extract(self,answer):
     parts=[{'category':'technical_fact','proposition':'Alpha supports voltage.','basis_target':'document_body','verification_obligation':'technical_truth'}]
     if kind=='mixed':parts.append({'category':'technical_fact','proposition':'5 MW = 5 MVA','basis_target':'mathematical_relation','verification_obligation':'technical_truth'})
     if kind=='unsupported':parts=[{'category':'source_quality_metadata','proposition':'The index records a source.','basis_target':'index_metadata','verification_obligation':'metadata_value'}]
     return parse({'claims':[{'anchor_id':anchors(answer)[0]['anchor_id'],'proposition':answer.text,'claim_type':'technical_fact' if kind!='unsupported' else 'source_quality_metadata','assertion_role':'asserted','semantic_qualifiers':[],'components':parts}],'non_claims':[]},answer)
   class Factory(ComponentFactory):
    def preflight(self):return k
    def create(self,rid,observer):
     h=make_fake_harness();h.observer=observer;h.extractor=Extractor();h.retriever=retriever
     h.retrieval_settings=RetrievalSettings(1,None,'aggregate' if kind=='missing' else 'per_claim_v1')
     h.verification=ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13)
     return Bundle(h)
   config=ServiceConfig(profile='synthetic_fixture',run_db=root/'runs.sqlite3',nli_enabled=enabled,fact_strategy='aggregate' if kind=='missing' else 'per_claim_v1',budget=RunBudget(max_revision_rounds=0))
   async def start(engine):engine.process=FakeProcess({'status':'complete','nli_three_class_result':'contradicted','logits':[2.,0.,-1.],'tokens':35},fail=fail);engine.identity={'fixture':True}
   with patch('services.local_nli.LocalNLI.start',new=start),TestClient(create_app(config,factory=Factory(config),access_token='synthetic-only')) as client:
    header={'Authorization':'Bearer synthetic-only'}
    text='Alpha supports voltage and 5 MW equals 5 MVA.' if kind=='mixed' else 'Alpha supports voltage.'
    submit=client.post('/runs',headers=header,json={'local_nli_enabled':enabled if selection is None else selection,'mode':'assess_existing','question':'synthetic_fixture concept review','existing_answer':text,'references':[{'label':'synthetic_fixture','text':'Alpha supports voltage.'}]})
    self.assertEqual(submit.status_code,202);rid=submit.json()['run_id']
    for _ in range(200):
     state=client.get('/runs/'+rid,headers=header).json()
     nli=client.get('/runs/'+rid+'/nli',headers=header).json()
     if state['status'] not in ('queued','running') and (nli['records'] or not (enabled if selection is None else selection)):break
     time.sleep(.01)
    result=client.get('/runs/'+rid+'/result',headers=header).json()
    diag=client.get('/runs/'+rid+'/nli',headers=header).json()
   retriever.close()
   return result,diag
 def test_explicit_off_task_uses_no_diagnostics_on_enabled_service(self):
  result,diag=self.exercise('body',enabled=True,selection=False)
  self.assertFalse(result['configuration']['local_nli_diagnostic']['enabled']);self.assertFalse(diag['enabled']);self.assertEqual(diag['records'],[])
 def test_actual_singleton_harness_output_saved_api_disagreement(self):
  result,diag=self.exercise('body')
  self.assertEqual(result['decision']['kind'],'review_required')
  self.assertTrue(result['execution']['required_stages_complete'])
  self.assertEqual(len(diag['records']),1);r=diag['records'][0]
  self.assertEqual(r['status'],'complete');self.assertEqual(r['production_status'],'supported');self.assertTrue(r['disagreement'])
  self.assertEqual(r['literal_binding']['type'],'unique_single_component_parent_span')
  self.assertIn('Alpha supports voltage.',r['semantic_input']['hypothesis'])
  self.assertEqual(r['answer_id'],result['answer']['final']['answer_id'])
 def test_actual_mixed_harness_output_does_not_expand_component(self):
  _,diag=self.exercise('mixed');reasons={r.get('reason') for r in diag['records']}
  self.assertIn('mixed_component_literal_binding_missing',reasons);self.assertIn('unsupported_basis_target',reasons)
  self.assertTrue(all(r['status']=='skipped' for r in diag['records']))
 def test_actual_unsupported_and_aggregate_mapping_skip(self):
  for kind,reason in [('unsupported','unsupported_basis_target'),('missing','explicit_component_delivery_missing_or_ambiguous')]:
   _,diag=self.exercise(kind);self.assertIn(reason,{r.get('reason') for r in diag['records']})
 def test_switch_failure_and_disagreement_leave_original_decision(self):
  off,_=self.exercise('body',enabled=False);on,diag=self.exercise('body',fail=True)
  self.assertEqual(off['decision'],on['decision']);self.assertEqual(diag['records'][0]['status'],'failed')

if __name__=='__main__':unittest.main()
