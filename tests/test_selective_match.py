"""Synthetic fixtures; no network/models/real library access."""
import asyncio
import time
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from rag.selective_match import plan,select,Work,retrieve
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.storage import KnowledgeStore
from core.validation import ContractError

class SelectiveTests(unittest.TestCase):
    def setUp(self):
        from tests.test_corpus_index import CorpusTests as Fixture
        self.f=Fixture();self.f.setUp()
    def tearDown(self):self.f.tearDown()

    def test_plan_keeps_conditions_units_entities_and_aliases(self):
        p=plan('无功功率与功率因数：SCM_UNIT937 不超过30 Mvar，仅在正弦时；电压稳定与并联电容。')
        for w in ('30','mvar','不','仅'):self.assertIn(w,p['scoring_terms'])
        self.assertTrue(any('937' in w for w in p['scoring_terms']))
        self.assertLessEqual(len(p['expressions']),3)
        self.assertTrue(all(' AND ' in x for x in p['expressions']))
        self.assertIn('无功功率',plan('无功')['scoring_terms'])
        self.assertEqual(plan('') ['expressions'],())

    def test_merge_uses_coverage_then_stage_rank_never_cross_scores(self):
        p=dict(groups=[('无功功率',),('继电保护',)])
        a=SimpleNamespace(text='无功功率');b=SimpleNamespace(text='继电保护');c=SimpleNamespace(text='无功功率')
        selected=select([(a,.00001,0,1),(b,999,1,1),(c,1000,2,1)],p,2)
        self.assertEqual([x[0] for x in selected],[a,b])

    def test_body_and_sql_caps_no_duplicate_charge(self):
        with KnowledgeStore(self.f.p,readonly=True) as store:
            w=Work(sql_limit=1,char_limit=1000)
            r=retrieve(store,self.f.request('无功功率 感性负载 并联电容 继电保护'),w)
            self.assertEqual(w.calls,1);self.assertEqual(w.chars,sum(len(e.text) for e in w.bodies.values()))
            self.assertLessEqual(len(r.evidence),3)
            empty=Work(sql_limit=3,char_limit=0)
            self.assertFalse(retrieve(store,self.f.request('无功功率'),empty).evidence)
            self.assertEqual(empty.chars,0)
            with self.assertRaises(TimeoutError):retrieve(store,self.f.request('无功功率'),Work(deadline=0))

    def test_certificate_identity_and_missing_replay_rejected(self):
        async def run():
            r=AsyncSQLiteBM25Retriever(self.f.p,execution_profile='selective_match_v1')
            try:
                q=self.f.request('无功功率');out=await r.retrieve(q)
                self.assertTrue(out.evidence);await r.validate_result(q,out)
                with self.assertRaises(ContractError):await r.validate_result(q,replace(out,hits=()))
                with self.assertRaises(ContractError):await r.validate_result(replace(q,query='电压'),out)
            finally:r.close()
        asyncio.run(run())

    def test_cancellation_releases_actual_sqlite_work_and_allows_next_query(self):
        import threading
        entered=threading.Event()
        def slow(store,q,w):
            entered.set()
            store.connection.execute('WITH RECURSIVE x(n) AS (VALUES(0) UNION ALL SELECT n+1 FROM x WHERE n<1000000000) SELECT sum(n) FROM x').fetchone()
        async def run():
            r=AsyncSQLiteBM25Retriever(self.f.p,execution_profile='selective_match_v1')
            try:
                with patch('rag.selective_match.retrieve',slow):
                    task=asyncio.create_task(r.retrieve(self.f.request('无功功率')))
                    for _ in range(300):
                        if entered.is_set():break
                        await asyncio.sleep(.01)
                    self.assertTrue(entered.is_set());task.cancel()
                    with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(task,2)
                    self.assertTrue(r._active.done())
                self.assertTrue((await r.retrieve(self.f.request('无功功率'))).evidence)
            finally:r.close()
        asyncio.run(run())

    def test_session_charges_all_intermediate_work_with_original_budget(self):
        from harness.retrieval import RetrievalSession
        from harness.contracts import RunBudget,RetrievalSettings
        from rag.contracts import RetrievalPurpose
        from core.models import TaskRequest,TaskMode
        async def run():
            r=AsyncSQLiteBM25Retriever(self.f.p,execution_profile='selective_match_v1')
            b=RunBudget(max_retrieval_calls=1,max_retrieval_chars_per_call=1000,max_retrieval_chars_total=1000)
            session=RetrievalSession(r,self.f.k,RetrievalSettings(context_options=None),b,time.perf_counter()+10,())
            try:
                req=TaskRequest('test',TaskMode.ASSESS_EXISTING,'synthetic_fixture','无功功率')
                out=await session.retrieve(RetrievalPurpose.VERIFICATION,req,None,(),query_override=req.question)
                self.assertTrue(out.evidence);self.assertGreater(session.chars,0)
                self.assertEqual(session.calls,1)
                self.assertEqual(session.chars,r.last_selective_work.chars)
                self.assertEqual(session.chars,sum(len(e.text) for e in out.evidence))
                second=await session.retrieve(RetrievalPurpose.VERIFICATION,req,None,(),query_override=req.question)
                self.assertIsNotNone(second.issue);self.assertEqual(session.calls,1)
            finally:r.close()
        asyncio.run(run())
