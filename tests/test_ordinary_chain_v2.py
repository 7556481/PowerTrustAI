"""Public synthetic mechanism regressions, no factual model accuracy claim."""
import unittest
from services.answer_constraints import character_limit
from services.audit_subject_query import question_subject,literal_subject
from services.condition_candidates import repair_guidance
from services.claim_obligations import DAILY_SYSTEM
from services.support_relation_v5 import INSTRUCTIONS

class OrdinaryChainTests(unittest.TestCase):
 def test_explicit_suffix_and_tightest_bound(self):
  self.assertEqual(character_limit('请用中文100字以内解释'),100)
  self.assertEqual(character_limit('150字符以下',('最多80字',)),80)
  self.assertIsNone(character_limit('不少于100字；讨论200个设备'))
 def test_concept_subject_without_truth_or_answer(self):
  self.assertEqual(question_subject('什么是电感？请用80字以内说明。'),'电感')
  self.assertEqual(question_subject('电容的主要作用是什么？'),'电容')
  self.assertEqual(question_subject('What is an inductor?'),'an inductor')
  self.assertEqual(question_subject('若条件C成立，能否保证性能？'),'')
  self.assertEqual(literal_subject('A filter can convert 5 units into 9 units.'),'A filter')
  self.assertEqual(literal_subject('Under condition C, a filter can do X.'),'')
 def test_no_new_implied_obligation_and_no_fake_null_id(self):
  self.assertIn('Do not add implicit deductions',DAILY_SYSTEM)
  self.assertIn('condition_id',INSTRUCTIONS)
  self.assertIn('NON-NULL',INSTRUCTIONS)
  self.assertIn('whole repair null',INSTRUCTIONS)
 def test_null_whole_repair_is_valid_but_null_id_is_rejected(self):
  from tests.test_audit_interface_v2 import InterfaceTests
  helper=InterfaceTests()
  legal,_=helper.exercise();self.assertFalse(legal.execution_issues)
  def mutate(v,d):
   v['findings'][0]['component_reviews'][0]['support_relation']['repair']={'replacement':'Synthetic correction','condition_id':None}
  illegal,seen=helper.exercise(mutate);self.assertTrue(illegal.execution_issues)
  self.assertEqual(len(seen),2) # Existing finite correction, not ID auto-replacement.

if __name__=='__main__':unittest.main()
