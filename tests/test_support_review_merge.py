"""Public synthetic_fixture: pending reception and task-only baseline freeze."""
from copy import deepcopy
import unittest

from evaluation.support_dataset import canonical, digest
from evaluation.support_review_quality import quality_entry, apply_quality_layer, amend_task
from evaluation.support_review_merge import receive, merge, prepare, relationships
from tests.test_support_dataset import sample


class PendingMergeTests(unittest.TestCase):
    def setUp(self):
        self.s = sample()
        self.s.update(group_id='synthetic_fixture-family', split='train')
        self.entry = quality_entry(self.s, disposition='candidate_ready',
            proposed_label='supported', flags=[], rationale='synthetic_fixture suggestion')

    def reviewed(self):
        return apply_quality_layer([self.s], [self.entry])[0]

    def test_basis_subset_and_empty_subset_survive_quality_layer(self):
        s = deepcopy(self.s)
        s['task']['other_basis'].append({'basis_id': 'input-2', 'type': 'input_snapshot', 'value': {}})
        from evaluation.support_dataset import task_key
        s['sample_id'] = task_key(s['task'])
        e = quality_entry(s, disposition='candidate_ready', proposed_label='supported', flags=[], rationale='fixture')
        e['basis_ids'] = ['input-2']
        self.assertEqual(apply_quality_layer([s], [e])[0]['quality_review']['basis_ids'], ['input-2'])
        e.update(proposed_label='insufficient_evidence', basis_ids=[])
        self.assertEqual(apply_quality_layer([s], [e])[0]['quality_review']['basis_ids'], [])
        e['basis_ids'] = ['outside']
        with self.assertRaises(ValueError):
            apply_quality_layer([s], [e])

    def test_reception_preserves_task_and_pending(self):
        out = receive([self.s], {'reviews': [self.entry]}, review_sha256='synthetic_fixture')
        self.assertEqual(out[0]['task'], self.s['task'])
        self.assertIsNone(out[0]['supervision']['label'])
        self.assertEqual(out[0]['supervision']['status'], 'pending')
        e = dict(self.entry, label_status='confirmed')
        with self.assertRaises(ValueError):
            receive([self.s], {'reviews': [e]}, review_sha256='fixture')

    def test_wrong_hash_quote_or_coverage_rejected(self):
        for e in (dict(self.entry, task_sha256='wrong'), dict(self.entry, quote='different'),
                  dict(self.entry, task_type='scalar_calculation')):
            with self.assertRaises(ValueError):
                receive([self.s], {'reviews': [e]}, review_sha256='fixture')
        with self.assertRaises(ValueError):
            receive([self.s], {'reviews': [self.entry, self.entry]}, review_sha256='fixture')

    def test_auxiliary_kept_but_not_primary_and_parent_split_preserved(self):
        old = self.reviewed()
        task = deepcopy(old['task']); task['claim']['proposition'] += ' with explicit source'
        new = amend_task(old, task, reason='fixture')
        e = quality_entry(new, disposition='auxiliary_only', proposed_label='supported', flags=[], rationale='changed target')
        new = apply_quality_layer([new], [e])[0]
        all_rows, primary, manifest, report = merge([('original', [old]), ('amended', [new])])
        self.assertEqual(len(all_rows), 2)
        self.assertEqual(len(primary), 1)
        self.assertEqual(manifest[1]['parent_sample_ids'], [old['sample_id']])
        self.assertEqual(report['confirmed_labels'], 0)
        new['split'] = 'test'
        with self.assertRaises(ValueError):
            merge([('original', [old]), ('amended', [new])])

    def test_freeze_has_no_labels_recipes_and_exact_prediction_hash_only(self):
        s = self.reviewed(); s['recipe'] = {'label_hint': 'secret_fixture_hint'}
        old = {'task_hashes': {s['sample_id']: digest(canonical(s['task']))},
               'predictions': [{'sample_id': s['sample_id'], 'status': 'valid_partial', 'label': 'supported'}]}
        frozen = prepare([s], old)
        request = frozen['requests'][0]
        self.assertTrue(request['reusable_original_prediction'])
        self.assertEqual(set(frozen['model_input']['samples'][0]), {'sample_id', 'task'})
        self.assertNotIn('secret_fixture_hint', request['messages'][1]['content'])
        self.assertNotIn('supervision', request['messages'][1]['content'])
        self.assertEqual(frozen['actual_calls'], 0)
        old['task_hashes'][s['sample_id']] = 'wrong'
        self.assertFalse(prepare([s], old)['requests'][0]['reusable_original_prediction'])

    def test_cross_split_sharing_reported_without_repartition(self):
        a = self.reviewed(); b = deepcopy(a)
        b['task']['claim']['proposition'] += ' different'
        from evaluation.support_dataset import task_key
        b['sample_id'] = task_key(b['task']); b['split'] = 'test'
        report = relationships([a, b])
        self.assertTrue(report['quote'][0]['cross_split'])
        self.assertTrue(report['evidence'][0]['cross_split'])
        self.assertEqual((a['split'], b['split']), ('train', 'test'))


if __name__ == '__main__':
    unittest.main()
