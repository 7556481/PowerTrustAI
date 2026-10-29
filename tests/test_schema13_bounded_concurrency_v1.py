"""Fixed schema13 inputs/responses; actual official-adapter worker threads, no HTTP."""
import asyncio
from collections import Counter
from dataclasses import asdict, replace
import json
import threading
import time
import unittest

from agents.evidence_verification import ModelEvidenceVerificationAgent
from backend.assembly import Bundle
from backend.config import ServiceConfig
from model_adapter.bounded_pair_v1 import BoundedPairAdapter, create_pair
from model_adapter.contracts import ModelMessage, ModelRequest, ModelSettings
from model_adapter.deepseek import DeepSeekAdapter
from model_adapter.runtime import ModelBudget, model_scope
from services.bounded_repair import eligible_repairs
from services.review_transport import expand
from tests.test_audit_interface_v2 import warrant
from tests.test_citation_workload import multi
from tests.test_fact_rereview_v3 import response


SETTINGS = ModelSettings('deepseek-flash', timeout_seconds=3,
                         max_output_tokens=8000, max_response_chars=96000)


class FixedExchange:
    """Counts work *inside* blocking transport, beyond asyncio scheduling."""
    def __init__(self, invalid=(), persistent=False, failures=None, delays=None):
        self.invalid = set(invalid)
        self.persistent = persistent
        self.failures = failures or {}
        self.delays = delays or {}
        self.lock = threading.Lock()
        self.active = Counter()
        self.maximum = Counter()
        self.seen = []
        self.finished = []

    def __call__(self, body, timeout, byte_limit):
        wire = json.loads(body)
        data = json.loads(wire['messages'][1]['content'])
        if 'TRANSPORT_VERSION' in data:
            data = expand(data)
        scopes = data.get('ORIGINAL_CITATION_SCOPES')
        key = scopes[0]['citation_index'] if scopes else 'fact'
        lane = 'domain' if data.get('fixture_domain') else 'fact'
        if lane == 'domain':
            key = 'domain'
        correction = len(wire['messages']) > 2
        with self.lock:
            self.seen.append((key, correction, wire))
            self.active[lane] += 1
            self.active['total'] += 1
            for name, count in self.active.items():
                self.maximum[name] = max(self.maximum[name], count)
        try:
            time.sleep(self.delays.get(key, .008))
            status = self.failures.get(key, 200)
            if key == 'domain':
                value = {}
            elif scopes:
                self_scope = scopes[0]
                quote = self_scope['QUOTE_CANDIDATES'][0]['quote_id']
                value = {'citation_reviews': [dict(citation_index=key, status='supported',
                    rationale='Fixed whole-substring comparison.', applicability_conditions=[],
                    bases=[{'type': 'text_excerpt', 'quote_id': quote}],
                    support_relation=warrant(data, [quote]))]}
            else:
                value = response(data)
                for finding in value['findings']:
                    for row in finding['component_reviews']:
                        row['support_relation'] = warrant(data, [finding['bases'][0]['quote_id']])
            if key in self.invalid and (not correction or self.persistent):
                value['citation_reviews' if scopes else 'findings'][0]['bases'][0]['quote_id'] = 'ILLEGAL'
            envelope = {'model': 'deepseek-flash', 'choices': [
                {'message': {'content': json.dumps(value)}, 'finish_reason': 'stop'}]}
            return status, json.dumps(envelope).encode()
        finally:
            with self.lock:
                self.active[lane] -= 1
                self.active['total'] -= 1
                self.finished.append((key, correction))


async def execute(profile, *, n=4, limit=20, invalid=(), persistent=False,
                  failures=None, delays=None, domain=False, message_profile='lossless_v1',
                  version=2, settings=SETTINGS):
    exchange = FixedExchange(invalid, persistent, failures, delays)
    children = [DeepSeekAdapter(settings, exchange=exchange)]
    if profile == 'citation_pair_v1':
        children.append(DeepSeekAdapter(settings, exchange=exchange))
    adapter = BoundedPairAdapter(*children) if len(children) == 2 else children[0]
    domain_adapter = DeepSeekAdapter(settings, exchange=exchange)
    bundle = Bundle(None, (adapter, domain_adapter))
    inp = multi(n, version)
    budget = ModelBudget(limit)
    agent = ModelEvidenceVerificationAgent(adapter, settings, schema_version=13,
        support_relation_checks=True, support_relation_version=6,
        review_message_profile=message_profile,
        correction_accounting='invocation_scoped_v1', review_execution_profile=profile)
    started = time.perf_counter()
    try:
        with model_scope(budget):
            if domain:
                from model_adapter.runtime import ModelClient
                message = (ModelMessage('system', 'Return JSON.'),
                           ModelMessage('user', '{"fixture_domain":true}'))
                out, _ = await asyncio.gather(agent.run(inp),
                    ModelClient(domain_adapter, settings).complete(message, 'fixture-domain', budget))
            else:
                out = await agent.run(inp)
        return out, budget, exchange, time.perf_counter() - started, inp
    finally:
        await bundle.drain()
        bundle.close()


def projection(out):
    value = asdict(out)
    value.pop('model_records')
    return value


def requests(exchange):
    return {(key, correction): wire for key, correction, wire in exchange.seen}


class Schema13BoundedTests(unittest.IsolatedAsyncioTestCase):
    async def compare(self, **kwargs):
        old = await execute('serial_v1', **kwargs)
        new = await execute('citation_pair_v1', **kwargs)
        self.assertEqual(projection(old[0]), projection(new[0]))
        self.assertEqual(requests(old[2]), requests(new[2]))
        self.assertEqual(old[1].used, new[1].used)
        self.assertEqual(old[4].answer, new[4].answer)
        self.assertEqual([eligible_repairs(f) for f in old[0].findings + old[0].citation_reviews],
                         [eligible_repairs(f) for f in new[0].findings + new[0].citation_reviews])
        return old, new

    async def test_full_contract_and_messages_match_both_carriers(self):
        for carrier in ('baseline_v1', 'lossless_v1'):
            old, new = await self.compare(message_profile=carrier,
                                          delays={k: .25 for k in range(4)})
            self.assertFalse(new[0].execution_issues)
            self.assertEqual(new[2].maximum['fact'], 2)
            self.assertEqual(old[2].maximum['fact'], 1)
            self.assertEqual(len(new[0].citation_reviews), 4)
            self.assertTrue(all(c.status.value == 'supported' for c in new[0].citation_reviews))
            self.assertEqual(new[2].seen[0][0], 'fact')
            self.assertEqual(new[2].finished[0][0], 'fact')

    async def test_single_and_no_citations(self):
        for n in (0, 1):
            _, new = await self.compare(n=n)
            self.assertEqual(new[2].maximum['fact'], 1)

    async def test_one_invalid_correction_and_two_invalid_reverse_completion(self):
        for invalid in (('fact',), (0,), (0, 1)):
            _, new = await self.compare(invalid=invalid, delays={0: .35, 1: .002})
            corrections = [key for key, correction, _ in new[2].seen if correction]
            self.assertEqual(corrections, [invalid[0]])
            self.assertEqual(sum(r.correction for r in new[1].records), 1)
            if len(invalid) == 2:
                self.assertLess(new[2].finished.index((1, False)), new[2].finished.index((0, False)))
                self.assertTrue(new[0].execution_issues)
                self.assertEqual(new[0].citation_reviews[1].status.value, 'not_assessable')
                self.assertEqual(new[0].citation_reviews[2].status.value, 'supported')

    async def test_failed_correction_retains_valid_peers(self):
        _, new = await self.compare(invalid=(0, 1), persistent=True)
        self.assertTrue(new[0].execution_issues)
        self.assertEqual(new[0].findings[0].status.value, 'supported')
        self.assertEqual(new[0].citation_reviews[3].status.value, 'supported')

    async def test_budget_shortfall_preserves_serial_priority(self):
        for limit in (0, 1, 2, 3, 5):
            for invalid in ((), (0, 1)):
                _, new = await self.compare(limit=limit, invalid=invalid)
                self.assertLessEqual(new[1].used, limit)

    async def test_fatal_stops_future_waves_and_keeps_inflight_peer(self):
        for status in (401, 503, 429):
            result, budget, exchange, _, _ = await execute('citation_pair_v1',
                failures={0: status}, delays={0: .003, 1: .025})
            self.assertIsNotNone(budget.fatal_error)
            self.assertEqual([key for key, _, _ in exchange.seen], ['fact', 0, 1])
            self.assertEqual(result.citation_reviews[1].status.value, 'supported')
            self.assertEqual(result.citation_reviews[2].status.value, 'not_assessable')
            self.assertTrue(result.execution_issues)
            self.assertFalse(any(r.correction for r in budget.records))

    async def test_rereview_uses_new_version_scopes_and_fresh_correction(self):
        old = await execute('citation_pair_v1', version=2, invalid=(0,))
        new = await execute('citation_pair_v1', version=3, invalid=(0,))
        self.assertEqual(sum(r.correction for r in new[1].records), 1)
        self.assertNotEqual(requests(old[2])[0, False], requests(new[2])[0, False])
        self.assertEqual(new[0].answer_version, 3)

    async def test_domain_correction_does_not_consume_fact_correction(self):
        from model_adapter.runtime import ModelClient
        exchange = FixedExchange(invalid=(0,), delays={0: .15})
        pair = BoundedPairAdapter(*(DeepSeekAdapter(SETTINGS, exchange=exchange) for _ in range(2)))
        domain = DeepSeekAdapter(SETTINGS, exchange=exchange)
        bundle = Bundle(None, (pair, domain))
        budget = ModelBudget(20)
        agent = ModelEvidenceVerificationAgent(pair, SETTINGS, schema_version=13,
            support_relation_checks=True, support_relation_version=6,
            review_execution_profile='citation_pair_v1')
        async def corrected_domain():
            await asyncio.sleep(.01)
            messages = (ModelMessage('system', 'Return JSON.'),
                        ModelMessage('user', '{"fixture_domain":true}'),
                        ModelMessage('user', '{"fixture_format_correction":true}'))
            return await ModelClient(domain, SETTINGS).complete(messages, 'fixture-domain', budget, True)
        try:
            with model_scope(budget):
                result, _ = await asyncio.gather(agent.run(multi(2)), corrected_domain())
            self.assertFalse(result.execution_issues)
            self.assertEqual([key for key, correction, _ in exchange.seen if correction], ['domain', 0])
            self.assertEqual(sum(r.correction for r in result.model_records), 1)
        finally:
            await bundle.drain()
            bundle.close()

    async def test_expired_total_deadline_sends_no_http(self):
        exchange = FixedExchange()
        pair = BoundedPairAdapter(*(DeepSeekAdapter(SETTINGS, exchange=exchange) for _ in range(2)))
        budget = ModelBudget(20, deadline=time.perf_counter() - 1)
        try:
            with model_scope(budget):
                out = await ModelEvidenceVerificationAgent(pair, SETTINGS, schema_version=13,
                    support_relation_checks=True, support_relation_version=6,
                    review_execution_profile='citation_pair_v1').run(multi(2))
            self.assertEqual(exchange.seen, [])
            self.assertEqual(budget.used, 0)
            self.assertTrue(out.execution_issues)
        finally:
            pair.close()

    async def test_physical_fact_two_domain_one_and_critical_path(self):
        delays = {'fact': .05, 0: .40, 1: .40, 2: .40, 3: .40, 'domain': .80}
        old, new = await self.compare(domain=True, delays=delays)
        self.assertEqual(new[2].maximum, Counter(fact=2, domain=1, total=3))
        self.assertEqual(old[2].maximum['total'], 2)
        # Scheduling proof is overlap/counts, not a machine-dependent speed threshold.
        self.assertEqual(old[1].used, 6)
        self.assertEqual(new[1].used, 6)

    async def test_timeout_and_cancel_keep_physical_leases_until_drain(self):
        for cancel in (False, True):
            lock = threading.Lock()
            active = 0
            maximum = 0
            started = threading.Event()
            release = threading.Event()
            def held(body, timeout, byte_limit):
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                    if active == 2:
                        started.set()
                try:
                    release.wait(2)
                    return 200, b'{"choices":[{"message":{"content":"{}"},"finish_reason":"stop"}]}'
                finally:
                    with lock:
                        active -= 1
            adapter = BoundedPairAdapter(*(DeepSeekAdapter(SETTINGS, exchange=held) for _ in range(2)))
            bundle = Bundle(None, (adapter,))
            request = ModelRequest('deepseek-flash', (ModelMessage('user', 'Return JSON.'),), 8000, 'fixture')
            try:
                tasks = [asyncio.create_task(adapter.complete(request)) for _ in range(2)]
                while not started.is_set():
                    await asyncio.sleep(.002)
                if cancel:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    for task in tasks:
                        with self.assertRaises(TimeoutError):
                            await asyncio.wait_for(task, .01)
                third = asyncio.create_task(adapter.complete(request))
                drain = asyncio.create_task(bundle.drain())
                await asyncio.sleep(.01)
                self.assertFalse(third.done())
                self.assertFalse(drain.done())
                self.assertEqual(maximum, 2)
                release.set()
                await third
                await drain
                self.assertEqual(active, 0)
                self.assertEqual(maximum, 2)
            finally:
                release.set()
                await bundle.drain()
                bundle.close()
            self.assertTrue(all(child._closed for child in adapter.children))

    async def test_agent_cancellation_records_and_releases_all_workers(self):
        exchange = FixedExchange(delays={0: .15, 1: .15})
        pair = BoundedPairAdapter(*(DeepSeekAdapter(SETTINGS, exchange=exchange) for _ in range(2)))
        bundle = Bundle(None, (pair,))
        budget = ModelBudget(20)
        agent = ModelEvidenceVerificationAgent(pair, SETTINGS, schema_version=13,
            support_relation_checks=True, support_relation_version=6,
            review_execution_profile='citation_pair_v1')
        try:
            with model_scope(budget):
                task = asyncio.create_task(agent.run(multi()))
                while exchange.maximum['fact'] < 2:
                    await asyncio.sleep(.002)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            await bundle.drain()
            self.assertEqual(exchange.active['total'], 0)
            self.assertEqual(len(exchange.seen), 3)
            self.assertEqual(sum(r.error_code == 'MODEL_CANCELLED' for r in budget.records), 2)
        finally:
            await bundle.drain()
            bundle.close()

    async def test_timeout_retains_independent_and_valid_sibling(self):
        settings = replace(SETTINGS, timeout_seconds=1)
        out, budget, exchange, _, _ = await execute('citation_pair_v1',
            settings=settings, n=2, delays={0: 1.5, 1: .002})
        self.assertEqual(out.findings[0].status.value, 'supported')
        self.assertEqual(out.citation_reviews[1].status.value, 'supported')
        self.assertIn('MODEL_TIMEOUT', [issue.code for issue in out.execution_issues])
        self.assertEqual(exchange.maximum['fact'], 2)
        self.assertEqual(exchange.active['total'], 0)

    def test_default_and_invalid_combinations_and_partial_construction_cleanup(self):
        self.assertEqual(ServiceConfig().fact_review_execution, 'serial_v1')
        ServiceConfig(fact_review_execution='citation_pair_v1')
        for kwargs in ({'verification_schema': 14}, {'profile': 'synthetic_fixture'},
                       {'fact_internal_flow': 'joint_v2'}, {'fact_review_contract': 'scope_v2'}):
            with self.assertRaises(ValueError):
                ServiceConfig(fact_review_execution='citation_pair_v1', **kwargs)
        class Child:
            closed = False
            def close(self):
                self.closed = True
        child = Child()
        count = 0
        def create(settings):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError('synthetic construction failure')
            return child
        with self.assertRaises(RuntimeError):
            create_pair(SETTINGS, create)
        self.assertTrue(child.closed)


class FactoryPersistenceTests(unittest.TestCase):
    def test_actual_factory_final_body_coverage_repair_and_partial_store(self):
        from tests import test_schema14_factory_flow as flow
        fixture = flow.FactoryFlowTests()
        for kwargs in ({'existing': True, 'two': True}, {'subject': True}, {'illegal': True}):
            old, _, _ = fixture.exercise(schema=13, **kwargs)
            new, provider, _ = fixture.exercise(schema=13, fact_execution='citation_pair_v1', **kwargs)
            self.assertEqual(old['answer']['final']['text'], new['answer']['final']['text'])
            self.assertEqual([v['text'] for v in old['answer']['versions']],
                             [v['text'] for v in new['answer']['versions']])
            self.assertEqual(old['decision']['kind'], new['decision']['kind'])
            self.assertEqual(old['execution']['required_stages_complete'],
                             new['execution']['required_stages_complete'])
            self.assertEqual(len(old['review_rounds']), len(new['review_rounds']))
            self.assertEqual(len(old['findings']['original_citations']),
                             len(new['findings']['original_citations']))
            self.assertEqual(new['configuration']['fact_review_execution']['fact_http_limit'], 2)
            if kwargs.get('subject'):
                self.assertEqual(len(new['review_rounds']), 2)
                self.assertEqual(new['answer']['final']['text'], flow.GOOD_FREQUENCY)
