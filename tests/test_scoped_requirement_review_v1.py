import unittest
from evaluation import scoped_requirement_review_v1 as scoped
from evaluation import requirement_review_v3 as base
from tests.test_requirement_review_v3 import fixture, prediction


class ScopedRequirementTests(unittest.TestCase):
    def test_boundary_is_not_a_requirement_and_labels_are_hidden(self):
        card = {'question': 'question', 'requirements': [
            {'id': 'R1', 'model_visible_task_requirement': 'isolation'},
            {'id': 'R2', 'model_visible_task_requirement': 'breaking'}],
            'conditional_support_boundary': {'trigger': 'extra capability',
                'requirement': 'preserve limits', 'mandatory_coverage_item': False},
            'source_pdf_sha256': 'fixture', 'evidence': []}
        task = scoped.model_input(card, {'id': 'sample', 'answer': 'Answer.',
            'proposed_support': 'SECRET_EXPECTATION'}, {})
        self.assertEqual(len(task['requirements']), 2)
        self.assertEqual(len(task['conditional_support_boundaries']), 1)
        self.assertNotIn('SECRET_EXPECTATION', scoped.canonical(task))
        self.assertEqual(''.join(u['text'] for u in task['answer_units']), task['answer'])

    def test_parser_is_unchanged_strict_v3(self):
        self.assertIs(scoped.parse, base.parse)
        task = fixture()
        result = scoped.parse(prediction(task), task)
        self.assertEqual(result['program_coverage']['value'], 'complete')

    def test_prompt_preserves_conditional_and_separate_support(self):
        self.assertIn('not extra mandatory coverage requirements', scoped.PROMPT)
        self.assertIn('Assess any added capability or safety guarantee separately', scoped.PROMPT)


if __name__ == '__main__':
    unittest.main()
