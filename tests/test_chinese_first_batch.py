from tests.temp_paths import ignored_temporary_directory
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import chinese_first_cross_language_v1 as t
from backend.config import ServiceConfig
from core.validation import ContractError
from model_adapter.contracts import ModelRequest, ModelMessage, ModelConnectionError
from rag.contracts import RetrievalHit, RetrievalResult, RetrievalRequest, RetrievalPurpose, ContextOptions
from rag.storage import KnowledgeStore, SourceMetadata
from rag.retriever import AsyncSQLiteBM25Retriever
from tests.test_schema14_factory_flow import SyntheticProvider, GOOD


class BatchTests(unittest.TestCase):
    def test_global_and_slot_limits_include_corrections_and_branches(self):
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            ledger=t.SendLedger(Path(tmp));ledger({'case':0,'variant':'A'},None,1)
            r=ModelRequest('deepseek-flash',(ModelMessage('user','{"answer_id":"same"}'),),8000,'evidence-bound-generation')
            ledger.claim(r);ledger.claim(replace(r,correction=True))
            with self.assertRaises(ContractError):ledger.claim(r)
            ledger({'case':0,'variant':'C'},None,3);ledger.claim(r)
            self.assertEqual(len(ledger.rows),3)
            q=ModelRequest('deepseek-flash',(ModelMessage('user','{"question":"EXI中文"}'),),1000,'generation-cross-language-query-v1')
            ledger.claim(q)
            with self.assertRaises(ContractError):ledger.claim(q)

    def exercise(self,fail=False):
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();doc=root/'x.md';doc.write_text(GOOD,encoding='utf-8')
            with KnowledgeStore(root/'index.sqlite3') as s:
                k=s.ingest(doc,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
                e=s.evidence(s.rows(k)[0]['fragment_id'],k)
            result=RetrievalResult((e,),k,hits=(RetrievalHit(e.evidence_id,e.provenance.fragment_id,1,1.0,'synthetic'),))
            frozen={(v,row['question']):(RetrievalRequest(row['question'],'voltage_stability_reactive_support',RetrievalPurpose.GENERATION,k,3,ContextOptions()),result) for row in t.N for v in ('A','C')}
            c=ServiceConfig(index_db=root/'index.sqlite3',knowledge_version=k,execution_path='langgraph_v1')
            ledger=t.SendLedger(root/'batch');p=SyntheticProvider()
            class Provider:
                def validate_request(self,r):pass
                def close(self):pass
                async def complete(self,r):
                    if fail:raise ModelConnectionError()
                    return await p.complete(r)
            async def run():
                validator=AsyncSQLiteBM25Retriever(c.index_db)
                try:return await t.answers(c,{'N':t.N},frozen,validator,lambda *a,**kw:t.LoggedAdapter(Provider(),ledger),ledger)
                finally:validator.close()
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch.object(t,'LOCAL',root),patch('harness.deepseek_trial.load_project_env',side_effect=AssertionError('No offline env load')):
                summary=asyncio.run(run())
            if fail:
                self.assertTrue(ledger.fatal);self.assertEqual(len(ledger.rows),1)
                self.assertEqual(len(summary['control']),1)
            else:
                self.assertEqual(len(ledger.rows),16);self.assertFalse(ledger.fatal)
                self.assertEqual(len(summary['control']),16)
                for raw in summary['outputs'].values():
                    self.assertEqual(raw['state'],'generated');self.assertFalse(raw['execution_issues'])
                    self.assertEqual(raw['evidence'][0]['evidence_id'],e.evidence_id)
                    self.assertEqual(raw['generation_output']['evidence_snapshot']['knowledge_version'],k)
                    self.assertEqual(len(raw['model_records']),1)
            return summary
    def test_16_generation_slots_actual_harness_store_and_fixed_snapshot(self):self.exercise()
    def test_shared_network_failure_stops_after_first_request(self):self.exercise(True)


if __name__=='__main__':unittest.main()
