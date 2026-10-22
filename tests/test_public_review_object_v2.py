"""Synthetic object-boundary wiring tests, no live services or old trial replay."""
import json
import socket
import unittest
from dataclasses import replace
from unittest.mock import patch
from tests.test_public_review_premise_v1 import Scripted, task, harness, TEXTS
from agents.premise_verification_v2 import PremiseVerificationAgentV2
from services.premise_claim_extractor_v2 import PremiseClaimExtractorV2, EXTRACTION_INSTRUCTION
from services.premise_review_protocol_v2 import PROFILE, PROMPT, INSTRUCTION
from core.models import AnswerDraft, TaskMode
from harness.contracts import RunBudget
from model_adapter.contracts import ModelSettings

class Adapter(Scripted):
    async def complete(self, request):
        if request.prompt_version == PROFILE + '-extraction':
            request = replace(request, prompt_version='public-review-premise-boundary-v1-dev-extraction')
        elif request.prompt_version == PROMPT:
            request = replace(request, prompt_version='evidence-verification-v9.21-task-premise-boundary-v1-dev')
        return await super().complete(request)

def build(adapter):
    h = harness(adapter)
    settings = ModelSettings('synthetic_fixture', max_output_tokens=8000, max_response_chars=96000)
    h.extractor = PremiseClaimExtractorV2(adapter, settings)
    h.verification = PremiseVerificationAgentV2(adapter, settings)
    return h

def kind_extraction(kinds):
    def change(wire, payload):
        for claim, kind in zip(wire['claims'], kinds):
            p = claim['components'][0]
            p.update(object_kind=kind, category='technical_fact', basis_target='technical_content',
                     verification_obligation='technical_truth', premise_ids=[] if kind=='literature' else [payload['TASK_PREMISES'][0]['premise_id']])
            claim['assertion_role'] = 'asserted'
    return change

class Boundaries(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        guard=patch.object(socket.socket,'connect',side_effect=AssertionError('offline'))
        guard.start();self.addCleanup(guard.stop)

    async def run_case(self, text, kinds, fact=None):
        req=task(TaskMode.ASSESS_EXISTING,existing_answer=AnswerDraft('new-object-v2',1,text))
        return await build(Adapter(extraction_change=kind_extraction(kinds),fact_change=fact)).run(req,RunBudget(max_revision_rounds=0))

    async def test_rule_restatement_needs_body_not_unrelated_premise(self):
        for text in ('At least 42 permits omitting O.', 'Regardless of the score omission is never mandatory.'):
            result=await self.run_case(text,['literature'])
            self.assertFalse(result.execution_issues)
            bases=result.verification_output.findings[0].bases
            self.assertEqual([b.type for b in bases],['text_excerpt'])
            self.assertEqual(result.extraction_output.claims[0].component_premise_ids,((),))

    async def test_generated_mainline_preserves_snapshot_and_v2_message_versions(self):
        result=await build(Adapter()).run(task(),RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        self.assertIsNotNone(result.verification_output.generation_snapshot)
        self.assertIn(PROFILE+'-extraction',[r.prompt_version for r in result.model_records])
        self.assertIn(PROMPT,[r.prompt_version for r in result.model_records])

    async def test_same_paragraph_mixed_rule_and_application_keep_separate_obligations(self):
        def change(wire,payload):
            kind_extraction(['literature'])(wire,payload)
            c=wire['claims'][0];p=dict(c['components'][0])
            p.update(object_kind='scenario_application',proposition='This stipulated 42 meets the rule.',premise_ids=[payload['TASK_PREMISES'][0]['premise_id']])
            c['components'].append(p)
        req=task(TaskMode.ASSESS_EXISTING,existing_answer=AnswerDraft('mixed-v2',1,'At least 42 permits O; this stipulated 42 therefore permits O.'))
        result=await build(Adapter(extraction_change=change)).run(req,RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        f=result.verification_output.findings[0]
        self.assertEqual([len(x.basis_indexes) for x in f.component_reviews],[1,2])

    async def test_real_application_missing_either_basis_is_still_rejected(self):
        for drop in ('text_excerpt','task_premise_reference'):
            def fact(wire,payload):
                for f in wire.get('findings',[]):
                    f['bases']=[b for b in f['bases'] if b['type']!=drop]
                    for r in f['component_reviews']:r['basis_indexes']=list(range(len(f['bases'])))
            result=await self.run_case('This score 42 therefore permits O.',['scenario_application'],fact)
            self.assertTrue(result.execution_issues)

    async def test_object_objection_is_valid_review_required_without_irrelevant_premise(self):
        def objection(wire,payload):
            for f in wire.get('findings',[]):
                f['bases']=[b for b in f['bases'] if b['type']=='text_excerpt']
                for r in f['component_reviews']:
                    r.update(status='not_assessable',basis_indexes=[0])
                    r['semantic_review'].update(fidelity='disputed',rationale='Frozen scenario_application should be literature: this clause restates the rule irrespective of the task score.')
                    r.pop('support_relation',None)
        result=await self.run_case('Omission is not mandatory.',['scenario_application'],objection)
        self.assertFalse(result.execution_issues)
        r=result.verification_output.findings[0].component_reviews[0]
        self.assertEqual(r.review_disposition,'review_required')
        self.assertEqual(r.fidelity_status,'disputed')
        self.assertNotEqual(result.report.decision.kind.value,'pass')
        self.assertEqual(result.extraction_output.claims[0].component_objects,('scenario_application',))

    async def test_wrong_application_can_be_faithfully_extracted_and_contradicted(self):
        def wrong(wire,payload):
            for f in wire.get('findings',[]):
                for r in f['component_reviews']:
                    r.update(status='contradicted',rationale='Actual task satisfies the permission threshold, not a prohibition.')
        result=await self.run_case('This score 42 prohibits O.',['scenario_application'],wrong)
        self.assertFalse(result.execution_issues)
        self.assertEqual(result.verification_output.findings[0].status.value,'contradicted')

    async def test_nested_classification_issue_remains_illegal(self):
        def nested(wire,payload):
            for f in wire.get('findings',[]):
                for r in f['component_reviews']:
                    r['semantic_review']['classification_issue']={'suggested_category':'technical_fact','rationale':'Wrong position and same category.'}
        result=await self.run_case('A general rule statement.',['literature'],nested)
        self.assertTrue(result.execution_issues)
        self.assertIn('SIBLING',INSTRUCTION)
        self.assertIn('Sharing an anchor',EXTRACTION_INSTRUCTION)

if __name__=='__main__':unittest.main()
