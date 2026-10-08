"""Offline synthetic checks of timing transparency, nesting and certificate path."""
import asyncio
from dataclasses import replace
import unittest
from unittest.mock import patch
from tests import test_corpus_index as fixtures
from rag.timing import capture_timing,span
from rag.retriever import AsyncSQLiteBM25Retriever
from core.validation import ContractError
from evaluation.retrieval_diagnosis import request_gaps,union_seconds


class SpanTests(unittest.TestCase):
    def test_missing_requested_limit_not_inferred_from_three_hits(self):
        gaps=request_gaps({'query':'synthetic','scenario_id':'fixture','purpose':'generation',
                           'knowledge_version':'fixture','hits':[1,2,3]})
        self.assertEqual(gaps,['max_results','context_options'])
        self.assertEqual(union_seconds([(0,5),(0,10),(1,3),(12,15)]),13)

    def test_nested_failure_only_exports_mechanical_metadata(self):
        with capture_timing(run_id='fixture',retrieval_id='R1') as log:
            with span('outer'):
                with self.assertRaises(ValueError):
                    with span('inner') as info:
                        info.update(result_count=2, query='PRIVATE', body='PRIVATE')
                        raise ValueError('PRIVATE')
        inner, outer = log.records
        self.assertEqual(inner['parent_id'], outer['span_id'])
        self.assertEqual(inner['status'], 'failed')
        self.assertEqual(inner['result_count'], 2)
        self.assertEqual(inner['retrieval_id'],'R1')
        self.assertNotIn('query', inner)
        self.assertNotIn('body', inner)
        self.assertGreaterEqual(outer['seconds'], inner['seconds'])
        self.assertLessEqual(outer['start_seconds'], inner['start_seconds'])


class RetrievalTimingTests(fixtures.CorpusTests):
    def test_output_identity_worker_context_and_no_second_ranking(self):
        async def run():
            r = AsyncSQLiteBM25Retriever(self.p)
            try:
                q = self.request('无功功率')
                baseline = await r.retrieve(q)
                with capture_timing() as log:
                    actual = await r.retrieve(q)
                    await r.validate_result(q, actual)
                self.assertEqual(baseline, actual)
                phases = [x['phase'] for x in log.records]
                self.assertEqual(phases.count('fts_execute_fetch_sort'), 1)
                self.assertIn('query_prepare', phases)
                self.assertIn('body_evidence_construct', phases)
                validation = next(x for x in log.records if x['phase'] == 'result_validation')
                self.assertTrue(validation['certificate_hit'])
                self.assertFalse(validation['ranking_replayed'])
                self.assertEqual(validation['ranking_sql_calls'],0)
                self.assertTrue(all(x['parent_id'] for x in log.records if x['phase'] == 'retriever_worker'))
            finally:
                r.close()
        asyncio.run(run())

    def test_changed_request_fallback_ranks_again_and_rejects(self):
        async def run():
            r = AsyncSQLiteBM25Retriever(self.p)
            try:
                q = self.request('无功功率')
                actual = await r.retrieve(q)
                with capture_timing() as log:
                    with self.assertRaises(ContractError):
                        await r.validate_result(replace(q, query='继电保护'), actual)
                validation = next(x for x in log.records if x['phase'] == 'result_validation')
                self.assertTrue(validation['ranking_replayed'])
                self.assertEqual(validation['ranking_sql_calls'],1)
                self.assertFalse(validation['certificate_hit'])
                self.assertEqual(validation['status'], 'failed')
                self.assertEqual(sum(x['phase']=='fts_execute_fetch_sort' for x in log.records), 1)
            finally:
                r.close()
        asyncio.run(run())
