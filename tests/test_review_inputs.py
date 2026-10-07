"""Declared capabilities and centralized compatibility; no protocol guessing in Harness."""
import unittest
from types import SimpleNamespace
from dataclasses import fields
from tests.test_fact_rereview_v3 import inputs
from agents.contracts import EvidenceVerificationInput,ReliabilityVerificationInput
from services.review_inputs import build,ReviewInputContractError

class InputTests(unittest.TestCase):
 def base(self):
  v=inputs(False);return EvidenceVerificationInput(**{f.name:getattr(v,f.name) for f in fields(EvidenceVerificationInput)})
 def test_declared_extended_contract_independent_of_schema_number(self):
  b=self.base();out=build(SimpleNamespace(schema_version=900,review_input_type=ReliabilityVerificationInput),b,delivery_summary='actual delivery')
  self.assertIsInstance(out,ReliabilityVerificationInput);self.assertIs(out.answer,b.answer);self.assertEqual(out.delivery_summary,'actual delivery')
 def test_historical_injected_schema13_still_extended(self):self.assertIsInstance(build(SimpleNamespace(schema_version=13),self.base()),ReliabilityVerificationInput)
 def test_incompatible_declared_contract_rejected(self):
  with self.assertRaises(ReviewInputContractError):build(SimpleNamespace(review_input_type=dict),self.base())
