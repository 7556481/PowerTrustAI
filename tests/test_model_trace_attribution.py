"""Public synthetic_fixture: concurrent managed requests, never provider access."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from agents.fakes import make_fake_harness
from core.models import ExecutionStatus
from core.validation import require
from evaluation.archive_replay import restore
from harness.contracts import RunBudget
from model_adapter.contracts import ModelCallRecord, ModelMessage, ModelResponse, ModelSettings
from model_adapter.runtime import ModelClient
from services.structured_model import structured_request
from tests.test_harness import request


class Adapter:
    def __init__(self, *, correction=False, delay=.025):
        self.correction, self.delay = correction, delay
        self.started = asyncio.Event()
        self.count = 0

    async def complete(self, value):
        self.count += 1
        if self.count >= 2:
            self.started.set()
        await self.started.wait()
        fact = value.messages[0].content == 'synthetic_fixture fact'
        await asyncio.sleep(self.delay if fact else .005)
        return ModelResponse('invalid' if fact and self.correction and not value.correction
                             else '{"ok":true}', 'synthetic_fixture', finish_reason='stop')


class ManagedReview:
    uses_model_adapter = True

    def __init__(self, delegate, client, label):
        self.delegate, self.client, self.label = delegate, client, label
        self.records = ()

    async def run(self, value):
        def parse(data):
            require(data == {'ok': True}, 'synthetic_fixture shape')
            return data
        _, self.records = await structured_request(self.client,
            (ModelMessage('user', 'synthetic_fixture ' + self.label),),
            'same-prompt-for-both-stages', parse)
        return await self.delegate.run(value)


def setup(adapter, timeout=1):
    h = make_fake_harness()
    client = ModelClient(adapter, ModelSettings('synthetic_fixture', timeout_seconds=timeout))
    h.verification = ManagedReview(h.verification, client, 'fact')
    h.domain_review = ManagedReview(h.domain_review, client, 'domain')
    return h


class AttributionTests(unittest.IsolatedAsyncioTestCase):
    def assert_binding(self, result):
        actual = {r.call_number: r for r in result.model_records}
        events = [e for e in result.trace.events if e.component == 'model_request']
        self.assertEqual(len(events), len(actual))
        self.assertEqual({json.loads(e.detail)['call_number'] for e in events}, set(actual))
        self.assertEqual(len({e.output_refs for e in events}), len(actual))
        for event in events:
            value = json.loads(event.detail)
            record = actual[value['call_number']]
            self.assertEqual(value, json.loads(json.dumps(asdict(record))))
            self.assertTrue(record.invocation_id)
            self.assertIn(record.component, ('evidence_verification', 'power_domain_review'))
            self.assertEqual(record.answer_version, 1)
            self.assertEqual(event.answer_version, record.answer_version)
            self.assertEqual(event.output_refs, (f'{result.run_id}:model:{record.call_number}',))

    async def test_concurrent_same_prompt_exact_once_and_stage_output_ownership(self):
        h = setup(Adapter())
        result = await h.run(request(), RunBudget(max_revision_rounds=0))
        self.assert_binding(result)
        self.assertEqual(sorted(r.call_number for r in result.model_records), [2, 3])
        self.assertFalse(result.execution_issues)
        self.assertEqual(len(h.verification.records), 1)
        self.assertEqual(len(h.domain_review.records), 1)
        self.assertTrue(all(r.component == 'evidence_verification' for r in h.verification.records))
        self.assertTrue(all(r.component == 'power_domain_review' for r in h.domain_review.records))

    async def test_one_correction_retains_invalid_attempt_without_cross_stage_records(self):
        h = setup(Adapter(correction=True))
        result = await h.run(request(), RunBudget(max_revision_rounds=0))
        self.assert_binding(result)
        self.assertEqual(sorted(r.call_number for r in result.model_records), [2, 3, 4])
        self.assertEqual(len(h.verification.records), 2)
        self.assertEqual(len(h.domain_review.records), 1)
        self.assertEqual([r.correction for r in h.verification.records], [False, True])
        self.assertEqual([r.output_status for r in h.verification.records], ['invalid_structure', 'valid_structure'])
        self.assertEqual(len({r.invocation_id for r in h.verification.records}), 1)

    async def test_provider_timeout_retained_and_sibling_success_not_duplicated(self):
        result = await setup(Adapter(delay=.2), timeout=.03).run(request(), RunBudget(max_revision_rounds=0))
        self.assert_binding(result)
        self.assertEqual({r.status for r in result.model_records},
                         {ExecutionStatus.TIMED_OUT, ExecutionStatus.SUCCEEDED})
        self.assertTrue(result.execution_issues)

    async def test_stage_timeout_retains_cancelled_transport(self):
        result = await setup(Adapter(delay=.2)).run(request(), RunBudget(max_revision_rounds=0, step_timeout_seconds=.04))
        self.assert_binding(result)
        self.assertEqual({r.status for r in result.model_records},
                         {ExecutionStatus.CANCELLED, ExecutionStatus.SUCCEEDED})
        self.assertTrue(any(i.status == ExecutionStatus.TIMED_OUT for i in result.execution_issues))

    async def test_run_cancel_preserves_inflight_call_records(self):
        adapter = Adapter(delay=10)
        h = setup(adapter, timeout=20)
        running = asyncio.create_task(h.run(request(), RunBudget(), run_id='synthetic_fixture-cancel'))
        await asyncio.wait_for(adapter.started.wait(), 2)
        await h.cancel('synthetic_fixture-cancel')
        result = await running
        self.assert_binding(result)
        self.assertEqual(len(result.model_records), 2)
        self.assertTrue(all(r.status == ExecutionStatus.CANCELLED for r in result.model_records))

    async def test_invalid_correction_stops_and_keeps_failed_output_and_valid_sibling(self):
        class Invalid(Adapter):
            async def complete(self, value):
                response = await super().complete(value)
                return ModelResponse('invalid', 'synthetic_fixture', finish_reason='stop') if value.messages[0].content.endswith('fact') else response
        result = await setup(Invalid()).run(request(), RunBudget(max_revision_rounds=0))
        self.assert_binding(result)
        self.assertEqual(len(result.model_records), 3)
        invalid = [r for r in result.model_records if r.component == 'evidence_verification']
        self.assertEqual([r.correction for r in invalid], [False, True])
        self.assertTrue(all(r.output_status == 'invalid_structure' for r in invalid))
        self.assertTrue(result.execution_issues)
        self.assertIsNotNone(result.domain_output)

    async def test_sqlite_checkpoint_result_restart_preserve_bindings(self):
        from backend.store import RunStore
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic_fixture.sqlite3'
            store = RunStore(path)
            value = request()
            rid = 'synthetic_fixture-persist'
            store.create(rid, value, {'profile': 'synthetic_fixture'})
            h = setup(Adapter(correction=True))
            h.observer = lambda snapshot: store.checkpoint(rid, snapshot)
            result = await h.run(value, RunBudget(max_revision_rounds=0), run_id=rid)
            store.mark(rid, 'finished', result=result)
            before = store.get(rid)['result']
            store.close()
            reopened = RunStore(path)
            try:
                self.assertEqual(reopened.get(rid)['result'], before)
                restored = restore(before, type(result))
                self.assert_binding(restored)
                saved = [row['event'] for row in reopened.events(rid)
                         if row['event']['component'] == 'model_request']
                self.assertEqual(len(saved), len(result.model_records))
                self.assertEqual({json.loads(row['detail'])['call_number'] for row in saved},
                                 {r.call_number for r in result.model_records})
            finally:
                reopened.close()

    def test_legacy_records_restore_without_inventing_ownership(self):
        value = json.loads(json.dumps(asdict(ModelCallRecord(1, 'synthetic_fixture', 'old', False,
                                                           ExecutionStatus.FAILED, 0))))
        for key in ('invocation_id', 'component', 'answer_version'):
            del value[key]
        restored = restore(value, ModelCallRecord)
        self.assertIsNone(restored.invocation_id)
        self.assertIsNone(restored.component)
        self.assertIsNone(restored.answer_version)
        projected = json.loads(json.dumps(asdict(restored)))
        for key in ('invocation_id', 'component', 'answer_version'):
            del projected[key]
        self.assertEqual(projected, value)
