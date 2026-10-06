"""Public synthetic fixture: compact selection, strict scope and valid objections."""
import asyncio,json,unittest
from copy import deepcopy
from dataclasses import replace
from tests.test_fact_rereview_v3 import inputs
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.verification_contract_v14 import ReviewCatalog,MARKER,SYSTEM
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from core.models import VerificationStatus as V

def response(payload):
 return {'judgments':[{'target_id':t['target_id'],'status':'supported' if t['allowed_basis_ids'] else 'insufficient_evidence','basis_ids':t['allowed_basis_ids'][:1],
  'reason':'Synthetic full target supported by literal delivered basis','conditions':[],'objection':None,'repair':None,'requires_authoritative_source':False} for t in payload['targets']]}

class CompactTests(unittest.TestCase):
 def exercise(self,mutate=None,inp=None):
  seen=[];inp=inp or inputs(True)
  class Adapter:
   async def complete(self,r):
    d=json.loads(r.messages[1].content);v=response(d);seen.append((r,d))
    if mutate:mutate(v,d,r.correction)
    return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  async def go():
   with model_scope(ModelBudget(6)):
    return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=14).run(inp)
  return asyncio.run(go()),seen
 def test_flat_targets_no_repeated_parent_or_basis_type(self):
  out,seen=self.exercise();self.assertFalse(out.execution_issues);self.assertEqual(len(seen),2)
  self.assertEqual(out.findings[0].status,V.SUPPORTED);self.assertIn(MARKER,out.citation_reviews[0].rationale)
  self.assertNotIn('source_kind',response(seen[0][1])['judgments'][0]);self.assertNotIn('basis_indexes',SYSTEM)
  from backend.assembly import ComponentFactory
  from backend.config import ServiceConfig
  self.assertEqual(ComponentFactory(ServiceConfig(profile='synthetic_fixture',verification_schema=14)).manifest(None)['template_sha256']['independent'],__import__('hashlib').sha256(SYSTEM.encode()).hexdigest())
 def test_old_duplicate_fields_rejected_not_silently_removed(self):
  def mutate(v,d,c):v['judgments'][0]['source_kind']='explanation'
  out,_=self.exercise(mutate);self.assertTrue(out.execution_issues)
 def test_unknown_or_cross_target_basis_rejected(self):
  def mutate(v,d,c):v['judgments'][0]['basis_ids']=['S1B0'] if d['targets'][0]['kind']=='fact' else ['S0B0']
  out,_=self.exercise(mutate);self.assertTrue(out.execution_issues)
 def test_real_objection_is_valid_and_raw_support_retained(self):
  def mutate(v,d,c):
   if d['targets'][0]['kind']=='fact':v['judgments'][0]['objection']={'kind':'fidelity','reason':'Synthetic extraction deleted literal qualification'}
  out,_=self.exercise(mutate);self.assertFalse(out.execution_issues);r=out.findings[0].component_reviews[0]
  self.assertEqual(r.raw_support_status,'supported');self.assertEqual(r.status,V.NOT_ASSESSABLE);self.assertEqual(r.fidelity_status,'disputed')
 def test_lost_condition_derived_and_source_bound_repair(self):
  def mutate(v,d,c):
   if d['targets'][0]['kind']=='fact':
    r=v['judgments'][0];b=r['basis_ids'][0];r['conditions']=[{'basis_id':b,'required':True,'answer_quote':'','preserved':False}];r['repair']={'basis_id':b,'replacement':'Synthetic complete target with its necessary qualification.'}
  out,_=self.exercise(mutate);self.assertFalse(out.execution_issues);r=out.findings[0].component_reviews[0]
  self.assertEqual(r.status,V.INSUFFICIENT_EVIDENCE)
  from services.bounded_repair import eligible_repairs
  self.assertTrue(eligible_repairs(out.findings[0]))
 def test_review_note_cannot_supply_answer_condition(self):
  def mutate(v,d,c):
   r=v['judgments'][0];r['conditions']=[{'basis_id':r['basis_ids'][0],'required':True,'answer_quote':'Not in the current answer','preserved':True}]
  out,_=self.exercise(mutate);self.assertTrue(out.execution_issues)
 def test_partial_peer_retained_and_one_stage_correction(self):
  def mutate(v,d,c):
   if d['targets'][0]['kind']=='fact':v['judgments'][0]['basis_ids']=['illegal']
  out,seen=self.exercise(mutate,inputs(False,True));self.assertTrue(out.execution_issues)
  self.assertEqual(len(seen),2);self.assertEqual(out.findings[1].status,V.SUPPORTED);self.assertEqual(out.findings[0].component_reviews[0].origin,'execution_incomplete')
 def test_program_unknown_metadata_cannot_be_sole_authority(self):
  inp=inputs(False);inp=replace(inp,generation_snapshot=None,seed_evidence=tuple(replace(e,source_type='industry_corpus_unverified') for e in inp.seed_evidence))
  def mutate(v,d,c):v['judgments'][0]['requires_authoritative_source']=True
  out,_=self.exercise(mutate,inp);self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status,V.INSUFFICIENT_EVIDENCE)
 def test_default_nli_unchanged_and_no_model_path_input(self):
  from backend.config import ServiceConfig
  self.assertFalse(ServiceConfig().nli_enabled);self.assertEqual(ServiceConfig().fact_strategy,'aggregate')

if __name__=='__main__':unittest.main()
