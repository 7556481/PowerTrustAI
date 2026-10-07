"""Generic syntactic query / strict source and polarity mechanisms; no API."""
import unittest
from dataclasses import replace
from services.audit_subject_query import query
from tests.test_fact_rereview_v3 import inputs
from tests.test_compact_review import response
from agents.verification_contract_v14 import ReviewCatalog
from services.operational_safety import parse,validate,baseline,VERSION
from agents.contracts import PowerDomainReviewOutput

class SubjectAndSafetyTests(unittest.TestCase):
 def test_subject_query_preserves_object_without_answer_rule(self):
  i=inputs(False);c=replace(i.claims[0],text='A converter can alter 50Hz into60Hz.',proposition='Translated normalized claim.')
  from types import SimpleNamespace as N
  f=N(claim_id=c.claim_id,status=N(value='insufficient_evidence'),component_reviews=(N(fidelity_status='faithful'),))
  self.assertEqual(query((c,),(f,)),'A converter')
  self.assertEqual(query((replace(c,text='A transformer can alter50Hz into60Hz.'),),(f,)),'A transformer')
  self.assertEqual(query((replace(c,text='Under condition C, a machine can do X.'),),(f,)),'')
 def test_danger_source_and_answer_version_strict(self):
  i=inputs(False);b=PowerDomainReviewOutput(i.answer.answer_id,i.answer.version,(),())
  row={'claim_id':i.claims[0].claim_id,'verdict':'dangerous','reason':'Synthetic damage due to removal of required fault protection','source_ids':['protection-duty']}
  out=parse({'safety_reviews':[row]},i,lambda v:b);validate(out,i.answer,i.claims)
  with self.assertRaises(ValueError):validate(out,replace(i.answer,version=i.answer.version+1),i.claims)
  with self.assertRaises(ValueError):parse({'safety_reviews':[dict(row,source_ids=['other'])]},i,lambda v:b)
  with self.assertRaises(ValueError):parse({'safety_reviews':[dict(row,source_ids=[])]},i,lambda v:b)
