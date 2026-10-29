import unittest
from dataclasses import replace
from backend.config import ServiceConfig
from unittest.mock import patch
from tests import test_schema14_factory_flow as old

class DeferredEvidenceTests(unittest.TestCase):
 def test_contract_restrictions(self):
  c=replace(ServiceConfig(),audit_evidence_profile='deferred_subject_v1')
  self.assertEqual((c.audit_strategy,c.fact_review_contract,c.local_revision_interface),('baseline','production','production'))
  for kw in ({'verification_schema':14},{'fact_review_execution':'citation_pair_v1'},{'retrieval_execution_profile':'selective_match_v1'}):
   with self.assertRaises(ValueError):replace(c,**kw)
 def test_actual_factory_revision_full_reaudit_and_store(self):
  real=old.ServiceConfig
  def config(*a,**k):return real(*a,**k,audit_evidence_profile='deferred_subject_v1')
  with patch.object(old,'ServiceConfig',side_effect=config):r,p,_=old.FactoryFlowTests().exercise(schema=13,subject=True)
  self.assertEqual(len(r['review_rounds']),2)
  self.assertEqual(len(r['answer']['versions']),2)
  self.assertTrue(any(x['query']=='A device' for x in r['retrieval']))
 def test_source_hazard_not_skipped(self):
  real=old.ServiceConfig
  with patch.object(old,'ServiceConfig',side_effect=lambda *a,**k:real(*a,**k,audit_evidence_profile='deferred_subject_v1')):
   r,_,_=old.FactoryFlowTests().exercise(schema=13,hazard=True)
  self.assertEqual(r['decision']['kind'],'reject')

 def test_generation_snapshot_actual_domain_reuse(self):
  real=old.ServiceConfig
  with patch.object(old,'ServiceConfig',side_effect=lambda *a,**k:real(*a,**k,audit_evidence_profile='deferred_subject_v1')):
   r,_,_=old.FactoryFlowTests().exercise(schema=13)
  self.assertTrue(any(x['query_method']=='production-evidence-reuse-v1' for x in r['retrieval']))
  self.assertTrue(any(x['purpose']=='verification' and x['query'] for x in r['retrieval']))
  self.assertFalse(any(x['purpose']=='domain_review' and x['query'] for x in r['retrieval']))

 def test_explicit_domain_gap_executes_original_search_and_rereview(self):
  import json
  from model_adapter.contracts import ModelResponse
  real=old.ServiceConfig;original=old.SyntheticProvider.complete;counts={'domain':0}
  async def response(provider,r):
   out=await original(provider,r)
   if r.prompt_version.startswith('power-domain-review'):
    counts['domain']+=1
    if counts['domain']==1:
     d=json.loads(out.text);d['checks'][0]['status']='not_assessable';d['checks'][0]['rationale']='Synthetic explicit gap needing independently supplied body.'
     return ModelResponse(json.dumps(d),r.model_id,finish_reason='stop')
   return out
  with patch.object(old,'ServiceConfig',side_effect=lambda *a,**k:real(*a,**k,audit_evidence_profile='deferred_subject_v1')),patch.object(old.SyntheticProvider,'complete',response):
   r,_,_=old.FactoryFlowTests().exercise(schema=13)
  self.assertEqual(counts['domain'],2)
  self.assertTrue(any(x['purpose']=='domain_review' and x['query'] for x in r['retrieval']))
  self.assertTrue(any(x['query_method']=='production-evidence-reuse-v1' for x in r['retrieval']))

 def test_outside_declared_scope_retains_pre_subject_search(self):
  real=old.ServiceConfig
  with patch.object(old,'ServiceConfig',side_effect=lambda *a,**k:real(*a,**k,audit_evidence_profile='deferred_subject_v1')):
   r,p,_=old.FactoryFlowTests().exercise(schema=13,subject=True,no_goal=True)
  first=next(d for d in p.payloads if 'claims' in d and 'QUOTE_CANDIDATES' in d)
  self.assertTrue(any(old.GOOD_FREQUENCY in q['text'] for q in first['QUOTE_CANDIDATES']))
  self.assertFalse(any(x['query_method']=='production-evidence-reuse-v1' for x in r['retrieval']))
 def test_smoke_budget_receipt_is_unique_and_rejects_unknown(self):
  import tempfile,json
  from pathlib import Path
  from harness.acceptance_budget import acceptance_factory
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'receipt.json';v=dict(version='production-supply-smoke-budget-v1',calls=12,tokens=1000,pending=[],cap=240,threshold=4000000);p.write_text(json.dumps(v))
   self.assertEqual(acceptance_factory(ServiceConfig(),p).config.audit_strategy,'baseline')
   with self.assertRaises(ValueError):acceptance_factory(ServiceConfig(),p)
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'receipt.json';v['pending']=[13];p.write_text(json.dumps(v))
   with self.assertRaises(ValueError):acceptance_factory(ServiceConfig(),p)

 def test_revised_round_fallback_clears_previous_reuse_flag(self):
  import asyncio
  from types import SimpleNamespace as NS
  from harness.production_supply_v1 import domain_supply
  async def original(purpose):return 'original-domain'
  ex=NS(active_snapshot=None,original_evidence=(),vd=NS(issue=None),domain_reused=True,retrieve_for=original)
  self.assertEqual(asyncio.run(domain_supply(ex)),'original-domain')
  self.assertFalse(ex.domain_reused)
