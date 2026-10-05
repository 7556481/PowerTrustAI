"""Public synthetic input: clarify interface while keeping strict rejection."""
import unittest
from core.models import AnswerDraft
from services.answer_anchors import anchors
from services.claim_obligations import parse,DAILY_SYSTEM,SYSTEM
from core.validation import ContractError
class DailyPromptTests(unittest.TestCase):
 def test_invalid_math_category_still_rejected_and_body_keeps_truth_obligation(self):
  a=AnswerDraft('synthetic',1,'Synthetic physical equation P = U I.')
  v={'claims':[{'anchor_id':anchors(a)[0]['anchor_id'],'proposition':a.text,'claim_type':'technical_fact','assertion_role':'asserted','semantic_qualifiers':[],'components':[{'category':'mathematical_relation','proposition':'P = U I','basis_target':'mathematical_relation','verification_obligation':'technical_truth'}]}],'non_claims':[]}
  with self.assertRaises(ContractError):parse(v,a)
  c=v['claims'][0]['components'][0];c['category']='technical_fact';c['basis_target']='technical_content'
  out=parse(v,a);self.assertEqual(out.claims[0].component_obligations,('technical_truth',))
  self.assertNotEqual(DAILY_SYSTEM,SYSTEM);self.assertIn('NEVER a category',DAILY_SYSTEM)
 def test_generation_brevity_is_not_post_output_truncation(self):
  from agents.generation import messages_for
  from agents.contracts import GenerationInput
  from core.models import TaskRequest,TaskMode
  m=messages_for(GenerationInput(TaskRequest('synthetic',TaskMode.QUESTION_ANSWER,'fixture','中文概念'),()),3,product_guidance=True)
  self.assertIn('150-300 Chinese characters',m[0].content)
  self.assertIn('No silent evidence truncation',m[0].content)
if __name__=='__main__':unittest.main()
