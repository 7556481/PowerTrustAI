"""Regression checks for the observed lexical/subject seam, no real corpus."""
import unittest
from rag.topic_lanes import plan
from rag.chinese_terms import terms
from evaluation.natural_answer_benefit_v3_materials import N


class DiagnosticTests(unittest.TestCase):
    def test_source_mention_is_a_body_anchor(self):
        expression = plan(N[0]['question'])[0][1]
        self.assertTrue(expression.endswith('AND (("nerc"))'))
        # The source organization in a document catalog is not automatically
        # present in an otherwise relevant paragraph's body postings.
        tokens = set(terms('Load between TO and DP is modeled in MW and Mvar.'))
        self.assertIn('to', tokens)
        self.assertNotIn('nerc', tokens)

    def test_english_body_does_not_match_chinese_technical_terms(self):
        body = set(terms('Dynamic reactive resources adjust output automatically.'))
        question = set(terms('动态无功资源怎样调整输出'))
        self.assertFalse(body & question)

    def test_format_word_can_become_body_anchor(self):
        self.assertTrue(plan(N[6]['question'])[0][1].endswith('AND (("文字"))'))


if __name__ == '__main__':
    unittest.main()
