"""One explicitly authorized development recheck; no automatic resume."""
import asyncio
import copy
import json
from pathlib import Path

from evaluation import premise_bound_review_v6 as protocol
from evaluation.eia_nrc_trial_v1 import preflight as original_preflight, validate
from evaluation.requirement_trial_v3 import execute
from evaluation.text_bound_review import canonical, sha, write

PLAN = Path('docs/reviewer-v6-development-recheck-plan-v1.json')
ORIGINAL = Path('data/evaluation_local/holdout-source-selection-v2/batch-eia-nrc-v1')


def prepare_tasks(original, plan):
    tasks = copy.deepcopy(original)
    validate(tasks)  # Exact original whitelist and order, before the role extension.
    if len(tasks) != len(plan['items']):
        raise ValueError('Exact planned item count required')
    for task, item in zip(tasks, plan['items']):
        if task['sample_id'] != item['sample_id']:
            raise ValueError('Fixed order required')
        if sha(canonical(task).encode()) != item['original_task_sha256_utf8']:
            raise ValueError('Original task changed')
        for evidence in task['evidence']:
            evidence['source_role'] = 'literature'
        if sha(canonical(task).encode()) != item['candidate_task_sha256_utf8']:
            raise ValueError('Candidate task changed')
        messages = [{'role':m.role, 'content':m.content} for m in protocol.messages(task)]
        if sha(canonical(messages).encode()) != item['candidate_messages_sha256_utf8']:
            raise ValueError('Messages changed')
    return tasks


def preflight(directory):
    frozen = json.loads((directory/'freeze.json').read_text(encoding='utf-8'))
    for name, digest in frozen['bound_file_hashes'].items():
        if sha(Path(name).read_bytes()) != digest:
            raise ValueError('Frozen file changed: '+name)
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    if plan['protocol'] != protocol.VERSION or sha(protocol.PROMPT.encode()) != plan['prompt_sha256_utf8']:
        raise ValueError('Protocol changed')
    if not frozen['owner_authorized'] or plan['execution']['maximum_calls'] != 16:
        raise ValueError('Authorization/plan mismatch')
    _, original = original_preflight(ORIGINAL)
    return frozen, plan, prepare_tasks(original, plan)


def run(directory):
    frozen, plan, tasks = preflight(directory)
    # Exclusive attempt marker is written before loading credentials or connecting.
    with (directory/'attempt.json').open('x', encoding='utf-8') as handle:
        json.dump({'automatic_resume':False, 'order':plan['order']}, handle)
    from backend.config import ServiceConfig
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    from model_adapter.runtime import ModelClient
    from services.response_diagnostics import ResponseDiagnostics, LOCAL_ROOT
    ServiceConfig.from_environment()
    s = plan['model_settings']
    settings = ModelSettings(s['model_id'], s['timeout_seconds'], s['max_output_tokens'],
                             s['max_response_chars'], s['endpoint'], 'DEEPSEEK_API_KEY')
    adapter = create_adapter(settings)
    def persist(sid, kind, value):
        if sid not in plan['order']:
            raise ValueError('Unplanned sample')
        write(directory/(sid+'.'+kind+'.json'), value)
    try:
        result = asyncio.run(execute(tasks, ModelClient(adapter, settings),
            ResponseDiagnostics(LOCAL_ROOT/'v6-development-trial-v1'/directory.name),
            persist, plan['execution']['budget_deadline_seconds'], protocol=protocol))
        write(directory/'execution.json', result)
    finally:
        adapter.close()
    print(canonical({'actual_calls':result['actual_calls'], 'attempted':len(result['controls']),
                     'elapsed_seconds':result['elapsed_seconds']}))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.run:
        run(args.directory)
    else:
        preflight(args.directory)
        print('Preflight passed; no API.')
