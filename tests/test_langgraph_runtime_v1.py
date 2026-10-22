"""Offline graph/sequence parity; no providers, credentials or cloud traces."""
import asyncio
from dataclasses import asdict, replace
import importlib.util
import types
import unittest
from unittest.mock import patch

from agents.fakes import make_fake_harness
from core.validation import InputError
from harness.contracts import RunBudget
from harness.execution import RunExecution
from harness.runtime import OfflineHarness
from harness.states import RunState
from tests import test_harness_stage_differential as baseline
from tests.test_harness import request
from tests.test_model_trace_attribution import Adapter, setup as managed_setup


AVAILABLE = importlib.util.find_spec('langgraph') is not None


@unittest.skipUnless(AVAILABLE, 'Optional requirements-langgraph.lock.txt not installed')
class GraphDifferentialTests(baseline.StageDifferentialTests):
    candidate_execution_path = 'langgraph_v1'

    @classmethod
    def setUpClass(cls):
        cls.old = types.SimpleNamespace(OfflineHarness=OfflineHarness, uuid4=None)

    async def test_product_policy_terminal_routes_and_revision_match(self):
        from agents.fakes import FakeConfig
        from core.models import VerificationStatus
        from harness.product_policy import ProductAuditPolicy
        cases = [
            (FakeConfig(), RunState.COMPLETED),
            (FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,
                                              VerificationStatus.SUPPORTED)), RunState.COMPLETED),
            (FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)), RunState.REJECTED),
            (FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)), RunState.NEEDS_INFORMATION),
            (FakeConfig(verification_error=True), RunState.EXECUTION_INCOMPLETE),
        ]
        for config, state in cases:
            def factory():
                h = make_fake_harness(config)
                h.policy = ProductAuditPolicy(synthetic_fixture=True)
                return h
            with self.subTest(state=state, config=config):
                value = await self.compare(factory)
                self.assertEqual(value['result']['state'], state)

    async def test_no_substantive_answer_skips_all_reviews(self):
        def factory():
            h = make_fake_harness()
            generate = h.generation.run

            async def no_answer(inputs):
                output = await generate(inputs)
                return replace(output, substantive_answer=False, answer=replace(
                    output.answer, text='synthetic_fixture: insufficient evidence.',
                    missing_information=('synthetic_fixture: required evidence missing',)))
            h.generation.run = no_answer
            return h
        value = await self.compare(factory)
        self.assertEqual(value['result']['state'], RunState.NEEDS_INFORMATION)
        self.assertFalse(value['verification_inputs'])
        self.assertFalse(value['domain_inputs'])
        self.assertFalse(value['extraction_versions'])

    async def test_exact_managed_message_content_and_correction(self):
        class RecordingAdapter(Adapter):
            def __init__(self):
                super().__init__(correction=True)
                self.requests = []

            async def complete(self, value):
                self.requests.append(asdict(value))
                return await super().complete(value)

        def factory():
            adapter = RecordingAdapter()
            h = managed_setup(adapter)
            h._fixture_requests = adapter.requests
            return h

        value = await self.compare(factory, budget=RunBudget(max_model_calls=4))
        self.assertEqual(len(value['transport_requests']), 3)
        self.assertEqual(sum(x['correction'] for x in value['transport_requests']), 1)


@unittest.skipUnless(AVAILABLE, 'Optional requirements-langgraph.lock.txt not installed')
class GraphControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_sqlite_wire_and_restore_compatibility(self):
        import tempfile
        from pathlib import Path
        from backend.store import RunStore
        from backend.serialization import wire
        from evaluation.archive_replay import restore
        from harness.contracts import HarnessResult
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(Path(directory) / 'synthetic.sqlite3')
            try:
                rid = 'synthetic-graph-storage'
                value = request()
                store.create(rid, value, {'profile': 'synthetic_fixture', 'execution_path': 'langgraph_v1'})
                h = managed_setup(Adapter(correction=True))
                h.execution_path = 'langgraph_v1'
                h.observer = lambda snapshot: store.checkpoint(rid, snapshot)
                result = await h.run(value, RunBudget(max_model_calls=4), run_id=rid)
                store.mark(rid, 'finished', result=result)
                saved = store.get(rid)['result']
                self.assertEqual(restore(saved, HarnessResult), result)
                self.assertTrue(store.events(rid))
                self.assertNotIn('next_stage', wire(result))
                self.assertEqual(len(result.model_records), 3)
            finally:
                store.close()

    async def test_graph_really_drives_all_stages_and_revision_loop(self):
        from contextlib import ExitStack
        from agents.fakes import FakeConfig
        from core.models import VerificationStatus
        from harness.graph_runtime_v1 import STAGES
        visits = []

        def wrap(name, original):
            async def stage(execution):
                visits.append(name)
                return await original(execution)
            return stage

        h = make_fake_harness(FakeConfig(verification_statuses=(
            VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED)))
        h.execution_path = 'langgraph_v1'
        with ExitStack() as stack:
            stack.enter_context(patch.object(RunExecution, 'run_stages', side_effect=AssertionError('No sequential driver')))
            for name in STAGES:
                stack.enter_context(patch.object(RunExecution, name, wrap(name, getattr(RunExecution, name))))
            result = await h.run(request(), RunBudget())
        self.assertEqual(result.state, RunState.COMPLETED)
        self.assertEqual(visits, [
            'validate_saved_inputs', 'generate', 'extract_and_tools', 'prepare_review',
            'review_pair', 'merge_and_decide', 'revise', 'extract_and_tools',
            'prepare_review', 'review_pair', 'merge_and_decide',
        ])

    async def test_graph_failure_never_runs_sequential_fallback(self):
        h = make_fake_harness()
        h.execution_path = 'langgraph_v1'
        with patch('harness.graph_runtime_v1.build_graph', side_effect=RuntimeError('synthetic graph failure')), \
             patch.object(RunExecution, 'run_stages', side_effect=AssertionError('No fallback')) as original:
            result = await h.run(request(), RunBudget())
        original.assert_not_called()
        self.assertEqual(result.state, RunState.FAILED)
        self.assertEqual(h.generation.inputs, [])
        self.assertEqual(h._runs, {})

    async def test_missing_optional_dependency_fails_before_agents_without_fallback(self):
        h = make_fake_harness()
        with patch.dict('sys.modules', {'harness.graph_runtime_v1': None}):
            result = await h.run(request(), RunBudget())
            self.assertEqual(result.state, RunState.COMPLETED)
            h.execution_path = 'langgraph_v1'
            with self.assertRaisesRegex(InputError, 'dependencies unavailable'):
                await h.run(request(), RunBudget())
        self.assertEqual(len(h.generation.inputs), 1)
        self.assertEqual(h._runs, {})

    async def test_no_checkpoint_retry_cache_or_cloud_under_outer_trace_context(self):
        from harness.graph_runtime_v1 import build_graph
        from langsmith import tracing_context
        graph = build_graph()
        self.assertIsNone(graph.checkpointer)
        self.assertIsNone(graph.cache)
        self.assertIsNone(graph.store)
        self.assertTrue(all(not node.retry_policy for node in graph.nodes.values()))
        h = make_fake_harness()
        h.execution_path = 'langgraph_v1'
        with tracing_context(enabled=True), \
             patch('socket.socket.connect', side_effect=AssertionError('Network prohibited')) as connect:
            result = await h.run(request(), RunBudget())
        connect.assert_not_called()
        self.assertEqual(result.state, RunState.COMPLETED)

    async def test_simultaneous_runs_have_independent_contexts_and_budgets(self):
        h = make_fake_harness()
        h.execution_path = 'langgraph_v1'
        first = replace(request(), task_id='fixture-first')
        second = replace(request(), task_id='fixture-second')
        a, b = await asyncio.gather(
            h.run(first, RunBudget(), run_id='first'),
            h.run(second, RunBudget(max_model_calls=2), run_id='second'),
        )
        self.assertEqual(a.state, RunState.COMPLETED)
        self.assertEqual(b.state, RunState.REVIEW_REQUIRED)
        self.assertEqual(a.answer.answer_id, 'fixture-first-answer')
        self.assertEqual(b.answer.answer_id, 'fixture-second-answer')
        self.assertEqual(h._runs, {})

    async def test_constructor_default_and_invalid_choice(self):
        h = make_fake_harness()
        self.assertEqual(h.execution_path, 'sequential')
        with self.assertRaises(InputError):
            OfflineHarness(h.generation, h.verification, h.domain_review, h.revision,
                           h.extractor, execution_path='unreviewed')
        h.execution_path = 'unreviewed'
        with self.assertRaises(InputError):
            await h.run(request(), RunBudget())
        self.assertFalse(h.generation.inputs)

    async def test_version_mismatch_stops_before_registration_or_calls(self):
        h = make_fake_harness()
        h.execution_path = 'langgraph_v1'
        with patch('harness.graph_runtime_v1.version', return_value='unexpected'):
            with self.assertRaisesRegex(InputError, 'differs from lock'):
                await h.run(request(), RunBudget())
        self.assertEqual(h._runs, {})
        self.assertEqual(h.generation.inputs, [])
