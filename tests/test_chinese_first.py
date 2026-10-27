from tests.temp_paths import ignored_temporary_directory
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from core.validation import ContractError
from rag.storage import KnowledgeStore, SourceMetadata
from rag.contracts import RetrievalRequest, RetrievalPurpose, ContextOptions
from rag.chinese_first import Catalog, ChineseFirstRetriever, lexical
from rag.retriever import AsyncSQLiteBM25Retriever
from services.generation_query import GenerationQueryConverter
from model_adapter.contracts import ModelResponse, ModelSettings, ModelOutputError
from model_adapter.runtime import ModelBudget, model_scope


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=self.root/'k.sqlite3'
        with KnowledgeStore(self.db) as s:
            for ident,title,body in [('first','Guide A','Dynamic reactive resources adjust output automatically within a specified voltage bandwidth. '*3),
                                      ('second','Guide B','Voltage control reserves and monitoring are discussed separately. '*3),
                                      ('third','中文材料','无功补偿能够调节电压。')]:
                f=self.root/(ident+'.md');f.write_text(body,encoding='utf-8')
                s.ingest(f,ident,SourceMetadata(document_title=title,publisher='Example Institute (EXI)' if ident!='third' else 'Another Publisher'))
            self.k=s.latest();self.catalog=Catalog(s.rows(self.k))
    def tearDown(self):self.temp.cleanup()
    def request(self,q):return RetrievalRequest(q,'concept',RetrievalPurpose.GENERATION,self.k,3,ContextOptions())

    def test_institution_retains_all_and_exact_title_limits_scope(self):
        self.assertEqual(len(self.catalog.resolve('EXI 的资料').members),2)
        self.assertEqual(len(self.catalog.resolve('依据《Guide A》').members),1)
        unknown=self.catalog.resolve('EXI《Absent Guide》')
        self.assertEqual(unknown.status,'source_not_found');self.assertFalse(unknown.members)
        self.assertIn('未找到',unknown.message)
        self.assertEqual(self.catalog.resolve('一般无功问题').status,'unspecified')
        self.assertEqual(self.catalog.resolve('NEXTEXIST').status,'unspecified')
        self.assertEqual(self.catalog.resolve('EXI《中文材料》').status,'source_conflict')

    def test_duplicate_titles_keep_all_versions_and_unknown_publisher_not_inferred(self):
        rows=[dict(r) for r in self.catalog.rows]
        for r in rows:
            m=json.loads(r['metadata']);m['document_title']='Same title';r['metadata']=json.dumps(m)
        c=Catalog(rows);self.assertEqual(len(c.resolve('《Same title》').members),3)
        self.assertEqual(c.resolve('NERC').status,'unspecified')

    def test_symbol_numeric_and_abbreviation_tokens(self):
        tokens=lexical('TO DP N-1 N-2 δ X 50 ms Q=V/X')
        for t in ('to','dp','n','1','2','δ','x','50','ms','='):
            self.assertIn(t,tokens)

    def test_one_conversion_full_replay_tamper_and_default_equivalence(self):
        async def run():
            class Converter:
                calls=0
                async def run(self,q):self.calls+=1;return 'dynamic reactive resources voltage bandwidth'
            converter=Converter();r=ChineseFirstRetriever(self.db,self.k,converter)
            base=AsyncSQLiteBM25Retriever(self.db,execution_profile='topic_v4_subject_v1')
            try:
                q=self.request('EXI动态无功资源如何调节？');out=await r.retrieve(q)
                await r.validate_result(q,out);self.assertEqual(converter.calls,1)
                self.assertTrue(out.evidence);self.assertLessEqual(len(out.hits),3)
                with self.assertRaises(ContractError):await r.validate_result(q,replace(out,hits=()))
                original=self.request('无功补偿');a=await base.retrieve(original);b=await r.retrieve(original)
                self.assertEqual(a,b);await r.validate_result(original,b);self.assertEqual(converter.calls,1)
                unknown=await r.retrieve(self.request('《Absent Guide》有什么？'))
                self.assertFalse(unknown.evidence);self.assertEqual(converter.calls,1)
                self.assertIn('未找到',unknown.execution_issues[0].message)
            finally:r.close();base.close()
        asyncio.run(run())

    def test_conversion_failure_not_replaced_by_original_lane(self):
        async def run():
            class Invalid:
                async def run(self,q):raise ModelOutputError()
            r=ChineseFirstRetriever(self.db,self.k,Invalid())
            try:
                with self.assertRaises(ModelOutputError):await r.retrieve(self.request('EXI无功资源'))
                self.assertFalse(r.plans)
            finally:r.close()
        asyncio.run(run())

    def test_converter_records_in_scope_and_no_correction(self):
        async def run():
            class Adapter:
                async def complete(self,request):
                    self.request=request
                    return ModelResponse('{"query":"voltage control"}',model_id='deepseek-flash')
            a=Adapter();budget=ModelBudget(1)
            with ignored_temporary_directory(dir=Path(__file__).resolve().parents[1]/'data/retrieval_local') as diag:
                c=GenerationQueryConverter(a,ModelSettings('deepseek-flash',30,1000),Path(diag))
                with model_scope(budget):self.assertEqual(await c.run('电压控制'),'voltage control')
            self.assertEqual(budget.used,1);self.assertEqual(len(budget.records),1)
            self.assertFalse(a.request.correction);self.assertEqual(a.request.max_output_tokens,1000)
        asyncio.run(run())

    def test_fusion_depth_and_ranking_are_deterministic(self):
        scope=self.catalog.resolve('EXI 无功')
        a,lanes=self.catalog.rank('EXI 无功',scope,'reactive voltage bandwidth')
        b,_=self.catalog.rank('EXI 无功',scope,'reactive voltage bandwidth')
        self.assertEqual(a,b);self.assertEqual(len(a),len(set(fid for fid,_ in a)))
        self.assertTrue(all(len(l['candidates'])<=20 for l in lanes))


if __name__=='__main__':unittest.main()
