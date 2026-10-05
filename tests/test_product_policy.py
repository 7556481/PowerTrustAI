"""Public synthetic_fixture product mechanisms, not semantic accuracy."""
import asyncio
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import unittest
from agents.fakes import make_fake_harness, FakeConfig
from core.models import *
from core.validation import ContractError
from harness.contracts import RunBudget
from harness.product_policy import ProductAuditPolicy
from rag.storage import KnowledgeStore,SourceMetadata
from tests.pdf_fixtures import make_pdf

class ProductTests(unittest.TestCase):
 def run_case(self,config=FakeConfig(),policy=None):
  h=make_fake_harness(config);h.policy=policy or ProductAuditPolicy(synthetic_fixture=True)
  r=asyncio.run(h.run(TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Conceptual explanation',engineering_context=EngineeringContext()),RunBudget()))
  return r,h
 def test_supported_automatically_passes(self):
  r,h=self.run_case();self.assertEqual(r.report.decision.kind,DecisionKind.PASS)
  self.assertEqual(r.report.decision.resolution,'complete')
 def test_revision_full_reextraction_and_version_decisions(self):
  r,h=self.run_case(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,VerificationStatus.SUPPORTED)))
  self.assertEqual(h.extractor.versions,[1,2]);self.assertEqual([x.report.decision.kind for x in r.review_rounds],[DecisionKind.REVISE,DecisionKind.PASS])
 def test_still_wrong_rejects_not_high_risk(self):
  r,h=self.run_case(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)))
  self.assertEqual(r.report.decision.kind,DecisionKind.REJECT);self.assertEqual(r.report.decision.risk_level,'medium')
 def test_missing_evidence_does_not_revision(self):
  r,h=self.run_case(FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)))
  self.assertEqual(r.report.decision.kind,DecisionKind.NEEDS_INFORMATION);self.assertEqual(h.extractor.versions,[1])
 def test_execution_failure_not_business_contradiction(self):
  r,h=self.run_case(FakeConfig(verification_error=True))
  self.assertEqual(r.report.decision.kind,DecisionKind.EXECUTION_INCOMPLETE);self.assertEqual(r.report.decision.risk_level,'unknown')
 def test_unvalidated_high_label_is_not_rejection(self):
  r,h=self.run_case(FakeConfig(domain_severities=(Severity.HIGH,)))
  self.assertEqual(r.report.decision.kind,DecisionKind.REVIEW_REQUIRED)
 def test_high_fixture_requires_reviewed_rule_and_literal_basis(self):
  from agents.contracts import PowerDomainReviewOutput
  class Reviewer:
   async def run(self,i):
    e=Evidence('fixture-high-e','fixture','v1','paragraph','synthetic explicit forbidden condition','synthetic_fixture')
    rule=DomainRule('fixture-reviewed-high','v1','synthetic_fixture reviewed criterion','fixture only','Mechanism only',False)
    f=DomainFinding('fixture-high',i.answer.answer_id,i.answer.version,tuple(c.claim_id for c in i.claims),Severity.HIGH,'fixture','Exact synthetic criterion',('fixture-reviewed-high',),(e.evidence_id,),bases=(TypedBasis('text_excerpt',e.evidence_id,EvidenceExcerpt(e.evidence_id,e.text,0,len(e.text))),))
    return PowerDomainReviewOutput(i.answer.answer_id,i.answer.version,(f,),(e,),rules=(rule,))
  h=make_fake_harness();h.domain_review=Reviewer();h.policy=ProductAuditPolicy(synthetic_fixture=True,high_risk_rules=('fixture-reviewed-high',))
  r=asyncio.run(h.run(TaskRequest('high',TaskMode.QUESTION_ANSWER,'synthetic_fixture','fixture'),RunBudget()))
  self.assertEqual(r.report.decision.kind,DecisionKind.REJECT);self.assertEqual(r.report.decision.risk_level,'high');self.assertEqual(h.extractor.versions,[1])
 def test_located_contradiction_can_repair_without_erasing_missing_domain_input(self):
  from agents.contracts import PowerDomainReviewOutput
  class MissingDomain:
   async def run(self,i):
    f=DomainFinding('missing',i.answer.answer_id,i.answer.version,(),Severity.LOW,'engineering_inputs','Missing context',missing_prerequisites=('context',),check_status='not_assessable')
    return PowerDomainReviewOutput(i.answer.answer_id,i.answer.version,(f,),())
  h=make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,VerificationStatus.SUPPORTED)))
  h.domain_review=MissingDomain();h.policy=ProductAuditPolicy(synthetic_fixture=True)
  r=asyncio.run(h.run(TaskRequest('partial',TaskMode.QUESTION_ANSWER,'synthetic_fixture','fixture'),RunBudget()))
  self.assertEqual([x.report.decision.kind for x in r.review_rounds],[DecisionKind.REVISE,DecisionKind.NEEDS_INFORMATION])
  self.assertEqual(h.extractor.versions,[1,2])
 def test_generation_guidance_preserves_schema_and_old_prompt(self):
  from agents.generation import messages_for
  from agents.contracts import GenerationInput
  from agents.fakes import fake_evidence
  i=GenerationInput(TaskRequest('fixture',TaskMode.QUESTION_ANSWER,'synthetic_fixture','One sentence'),(fake_evidence(),))
  old=messages_for(i,3);new=messages_for(i,3,product_guidance=True)
  self.assertNotIn('Product generation guidance',old[0].content)
  self.assertIn('explicitly attribute',new[0].content)
  self.assertEqual(old[1:],new[1:])
 def test_real_policy_rejects_empty_checks(self):
  r,h=self.run_case(policy=ProductAuditPolicy());self.assertEqual(r.report.decision.kind,DecisionKind.EXECUTION_INCOMPLETE)

class VerifiedPDFCacheTests(unittest.TestCase):
 def test_external_commit_invalidates_verified_pdf_and_no_evidence_change(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pdf=root/'fixture.pdf';pdf.write_bytes(make_pdf(['synthetic_fixture alpha condition']))
   db=root/'k.sqlite3'
   with KnowledgeStore(db) as s:ing=s.ingest(pdf,'fixture',SourceMetadata(source_type='synthetic_fixture'))
   with KnowledgeStore(db,readonly=True,validated_pdf_cache=True) as s:
    fid=s.rows(ing.knowledge_version)[0]['fragment_id'];a=s.evidence(fid,ing.knowledge_version);b=s.evidence(fid,ing.knowledge_version)
    self.assertEqual(a,b);self.assertEqual(s.pdf_validation_hits,1)
    with closing(sqlite3.connect(db)) as other:
     other.execute("UPDATE pdf_pages SET raw_text='tampered' WHERE document_id='fixture'");other.commit()
    with self.assertRaises(ContractError):s.evidence(fid,ing.knowledge_version)
class ProductionShapeTests(unittest.TestCase):
 def test_actual_schema13_and_domain4_harness_can_auto_pass(self):
  import json
  from agents.evidence_verification import ModelEvidenceVerificationAgent
  from agents.power_domain_review import ModelPowerDomainReviewAgent
  from model_adapter.contracts import ModelSettings,ModelResponse
  from services.answer_anchors import anchors
  from services.claim_obligations import parse
  from tests.test_fact_rereview_v3 import response
  from rag.retriever import AsyncSQLiteBM25Retriever
  class Extractor:
   async def extract(self,a):
    return parse({'claims':[{'anchor_id':anchors(a)[0]['anchor_id'],'proposition':a.text,'claim_type':'technical_fact','assertion_role':'asserted','semantic_qualifiers':[],'components':[{'category':'technical_fact','proposition':a.text,'basis_target':'document_body','verification_obligation':'technical_truth'}]}],'non_claims':[]},a)
  class FactAdapter:
   async def complete(self,r):return ModelResponse(json.dumps(response(json.loads(r.messages[1].content),status='supported')),r.model_id,finish_reason='stop')
  class DomainAdapter:
   async def complete(self,r):
    v={'checks':[{'check_id':key,'status':'no_issue' if key=='analysis_scope' else 'not_applicable','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule','rationale':'synthetic_fixture conceptual bounded check; no operations or quantities','missing_prerequisites':[]} for key in ('answer_units','analysis_scope','operating_prerequisites')]}
    return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);f=root/'fixture.md';f.write_text('Alpha supports voltage.','utf-8');db=root/'k.sqlite3'
   with KnowledgeStore(db) as s:k=s.ingest(f,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
   retriever=AsyncSQLiteBM25Retriever(db)
   try:
    h=make_fake_harness(FakeConfig(text='Alpha supports voltage.'));h.extractor=Extractor();h.retriever=retriever;h.policy=ProductAuditPolicy()
    h.verification=ModelEvidenceVerificationAgent(FactAdapter(),ModelSettings('synthetic_fixture'),schema_version=13)
    h.domain_review=ModelPowerDomainReviewAgent(DomainAdapter(),ModelSettings('synthetic_fixture'),protocol_version=4)
    result=asyncio.run(h.run(TaskRequest('shape',TaskMode.QUESTION_ANSWER,'synthetic_fixture','Alpha voltage',engineering_context=EngineeringContext()),RunBudget(),knowledge_version=k))
    self.assertEqual(result.report.decision.kind,DecisionKind.PASS,result.termination_reason)
    self.assertEqual(result.report.decision.execution_integrity,'complete')
   finally:retriever.close()
 def test_unexecuted_mathematical_relation_cannot_pass(self):
  from types import SimpleNamespace as NS
  f=NS(claim_id='c',finding_id='f',status=VerificationStatus.SUPPORTED,bases=(),component_reviews=())
  c=NS(claim_id='c',claim_type='technical_fact',assertion_role='asserted',components=(NS(component_id='p'),),component_basis_targets=('mathematical_relation',))
  v=NS(findings=(f,),execution_issues=(),citation_reviews=(),consistency_checks=())
  d=NS(findings=(NS(finding_id='d',severity=Severity.NONE,check_status='no_issue',category='fixture',rationale='synthetic fixture',missing_prerequisites=()),),execution_issues=(),consistency_checks=(),rules=())
  a=NS(citations=(),missing_information=())
  r=ProductAuditPolicy(synthetic_fixture=True).decide_context(v,d,RunBudget(),0,request=NS(engineering_context=EngineeringContext()),answer=a,claims=(c,),extraction=None,issues=(),retrieval=None)
  self.assertEqual(r.kind,DecisionKind.NEEDS_INFORMATION);self.assertEqual(r.reason_codes,('REGISTERED_CALCULATION_REQUIRED',))
