"""Synthetic full-clause/condition checks, not a semantic gold benchmark."""
import unittest
from tests.test_support_relation import wire,scope
from services.support_relation import normalize
from core.validation import ContractError
class WholeClaimTests(unittest.TestCase):
 def value(self,**kw):
  v=wire();v['citation_reviews'][0]['support_relation'].update(whole_claim_supported=True,missing_clauses=[],conditions_preserved=True,authority_scope='explanation')
  v['citation_reviews'][0]['support_relation'].update(kw);return v
 def test_true_subset_cannot_approve_complete_causal_sentence(self):
  with self.assertRaises(ContractError):normalize(self.value(whole_claim_supported=False,missing_clauses=['Unsupported system-level causal link']),'citation_reviews',[scope('unused'),scope('Synthetic: L and C exchange energy locally.')],2)
 def test_ideal_condition_cannot_disappear(self):
  with self.assertRaises(ContractError):normalize(self.value(conditions_preserved=False),'citation_reviews',[scope('unused'),scope('Synthetic: at fixed voltage, ideal capacitor has zero active power.')],2)
 def test_insufficient_with_explicit_gap_is_retained(self):
  v=self.value(whole_claim_supported=False,missing_clauses=['quantifier beyond source'],conditions_preserved=False)
  v['citation_reviews'][0]['status']='insufficient_evidence'
  out=normalize(v,'citation_reviews',[scope('unused'),scope('Synthetic: some devices use magnetic fields.')],2)
  self.assertEqual(out['citation_reviews'][0]['status'],'insufficient_evidence')
 def test_complete_limited_claim_and_legacy_profile(self):
  out=normalize(self.value(),'citation_reviews',[scope('unused'),scope('Synthetic: explicit complete qualified relationship.')],2)
  self.assertIn('source-support-relation-v2',out['citation_reviews'][0]['rationale'])
  normalize(wire(),'citation_reviews',[scope('unused'),scope('Synthetic: legacy statement.')],1)
 def test_unverified_corpus_can_explain_but_not_sole_normative_authority(self):
  s=scope('Synthetic corpus: a stated value.');s.by_wire['q'].evidence_id='e'
  s.metadata=[{'evidence_id':'e','source_type':'industry_corpus_unverified'}]
  normalize(self.value(),'citation_reviews',[scope('unused'),s],2)
  for kind in ('normative_requirement','setting','engineering_guarantee'):
   with self.assertRaises(ContractError):normalize(self.value(authority_scope=kind),'citation_reviews',[scope('unused'),s],2)
