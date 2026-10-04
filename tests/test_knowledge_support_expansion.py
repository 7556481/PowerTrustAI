"""Public synthetic_fixture checks, no official documents or private archives."""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest

from evaluation.knowledge_support_expansion import build, ingest_sources, seed_overlap
from rag.storage import KnowledgeStore, SourceMetadata


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'base.db'
        with KnowledgeStore(self.base) as store:
            path = self.root / 'old.md'
            path.write_text('# synthetic_fixture\nOld immutable evidence.', encoding='utf8')
            self.old = store.ingest(path, 'old').knowledge_version
        self.path = self.root / 'new.md'
        self.path.write_text('# synthetic_fixture\nA controller requires a validated model.', encoding='utf8')
        self.manifest = {'sources': [{'document_id': 'new', 'role': 'development', 'file': str(self.path),
            'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(), 'metadata': {
                'source_uri': 'https://example.org/synthetic_fixture', 'publisher': 'synthetic_fixture',
                'document_title': 'synthetic_fixture', 'applicability': ['synthetic_fixture only']}}]}
        self.family = {'family_id': 'synthetic_fixture-controller', 'document_id': 'new', 'file_page': None,
            'anchor_text': 'A controller requires a validated model.',
            'base_proposition': 'A controller requires a validated model.',
            'variants': [{'proposition': 'A controller never requires a validated model.',
                          'operation': 'negation', 'suggestion': 'contradicted', 'reason': 'synthetic_fixture proposal'}]}

    def setup_store(self):
        report = ingest_sources(self.base, self.root / 'new.db', self.manifest, 'development')
        store = KnowledgeStore(self.root / 'new.db')
        self.addCleanup(store.close)
        return store, report

    def test_old_snapshot_and_source_version(self):
        store, report = self.setup_store()
        self.assertTrue(report['old_snapshot_unchanged'])
        self.assertEqual(len(store.rows(self.old)), 1)
        self.assertEqual(len(store.rows(report['knowledge_version'])), 2)
        self.assertNotEqual(self.old, report['knowledge_version'])

    def test_exact_locator_pending_and_parent_group(self):
        store, r = self.setup_store()
        samples, report = build(store, r['knowledge_version'], self.manifest, [self.family])
        self.assertEqual(report['pending_count'], 2)
        self.assertEqual(len({s['group_id'] for s in samples}), 1)
        self.assertTrue(all(s['supervision']['label'] is None for s in samples))
        quote = samples[0]['task']['evidence'][0]
        self.assertEqual(quote['text'], self.family['anchor_text'])
        original = store.evidence(quote['metadata']['provenance']['fragment_id'], r['knowledge_version'])
        start = quote['start_offset'] - original.provenance.start_offset
        self.assertEqual(original.text[start:start + len(quote['text'])], quote['text'])
        self.assertEqual(quote['metadata']['source_id'], 'new')

    def test_reserved_document_rejected(self):
        store, r = self.setup_store()
        m = deepcopy(self.manifest); m['sources'][0]['role'] = 'reserved_evaluation'
        samples, report = build(store, r['knowledge_version'], m, [self.family])
        self.assertEqual(samples, [])
        self.assertIn('reserved', report['failures'][0]['reason'])

    def test_failed_family_preserves_valid_other_family(self):
        store, r = self.setup_store()
        bad = deepcopy(self.family); bad.update(family_id='synthetic_fixture-missing', anchor_text='not in source')
        samples, report = build(store, r['knowledge_version'], self.manifest, [bad, self.family])
        self.assertEqual(len(samples), 2)
        self.assertEqual(len(report['failures']), 1)

    def test_mistranscription_not_silently_corrected(self):
        store, r = self.setup_store()
        bad = deepcopy(self.family); bad['base_proposition'] = 'A model requires a controller.'
        samples, report = build(store, r['knowledge_version'], self.manifest, [bad])
        self.assertFalse(samples)
        self.assertIn('faithfully', report['failures'][0]['reason'])
        bad['base_proposition'] = self.family['base_proposition'].replace('.', '!')
        samples, report = build(store, r['knowledge_version'], self.manifest, [bad])
        self.assertFalse(samples)  # normalization cannot erase meaningful symbols

    def test_hash_and_protocol_rejected_before_copy(self):
        m = deepcopy(self.manifest); m['sources'][0]['sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'hash'):
            ingest_sources(self.base, self.root / 'bad.db', m, 'development')
        self.assertFalse((self.root / 'bad.db').exists())
        m = deepcopy(self.manifest); m['sources'][0]['metadata']['source_uri'] = 'file:///private.pdf'
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            ingest_sources(self.base, self.root / 'bad.db', m, 'development')

    def test_overwrite_and_duplicate_family_forbidden(self):
        store, r = self.setup_store()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            ingest_sources(self.base, self.root / 'new.db', self.manifest, 'development')
        with self.assertRaisesRegex(ValueError, 'duplicate family'):
            build(store, r['knowledge_version'], self.manifest, [self.family, self.family])
        ambiguous = deepcopy(self.manifest)
        extra = deepcopy(ambiguous['sources'][0]); extra['role'] = 'reserved_evaluation'
        ambiguous['sources'].append(extra)
        with self.assertRaisesRegex(ValueError, 'duplicate source role'):
            build(store, r['knowledge_version'], ambiguous, [self.family])

    def test_seed_overlap_report_without_mutation(self):
        store, r = self.setup_store()
        samples, _ = build(store, r['knowledge_version'], self.manifest, [self.family])
        original = deepcopy(samples)
        report = seed_overlap(samples, original)
        self.assertTrue(report['near_duplicate_pairs'])
        self.assertTrue(report['shared_exact_quote_sha256'])
        self.assertEqual(samples, original)

    def test_duplicate_edit_deduplicated_and_bad_sibling_atomic(self):
        store, r = self.setup_store()
        family = deepcopy(self.family)
        family['variants'].append(deepcopy(family['variants'][0]))
        samples, report = build(store, r['knowledge_version'], self.manifest, [family])
        self.assertEqual(report['raw_count'], 3)
        self.assertEqual(len(samples), 2)
        family['variants'][-1]['suggestion'] = 'pass'
        samples, report = build(store, r['knowledge_version'], self.manifest, [family])
        self.assertEqual(samples, [])
        self.assertEqual(len(report['failures']), 1)


if __name__ == '__main__':
    unittest.main()
