import unittest
from evaluation.reviewer_remaining8_v5 import validate, IDS
from tests.test_premise_bound_review_v4 import fixture


class RemainingEightTests(unittest.TestCase):
    def tasks(self):
        tasks=[fixture(s) for s in IDS]
        for t in tasks:
            if t['sample_id'].startswith('H-SI'):
                t['requirements'].append({'requirement_id':'R3','description':'fixture'})
        return tasks

    def test_exact_eight_with_three_requirement_inputs(self): validate(self.tasks())

    def test_no_A04_extra_reordered_or_missing_case(self):
        tasks=self.tasks()
        for wrong in [tasks[:-1],tasks+[fixture('H-MIT-001-A04')],list(reversed(tasks))]:
            with self.assertRaises(AssertionError):validate(wrong)

    def test_no_label_fields_and_no_rewritten_units(self):
        for edit in ['labels','units']:
            tasks=self.tasks()
            if edit=='labels':tasks[0]['expected_support']='SECRET'
            else:tasks[0]['answer_units'][0]['text']='changed'
            with self.assertRaises(AssertionError):validate(tasks)
