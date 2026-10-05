"""Public synthetic_fixture: real BM25 session and existing Harness routing."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agents.generation import EvidenceGenerationAgent, messages_for
from agents.contracts import GenerationInput
from agents.fakes import make_fake_harness, FakeConfig, FakeEvidenceVerificationAgent
from core.models import TaskRequest, TaskMode, VerificationStatus
from harness.contracts import RunBudget
from harness.product_policy import ProductAuditPolicy
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata
from services.generation_query import GenerationQueryConverter, english_corpus
from tests.test_generation import ScriptAdapter, response
from model_adapter.contracts import ModelSettings, ModelResponse, ModelConnectionError


class QueryTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, converted='voltage reactive resources', failure=False, generated=False, unsupported=False):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);md=root/'fixture.md';md.write_text('# synthetic_fixture\n\n'+
                'Voltage reactive resources maintain acceptable bus voltage under normal and fault conditions. '*3)
            with KnowledgeStore(root/'k.db') as store:
                item=store.ingest(md,'fixture',SourceMetadata(source_type='synthetic_fixture'))
                self.assertTrue(english_corpus(store.rows(item.knowledge_version)))
            adapter=ScriptAdapter(ModelConnectionError() if failure else ModelResponse(json.dumps({'query':converted})))
            retriever=AsyncSQLiteBM25Retriever(root/'k.db')
            h=make_fake_harness();h.retriever=retriever;h.policy=ProductAuditPolicy(synthetic_fixture=True)
            if unsupported:
                h.verification=FakeEvidenceVerificationAgent(FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)))
            with patch('services.response_diagnostics.LOCAL_ROOT', root):
                h.generation_query_converter=GenerationQueryConverter(adapter,ModelSettings('synthetic_model'),root/'diag')
            h.generation_corpus_english=True
            gen_adapter=ScriptAdapter(response())
            if not generated:h.generation=EvidenceGenerationAgent(gen_adapter,ModelSettings('synthetic_model'))
            request=TaskRequest('synthetic',TaskMode.QUESTION_ANSWER,'voltage_stability','为什么需要无功资源？只作概念解释。')
            try:
                with patch('services.response_diagnostics.LOCAL_ROOT', root):
                    result=await h.run(request,RunBudget(),knowledge_version=item.knowledge_version)
            finally:retriever.close()
            return result,adapter.requests,gen_adapter.requests

    async def test_once_original_then_converted_hits_then_existing_review(self):
        result,requests,_=await self.run_case(generated=True)
        self.assertEqual(len(requests),1)
        self.assertEqual(result.retrieval_records[0].outcome,'empty')
        self.assertEqual(result.retrieval_records[1].outcome,'hits')
        self.assertEqual(result.retrieval_records[1].query,'voltage reactive resources')
        self.assertTrue(result.review_rounds)

    async def test_still_empty_no_generation_or_audit_calls(self):
        result,requests,generation=await self.run_case('unfindablexyz')
        self.assertEqual(len(requests),1);self.assertFalse(generation)
        self.assertEqual(result.state.value,'needs_information')
        self.assertFalse(result.review_rounds);self.assertFalse(result.execution_issues)
        self.assertIn('当前检索未找到',result.answer.text)
        self.assertEqual(result.report.decision.reason_codes,('NO_SUBSTANTIVE_ANSWER',))
        self.assertFalse(any(e.component in ('claim_extraction','evidence_verification','power_domain_review') for e in result.trace.events))

    async def test_hits_do_not_force_supported_or_pass(self):
        result,_,_=await self.run_case(generated=True,unsupported=True)
        self.assertEqual(result.retrieval_records[1].outcome,'hits')
        self.assertEqual(result.report.decision.kind.value,'needs_information')
        self.assertTrue(result.review_rounds)

    async def test_conversion_failure_not_evidence_or_fact_failure(self):
        result,requests,generation=await self.run_case(failure=True)
        self.assertEqual(len(requests),1);self.assertFalse(generation)
        self.assertEqual(len(result.retrieval_records),1)
        self.assertTrue(result.execution_issues);self.assertIsNone(result.verification_output)
        self.assertEqual(result.state.value,'execution_incomplete')

    async def test_malformed_conversion_no_retry(self):
        result,requests,_=await self.run_case('中文不合法')
        self.assertEqual(len(requests),1);self.assertTrue(result.execution_issues)

    def test_language_gate_and_generation_prompt(self):
        from services.generation_query import english_fallback_available
        self.assertTrue(english_fallback_available([{'raw_text':'English reference '*100},{'raw_text':'中文资料'}]))
        self.assertFalse(english_corpus([{'raw_text':'中文资料'+('english '*100)}]))
        req=TaskRequest('synthetic',TaskMode.QUESTION_ANSWER,'fixture','中文问题')
        prompt=messages_for(GenerationInput(req,()),3)[0].content
        self.assertIn('answer in Chinese',prompt)
        self.assertIn('Do not call another model',prompt)

    def test_ui_collapsed_and_citations_only(self):
        html=Path('backend/static/index.html').read_text(encoding='utf-8')
        self.assertIn('<details class="panel"><summary>审核详情：逐项发现',html)
        self.assertNotIn('<details class="panel" open',html)
        self.assertLess(html.index('id="answers"'),html.index('id="decision"'))
        script=Path('backend/static/app.js').read_text(encoding='utf-8')
        self.assertIn('if(!cited.has(e.evidence_id))continue',script)

    def test_failed_query_display_is_specific_chinese(self):
        from backend.presentation import explain
        result=explain({'execution':{'status':'finished','execution_issues':[
            {'component':'generation_query_conversion','code':'MODEL_CONNECTION_FAILED'}]}})
        self.assertIn('未生成回答',result['answer_unavailable_reason'])
        self.assertIn('转换失败',result['reasons'][0])

    async def test_uncited_model_text_never_bypasses_audit(self):
        from tests.test_generation import inputs
        v={'answer_id':'synthetic-answer','version':1,'text':'Unsupported technical assertion.',
           'citations':[],'assumptions':[],'missing_information':['Missing supporting material.'],
           'evidence_sufficient':False}
        output=await EvidenceGenerationAgent(ScriptAdapter(ModelResponse(json.dumps(v))),
            ModelSettings('synthetic_model')).run(inputs())
        self.assertTrue(output.substantive_answer)
