"""Small synthetic stores only; no private freeze, corpus, model or environment."""
from copy import deepcopy
import sqlite3
from time import perf_counter
import unittest
from contextlib import closing

from backend.serialization import wire
from core.models import AnswerDraft, TaskMode, TaskRequest
from evaluation.audit_retrieval_final_v1 import (CountedConnection, _counts, diagnose_group,
    request_projection, service_busy, validate_freeze)
from harness.contracts import RetrievalSettings, RunBudget
from harness.retrieval import RetrievalSession
from rag.contracts import RetrievalPurpose
from rag.retriever import AsyncSQLiteBM25Retriever
from tests import test_corpus_index as fixtures


class DiagnosticTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = fixtures.CorpusTests()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    async def group(self):
        f = self.fixture
        r = AsyncSQLiteBM25Retriever(f.p, execution_profile='topic_v4_subject_v1')
        budget = RunBudget(step_timeout_seconds=5)
        session = RetrievalSession(r, f.k, RetrievalSettings(), budget, perf_counter()+10, ())
        answer = AnswerDraft('fixture-answer', 1, 'Synthetic review text.')
        request = TaskRequest('fixture', TaskMode.ASSESS_EXISTING, 'synthetic_fixture',
                              'Synthetic fixture question.', existing_answer=answer)
        try:
            deliveries = [await session.retrieve(purpose, request, answer, (), query_override='无功功率')
                          for purpose in (RetrievalPurpose.VERIFICATION, RetrievalPurpose.DOMAIN_REVIEW)]
        finally:
            r.close()
        self.assertTrue(all(not d.issue for d in deliveries))
        return dict(run_id='fixture', knowledge_version=f.k, budget=wire(budget),
            fact_strategy='aggregate', execution_profile='topic_v4_subject_v1',
            scenario_id='synthetic_fixture', audit_records=[wire(d.record) for d in deliveries],
            saved_evidence=wire(deliveries[0].evidence), provided_evidence=[], initial_calls=0,
            initial_chars=0, known_evidence_ids=[])

    async def test_instrumentation_preserves_full_history_supply_budget_and_closes(self):
        group = await self.group()
        row, private = await diagnose_group(self.fixture.p, group, perf_counter()+10)
        self.assertEqual(row['query_count'], 2)
        self.assertEqual([r['ranking_statements'] for r in row['requests']], [1, 0])
        self.assertEqual([r['certificate_hits'] for r in row['requests']], [1, 1])
        self.assertEqual([r['rank_cache_hits'] for r in row['requests']], [0, 1])
        self.assertTrue(all(r['historical_record_and_delivered_bodies_equal'] for r in row['requests']))
        self.assertEqual(private[0]['result'], private[1]['result'])
        self.assertEqual(private[1]['delivery']['record']['calls_used'], 2)
        self.assertTrue(all(r['phases']['store_open_and_schema'] >= 0 for r in row['requests']))

    async def test_missing_parameters_or_expanded_count_rejected_without_search(self):
        group = await self.group()
        freeze = dict(version='audit-retrieval-final-freeze-v1', groups=[group],
                      per_group_query_counts=[2], performance_seconds_cap=1200)
        validate_freeze(freeze)
        bad = deepcopy(freeze)
        bad['groups'][0]['audit_records'][0]['request_options'] = None
        with self.assertRaises(ValueError):
            validate_freeze(bad)
        with self.assertRaises(ValueError):
            validate_freeze(dict(freeze, per_group_query_counts=[3]))

    async def test_business_differences_not_removed_and_partial_result_archived(self):
        group = await self.group()
        group['audit_records'][0]['hits'][0]['score'] += 1
        archive = self.fixture.p.parent/'partial.json'
        with self.assertRaisesRegex(ValueError, 'hits'):
            await diagnose_group(self.fixture.p, group, perf_counter()+10, archive)
        self.assertTrue(archive.is_file())
        self.assertIn('result', archive.read_text(encoding='utf-8'))
        baseline = group['audit_records'][0]
        self.assertEqual(request_projection(baseline),
                         request_projection(dict(baseline, retrieval_id='other', duration_ms=999)))
        self.assertNotEqual(request_projection(baseline), request_projection(dict(baseline, offered_chars=0)))

    def test_counter_retains_counts_only_and_busy_probe_does_not_mutate(self):
        from collections import Counter
        counter = Counter()
        token = _counts.set(counter)
        try:
            with closing(sqlite3.connect(':memory:', factory=CountedConnection)) as db:
                db.execute('SELECT ?', ('PRIVATE fixture text',)).fetchone()
            self.assertEqual(dict(counter), {'sql_statements': 1})
        finally:
            _counts.reset(token)
        path = self.fixture.p.parent/'runs.sqlite3'
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE runs(status TEXT)')
            db.execute("INSERT INTO runs VALUES('finished')")
            db.commit()
        before = path.read_bytes()
        self.assertFalse(service_busy(path))
        self.assertEqual(before, path.read_bytes())

    async def test_expired_deadline_stops_without_results(self):
        group = await self.group()
        with self.assertRaises(TimeoutError):
            await diagnose_group(self.fixture.p, group, perf_counter()-1)
