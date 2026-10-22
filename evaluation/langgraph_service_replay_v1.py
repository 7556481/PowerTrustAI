"""Strictly local response replay; no provider construction or .env loading.

Uses the original run_fixed controller. Archive reads and new replay output stay
inside ignored data. Replay operations are not new model generations or scores.
"""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from evaluation import reviewer_baseline_trial_v1 as trial
from evaluation.batch_control import run_fixed
from evaluation.reviewer_graph_v1 import review_task
from evaluation.text_bound_review import canonical, sha, write
from model_adapter.contracts import ModelResponse, ModelSettings
from model_adapter.runtime import ModelBudget, ModelClient, model_scope


ARCHIVE = Path('data/retrieval_local/reviewer-baseline-v1/batch-v1')
OUTPUT = Path('data/evaluation_local/langgraph-adapter-v1/service-integration-replay-v1')


def normalized(value):
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()
                if k not in ('elapsed_seconds', 'duration_ms')}
    if isinstance(value, (list, tuple)):
        return [normalized(x) for x in value]
    return value


def current_runtime_replay_preflight(directory):
    # New read-only replay profile. Never replace the old live-batch preflight.
    # These two unrelated/default-runtime files evolved since the original batch;
    # bind BOTH identities explicitly, while original tasks/messages/parser remain exact.
    import inspect
    original=inspect.getsource(trial.preflight)
    old="if sha(Path(p).read_bytes())!=h:raise ValueError('Frozen file changed: '+p)"
    new="if sha(Path(p).read_bytes())!=h and p not in ('backend/config.py','model_adapter/runtime.py'):raise ValueError('Replay protocol/source changed: '+p)"
    if old not in original:raise ValueError('Original preflight shape changed')
    namespace=dict(vars(trial));exec(compile(original.replace(old,new),'<explicit-read-only-current-runtime-replay>', 'exec'),namespace)
    return namespace['preflight'](directory)


def read_archive():
    # Read-only original identity checks: never trial.run(), never touch attempt.
    freeze, tasks = current_runtime_replay_preflight(trial.DIRECTORY)
    audit = json.loads((trial.PUBLIC / 'actual-call-hashes-v1.json').read_text(encoding='utf-8'))['calls']
    expected_files = {x['response_file_sha256']: x for x in audit}
    responses = {}
    allowed = {
        'scope', 'schema_version', 'call_number', 'prompt_version', 'response_contract_version',
        'candidate_catalog_path', 'input_snapshot_path', 'request_metrics', 'correction',
        'model_id', 'finish_reason', 'response_text', 'response_sha256', 'validation_error',
        'request_messages_path',
    }
    for path in ARCHIVE.glob('response-*.json'):
        raw = path.read_bytes()
        expected = expected_files.get(sha(raw))
        if expected is None:
            raise ValueError('Unbound archived response')
        data = json.loads(raw)
        if set(data) != allowed or data['scope'] != 'PRIVATE_MODEL_RESPONSE_DIAGNOSTIC':
            raise ValueError('Unexpected response archive schema')
        if data['call_number'] != expected['call_number'] or data['call_number'] in responses:
            raise ValueError('Archived call identity')
        if sha(data['response_text'].encode()) != expected['response_sha256_utf8']:
            raise ValueError('Archived response text hash')
        if data['prompt_version'] != trial.v7.VERSION or data['response_contract_version'] != trial.v6.VERSION:
            raise ValueError('Archived prompt/contract identity')
        scope_path = Path(data['request_messages_path']).resolve()
        if (not scope_path.is_relative_to(ARCHIVE.resolve()) or
                not scope_path.name.startswith('scope-') or scope_path.suffix != '.json'):
            raise ValueError('Archived scope path outside allowlist')
        scope = json.loads(scope_path.read_text(encoding='utf-8'))
        if set(scope) != {'scope', 'prompt_version', 'correction', 'messages', 'scope_sha256'}:
            raise ValueError('Archived message scope schema')
        digest = sha(json.dumps({k: v for k, v in scope.items() if k != 'scope_sha256'},
                                ensure_ascii=False, sort_keys=True).encode())
        if digest != scope['scope_sha256'] or digest != expected['messages_scope_sha256']:
            raise ValueError('Archived pre-send scope hash')
        if sha(canonical(scope['messages']).encode()) != expected['messages_sha256_utf8']:
            raise ValueError('Archived messages hash')
        if scope['correction'] != data['correction'] or scope['prompt_version'] != trial.v7.VERSION:
            raise ValueError('Archived message metadata')
        responses[data['call_number']] = {**data, 'expected': expected}
    if set(responses) != set(range(1, 26)) or len(audit) != 25:
        raise ValueError('Exact original 25-response archive required')
    return freeze, tasks, [responses[n] for n in range(1, 26)]


class RecordedAdapter:
    """Return archived text only after exact request binding; never transport."""
    def __init__(self, responses):
        self.responses, self.position = responses, 0
        self.checked = []

    async def complete(self, request):
        if self.position >= len(self.responses):
            raise ValueError('Replay exhausted; no new request allowed')
        row = self.responses[self.position]
        messages = [{'role': m.role, 'content': m.content} for m in request.messages]
        expected = row['expected']
        digest = sha(canonical(messages).encode())
        if (digest != expected['messages_sha256_utf8'] or
                request.correction != row['correction'] or request.prompt_version != row['prompt_version']):
            raise ValueError('Replay request differs from original frozen messages')
        self.position += 1
        self.checked.append({'call_number': row['call_number'], 'sample_id': expected['sample_id'],
                             'messages_sha256_utf8': digest, 'response_sha256_utf8': row['response_sha256'],
                             'correction': request.correction})
        # Historical usage is not a new bill. Preserve archived text/model/finish.
        return ModelResponse(row['response_text'], row['model_id'], finish_reason=row['finish_reason'])


async def execute_graph(tasks, client, persist):
    begin = perf_counter()
    budget = ModelBudget(limit=48, deadline=begin + 4320)
    lookup = {t['sample_id']: t for t in tasks}

    async def submit(task):
        return {'sample_id': task['sample_id']}

    async def collect(accepted):
        task = lookup[accepted['sample_id']]
        started = perf_counter()
        try:
            value = await review_task(task, client)
            return {'sample_id': task['sample_id'], 'status': 'complete',
                    'prediction': value, 'elapsed_seconds': perf_counter() - started}
        except Exception as exc:
            return {'sample_id': task['sample_id'], 'status': 'failed',
                    'error_code': 'SERVICE_EXECUTION_FAILED',
                    'issue_code': getattr(exc, 'code', type(exc).__name__),
                    'elapsed_seconds': perf_counter() - started}

    with model_scope(budget):
        controls = await run_fixed([{'id': t['sample_id'], 'input': t} for t in tasks],
                                   submit=submit, collect=collect, persist=persist)
    return {'actual_calls': budget.used, 'records': [asdict(r) for r in budget.records],
            'controls': controls, 'elapsed_seconds': perf_counter() - begin}


async def replay(tasks, responses, variant):
    adapter = RecordedAdapter(responses)
    client = ModelClient(adapter, ModelSettings('deepseek-flash', 90, 2000, 24000))
    saved = {}

    def persist(sid, kind, value):
        saved.setdefault(sid, {})[kind] = value

    if variant == 'sequential':
        result = await trial.execute(tasks, client, None, persist)
    elif variant == 'langgraph_v1':
        result = await execute_graph(tasks, client, persist)
    else:
        raise ValueError('Unknown replay variant')
    if adapter.position != 25 or len(result['controls']) != 24:
        raise ValueError('Replay stopped before consuming the exact original batch')
    if (result['actual_calls'] != 25 or len(result['records']) != 25 or
            sum(r['correction'] for r in result['records']) != 1):
        raise ValueError('Replay request/correction count differs from original')
    return {'execution': result, 'saved': saved, 'checked_messages': adapter.checked}


def run(output=OUTPUT):
    output = Path(output).resolve()
    allowed_root = OUTPUT.parent.resolve()
    if not output.is_relative_to(allowed_root) or output == allowed_root:
        raise ValueError('Replay output must be a fresh child of ignored adapter data')
    if output.exists():
        raise FileExistsError('Replay output already exists; preserve it')
    freeze, tasks, responses = read_archive()
    attempt = trial.DIRECTORY / 'attempt.json'
    attempt_hash = sha(attempt.read_bytes())
    output.mkdir(parents=True)

    async def compare():
        values = []
        # Windows builds an internal loopback socketpair while creating the
        # event loop. Start the guard after loop creation, before any replay.
        with patch('socket.socket.connect', side_effect=AssertionError('Replay network prohibited')) as network:
            for variant in ('sequential', 'langgraph_v1'):
                value = await replay(tasks, responses, variant)
                write(output / (variant + '.json'), value)
                values.append(value)
            if normalized(values[0]) != normalized(values[1]):
                raise ValueError('Unexplained component replay difference')
        network.assert_not_called()
        return values

    values = asyncio.run(compare())
    item_hashes = []
    for task in tasks:
        sid = task['sample_id']
        prediction = values[1]['saved'][sid]['result']['prediction']
        original = json.loads((trial.DIRECTORY / (sid + '.result.json')).read_text(encoding='utf-8'))['prediction']
        if prediction != original:
            raise ValueError('Replay changed original prediction: ' + sid)
        item_hashes.append({'sample_id': sid, 'prediction_sha256_utf8': sha(canonical(prediction).encode()),
                            'coverage_slots': len(prediction['requirements']),
                            'judgments': sum(len(u['judgments']) for u in prediction['units'])})
    if sha(attempt.read_bytes()) != attempt_hash:
        raise ValueError('Original attempt marker changed')
    summary = {
        'kind': 'offline_recorded_response_replay_not_new_semantic_score',
        'items': 24, 'response_records_per_path': 25, 'corrections_per_path': 1,
        'coverage_slots': sum(x['coverage_slots'] for x in item_hashes),
        'reference_units_from_frozen_batch': 58,
        'judgments': sum(x['judgments'] for x in item_hashes),
        'exact_message_hash_checks_per_path': 25, 'all_predictions_equal_original': True,
        'all_business_outputs_records_and_controls_equal_between_paths': True,
        'real_model_calls': 0, 'network_calls': 0, 'old_attempt_sha256': attempt_hash,
        'original_frozen_files_checked': len(freeze['bound_file_hashes']),
        'current_runtime_replay_profile': 'explicit-2-file-source-evolution-v1-not-original-live-preflight',
        'source_evolution': [{'path':p,'historical_sha256':freeze['bound_file_hashes'][p],
                              'current_sha256':sha(Path(p).read_bytes())} for p in ('backend/config.py','model_adapter/runtime.py')],
        'raw_output_directory': str(output), 'prediction_identities': item_hashes,
        'elapsed_seconds': {name: value['execution']['elapsed_seconds']
                            for name, value in zip(('sequential', 'langgraph_v1'), values)},
        'limitations': ['25 adapter operations per path return saved text; no new generation',
                        'one sequential-then-graph pass; elapsed time is not a latency study',
                        'reference labels, alignment and semantic statistics were not re-adjudicated'],
    }
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = run(args.output)
    print(canonical({k: result[k] for k in ('kind', 'items', 'response_records_per_path',
                                           'coverage_slots', 'judgments', 'real_model_calls')}))
