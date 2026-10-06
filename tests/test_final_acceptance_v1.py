"""Public synthetic fixtures; different topics, no electrical answer hardcoding."""
import unittest,json,asyncio
from types import SimpleNamespace as NS
from dataclasses import replace
from tests.test_support_relation_v2 import WholeClaimTests
from tests.test_support_relation import scope
from services.support_relation import normalize,instructions
from core.validation import ContractError
from core.models import *
from harness.product_policy import ProductAuditPolicy
from harness.contracts import RunBudget
from agents.fakes import make_fake_harness,FakeConfig
from backend.presentation import unresolved_items
class BodyConditions(unittest.TestCase):
 def value(self):
  v=WholeClaimTests().value();r=v['citation_reviews'][0]['support_relation']
  r.update(answer_conditions=[{'source_quote_id':'q','source_condition':'at constant pressure','answer_quote':'at constant pressure'}],causal_direction_preserved=True,repair=None)
  return v
 def runvalue(self,v,body):
  a=NS(text=body,citations=[NS(start_offset=0,end_offset=len(body))])
  return normalize(v,'citation_reviews',[scope('unused'),scope('Synthetic: at constant pressure, warming expands a gas.')],3,a)
 def test_condition_is_in_body_not_review_notes(self):
  v=self.value();v['citation_reviews'][0]['applicability_conditions']=['at constant pressure']
  with self.assertRaises(ContractError):self.runvalue(v,'Warming expands the gas.')
  self.runvalue(self.value(),'At fixed conditions: at constant pressure, warming expands the gas.')
 def test_answer_ratio_cannot_stand_in_for_a_qualifier(self):
  v=self.value();v['citation_reviews'][0]['support_relation']['answer_conditions'][0]['answer_quote']='Warming expands gas'
  with self.assertRaises(ContractError):self.runvalue(v,'Warming expands gas')
 def test_product_limit_rejects_overlong_whole_answer_without_cutting(self):
  from services.answer_constraints import product_default_limit,validate_length
  request=TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','简要解释概念',engineering_context=EngineeringContext())
  answer=AnswerDraft('a',1,'字'*301)
  with self.assertRaises(ContractError):validate_length(answer,request.question,default_limit=product_default_limit(request))
  self.assertEqual(len(answer.text),301)
 def test_converse_cannot_be_supported(self):
  v=self.value();v['citation_reviews'][0]['support_relation']['causal_direction_preserved']=False
  with self.assertRaises(ContractError):self.runvalue(v,'at constant pressure')
 def test_repair_requires_selected_literal_body(self):
  v=self.value();v['citation_reviews'][0]['status']='insufficient_evidence';r=v['citation_reviews'][0]['support_relation'];r['conditions_preserved']=False;r['answer_conditions'][0]['answer_quote']=''
  r['repair']={'replacement':'At constant pressure, warming expands gas.','source_quote_id':'q','source_excerpt':'at constant pressure'}
  self.runvalue(v,'Warming always expands gas.')
  r['repair']['source_excerpt']='invented material'
  with self.assertRaises(ContractError):self.runvalue(v,'Warming always expands gas.')
 def test_instructions_forbid_reverse_and_detail_condition_substitute(self):
  self.assertIn('A->B does not prove B->A',instructions(3));self.assertIn('reviewer applicability_conditions',instructions(3))
class RepairPolicy(unittest.TestCase):
 def run_case(self,with_source=True,execution_error=False,remains=False):
  h=make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,VerificationStatus.INSUFFICIENT_EVIDENCE if remains else VerificationStatus.SUPPORTED),verification_error=execution_error))
  h.policy=ProductAuditPolicy(synthetic_fixture=True);original=h.verification.run
  async def review(i):
   out=await original(i)
   if i.answer.version==1 and with_source:
    text='Synthetic: under condition C, effect E follows cause A.'
    e=Evidence('repair-e','fixture','v1','paragraph',text,'synthetic_fixture')
    relation={'repair':{'replacement':'Under C, A causes E.','source_quote_id':'q','source_excerpt':text}}
    f=out.findings[0];f=replace(f,rationale='Located qualifier loss [source-support-relation-v3] '+json.dumps(relation),bases=(TypedBasis('text_excerpt',e.evidence_id,EvidenceExcerpt(e.evidence_id,text,0,len(text))),))
    out=replace(out,findings=(f,),evidence=out.evidence+(e,))
   return out
  h.verification.run=review
  result=asyncio.run(h.run(TaskRequest('repair-fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Explain the conditional mechanism',engineering_context=EngineeringContext()),RunBudget()))
  return result,h
 def test_explicit_bound_repair_reextracts_and_reaudits(self):
  r,h=self.run_case();self.assertEqual(h.extractor.versions,[1,2]);self.assertEqual([x.report.decision.kind for x in r.review_rounds],[DecisionKind.REVISE,DecisionKind.PASS])
 def test_single_repair_cannot_turn_remaining_gap_into_pass(self):
  r,h=self.run_case(remains=True);self.assertEqual(h.extractor.versions,[1,2]);self.assertEqual(r.report.decision.kind,DecisionKind.NEEDS_INFORMATION)
 def test_old_policy_does_not_acquire_new_repair_behavior(self):
  r,h=self.run_case();round=r.review_rounds[0];request=TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','fixture',engineering_context=EngineeringContext())
  d=ProductAuditPolicy(synthetic_fixture=True,version='product-decision-v1.1').decide_context(round.verification,round.domain_review,RunBudget(),0,request=request,answer=round.answer,claims=round.verification.claims,extraction=round.extraction,issues=(),retrieval=None)
  self.assertEqual(d.kind,DecisionKind.NEEDS_INFORMATION)
 def test_missing_basis_is_not_repairable(self):
  r,h=self.run_case(False);self.assertEqual(r.report.decision.kind,DecisionKind.NEEDS_INFORMATION);self.assertEqual(h.extractor.versions,[1])
 def test_execution_failure_is_not_a_repair(self):
  r,h=self.run_case(execution_error=True);self.assertEqual(r.report.decision.kind,DecisionKind.EXECUTION_INCOMPLETE)
 def test_missing_engineering_input_blocks_new_evidence_gap_repair(self):
  from agents.contracts import PowerDomainReviewOutput
  from services.bounded_repair import repair_proposals
  r,h=self.run_case();round=r.review_rounds[0]
  f=DomainFinding('missing',round.answer.answer_id,1,(),Severity.NONE,'engineering_inputs','Missing plant model',missing_prerequisites=('model',),check_status='not_assessable')
  d=replace(round.domain_review,findings=(f,))
  request=TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Plant performance',engineering_context=EngineeringContext(goal='plant_assessment'))
  decision=h.policy.decide_context(round.verification,d,RunBudget(),0,request=request,answer=round.answer,claims=round.verification.claims,extraction=round.extraction,issues=(),retrieval=None)
  self.assertEqual(decision.kind,DecisionKind.NEEDS_INFORMATION)
class PresentationTests(unittest.TestCase):
 def test_unresolved_uses_actual_current_sentence_not_generic_engineering(self):
  r={'answer':{'final':{'text':'Synthetic question answer.'}},'snapshots':{'extraction':{'claims':[{'claim_id':'c','text':'Actual sentence.'}]}},'findings':{'model_fact':[{'claim_id':'c','status':'insufficient_evidence','rationale':'Causal direction not established','finding_id':'f'}]}}
  self.assertEqual(unresolved_items(r)[0]['sentence'],'Actual sentence.');self.assertIn('Causal direction',unresolved_items(r)[0]['reason'])
