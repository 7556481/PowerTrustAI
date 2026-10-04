"""Public synthetic_fixture for selective review and immutable task repairs."""
from copy import deepcopy
import unittest
from evaluation.support_review_quality import import_analysis, amend_task, prediction_scope, quality_entry, apply_quality_layer
from evaluation.support_dataset import canonical, digest, task_key
from tests.test_support_dataset import sample


class ReviewQualityTests(unittest.TestCase):
    def setUp(self):
        self.samples = [sample()]
        self.samples[0].update(group_id='synthetic_fixture-family', split='development_only')
        s = self.samples[0]
        self.row = {'sample_id': s['sample_id'], 'task_sha256': s['sample_id'],
                    'task_type': s['task']['task_type'], 'disposition': 'candidate_ready',
                    'proposed_label': 'supported', 'basis_ids': ['q1'], 'quality_flags': []}
        self.analysis = {'summary': {'source_zip_sha256': 'synthetic_fixture',
                         'dispositions': {'candidate_ready': 1}}, 'reviews': [self.row]}

    def run_import(self, analysis=None, selection=()):
        return import_analysis(self.samples, analysis or self.analysis,
            expected_source_zip_sha256='synthetic_fixture', review_zip_sha256='synthetic_fixture-review',
            confirmed_selection=selection)

    def test_disposition_does_not_confirm_a_label(self):
        output, checks = self.run_import()
        self.assertEqual(checks['confirmed_labels'], 0)
        self.assertEqual(output[0]['supervision']['status'], 'pending')
        self.assertEqual(output[0]['task'], self.samples[0]['task'])

    def test_explicit_selection_only(self):
        review = {'sample_id': self.row['sample_id'], 'task_sha256': self.row['task_sha256'],
                  'status': 'confirmed', 'label': 'supported', 'basis_ids': ['q1'],
                  'source': 'ai_assisted_user_supervised', 'reviewer_id': 'synthetic_fixture-user'}
        output, checks = self.run_import(selection=[review])
        self.assertEqual(checks['confirmed_labels'], 1)
        self.assertEqual(self.samples[0]['supervision']['status'], 'pending')
        self.assertEqual(output[0]['supervision']['label'], 'supported')
        corrected = dict(review, label='insufficient_evidence', note='synthetic_fixture explicit user correction')
        output, _ = self.run_import(selection=[corrected])
        self.assertEqual(output[0]['supervision']['label'], 'insufficient_evidence')

    def test_hold_cannot_be_confirmed_via_selection(self):
        a = deepcopy(self.analysis); a['reviews'][0]['disposition'] = 'hold'
        a['summary']['dispositions'] = {'hold': 1}
        output, _ = self.run_import(a)
        self.assertFalse(output[0]['eligible_for_baseline'])
        with self.assertRaisesRegex(ValueError, 'ready'):
            self.run_import(a, [{'sample_id': self.row['sample_id']}])

    def test_wrong_task_and_scope_rejected(self):
        for field, value in [('task_sha256', 'wrong'), ('basis_ids', ['outside']), ('group_id', 'wrong-family')]:
            a = deepcopy(self.analysis); a['reviews'][0][field] = value
            with self.assertRaises(ValueError):
                self.run_import(a)

    def test_duplicate_and_wrong_source_rejected(self):
        a = deepcopy(self.analysis); a['reviews'].append(deepcopy(self.row))
        with self.assertRaises(ValueError):
            self.run_import(a)
        a = deepcopy(self.analysis); a['summary']['source_zip_sha256'] = 'other'
        with self.assertRaisesRegex(ValueError, 'different frozen'):
            self.run_import(a)

    def test_amendment_new_hash_no_inherited_label_or_observation(self):
        s = deepcopy(self.samples[0]); s['supervision'].update(status='confirmed', label='supported', reviewer_id='synthetic_fixture', note='old judgment must not leak')
        task = deepcopy(s['task']); task['claim']['proposition'] = 'A different conditional target.'
        task['claim']['text'] = task['claim']['proposition']; task['answer_excerpt'] = task['claim']['proposition']
        amended = amend_task(s, task, reason='synthetic_fixture qualifier correction')
        self.assertNotEqual(amended['sample_id'], s['sample_id'])
        self.assertEqual(amended['sample_id'], task_key(task))
        self.assertEqual(amended['supervision']['status'], 'pending')
        self.assertIsNone(amended['supervision']['suggestion_label'])
        self.assertFalse(amended['observations'])
        self.assertNotIn('note', amended['supervision'])
        self.assertEqual(amended['group_id'], s['group_id'])
        with self.assertRaisesRegex(ValueError, 'actual task'):
            amend_task(s, s['task'], reason='cannot just relabel')

    def test_old_prediction_cannot_follow_parent_into_repair(self):
        s = self.samples[0]; t = deepcopy(s['task']); t['claim']['proposition'] += ' under a new condition'
        amended = amend_task(s, t, reason='synthetic_fixture')
        predictions = {'predictions': [{'sample_id': s['sample_id'], 'status': 'valid_partial', 'label': 'supported'}],
                      'task_hashes': {s['sample_id']: digest(canonical(s['task']))}}
        self.assertEqual(len(prediction_scope([s], predictions)['valid_original_predictions']), 1)
        self.assertEqual(len(prediction_scope([amended], predictions)['valid_original_predictions']), 0)

    def test_recipe_does_not_determine_quality_label(self):
        s = deepcopy(self.samples[0]); s['recipe'] = {'operation': 'negation'}
        entry = quality_entry(s, disposition='hold', proposed_label=None,
                              flags=['unresolved_parent'], rationale='synthetic_fixture no basis')
        self.assertIsNone(entry['proposed_label'])
        revised = apply_quality_layer([s], [entry])[0]
        self.assertEqual(revised['sample_id'], s['sample_id'])
        self.assertFalse(revised['eligible_for_baseline'])
        self.assertIsNone(revised['supervision']['suggestion_label'])
        self.assertEqual(s['supervision']['suggestion_label'], 'supported')
        entry = quality_entry(s, disposition='candidate_ready', proposed_label='insufficient_evidence',
                              flags=['universal_scope_extension'], rationale='Unsupported scope is a valid task, not a broken one.')
        self.assertEqual(entry['proposed_label'], 'insufficient_evidence')
        with self.assertRaises(ValueError):
            quality_entry(s, disposition='candidate_ready', proposed_label='contradicted',
                          flags=['stale_qualifiers'], rationale='bad shortcut')


if __name__ == '__main__':
    unittest.main()
