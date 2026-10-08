"""Synthetic selection contract; ID safety is separate from semantic accuracy."""
import unittest,asyncio,json
from dataclasses import replace
from tests import test_fact_rereview_v3 as fixture
from tests.test_audit_interface_v2 import warrant
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from services.support_relation_v5 import relation
from core.models import Evidence,VerificationStatus
class SelectionV6Tests(unittest.TestCase):
 def run_case(self,invalid=None):
  inp=fixture.inputs(False,two=True);inp=replace(inp,seed_evidence=inp.seed_evidence+(Evidence('synthetic-second-body','synthetic-source2','v1','synthetic chars','A separate synthetic source mentions the three categories.','synthetic_fixture'),))
  seen=[]
  class Adapter:
   async def complete(self,req):
    d=json.loads(req.messages[1].content);seen.append(d);v=fixture.response(d)
    for i,f in enumerate(v['findings']):
     q=d['QUOTE_CANDIDATES'][0 if i==0 else -1]['quote_id'];f['bases']=[{'type':'text_excerpt','quote_id':q}]
     for row in f['component_reviews']:
      row['basis_indexes']=[0];row['support_relation']=warrant(d,[q])
      if i==0 and invalid=='duplicate':row['support_relation']['quote_ids']=['alien']
      if i==0 and invalid=='condition':
       wrong=next(c for c in d['SOURCE_CONDITION_CANDIDATES']['candidates'] if c['quote_id']!=q)
       row['support_relation']['answer_conditions']=[{'condition_id':wrong['condition_id'],'necessity':'required','answer_quote':'','relationship':'missing','reason':'Synthetic cross-component borrowing is forbidden'}]
    return ModelResponse(json.dumps(v),req.model_id,finish_reason='stop')
  async def go():
   with model_scope(ModelBudget(2)):return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13,support_relation_checks=True,support_relation_version=6).run(inp)
  return asyncio.run(go()),seen
 def test_program_binds_two_distinct_local_selections(self):
  r,d=self.run_case();self.assertFalse(r.execution_issues)
  a,b=[relation(f.component_reviews[0].rationale)['quote_ids'] for f in r.findings]
  self.assertNotEqual(a,b)
  self.assertEqual(a,[d[0]['QUOTE_CANDIDATES'][0]['quote_id']]);self.assertEqual(b,[d[0]['QUOTE_CANDIDATES'][-1]['quote_id']])
 def test_illegal_duplicate_model_field_not_replaced_valid_peer_retained(self):
  r,_=self.run_case('duplicate');self.assertTrue(r.execution_issues);self.assertEqual(r.findings[1].status,VerificationStatus.SUPPORTED)
 def test_condition_cannot_borrow_an_unselected_body_carrier(self):
  r,_=self.run_case('condition');self.assertTrue(r.execution_issues);self.assertEqual(r.findings[1].status,VerificationStatus.SUPPORTED)
