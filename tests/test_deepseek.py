"""Mock transport only. These tests never read API credentials or call a paid API."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.validation import InputError
from harness.deepseek_trial import run_trial, fee_summary
from model_adapter.contracts import *
from model_adapter.deepseek import DeepSeekAdapter, create_adapter, parse_response, estimate_cost
from model_adapter.runtime import ModelClient, ModelBudget
from rag.storage import KnowledgeStore, SourceMetadata


def envelope(text='{"ok":true}', usage=True):
    data = {"model": "returned-model-identifier", "choices": [{"message": {"content": text}, "finish_reason": "stop"}]}
    if usage:
        data["usage"] = {"prompt_tokens": 30, "completion_tokens": 8, "total_tokens": 38,
                         "prompt_cache_hit_tokens": 10, "prompt_cache_miss_tokens": 20}
    return json.dumps(data).encode()


class DeepSeekTests(unittest.IsolatedAsyncioTestCase):
    def settings(self, **kwargs):
        return ModelSettings("deepseek-flash", **kwargs)

    def request(self):
        return ModelRequest("configured-model-id", (ModelMessage("system", "Return JSON."),), 48, "synthetic_fixture")

    async def test_payload_configurable_model_json_thinking_disabled_single_call(self):
        requests = []
        def exchange(body, timeout, limit):
            requests.append(json.loads(body))
            return 200, envelope()
        adapter = DeepSeekAdapter(self.settings(), exchange=exchange)
        self.addCleanup(adapter.close)
        result = await adapter.complete(self.request())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["model"], "configured-model-id")
        self.assertEqual(requests[0]["response_format"], {"type": "json_object"})
        self.assertEqual(requests[0]["thinking"], {"type": "disabled"})
        self.assertFalse(requests[0]["stream"])
        self.assertEqual(requests[0]["max_tokens"], 48)
        self.assertNotIn("Authorization", requests[0])
        self.assertEqual(result.model_id, "returned-model-identifier")
        self.assertEqual(result.usage.cache_hit_tokens, 10)

    async def test_http_failure_mapping_no_retry_or_server_body_leak(self):
        failures = {400: ModelRequestError, 401: ModelAuthenticationError, 402: ModelBalanceError,
                    403: ModelAuthenticationError, 422: ModelRequestError, 429: ModelRateLimitError,
                    500: ModelServiceError, 503: ModelServiceError, 302: ModelRequestError}
        for status, error in failures.items():
            calls = []
            def exchange(*args):
                calls.append(1)
                return status, b"private server diagnostic not to log"
            adapter = DeepSeekAdapter(self.settings(), exchange=exchange)
            try:
                budget = ModelBudget(limit=2)
                with self.assertRaises(error) as caught:
                    await ModelClient(adapter, self.settings()).complete(self.request().messages, "synthetic", budget)
                self.assertEqual(len(calls), 1)
                self.assertEqual(len(budget.records), 1)
                self.assertEqual(budget.records[0].error_code, error.code)
                self.assertNotIn("private server diagnostic", str(caught.exception))
            finally:
                adapter.close()

    async def test_unknown_usage_and_empty_content_preserved(self):
        result = parse_response(200, envelope("", usage=False), "deepseek-flash")
        self.assertEqual(result.text, "")
        self.assertIsNone(result.usage)
        self.assertEqual(result.cost_estimate.status, "unavailable")
        self.assertIsNone(result.cost_estimate.usd_lower)

    async def test_malformed_envelope_and_usage_rejected(self):
        for raw in (b"not JSON", b"{}", b'{"choices":[]}',
                    b'{"choices":[{"message":{"content":3}}]}',
                    b'{"choices":[{"message":{"content":"ok"}}],"usage":{"prompt_tokens":-1}}'):
            with self.assertRaises(ModelOutputError):
                parse_response(200, raw, "deepseek-flash")

    async def test_price_snapshot_ranges_no_fabricated_service_cost(self):
        usage = ModelUsage(1000, 2000, 3000, cache_hit_tokens=200, cache_miss_tokens=800)
        estimate = estimate_cost("deepseek-flash", usage)
        peak = (200 * 0.006 + 800 * 0.30 + 2000 * 1.20) / 1_000_000
        self.assertAlmostEqual(estimate.usd_upper, peak)
        self.assertAlmostEqual(estimate.usd_lower, peak / 2)
        self.assertEqual(estimate.price_date, "2026-10-02")
        self.assertIsNone(usage.cost_amount)
        for unknown in (None, ModelUsage(1000, 2000, 3000), ModelUsage(1000, 2000, 3000, cache_hit_tokens=1, cache_miss_tokens=1)):
            self.assertEqual(estimate_cost("deepseek-flash", unknown).status, "unavailable")
        self.assertEqual(estimate_cost("unpriced-model", usage).status, "unavailable")
        summary = fee_summary([{"cost_estimate": asdict(estimate)}, {"cost_estimate": None}])
        self.assertFalse(summary["complete_estimate"])
        self.assertEqual(summary["known_estimate_requests"], 1)

    async def test_cost_cache_usage_reaches_call_record(self):
        adapter = DeepSeekAdapter(self.settings(), exchange=lambda *args: (200, envelope()))
        self.addCleanup(adapter.close)
        budget = ModelBudget(limit=1)
        await ModelClient(adapter, self.settings()).complete(self.request().messages, "synthetic", budget)
        self.assertEqual(budget.records[0].usage.cache_miss_tokens, 20)
        self.assertEqual(budget.records[0].cost_estimate.status, "off_peak_to_peak_range")
        self.assertEqual(budget.records[0].finish_reason, "stop")

    async def test_endpoint_restriction_and_missing_key_no_network(self):
        for url in ("http://api.deepseek.com", "https://third-party.invalid", "https://api.deepseek.com?private=1",
                    "https://api.deepseek.com/other"):
            with patch("model_adapter.deepseek.credential_from_environment") as reader:
                with self.assertRaises(InputError):
                    create_adapter(self.settings(endpoint=url))
                reader.assert_not_called()
        with patch("model_adapter.deepseek.credential_from_environment", side_effect=InputError("missing")):
            with self.assertRaises(InputError):
                create_adapter(self.settings())

    async def test_timeout_worker_keeps_running_no_extra_post(self):
        finished = threading.Event()
        calls = []
        def slow(*args):
            calls.append(1)
            time.sleep(0.15)
            finished.set()
            return 200, envelope()
        adapter = DeepSeekAdapter(self.settings(), exchange=slow)
        self.addCleanup(adapter.close)
        with self.assertRaises(ModelTimeoutError):
            await ModelClient(adapter, self.settings(timeout_seconds=0.02)).complete(
                self.request().messages, "synthetic", ModelBudget())
        self.assertFalse(finished.is_set())
        with self.assertRaises(ModelConnectionError):
            await adapter.complete(self.request())
        self.assertEqual(len(calls), 1)
        await asyncio.to_thread(finished.wait, 1)

    async def test_transport_connection_and_socket_timeout_mapping(self):
        for error, expected in ((OSError("private diagnostic"), ModelConnectionError), (TimeoutError(), ModelTimeoutError)):
            def exchange(*args):
                raise error
            adapter = DeepSeekAdapter(self.settings(), exchange=exchange)
            try:
                with self.assertRaises(expected):
                    await adapter.complete(self.request())
            finally:
                adapter.close()

    async def test_connection_failure_stops_five_questions(self):
        calls = []
        def exchange(*args):
            calls.append(1)
            return 402, b"not logged"
        adapter = DeepSeekAdapter(self.settings(), exchange=exchange)
        self.addCleanup(adapter.close)
        args = SimpleNamespace(connection_only=False, knowledge_version="synthetic", draft_max_tokens=1800)
        result = await run_trial(args, adapter, self.settings(max_output_tokens=48))
        self.assertEqual(len(calls), 1)
        self.assertFalse(result["runs"])
        self.assertEqual(result["connection"]["code"], "MODEL_INSUFFICIENT_BALANCE")

    async def test_bounded_ping_then_five_with_at_most_one_correction_and_generated_only(self):
        # Real orchestration and SQLite, but synthetic text and a scripted HTTP exchange.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            md = path / "synthetic_fixture.md"
            md.write_text("# synthetic_fixture\n\nVoltage stability reactive reserve QV generator capability constraints.\n", encoding="utf-8")
            db = path / "knowledge.sqlite3"
            with KnowledgeStore(db) as store:
                kv = store.ingest(md, "synthetic", SourceMetadata(source_type="synthetic_fixture")).knowledge_version
            calls, initial = [], set()
            def exchange(body, *args):
                payload = json.loads(body)
                calls.append(payload)
                if len(payload["messages"]) == 2:
                    return 200, envelope()
                question = json.loads(payload["messages"][1]["content"])
                key = question["answer_id"]
                if key not in initial:
                    initial.add(key)
                    return 200, envelope("invalid json")
                docs = json.loads(payload["messages"][2]["content"])
                text = "synthetic_fixture answer"
                answer = {"answer_id": key, "version": 1, "text": text, "citations": [
                    {"start_offset": 0, "end_offset": len(text), "evidence_ids": [docs["evidence"][0]["evidence_id"]]}],
                    "assumptions": [], "missing_information": [], "evidence_sufficient": True}
                return 200, envelope(json.dumps(answer))
            adapter = DeepSeekAdapter(self.settings(), exchange=exchange)
            try:
                args = SimpleNamespace(db=str(db), knowledge_version=kv, connection_only=False,
                    draft_max_tokens=1800, official_five=True, question=None, simulate_fixture=False,
                    max_calls=2, duration=20, step_timeout=10, requirement=[])
                result = await run_trial(args, adapter, self.settings(max_output_tokens=48))
                self.assertEqual(len(calls), 11)
                self.assertEqual(result["initial_generations"], 5)
                self.assertEqual(result["format_corrections"], 5)
                self.assertTrue(result["real_generation_completed"])
                self.assertTrue(all(r["result"]["state"] == "generated" and r["result"]["report"] is None for r in result["runs"]))
                self.assertTrue(all(r["citation_map"] for r in result["runs"]))
            finally:
                adapter.close()
