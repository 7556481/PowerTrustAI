import unittest
from copy import deepcopy
from evaluation.format_stability_inputs_v1 import build, prepare
from evaluation import premise_bound_review_v6 as v6, premise_bound_review_v7 as v7


class FormatPreparationTests(unittest.TestCase):
    def test_four_fixed_pairs_balanced(self):
        order = prepare(build())
        self.assertEqual([r['arm'] for r in order],
                         ['v6','v7','v7','v6','v6','v7','v7','v6'])
        self.assertEqual(len({r['request_id'] for r in order}), 8)
        for i in range(0,8,2):
            self.assertEqual(order[i]['task_sha256_utf8'],order[i+1]['task_sha256_utf8'])

    def test_messages_differ_only_system_prompt(self):
        for task in build():
            self.assertEqual(v6.messages(task)[1:],v7.messages(task)[1:])
        self.assertIs(v6.parse,v7.parse)

    def test_expected_fields_cannot_be_added(self):
        tasks = build(); tasks[0]['expected_label'] = 'SECRET'
        with self.assertRaises(ValueError):prepare(tasks)

    def test_changed_content_or_order_rejected(self):
        for wrong in [build()[::-1],build()[:-1]]:
            with self.assertRaises(ValueError):prepare(wrong)
        wrong=build();wrong[1]['answer']+='extra'
        with self.assertRaises(ValueError):prepare(wrong)

    def test_preparation_does_not_mutate_inputs(self):
        tasks=build();before=deepcopy(tasks);prepare(tasks)
        self.assertEqual(tasks,before)

    def test_units_and_premise_spans_exact(self):
        tasks=build()
        self.assertEqual([len(t['answer_units']) for t in tasks],[1,2,1,2])
        for t in tasks:
            for u in t['answer_units']:
                self.assertEqual(t['answer'][u['start']:u['end']],u['text'])
            for premise in t['scenario_premises']:
                self.assertEqual(t['question'][premise['start']:premise['end']],premise['text'])
