"""Public synthetic interfaces, not case-specific electrical answer rules."""
import asyncio,json,unittest
from dataclasses import replace
from tests.test_fact_rereview_v3 import inputs,response
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from core.models import VerificationStatus,AnswerDraft
from services.answer_body import validate
from core.validation import ContractError

def warrant(d,quote_ids,status='supported',conditions=None,repair=None):
 return {'source_kind':'explanatory_body','quote_ids':quote_ids,'explanation':'Synthetic bounded source assertion and full qualified proposition compared.',
 'whole_claim_supported':status=='supported','missing_clauses':[],'conditions_preserved':True,'authority_scope':'explanation',
 'answer_conditions':conditions or [],'causal_direction_preserved':True,'repair':repair}

class InterfaceTests(unittest.TestCase):
 def exercise(self,transform=None,conditional=False):
  inp=inputs(False)
  if conditional:inp=replace(inp,claims=tuple(replace(c,assertion_role='conditional') for c in inp.claims))
  seen=[]
  class Adapter:
   async def complete(self,r):
    d=json.loads(r.messages[1].content);v=response(d);seen.append(d)
    for f in v['findings']:
     for row in f['component_reviews']:
      row['support_relation']=warrant(d,[f['bases'][k]['quote_id'] for k in row['basis_indexes']])
      if conditional:row['semantic_review']['assertion_role']='asserted'
    if transform:transform(v,d)
    return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  async def go():
   with model_scope(ModelBudget(2)):
    return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13,support_relation_checks=True,support_relation_version=5).run(inp)
  return asyncio.run(go()),seen
 def test_raw_support_disagreement_is_valid_needs_review_not_execution_failure(self):
  out,seen=self.exercise(conditional=True);self.assertFalse(out.execution_issues)
  row=out.findings[0].component_reviews[0]
  self.assertEqual(row.raw_support_status,'supported');self.assertEqual(row.status,VerificationStatus.NOT_ASSESSABLE);self.assertEqual(row.review_disposition,'review_required');self.assertEqual(row.reviewed_assertion_role,'asserted')
  from harness.product_policy import ProductAuditPolicy
  from harness.contracts import RunBudget
  from agents.contracts import PowerDomainReviewOutput
  from core.models import DomainFinding,Severity,EngineeringContext,DecisionKind
  inp=inputs(False);claims=out.claims
  domain=PowerDomainReviewOutput(inp.answer.answer_id,inp.answer.version,tuple(DomainFinding('d-'+k,inp.answer.answer_id,inp.answer.version,(),Severity.NONE,k,'Synthetic scoped check completed',check_status='not_applicable') for k in ('answer_units','analysis_scope','operating_prerequisites','engineering_inputs','simulation_boundary')),())
  decision=ProductAuditPolicy().decide_context(out,domain,RunBudget(),0,request=replace(inp.request,engineering_context=EngineeringContext()),answer=inp.answer,claims=claims,extraction=None,issues=(),retrieval=None)
  self.assertEqual(decision.kind,DecisionKind.REVIEW_REQUIRED);self.assertEqual(decision.execution_integrity,'complete')
 def test_condition_id_binds_exact_range_version_without_free_source_text(self):
  def mutate(v,d):
   row=v['findings'][0]['component_reviews'][0];c=d['SOURCE_CONDITION_CANDIDATES']['candidates'][0]
   row['support_relation']['answer_conditions']=[{'condition_id':c['condition_id'],'necessity':'required','answer_quote':d['answer']['text'],'relationship':'preserved','reason':'Synthetic faithfully paraphrased body condition'}]
  out,_=self.exercise(mutate);self.assertFalse(out.execution_issues)
  from services.support_relation_v5 import relation
  binding=relation(out.findings[0].component_reviews[0].rationale)['condition_bindings'][0]
  self.assertEqual(binding['source_version'],'v1');self.assertEqual(binding['text'],inputs(False).seed_evidence[0].text)
  self.assertEqual(binding['end_offset']-binding['start_offset'],len(binding['text']))
 def test_unknown_id_rejected_not_automatically_replaced(self):
  def mutate(v,d):v['findings'][0]['component_reviews'][0]['support_relation']['answer_conditions']=[{'condition_id':'other-scope','necessity':'required','answer_quote':'','relationship':'missing','reason':'Synthetic missing'}]
  out,_=self.exercise(mutate);self.assertTrue(out.execution_issues)
 def test_missing_condition_derives_insufficient_retains_model_supported(self):
  def mutate(v,d):
   row=v['findings'][0]['component_reviews'][0];cid=d['SOURCE_CONDITION_CANDIDATES']['candidates'][0]['condition_id']
   row['support_relation']['answer_conditions']=[{'condition_id':cid,'necessity':'required','answer_quote':'','relationship':'missing','reason':'Necessary qualifier not in the actual answer'}]
   row['support_relation']['repair']={'condition_id':cid,'replacement':'Synthetic repaired complete proposition with its qualifier.'}
  out,_=self.exercise(mutate);self.assertFalse(out.execution_issues)
  row=out.findings[0].component_reviews[0];self.assertEqual(row.raw_support_status,'supported');self.assertEqual(row.status,VerificationStatus.INSUFFICIENT_EVIDENCE)
  from services.bounded_repair import eligible_repairs
  self.assertTrue(eligible_repairs(out.findings[0]))
 def test_wrong_basis_stays_illegal_despite_classification_disagreement(self):
  def mutate(v,d):
   f=v['findings'][0];f['bases']=[{'type':'answer_text_reference','anchor_id':d['ANSWER_ANCHORS'][0]['anchor_id']}]
   for r in f['component_reviews']:r.pop('support_relation',None)
  out,_=self.exercise(mutate,conditional=True);self.assertTrue(out.execution_issues)
 def test_id_leak_rejected_without_mutating_technical_text(self):
  a=AnswerDraft('a',1,'Under condition C, A causes B (e-'+'a'*64+').')
  with self.assertRaises(ContractError):validate(a)
  self.assertIn('Under condition C',a.text);validate(AnswerDraft('a',1,'Under condition C, A causes B.'))

if __name__=='__main__':unittest.main()
