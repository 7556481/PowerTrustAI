"""Compare shared stages with a SHA-bound pre-refactor Harness, entirely offline.

The old implementation is read from local Git into memory, never executed as a
service or copied into a second production implementation. No provider or .env.
"""
import asyncio
from contextlib import ExitStack
from dataclasses import asdict, is_dataclass, replace
import hashlib
import inspect
import itertools
import json
from pathlib import Path
import subprocess
import types
import unittest
from unittest.mock import patch
from uuid import UUID

from agents.fakes import FakeConfig, make_fake_harness
from core.models import TaskMode, VerificationStatus, ExecutionStatus
from harness.contracts import RunBudget
from harness.runtime import OfflineHarness
from harness.states import RunState
from tests.test_harness import request
from tests.test_model_trace_attribution import Adapter, setup as managed_setup


BASE_COMMIT = '1d5528ff5eb15b79cd1479b1b6864cb4a0f904c5'
BASE_RUNTIME_SHA = '0376f1b87ee5426e6010dd88e1a6148ba47fa1f9f545c05bb34594ff121c2b12'
BASE_CHECKOUT_CRLF_SHA = 'ca232dd2edb2e8d4bf2541cd22cea37bea7452159f7bdb31d70b3fff7e25ede2'


def legacy_module():
    source = subprocess.check_output(
        ['git', 'show', f'{BASE_COMMIT}:harness/runtime.py'],
        cwd=Path(__file__).resolve().parents[1],
    )
    if hashlib.sha256(source).hexdigest() != BASE_RUNTIME_SHA:
        raise AssertionError('Pre-refactor runtime identity changed')
    if hashlib.sha256(source.replace(b'\n', b'\r\n')).hexdigest() != BASE_CHECKOUT_CRLF_SHA:
        raise AssertionError('Pre-refactor CRLF checkout identity changed')
    module = types.ModuleType('powertrust_pre_stage_refactor_fixture')
    exec(compile(source, '<local-git-pre-stage-refactor>', 'exec'), module.__dict__)
    return module


def canonical(value):
    """Ignore wall-clock observations only; all IDs and field values stay bound."""
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()
                if k not in ('timestamp_utc', 'duration_ms')}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if isinstance(value, str) and value.startswith('{'):
        try:
            return canonical(json.loads(value))
        except json.JSONDecodeError:
            pass
    return value


class StageDifferentialTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = legacy_module()

    async def compare(self, factory=None, *, task=None, budget=None, options=None,
                      cancel=False, observer_failure=None):
        values = []
        for old in (True, False):
            h = (factory or make_fake_harness)()
            # Constructors are unchanged. Only bind the original run/cancel
            # implementation for the reference side; agents are fresh doubles.
            if old:
                h.__class__ = self.old.OfflineHarness
            snapshots = []
            completed_peer = asyncio.Event()

            def observe(snapshot):
                snapshots.append(canonical(snapshot))
                if snapshot['event'].component == 'power_domain_review':
                    completed_peer.set()
                if observer_failure == snapshot['event'].component:
                    raise OSError('synthetic_fixture persistence failure')

            h.observer = observe
            # Fixed generated IDs preserve cross-references, unlike deleting ID
            # fields from a diff. Input answer/claim/evidence IDs are untouched.
            ids = itertools.count(1)
            fixed_uuid = lambda: UUID(int=next(ids))
            with ExitStack() as stack:
                stack.enter_context(patch.object(self.old, 'uuid4', fixed_uuid))
                stack.enter_context(patch('harness.execution.uuid4', fixed_uuid))
                stack.enter_context(patch('harness.retrieval.uuid4', fixed_uuid))
                error = result = None
                try:
                    running = asyncio.create_task(h.run(
                        task or request(), budget or RunBudget(),
                        run_id='synthetic_fixture-differential', **(options or {})))
                    if cancel:
                        await asyncio.wait_for(completed_peer.wait(), 2)
                        await h.cancel('synthetic_fixture-differential')
                    result = await running
                except Exception as exc:
                    error = (type(exc).__name__, str(exc))
            self.assertEqual(h._runs, {})
            values.append(canonical({
                'result': result, 'error': error, 'snapshots': snapshots,
                'generation_inputs': h.generation.inputs,
                'verification_inputs': getattr(h.verification, 'inputs',
                                               getattr(getattr(h.verification, 'delegate', None), 'inputs', [])),
                'domain_inputs': getattr(h.domain_review, 'inputs',
                                         getattr(getattr(h.domain_review, 'delegate', None), 'inputs', [])),
                'extraction_versions': h.extractor.versions,
            }))
        self.assertEqual(values[0], values[1])
        return values[1]

    def test_public_interface_and_exception_exports(self):
        self.assertEqual(inspect.signature(self.old.OfflineHarness.run),
                         inspect.signature(OfflineHarness.run))
        self.assertEqual(inspect.signature(self.old.OfflineHarness.cancel),
                         inspect.signature(OfflineHarness.cancel))
        from harness.execution import HarnessObserverError as internal
        from harness.runtime import HarnessObserverError as public
        self.assertIs(internal, public)

    async def test_both_modes_and_early_terminal_modes(self):
        for mode in TaskMode:
            with self.subTest(mode=mode):
                value = await self.compare(task=request(mode))
                self.assertEqual(value['result']['state'], RunState.COMPLETED)
        for option, mode, state in (
            ('generation_only', TaskMode.QUESTION_ANSWER, RunState.GENERATED),
            ('evidence_only', TaskMode.ASSESS_EXISTING, RunState.EVIDENCE_REVIEWED),
        ):
            with self.subTest(option=option):
                value = await self.compare(task=request(mode), options={option: True})
                self.assertEqual(value['result']['state'], state)
                self.assertEqual(value['domain_inputs'], [])

    async def test_revision_reextracts_and_reaudits_both_versions(self):
        config = FakeConfig(verification_statuses=(
            VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED))
        value = await self.compare(lambda: make_fake_harness(config))
        self.assertEqual(value['extraction_versions'], [1, 2])
        self.assertEqual([x['answer']['version'] for x in value['domain_inputs']], [1, 2])
        self.assertEqual([x['answer']['version'] for x in value['verification_inputs']], [1, 2])
        self.assertEqual(len(value['result']['review_rounds']), 2)
        self.assertEqual(value['result']['answer']['version'], 2)

    async def test_partial_failure_timeout_and_bad_id_keep_peer(self):
        cases = [FakeConfig(verification_error=True), FakeConfig(domain_error=True),
                 FakeConfig(bad_evidence_id=True), FakeConfig(bad_claim_id=True),
                 FakeConfig(verification_delay=.2)]
        for config in cases:
            with self.subTest(config=config):
                value = await self.compare(lambda: make_fake_harness(config),
                                           budget=RunBudget(step_timeout_seconds=.04))
                self.assertTrue(value['result']['execution_issues'])
                report = value['result']['report']
                peer = 'verification_findings' if config.domain_error else 'domain_findings'
                self.assertTrue(report[peer])

    async def test_cancel_retains_completed_peer_event_and_cleans_registry(self):
        value = await self.compare(
            lambda: make_fake_harness(FakeConfig(verification_delay=10)), cancel=True)
        self.assertEqual(value['result']['state'], RunState.CANCELLED)
        peer = [x for x in value['snapshots']
                if x['event']['component'] == 'power_domain_review']
        self.assertEqual(len(peer), 1)
        self.assertTrue(peer[0]['stage_output']['findings'])

    async def test_observer_failure_stops_without_fabricated_result(self):
        for component in ('state', 'power_domain_review', 'audit_policy', 'termination'):
            with self.subTest(component=component):
                value = await self.compare(observer_failure=component)
                self.assertEqual(value['error'][0], 'HarnessObserverError')
                self.assertIsNone(value['result'])
                self.assertEqual(value['snapshots'][-1]['event']['component'], component)

    async def test_shared_managed_budget_correction_and_call_ownership(self):
        value = await self.compare(lambda: managed_setup(Adapter(correction=True)),
                                   budget=RunBudget(max_model_calls=4))
        records = value['result']['model_records']
        # Records are retained in completion order; call numbers bind admission.
        self.assertEqual(sorted(x['call_number'] for x in records), [2, 3, 4])
        self.assertEqual(sum(x['correction'] for x in records), 1)
        for record in records:
            self.assertIn(record['component'], ('evidence_verification', 'power_domain_review'))
            self.assertEqual(record['answer_version'], 1)
        fact = [x for x in records if x['component'] == 'evidence_verification']
        self.assertEqual(len({x['invocation_id'] for x in fact}), 1)

    async def test_managed_timeout_and_exhausted_shared_budget(self):
        value = await self.compare(lambda: managed_setup(Adapter(delay=.3), timeout=.04),
                                   budget=RunBudget(max_revision_rounds=0))
        self.assertEqual({x['status'] for x in value['result']['model_records']},
                         {ExecutionStatus.TIMED_OUT, ExecutionStatus.SUCCEEDED})
        value = await self.compare(budget=RunBudget(max_model_calls=2))
        self.assertTrue(value['result']['report']['verification_findings'])
        self.assertFalse(value['result']['report']['domain_findings'])

    async def test_invalid_input_fails_before_observer_or_agent(self):
        value = await self.compare(task=replace(request(), question=' '))
        self.assertEqual(value['error'][0], 'InputError')
        self.assertFalse(value['snapshots'])
        self.assertFalse(value['generation_inputs'])

    async def test_scalar_tool_preserves_contract_result_and_budget(self):
        from tools.unit_conversion import UnitConversionTool

        def factory():
            h = make_fake_harness(FakeConfig(text='230 kV equals 230000 V.'))
            h.unit_tool = UnitConversionTool(version='scalar-si-conversion-v2')
            return h

        value = await self.compare(factory)
        self.assertTrue(value['result']['tool_results'])
        self.assertEqual(value['result']['tool_results'][0]['payload']['output_value'], 230000)

    async def test_retrieval_revision_and_failure_match_with_same_snapshot(self):
        from tests.test_harness_retrieval import HarnessRetrievalTests
        from rag.contracts import RetrievalPurpose
        fixture = HarnessRetrievalTests()
        fixture.setUp()
        try:
            config = FakeConfig(verification_statuses=(
                VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED))
            options = {'knowledge_version': fixture.original.knowledge_version}
            value = await self.compare(lambda: fixture.harness(config),
                                       task=fixture.request(), options=options)
            self.assertEqual(value['extraction_versions'], [1, 2])
            self.assertTrue(value['result']['retrieval_records'])

            async def fail_fact(query):
                if query.purpose == RetrievalPurpose.VERIFICATION:
                    raise RuntimeError('synthetic_fixture retrieval failure')

            fixture.retriever.hook = fail_fact
            value = await self.compare(fixture.harness, task=fixture.request(), options=options)
            self.assertTrue(value['result']['report']['domain_findings'])
            self.assertFalse(value['result']['report']['verification_findings'])
        finally:
            # This fixture is used inside our running async test, rather than
            # through its own unittest runner. Close its resources directly.
            fixture.actual.close()
            fixture.tmp.cleanup()
