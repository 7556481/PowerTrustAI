"""Synthetic component graph/replay safeguards, never real model access."""
from dataclasses import asdict
from copy import deepcopy
import importlib.util
import unittest

from evaluation import reviewer_baseline_trial_v1 as trial
from evaluation.text_bound_review import canonical, sha
from model_adapter.contracts import ModelConnectionError, ModelRequest, ModelResponse, ModelSettings
from model_adapter.runtime import ModelClient
from tests.test_format_stability_trial_v1 import prediction
from tests.test_text_bound_review import Adapter


@unittest.skipUnless(importlib.util.find_spec('langgraph'), 'Optional graph lock not installed')
class ReviewerGraphTests(unittest.IsolatedAsyncioTestCase):
    async def execute(self, items, path, persist=None):
        from evaluation.langgraph_replay_v1 import execute_graph
        adapter = Adapter(items)
        client = ModelClient(adapter, ModelSettings('synthetic_fixture'))
        if path == 'sequential':
            result = await trial.execute(trial.prepare_tasks(), client, None, persist or (lambda *args: None))
        else:
            result = await execute_graph(trial.prepare_tasks(), client, persist or (lambda *args: None))
        return result, [asdict(x) for x in adapter.requests]

    async def test_all24_same_results_messages_records_and_one_correction(self):
        from evaluation.langgraph_replay_v1 import normalized
        tasks = trial.prepare_tasks()
        items = [{}, prediction(tasks[0])] + [prediction(t) for t in tasks[1:]]
        saved = []
        for path in ('sequential', 'langgraph_v1'):
            rows = {}
            result, messages = await self.execute(items, path, lambda sid, k, v: rows.update({(sid, k): v}))
            self.assertEqual(result['actual_calls'], 25)
            self.assertEqual(len(result['controls']), 24)
            self.assertEqual(sum(r['correction'] for r in result['records']), 1)
            saved.append(normalized({'result': result, 'rows': rows, 'messages': messages}))
        self.assertEqual(saved[0], saved[1])

    async def test_final_invalid_output_stops_after_one_correction(self):
        for path in ('sequential', 'langgraph_v1'):
            result, messages = await self.execute([{}, {}], path)
            self.assertEqual(len(messages), 2)
            self.assertEqual(result['actual_calls'], 2)
            self.assertEqual(len(result['controls']), 1)
            self.assertTrue(result['controls'][0]['stop'])

    async def test_transport_failure_not_retried(self):
        result, messages = await self.execute([ModelConnectionError()], 'langgraph_v1')
        self.assertEqual(len(messages), 1)
        self.assertTrue(result['controls'][0]['stop'])

    async def test_failed_acceptance_persistence_means_zero_adapter_operations(self):
        def fail(*args):
            raise OSError('synthetic persistence failure')
        result, messages = await self.execute([], 'langgraph_v1', fail)
        self.assertEqual(messages, [])
        self.assertEqual(result['actual_calls'], 0)
        self.assertTrue(result['controls'][0]['stop'])

    async def test_all24_corrections_share_one_48_operation_budget(self):
        items = [item for task in trial.prepare_tasks() for item in ({}, prediction(task))]
        result, messages = await self.execute(items, 'langgraph_v1')
        self.assertEqual(len(messages), 48)
        self.assertEqual(result['actual_calls'], 48)
        self.assertEqual(len(result['controls']), 24)
        self.assertEqual([r['call_number'] for r in result['records']], list(range(1, 49)))

    async def test_recorded_adapter_rejects_message_changes_without_consuming_response(self):
        from evaluation.langgraph_replay_v1 import RecordedAdapter
        task = trial.prepare_tasks()[0]
        messages = trial.v7.messages(task)
        expected = {'call_number': 1, 'sample_id': task['sample_id'],
                    'messages_sha256_utf8': sha(canonical([asdict(m) for m in messages]).encode())}
        row = {'expected': expected, 'correction': False, 'prompt_version': trial.v7.VERSION,
               'call_number': 1, 'response_sha256': sha(b'{}'), 'response_text': '{}',
               'model_id': 'synthetic_fixture', 'finish_reason': 'stop'}
        adapter = RecordedAdapter([row])
        request = ModelRequest('synthetic_fixture', messages[:-1], 2000, trial.v7.VERSION)
        with self.assertRaisesRegex(ValueError, 'differs'):
            await adapter.complete(request)
        self.assertEqual(adapter.position, 0)
        request = ModelRequest('synthetic_fixture', messages, 2000, trial.v7.VERSION)
        response = await adapter.complete(request)
        self.assertIsInstance(response, ModelResponse)
        self.assertEqual(adapter.position, 1)
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            await adapter.complete(request)

    async def test_task_whitelist_rejects_reference_leak_before_adapter(self):
        from evaluation.reviewer_graph_v1 import review_task
        task = deepcopy(trial.prepare_tasks()[0])
        task['expected_label'] = 'DO_NOT_SEND'
        adapter = Adapter([])
        with self.assertRaisesRegex(ValueError, 'whitelist'):
            await review_task(task, ModelClient(adapter, ModelSettings('synthetic_fixture')))
        self.assertFalse(adapter.requests)
