"""Synthetic concurrency regressions; no provider, environment file or paid calls."""
import asyncio
import json
import socket
import unittest
from unittest.mock import patch

from agents.evidence_verification import ModelEvidenceVerificationAgent
from core.models import VerificationStatus
from core.validation import require
from model_adapter.contracts import ModelMessage, ModelResponse, ModelSettings
from model_adapter.runtime import ModelBudget, ModelClient, model_scope, model_invocation_scope, current_model_invocation
from services.structured_model import structured_request
from tests.test_citation_workload import multi
from tests.test_fact_rereview_v3 import response


PROFILE = 'invocation_scoped_v1'
FACT_PROMPT = 'evidence-verification-v9.6-explicit-frozen-stance'


class CorrectionAccountingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        guard = patch.object(socket.socket, 'connect', side_effect=AssertionError('offline only'))
        guard.start()
        self.addCleanup(guard.stop)

    async def exercise(self, profile, *, foreign_component='power_domain_review',
                       foreign_prompt='synthetic-domain', limit=40, invalid_all_citations=False):
        inp = multi(2 if invalid_all_citations else 1)
        done, started = asyncio.Event(), asyncio.Event()
        seen = []

        class FactAdapter:
            async def complete(self, request):
                seen.append(request)
                payload = json.loads(request.messages[1].content)
                if 'ORIGINAL_CITATION_SCOPES' not in payload:
                    started.set()
                    await done.wait()
                    value = response(payload)
                else:
                    if invalid_all_citations or not request.correction:
                        return ModelResponse('{bad')
                    value = {'citation_reviews': [{'citation_index': s['citation_index'], 'status': 'supported',
                        'rationale': 'Synthetic source supports the complete bound substring.',
                        'applicability_conditions': [], 'bases': [{'type': 'text_excerpt',
                        'quote_id': s['QUOTE_CANDIDATES'][0]['quote_id']}]} for s in payload['ORIGINAL_CITATION_SCOPES']]}
                return ModelResponse(json.dumps(value))

        class ForeignAdapter:
            async def complete(self, request):
                return ModelResponse('{"valid": true}' if request.correction else '{bad')

        settings, budget = ModelSettings('synthetic_fixture'), ModelBudget(limit)
        agent = ModelEvidenceVerificationAgent(FactAdapter(), settings, schema_version=13,
                                              correction_accounting=profile)

        async def fact():
            with model_invocation_scope('fact-owner', 'evidence_verification', inp.answer.version):
                return await agent.run(inp)

        async def foreign():
            await started.wait()
            with model_invocation_scope('other-owner', foreign_component, inp.answer.version):
                def parse(value):
                    require(value == {'valid': True}, 'synthetic contract')
                    return value
                await structured_request(ModelClient(ForeignAdapter(), settings),
                    (ModelMessage('user', 'synthetic'),), foreign_prompt, parse)
            done.set()

        with model_scope(budget):
            output, _ = await asyncio.gather(fact(), foreign())
        return output, budget, seen

    async def test_reproduce_domain_correction_suppresses_legacy_fact_correction(self):
        old, budget, seen = await self.exercise('shared_slice_v1')
        self.assertTrue(old.execution_issues)
        self.assertEqual(len(seen), 2)
        self.assertFalse(any(r.correction for r in seen))
        self.assertEqual(budget.used, 4)

    async def test_scoped_correction_ignores_domain_but_still_shares_budget(self):
        fixed, budget, seen = await self.exercise(PROFILE)
        self.assertFalse(fixed.execution_issues)
        self.assertEqual(len(seen), 3)
        self.assertEqual(sum(r.correction for r in seen), 1)
        self.assertEqual(budget.used, 5)
        self.assertEqual(len(fixed.model_records), 3)
        self.assertTrue(all(r.invocation_id == 'fact-owner' for r in fixed.model_records))
        self.assertEqual(fixed.citation_reviews[0].status, VerificationStatus.SUPPORTED)

    async def test_same_prompt_and_component_from_other_invocation_cannot_take_correction(self):
        fixed, budget, _ = await self.exercise(PROFILE, foreign_component='evidence_verification', foreign_prompt=FACT_PROMPT)
        self.assertFalse(fixed.execution_issues)
        self.assertEqual(len(fixed.model_records), 3)
        self.assertTrue(all(r.invocation_id == 'fact-owner' for r in fixed.model_records))
        self.assertEqual(budget.used, 5)

    async def test_shared_global_limit_still_blocks_own_correction(self):
        fixed, budget, seen = await self.exercise(PROFILE, limit=4)
        self.assertTrue(fixed.execution_issues)
        self.assertEqual(budget.used, 4)
        self.assertEqual(len(seen), 2)
        self.assertEqual(fixed.citation_reviews[0].status, VerificationStatus.NOT_ASSESSABLE)

    async def test_fact_stage_keeps_only_one_correction_after_invalid_final(self):
        fixed, budget, seen = await self.exercise(PROFILE, invalid_all_citations=True)
        self.assertTrue(fixed.execution_issues)
        self.assertEqual(sum(r.correction for r in seen), 1)
        self.assertEqual(len(seen), 3)
        self.assertEqual(budget.used, 5)
        self.assertTrue(all(c.status == VerificationStatus.NOT_ASSESSABLE for c in fixed.citation_reviews))

    async def test_standalone_owner_is_program_bound_and_default_is_unchanged(self):
        class Adapter:
            async def complete(self, request):
                return ModelResponse(json.dumps(response(json.loads(request.messages[1].content))))
        agent = ModelEvidenceVerificationAgent(Adapter(), ModelSettings('synthetic_fixture'), schema_version=13,
                                               correction_accounting=PROFILE)
        from tests.test_fact_rereview_v3 import inputs
        self.assertIsNone(current_model_invocation())
        with model_scope(ModelBudget(2)):
            out = await agent.run(inputs(False))
        self.assertFalse(out.execution_issues)
        self.assertIsNotNone(out.model_records[0].invocation_id)
        self.assertEqual(out.model_records[0].component, 'evidence_verification')
        self.assertIsNone(current_model_invocation())
        default = ModelEvidenceVerificationAgent(Adapter(), ModelSettings('synthetic_fixture'), schema_version=13)
        self.assertEqual(default.correction_accounting, 'shared_slice_v1')
        with self.assertRaises(ValueError):
            ModelEvidenceVerificationAgent(Adapter(), ModelSettings('synthetic_fixture'), schema_version=14,
                                            correction_accounting=PROFILE)
        with self.assertRaises(ValueError):
            ModelEvidenceVerificationAgent(Adapter(), ModelSettings('synthetic_fixture'), schema_version=13,
                                            correction_accounting='unknown')

    async def test_initial_messages_unchanged_between_accounting_versions(self):
        _, _, old = await self.exercise('shared_slice_v1')
        _, _, new = await self.exercise(PROFILE)
        self.assertEqual(old, new[:2])
        self.assertTrue(new[2].correction)

    async def test_cancellation_preserves_record_and_does_not_retry(self):
        started = asyncio.Event()
        seen = []
        class Adapter:
            async def complete(self, request):
                seen.append(request)
                started.set()
                await asyncio.Event().wait()
        from tests.test_fact_rereview_v3 import inputs
        budget = ModelBudget(40)
        with model_scope(budget):
            task = asyncio.create_task(ModelEvidenceVerificationAgent(Adapter(), ModelSettings('synthetic_fixture'),
                schema_version=13, correction_accounting=PROFILE).run(inputs(False)))
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(len(seen), 1)
        self.assertEqual(budget.used, 1)
        self.assertEqual(len(budget.records), 1)
        self.assertEqual(budget.records[0].status.value, 'cancelled')
