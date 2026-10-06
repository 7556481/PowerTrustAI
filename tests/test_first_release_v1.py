"""Public synthetic fixtures: gap relevance, partial repair and semantic conditions."""
import unittest,json,asyncio,tempfile
from dataclasses import replace
from types import SimpleNamespace as NS
from pathlib import Path
from unittest.mock import patch
from tests import test_final_acceptance_v1 as previous
from tests.test_support_relation import scope
from harness.product_policy import ProductAuditPolicy
from harness.contracts import RunBudget
from core.models import *
from services.support_relation import normalize
from services.bounded_repair import GAP_MARKER

class ProductScopeTests(unittest.TestCase):
 def context(self):
  r,h=previous.RepairPolicy().run_case();rd=r.review_rounds[-1]
  q=TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Explain only the concept',engineering_context=EngineeringContext())
  return h,rd,q
 def decision(self,rd,q,answer=None,domain=None,round=1):
  return ProductAuditPolicy(synthetic_fixture=True).decide_context(rd.verification,domain or rd.domain_review,RunBudget(),round,request=q,answer=answer or rd.answer,claims=rd.verification.claims,extraction=rd.extraction,issues=(),retrieval=None)
 def test_gap_relevance_not_nonempty_list_decides(self):
  _,rd,q=self.context();answer=replace(rd.answer,missing_information=('Plant capacity unknown',))
  for applicability,kind in [('unrequested_extension',DecisionKind.PASS),('scope_note',DecisionKind.PASS),('required',DecisionKind.NEEDS_INFORMATION),('uncertain',DecisionKind.REVIEW_REQUIRED)]:
   f=DomainFinding('gap',answer.answer_id,answer.version,(),Severity.NONE,'analysis_scope','Task-bound review'+GAP_MARKER+json.dumps([{'index':0,'applicability':applicability,'reason':'Synthetic scoped condition'}]),check_status='no_issue')
   self.assertEqual(self.decision(rd,q,answer,replace(rd.domain_review,findings=(f,))).kind,kind)
  self.assertEqual(self.decision(rd,q,answer).kind,DecisionKind.REVIEW_REQUIRED)
 def test_one_repair_with_other_gap_still_reaudits_not_auto_pass(self):
  r,h=previous.RepairPolicy().run_case(remains=True);rd=r.review_rounds[0]
  missing=replace(rd.verification.findings[0],finding_id='other',claim_id='other',rationale='Missing independent evidence',bases=())
  claim=replace(rd.verification.claims[0],claim_id='other')
  review=replace(rd.verification,findings=rd.verification.findings+(missing,),claims=rd.verification.claims+(claim,))
  q=TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Explain both',engineering_context=EngineeringContext())
  p=ProductAuditPolicy(synthetic_fixture=True)
  d=p.decide_context(review,rd.domain_review,RunBudget(),0,request=q,answer=rd.answer,claims=review.claims,extraction=None,issues=(),retrieval=None)
  self.assertEqual(d.kind,DecisionKind.REVISE)
  d=p.decide_context(review,rd.domain_review,RunBudget(),1,request=q,answer=rd.answer,claims=review.claims,extraction=None,issues=(),retrieval=None)
  self.assertEqual(d.kind,DecisionKind.NEEDS_INFORMATION)
 def test_missing_engineering_not_erased_by_correctable_answer_defect(self):
  r,h=previous.RepairPolicy().run_case();rd=r.review_rounds[0]
  f=DomainFinding('input',rd.answer.answer_id,1,(),Severity.NONE,'engineering_inputs','Missing network model',missing_prerequisites=('network model',),check_status='not_assessable')
  q=TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Assess plant',engineering_context=EngineeringContext(goal='plant_assessment'))
  self.assertEqual(self.decision(rd,q,domain=replace(rd.domain_review,findings=(f,)),round=0).kind,DecisionKind.REVISE)
  final=r.review_rounds[-1]
  f=replace(f,answer_version=final.answer.version)
  self.assertEqual(self.decision(final,q,domain=replace(final.domain_review,findings=(f,))).kind,DecisionKind.NEEDS_INFORMATION)

class SemanticConditions(unittest.TestCase):
 def test_faithful_paraphrase_allowed_uncertain_never_supported(self):
  v=previous.BodyConditions().value();pair=v['citation_reviews'][0]['support_relation']['answer_conditions'][0]
  pair.update(answer_quote='while pressure is held unchanged',relationship='preserved',reason='Both specify constant pressure, without broadening to constant volume')
  a=NS(text='Warming expands gas while pressure is held unchanged',citations=[NS(start_offset=0,end_offset=59)])
  normalize(v,'citation_reviews',[scope('unused'),scope('at constant pressure, warming expands gas')],4,a)
  pair['relationship']='uncertain'
  from core.validation import ContractError
  with self.assertRaises(ContractError):normalize(v,'citation_reviews',[scope('unused'),scope('at constant pressure, warming expands gas')],4,a)
 def test_source_and_answer_excerpts_remain_literal(self):
  v=previous.BodyConditions().value();pair=v['citation_reviews'][0]['support_relation']['answer_conditions'][0];pair.update(relationship='preserved',reason='Synthetic equivalence')
  pair['source_condition']='not present in source'
  from core.validation import ContractError
  with self.assertRaises(ContractError):normalize(v,'citation_reviews',[scope('unused'),scope('at constant pressure')],4,NS(text='at constant pressure',citations=[NS(start_offset=0,end_offset=20)]))

class ServerSelection(unittest.IsolatedAsyncioTestCase):
 async def test_initial_model_load_failure_does_not_reject_audit(self):
  from backend.service import ApplicationService
  from backend.config import ServiceConfig
  from backend.store import RunStore
  from tests.test_local_nli import terminal,task
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);python=root/'python.exe';python.touch();profile=root/'profile.json';profile.write_text('{}');checkpoint=root/'checkpoint';checkpoint.mkdir()
   store=RunStore(root/'runs.sqlite3');config=ServiceConfig(profile='synthetic_fixture',run_db=root/'runs.sqlite3',nli_python=python,nli_checkpoint=checkpoint,nli_profile=profile)
   service=ApplicationService(config,store)
   async def unavailable(engine):engine.failure='model_unavailable'
   with patch('services.local_nli.LocalNLI.start',new=unavailable):
    await service.start();rid=await service.submit(task(),nli_enabled=True);await terminal(service,rid)
    self.assertEqual(store.get(rid)['status'],'finished');self.assertIsNotNone(store.get(rid)['result']['report'])
    self.assertEqual(service.nli_result(rid)['error_code'],'model_unavailable');self.assertFalse(service.nli_capability()['available'])
    await service.stop()
   store.close()
 async def test_configured_model_not_loaded_for_off_task(self):
  from backend.service import ApplicationService
  from backend.config import ServiceConfig
  from backend.store import RunStore
  from tests.test_local_nli import terminal,task
  with tempfile.TemporaryDirectory() as directory:
   store=RunStore(Path(directory)/'runs.sqlite3');svc=ApplicationService(ServiceConfig(profile='synthetic_fixture',run_db=store.path) if hasattr(store,'path') else ServiceConfig(profile='synthetic_fixture',run_db=Path(directory)/'runs.sqlite3'),store)
   with patch('services.local_nli.LocalNLI.start',side_effect=AssertionError('Off must not load')):
    await svc.start();rid=await svc.submit(task(),nli_enabled=False);await terminal(svc,rid)
    self.assertFalse(store.get(rid)['config']['local_nli_diagnostic']['enabled']);self.assertEqual(svc.nli_result(rid)['records'],[])
    await svc.stop()
   store.close()
 def test_browser_cannot_supply_model_path(self):
  from backend.api import Submit
  from pydantic import ValidationError
  with self.assertRaises(ValidationError):Submit(mode='question_answer',question='fixture',local_nli_checkpoint='C:/fake')

if __name__=='__main__':unittest.main()
