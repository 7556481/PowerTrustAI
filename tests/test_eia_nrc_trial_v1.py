import unittest
from evaluation.eia_nrc_trial_v1 import validate, ORDER
from tests.test_premise_bound_review_v4 import fixture


class TrialGateTests(unittest.TestCase):
    def tasks(self):return [fixture(s) for s in ORDER]

    def test_exact_interleaved_order_accepted(self):validate(self.tasks())

    def test_wrong_order_missing_extra_cases_rejected(self):
        tasks=self.tasks()
        for wrong in [list(reversed(tasks)),tasks[:-1],tasks+[fixture('extra')]]:
            with self.assertRaises(ValueError):validate(wrong)

    def test_labels_and_reference_units_rejected(self):
        for key in ['expected_support','reference_units','sample_role']:
            tasks=self.tasks();tasks[0][key]='SECRET'
            with self.assertRaises(ValueError):validate(tasks)

    def test_reference_requirement_reason_rejected(self):
        tasks=self.tasks();tasks[0]['requirements'][0]['rationale']='SECRET'
        with self.assertRaises(ValueError):validate(tasks)
