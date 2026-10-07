"""Regression for historical gap: explicit capability now reaches the parser."""
import asyncio,unittest
from dataclasses import replace
from agents.fakes import make_fake_harness
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings
from harness.contracts import RunBudget
from tests.test_fact_rereview_v3 import inputs

class KnownGap(unittest.TestCase):
 def test_schema14_actual_harness_receives_extended_input(self):
  inp=inputs(False);calls=[]
  class Adapter:
   async def complete(self,r):calls.append(r);raise AssertionError('No remote request expected')
  class Extractor:
   async def extract(self,answer):return inp.claims
  h=make_fake_harness();h.verification=ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=14);h.extractor=Extractor()
  result=asyncio.run(h.run(replace(inp.request,provided_evidence=inp.seed_evidence),RunBudget()))
  self.assertTrue(calls)
  self.assertFalse(any('has no attribute' in i.message for i in result.execution_issues))
  self.assertNotEqual(getattr(result.report.decision,'kind',None),'pass')

if __name__=='__main__':unittest.main()
