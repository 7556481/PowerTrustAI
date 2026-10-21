import unittest
from evaluation.reviewer_fixed_batch_v1 import make_task, validate
from evaluation import premise_bound_review_v4 as protocol
from tests.test_premise_bound_review_v4 import fixture, prediction


class FixedBatchTests(unittest.TestCase):
    def test_three_requirements_are_preserved_without_expected_labels(self):
        card={'question':'fixture', 'source_url':'fixture',
              'requirements':[{'id':'R'+str(i),'requirement':'task '+str(i),
                               'expected':'SECRET_EXPECTATION'} for i in range(1,4)],
              'evidence_snapshot':{'candidate_excerpt_id':'E1','normalized_text':'fixture',
                  'pdf_page_1based':1,'printed_page':None,'locator':'fixture',
                  'source_sha256':'fixture'},'expected':'SECRET_EXPECTATION'}
        task=make_task(card,{'candidate_id':'fixture','answer':'合成回答。',
                             'expected':'SECRET_EXPECTATION'})
        self.assertEqual(len(task['requirements']),3)
        self.assertNotIn('SECRET_EXPECTATION',str(protocol.messages(task)))

    def test_wrong_fixed_plan_rejected(self):
        with self.assertRaises(AssertionError): validate([])
        with self.assertRaises(AssertionError): validate([fixture()]*12)

    def test_protocol_preserves_three_requirements(self):
        task=fixture();task['requirements'].append({'requirement_id':'R3','description':'fixture'})
        result=protocol.parse(prediction(task),task)
        self.assertEqual(len(result['requirements']),3)
