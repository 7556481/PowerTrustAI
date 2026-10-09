import asyncio
from dataclasses import replace
import unittest
from unittest.mock import patch
from tests import test_corpus_index as fixtures
from rag.chinese_terms import query_expression,TOPIC_VERSION
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.contracts import RetrievalPurpose
from rag.timing import capture_timing
from core.validation import ContractError

class TopicTests(unittest.TestCase):
    def test_format_metadata_removed_but_actual_conditions_units_retained(self):
        q='正弦稳态 有功功率 视在功率 用150字以内说明'
        old=query_expression(q);new=query_expression(q,TOPIC_VERSION)
        self.assertIn('150',old);self.assertNotIn('150',new)
        self.assertIn('正弦',new);self.assertIn('稳态',new);self.assertIn('有功功率',new)
        self.assertIn('150',query_expression('150字节',TOPIC_VERSION))
        suffix='\nvoltage_stability_reactive_support\nengineering prerequisites constraints operating limits applicability'
        self.assertEqual(query_expression('无功功率'+suffix,TOPIC_VERSION),query_expression('无功功率',TOPIC_VERSION))
        self.assertIn('engineering',query_expression('engineering limits',TOPIC_VERSION))

class OptimizedTests(fixtures.CorpusTests):
    def test_rank_cache_rebuilds_bodies_and_keeps_complete_request_validation(self):
        async def run():
            r=AsyncSQLiteBM25Retriever(self.p,execution_profile='topic_v3_rank_v1')
            try:
                q=self.request('无功功率');first=await r.retrieve(q)
                changed=replace(q,purpose=RetrievalPurpose.DOMAIN_REVIEW)
                import rag.corpus_index as ci
                with patch('rag.corpus_index.corpus_evidence',wraps=ci.corpus_evidence) as bodies:
                    with capture_timing() as log:
                        second=await r.retrieve(changed);await r.validate_result(changed,second)
                    self.assertGreater(bodies.call_count,0)
                self.assertEqual(first,second)
                ranking=next(x for x in log.records if x['phase']=='fts_execute_fetch_sort')
                self.assertTrue(ranking['rank_cache_hit'])
                with self.assertRaises(ContractError):await r.validate_result(changed,replace(second,hits=()))
                with capture_timing() as log:await r.retrieve(replace(q,max_results=1))
                self.assertFalse(next(x for x in log.records if x['phase']=='fts_execute_fetch_sort')['rank_cache_hit'])
            finally:r.close()
        asyncio.run(run())

    def test_cached_rank_never_hides_changed_published_identity(self):
        async def run():
            r=AsyncSQLiteBM25Retriever(self.p,execution_profile='topic_v3_rank_v1')
            try:
                q=self.request('无功功率');await r.retrieve(q)
                import os
                s=self.p.stat();os.utime(self.p,ns=(s.st_atime_ns,s.st_mtime_ns+1000000000))
                with self.assertRaises(ContractError):await r.retrieve(q)
            finally:r.close()
        asyncio.run(run())
