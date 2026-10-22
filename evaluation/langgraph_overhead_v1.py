"""Bounded local fake-agent timing; no provider, corpus download or semantic score."""
import argparse
import asyncio
import json
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch

from agents.fakes import FakeConfig, make_fake_harness
from core.models import TaskRequest, TaskMode, VerificationStatus
from evaluation.text_bound_review import write
from harness.contracts import RunBudget


OUTPUT = Path('data/evaluation_local/langgraph-adapter-v1/overhead-v1')


async def measure():
    request = TaskRequest('synthetic-timing', TaskMode.QUESTION_ANSWER,
                          'synthetic_fixture', 'Explain voltage stability')

    async def once(path, revision=False):
        statuses = ((VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED)
                    if revision else (VerificationStatus.SUPPORTED,))
        harness = make_fake_harness(FakeConfig(verification_statuses=statuses))
        harness.execution_path = path
        begin = perf_counter()
        result = await harness.run(request, RunBudget())
        elapsed = (perf_counter() - begin) * 1000
        if result.state.value != 'completed' or len(result.review_rounds) != (2 if revision else 1):
            raise AssertionError('Timing fixture changed behavior')
        return elapsed

    with patch('socket.socket.connect', side_effect=AssertionError('No benchmark network')) as network:
        # A fresh process gives a real first-selected-path import/compile cost.
        cold = {name: await once(name) for name in ('sequential', 'langgraph_v1')}
        for _ in range(3):
            for name in cold:
                await once(name)
        rows = []
        for revision in (False, True):
            for pair in range(30):
                order = ('sequential', 'langgraph_v1') if pair % 2 == 0 else ('langgraph_v1', 'sequential')
                for name in order:
                    rows.append({'case': 'one_revision' if revision else 'no_revision',
                                 'pair': pair, 'path': name, 'milliseconds': await once(name, revision)})
    network.assert_not_called()
    groups = []
    for case in ('no_revision', 'one_revision'):
        for name in ('sequential', 'langgraph_v1'):
            timings = sorted(r['milliseconds'] for r in rows if r['case'] == case and r['path'] == name)
            groups.append({'case': case, 'path': name, 'runs': len(timings),
                           'median_ms': median(timings), 'p95_ms': timings[ceil(.95 * len(timings)) - 1],
                           'minimum_ms': timings[0], 'maximum_ms': timings[-1]})
    return {'kind': 'local_fake_agent_overhead_not_model_latency', 'cold_first_call_ms': cold,
            'warmup_per_path': 3, 'warm_groups': groups, 'real_model_calls': 0,
            'network_calls': 0, 'observer': 'none for both paths',
            'limitations': ['single local process, correlated synthetic runs',
                            'cold graph includes imports/compile; warm graph reuses structure',
                            'does not estimate service latency, API cost or semantic quality'],
            'raw_timings': rows}


def run(output=OUTPUT):
    output = Path(output).resolve()
    if not output.is_relative_to(OUTPUT.parent.resolve()) or output == OUTPUT.parent.resolve():
        raise ValueError('Output must remain in ignored adapter data')
    output.mkdir(parents=True, exist_ok=False)
    result = asyncio.run(measure())
    write(output / 'timings.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'raw_timings'}, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)
