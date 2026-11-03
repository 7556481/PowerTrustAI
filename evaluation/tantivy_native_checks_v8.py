"""Offline checks for diagnostic failure isolation, without a Frida dependency."""
import io
import json
import tempfile
import unittest
import time
from pathlib import Path

from evaluation.tantivy_full_identity_v1 import DiagnosticWriter
from evaluation.tantivy_native_trace_v8 import BoundedLog


class NativeDiagnosticChecks(unittest.TestCase):
    def test_add_primary_and_cleanup_stay_separate(self):
        primary = ValueError('first add failure')

        class Inner:
            closes = 0

            def add_document(self, value):
                raise primary

            def wait_merging_threads(self):
                self.closes += 1
                raise RuntimeError('later join failure')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inner = Inner()
            writer = DiagnosticWriter(inner, root)
            with self.assertRaises(ValueError) as caught:
                writer.add_document(None)
            self.assertIs(caught.exception, primary)
            with self.assertRaises(RuntimeError):
                writer.wait_merging_threads()
            writer.wait_merging_threads()
            self.assertEqual(inner.closes, 1)
            rows = [json.loads(line) for line in (root / 'native-errors.jsonl').read_text().splitlines()]
            self.assertEqual([r['operation'] for r in rows], ['add_document', 'wait_merging_threads'])

    def test_native_logging_failure_does_not_replace_primary(self):
        from unittest.mock import patch
        primary = OSError('native original')

        class Inner:
            def add_document(self, value):
                raise primary

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'native-errors.jsonl').mkdir()
            with patch('sys.stderr', io.StringIO()) as fallback:
                with self.assertRaises(OSError) as caught:
                    DiagnosticWriter(Inner(), root).add_document(None)
                self.assertIs(caught.exception, primary)
                self.assertIn('logging_error', fallback.getvalue())

    def test_bounded_trace_failure_preserves_native_record_in_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            fallback = io.StringIO()
            log = BoundedLog(Path(directory) / 'trace.jsonl', 0, fallback)
            self.assertFalse(log.emit({'operation': 'WriteFile', 'winerror': 5}))
            self.assertTrue(log.failed)
            self.assertIn('"winerror": 5', fallback.getvalue())
            self.assertIn('diagnostic_logging_error', fallback.getvalue())

    def test_trace_log_failure_requests_stop_without_raising(self):
        from unittest.mock import patch
        from evaluation.tantivy_native_trace_v8 import TraceSession
        with tempfile.TemporaryDirectory() as directory, patch('sys.stderr', io.StringIO()):
            root = Path(directory)
            trace = TraceSession({'directory': str(root / 'trace')}, 123, 4.5, root / 'stop.json')
            trace.log.limit = 0
            trace.message({'type': 'send', 'payload': {'pid': 123, 'failed': True, 'winerror': 5}}, None)
            self.assertTrue((root / 'stop.json').exists())
            self.assertEqual(json.loads((root / 'trace/first-native-errors.jsonl').read_text())['winerror'], 5)

    def test_readonly_reopen_audit_covers_all_ids_and_rejects_duplicates(self):
        import hashlib
        import sqlite3
        import tantivy
        from evaluation.tantivy_native_long_v8 import audit
        from rag.tantivy_build import atomic, create_index
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'build').mkdir()
                index = create_index(root / 'build/tantivy')
                writer = index.writer(heap_size=128000000, num_threads=1)
                ids = [-x for x in range(1, 675)] + [1, 2]
                for n, rid in enumerate(ids):
                    actual = ids[0] if duplicate and n == 1 else rid
                    writer.add_document(tantivy.Document(rowid=actual, terms='synthetic audit'))
                writer.commit()
                writer.wait_merging_threads()
                con = sqlite3.connect(root / 'build/mapping.sqlite3')
                con.execute('create table rows(position integer primary key,rowid integer unique,fragment_id text,body_sha text,terms_sha text)')
                rows = [(n, rid, str(rid), 'synthetic-body', 'synthetic-terms') for n, rid in enumerate(ids)]
                con.executemany('insert into rows values(?,?,?,?,?)', rows)
                con.commit()
                con.close()
                digest = hashlib.sha256()
                for row in rows:
                    digest.update(json.dumps(row).encode())
                atomic(root / 'build/checkpoint.json', {'count': len(ids), 'mapping_hash': digest.hexdigest()})
                atomic(root / 'plan.json', {'deadline': time.time()+120, 'diagnostic_run': {'root': str(root)}})
                if duplicate:
                    with self.assertRaises(sqlite3.IntegrityError):
                        audit(root / 'plan.json')
                    self.assertFalse((root / 'reopen-audit.json').exists())
                else:
                    audit(root / 'plan.json')
                    self.assertEqual(json.loads((root / 'reopen-audit.json').read_text())['count'], len(ids))


if __name__ == '__main__':
    unittest.main()
