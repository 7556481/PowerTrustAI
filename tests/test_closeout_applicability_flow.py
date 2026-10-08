"""Public synthetic_fixture, actual Factory/Harness/parser/Store/API, no model API."""
import unittest,json
from tests.test_schema14_factory_flow import FactoryFlowTests
from services.task_applicability import MARKER
class ApplicabilityFactoryTests(unittest.TestCase):
 def go(self,**kwargs):return FactoryFlowTests().exercise(schema=13,**kwargs)[0]
 def scope(self,r):
  f=next(f for f in r['findings']['domain'] if f['category']=='analysis_scope')
  return json.loads(f['rationale'].rsplit(MARKER,1)[1])
 def test_no_goal_concept_does_not_require_plant_or_simulation(self):
  r=self.go(no_goal=True,concept=True)
  self.assertEqual(self.scope(r)['scope'],'conceptual');self.assertEqual(r['decision']['kind'],'pass')
  checks={f['category']:f['check_status'] for f in r['findings']['domain']}
  for k in ['engineering_inputs','input_units:units-input','simulation_boundary']:self.assertEqual(checks[k],'not_applicable')
 def test_no_goal_engineering_keeps_required_input_analysis(self):
  r=self.go(no_goal=True,task_scope='engineering')
  self.assertTrue(r['execution']['required_stages_complete']);self.assertNotEqual(r['decision']['kind'],'pass')
  self.assertEqual(next(f for f in r['findings']['domain'] if f['category']=='simulation_boundary')['check_status'],'not_assessable')
 def test_conceptual_selection_does_not_exempt_asserted_guarantee(self):
  r=self.go(guarantee=True,task_scope='engineering')
  self.assertEqual(self.scope(r)['scope'],'engineering');self.assertNotEqual(r['decision']['kind'],'pass')
 def test_real_scope_uncertainty_retained_not_defaulted(self):
  r=self.go(no_goal=True,task_scope='uncertain')
  self.assertEqual(self.scope(r)['scope'],'uncertain');self.assertEqual(r['decision']['kind'],'review_required')
 def test_pure_evidence_gap_not_scope_classifier_override(self):
  r=self.go(no_goal=True,evidence_gap=True)
  self.assertTrue(r['execution']['required_stages_complete']);self.assertNotEqual(r['decision']['kind'],'pass')
 def test_multiple_claims_and_isolated_original_scopes(self):
  r=self.go(existing=True,two=True,no_goal=True)
  self.assertTrue(r['execution']['required_stages_complete']);self.assertEqual(len(r['findings']['original_citations']),2)
 def test_illegal_source_id_is_rejected_and_peer_preserved(self):
  r=self.go(existing=True,two=True,illegal=True,no_goal=True)
  self.assertFalse(r['execution']['required_stages_complete']);self.assertNotEqual(r['decision']['kind'],'pass')
  self.assertTrue(any(f['status']=='supported' for f in r['findings']['model_fact']))

 def test_scope_note_and_task_scope_records_both_remain_readable(self):
  r=self.go(no_goal=True,scope_note=True)
  self.assertEqual(r['decision']['kind'],'pass')
  self.assertEqual(self.scope(r)['scope'],'conceptual')
