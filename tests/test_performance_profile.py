"""Public synthetic timing fixture; no credentials, models, network or index."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from evaluation.performance_profile import summarize, read_summary


class ProfileTests(unittest.TestCase):
    def test_readonly_scope_roles_without_exporting_private_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / 'data/retrieval_local'
            local.mkdir(parents=True)
            catalog = local / 'scope-fixture.json'
            catalog.write_text(json.dumps({'section': 'BOUNDED_ORIGINAL_CITATIONS_UNTRUSTED',
                                           'answer': 'DO_NOT_EXPORT'}), encoding='utf-8')
            database = root / 'runs.sqlite3'
            with closing(sqlite3.connect(database)) as db:
                db.execute('CREATE TABLE runs(id TEXT,status TEXT,config TEXT,snapshot TEXT,result TEXT)')
                db.execute('CREATE TABLE events(run_id TEXT,ordinal INTEGER,payload TEXT)')
                raw = {'duration_ms': 10, 'model_records': [{
                    'call_number': 1, 'component': 'evidence_verification', 'duration_ms': 5,
                    'correction': False, 'status': 'succeeded', 'candidate_catalog_path': str(catalog)}]}
                db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',
                           ('fixture', 'finished', '{}', None, json.dumps(raw)))
                db.commit()
            before = database.read_bytes()
            with patch('evaluation.performance_profile.__file__', str(root / 'evaluation/profile.py')):
                result = read_summary(database, 'fixture')
            self.assertEqual(result['model_calls'][0]['review_role'], 'original_citations')
            self.assertNotIn('DO_NOT_EXPORT', json.dumps(result))
            self.assertEqual(before, database.read_bytes())

    def test_parallel_and_nested_work_not_reported_as_end_to_end(self):
        call = {'call_number': 1, 'component': 'evidence_verification', 'duration_ms': 8000,
                'correction': False, 'status': 'succeeded', 'usage': {'total_tokens': 10},
                'private_response': 'DO_NOT_EXPORT'}
        row = {'id': 'fixture', 'status': 'finished', 'started': '2026-01-01T00:00:00+00:00',
               'created': '2026-01-01T00:00:00+00:00', 'ended': '2026-01-01T00:00:10+00:00',
               'result': {'duration_ms': 10000, 'model_records': [call, dict(call, call_number=2)],
                          'answer': {'text': 'DO_NOT_EXPORT'}, 'retrieval_records': []}}
        result = summarize(row, [])
        self.assertEqual(result['harness_seconds'], 10)
        self.assertEqual(result['model_resource_seconds_sum'], 16)
        self.assertEqual(result['model_call_count'], 2)
        self.assertNotIn('DO_NOT_EXPORT', json.dumps(result))
        self.assertIsNone(result['unknown']['browser_first_paint_seconds'])
        labelled = summarize(row, [], {'private_answer': 'DO_NOT_EXPORT'}, {1: 'original_citations', 2: 'DO_NOT_EXPORT'})
        self.assertEqual(labelled['model_calls'][0]['review_role'], 'original_citations')
        self.assertEqual(labelled['model_calls'][1]['review_role'], 'unknown')
        self.assertNotIn('DO_NOT_EXPORT', json.dumps(labelled))

    def test_missing_usage_failure_and_answer_event_are_preserved(self):
        call = {'call_number': 3, 'component': 'revision', 'duration_ms': 12,
                'correction': True, 'status': 'failed', 'answer_version': 2, 'usage': None}
        row = {'id': 'fixture', 'status': 'failed', 'started': '2026-01-01T00:00:00+00:00',
               'result': {'duration_ms': 12000, 'model_records': [call], 'revision_outputs': []}}
        event = {'event': {'component': 'answer_created', 'timestamp_utc': '2026-01-01T00:00:03+00:00'}}
        result = summarize(row, [event])
        self.assertEqual(result['unknown_usage_calls'], 1)
        self.assertEqual(result['correction_count'], 1)
        self.assertEqual(result['answer_created_event_wall_offset_seconds'], 3)
        self.assertIsNone(result['run_wall_seconds'])
        self.assertEqual(result['model_calls'][0]['request_id'], 'fixture:model:3')
        self.assertEqual(result['model_calls'][0]['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
