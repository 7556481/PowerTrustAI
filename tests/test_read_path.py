"""Read projections stay equivalent to full-row legacy reads, synthetic only."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend.service import ApplicationService
from backend.store import RunStore, StorageError, BindingError
from backend.serialization import dumps


class ReadPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RunStore(Path(self.temp.name)/'runs.sqlite3')
        self.service = ApplicationService(SimpleNamespace(queue_capacity=2), self.store, factory=object())
        self.store.create('A', dict(mode='question_answer', question='synthetic'),
                          dict(profile='synthetic_fixture', knowledge_version='synthetic'))
        self.answer = dict(answer_id='a', version=1, text='synthetic answer', citations=[])
        self.evidence = dict(evidence_id='e', source_id='fixture', source_version='1', text='synthetic evidence')
        self.raw = dict(answer=self.answer, evidence=[self.evidence], review_rounds=[])

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_state_and_result_equivalent_for_empty_partial_terminal_and_volatile(self):
        for kind in ['empty', 'partial', 'finished', 'cancelled', 'failed']:
            with self.subTest(kind=kind):
                if kind != 'empty':
                    self.store.db.execute('UPDATE runs SET snapshot=? WHERE id=?', (dumps(self.raw), 'A'))
                    self.store.db.commit()
                if kind in ('finished', 'cancelled', 'failed'):
                    self.store.mark('A', kind, result=self.raw)
                self.service.volatile_errors = {'A': 'RUN_STORAGE_FAILED'} if kind == 'failed' else {}
                current = (self.service.state('A'), self.service.result('A'))
                with patch.object(self.store, 'state_row', self.store.get), \
                     patch.object(self.store, 'require_run', self.store.get):
                    legacy = (self.service.state('A'), self.service.result('A'))
                self.assertEqual(current, legacy)

    def test_nonempty_ordered_reads_bindings_and_legacy_reopen(self):
        self.store.mark('A', 'finished', result=self.raw)
        for ordinal in [2, 1]:
            self.store.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                                  ('A', str(ordinal), ordinal, dumps({'ordinal': ordinal}), dumps({'value': ordinal})))
        self.store.db.commit()
        review = self.store.add_review('A', dict(answer_id='a', answer_version=1, action='note', note='synthetic'))
        actual = (self.store.events('A'), self.store.objects('A', 'answer'),
                  self.store.evidence('A', 'e'), self.store.reviews('A'))
        with patch.object(self.store, 'require_run', self.store.get):
            self.assertEqual(actual, (self.store.events('A'), self.store.objects('A', 'answer'),
                                     self.store.evidence('A', 'e'), self.store.reviews('A')))
        self.assertEqual([r['event']['ordinal'] for r in actual[0]], [1, 2])
        self.assertEqual(actual[3], [review])
        with self.assertRaises(BindingError):
            self.store.add_review('A', dict(answer_id='a', answer_version=2, action='note'))
        with self.assertRaises(BindingError):
            with self.store.tx(): self.store.index('A', dict(self.answer, text='changed'))
        self.store.close(); self.store = RunStore(Path(self.temp.name)/'runs.sqlite3')
        self.assertEqual(self.store.reviews('A'), actual[3])
        self.assertEqual(self.store.evidence('A', 'e'), self.evidence)

    def test_missing_run_and_closed_storage_keep_error_boundaries(self):
        calls = [lambda rid: self.store.state_row(rid), lambda rid: self.store.events(rid),
                 lambda rid: self.store.objects(rid, 'answer'), lambda rid: self.store.evidence(rid, 'e'),
                 lambda rid: self.store.reviews(rid)]
        for call in calls:
            with self.assertRaises(KeyError) as error: call('missing')
            self.assertEqual(error.exception.args, ('missing',))
        with self.assertRaises(KeyError) as error: self.store.evidence('A', 'missing-evidence')
        self.assertEqual(error.exception.args, ('missing-evidence',))
        self.store.close()
        for call in calls:
            with self.assertRaises(StorageError): call('A')
