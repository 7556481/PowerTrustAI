import unittest
from copy import deepcopy
from evaluation import rule_chain_trial_v1 as rule
from tests.test_requirement_review_v3 import fixture,prediction


class RuleChainTests(unittest.TestCase):
    def test_input_scope_preserved_without_gold_or_hidden_scope_id(self):
        card={'question':'question','requirements':[{'id':'R1','model_visible_task_requirement':'mapping'},
            {'id':'R2','model_visible_task_requirement':'rule'}],'candidate_reference':'GOLD_SECRET',
            'evidence':[{'id':'e1','text':'definition','url':'fixture','locator':'def','text_basis':'fixture'},
            {'id':'e2','text':'rule','url':'fixture','locator':'rule','text_basis':'fixture',
             'scope_context':[{'id':'scope','text':'scope complete','url':'fixture',
                              'locator':'parent','text_basis':'fixture'}]}]}
        task=rule.model_input(card,{'id':'sample','answer':'Answer.',
                                    'proposed_completeness':'GOLD_SECRET'})
        self.assertEqual(task['evidence'][1]['scope_context'][0]['text'],'scope complete')
        self.assertNotIn('id',task['evidence'][1]['scope_context'][0])
        self.assertNotIn('GOLD_SECRET',rule.canonical(task))
        self.assertIs(rule.PROMPT,rule.base.PROMPT)

    def test_reviewer_reconstruction_does_not_mechanically_fill_missing_R1(self):
        task=fixture();value=prediction(task)
        value['requirements'][0].update(coverage='missing',unit_ids=[],
            rationale='Reviewer can derive the mapping, but answer omits it.')
        result=rule.parse(value,task)
        self.assertEqual(result['requirements'][0]['coverage'],'missing')
        self.assertEqual(result['program_coverage']['value'],'incomplete')

    def test_unsupported_lifespan_does_not_erase_covered_requirements(self):
        task=fixture();value=prediction(task)
        j=deepcopy(value['units'][0]['judgments'][0])
        j.update(proposition='Signs last ten years.',support='insufficient_evidence',basis_ids=[])
        value['units'][0]['composition']='multiple'
        value['units'][0]['judgments'].append(j)
        result=rule.parse(value,task)
        self.assertEqual(result['program_coverage']['value'],'complete')


if __name__=='__main__':unittest.main()
