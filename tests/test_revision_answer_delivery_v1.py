"""Candidate wiring and unchanged repair gates; synthetic, not semantic scores."""
import json
import unittest
from dataclasses import replace
from unittest.mock import patch
from agents.revision import ModelRevisionAgent
from agents.revision_contract_v2 import ANSWER_ONLY_PROMPT_VERSION, parse
from agents.contracts import RevisionInput
from agents.fakes import make_fake_harness, FakeConfig
from core.models import TaskRequest, TaskMode, VerificationStatus
from core.validation import ContractError
from harness.contracts import RunBudget
from model_adapter.contracts import ModelSettings, ModelResponse
from model_adapter.runtime import ModelBudget, model_scope


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_message_snapshot_and_unchanged_all_retained_gate(self):
        h=make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)))
        request=TaskRequest('t',TaskMode.QUESTION_ANSWER,'s','Explain the condition and conclusion.')
        r=await h.run(request,RunBudget(max_revision_rounds=0))
        inputs=RevisionInput(request,r.answer,r.verification_output,r.domain_output,r.evidence,())
        ids=[f.finding_id for f in inputs.verification.findings+inputs.domain_review.findings]
        value=dict(answer_units=[dict(kind='technical',text='Under the stated condition, the corrected conclusion holds.',evidence_ids=[])],
                   assumptions=[],missing_information=[],finding_actions=[dict(finding_id=f,action='modified' if i==0 else 'retained',explanation='Fixture proposed correction' if i==0 else 'Fixture unchanged finding') for i,f in enumerate(ids)])
        seen=[]
        class Adapter:
            async def complete(self,request):
                seen.append(request)
                return ModelResponse(json.dumps(value),request.model_id,finish_reason='stop')
        with model_scope(ModelBudget(40)):
            out=await ModelRevisionAgent(Adapter(),ModelSettings('synthetic'),protocol_version=2,clean_answer_body=True,answer_delivery='answer_only_v1').run(inputs)
        self.assertEqual(out.prompt_version,ANSWER_ONLY_PROMPT_VERSION)
        self.assertEqual(out.evidence_snapshot.input_prompt_version,ANSWER_ONLY_PROMPT_VERSION)
        self.assertIn('ONLY in finding_actions.explanation',seen[0].messages[0].content)
        self.assertIn('complete independent re-review',seen[0].messages[0].content)
        for a in value['finding_actions']:a['action']='retained'
        with self.assertRaises(ContractError):parse(value,inputs)
        value['finding_actions'][0]['action']='modified'
        value['answer_units'][0]['text']=inputs.answer.text
        with self.assertRaises(ContractError):parse(value,inputs)
        value['answer_units'][0]['text']='Changed.'
        value['finding_actions'][-1]['action']='unresolved'
        out=parse(value,inputs)
        self.assertIn(ids[-1],out.unresolved_finding_ids)


class FactoryTests(unittest.TestCase):
    def test_factory_graph_store_api_two_versions_and_failure(self):
        import tests.test_schema14_factory_flow as f
        from harness.graph_runtime_v1 import validate_versions, build_graph
        validate_versions();build_graph()
        original=f.ServiceConfig
        with patch.object(f,'ServiceConfig',side_effect=lambda **kw:original(**kw,revision_answer_delivery='answer_only_v1',execution_path='langgraph_v1')):
            for kw in (dict(),dict(existing=True,revision=True,subject=True),dict(evidence_gap=True),dict(fault=True)):
                result,provider,_=f.FactoryFlowTests().exercise(schema=13,concept=True,**kw)
                if kw.get('revision'):
                    self.assertEqual(len(result['answer']['versions']),2)
                    self.assertTrue(result['execution']['required_stages_complete'])
                    revisions=[r for r in provider.requests if r.prompt_version==ANSWER_ONLY_PROMPT_VERSION]
                    self.assertEqual(len(revisions),1)
                if kw.get('objection') or kw.get('evidence_gap') or kw.get('fault'):
                    self.assertNotEqual(result['decision']['kind'],'pass')

    def test_default_invalid_and_legacy(self):
        from backend.config import ServiceConfig
        self.assertEqual(ServiceConfig().revision_answer_delivery,'production')
        with self.assertRaises(ValueError):ServiceConfig(revision_answer_delivery='unknown')
        with self.assertRaises(ContractError):ModelRevisionAgent(None,ModelSettings('synthetic'),answer_delivery='answer_only_v1')
