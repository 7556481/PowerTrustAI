"""Once-only, explicitly authorized eight-item development batch; no new scheduler."""
import argparse
import asyncio
import json
from pathlib import Path

from evaluation import premise_bound_review_v5 as protocol
from evaluation.requirement_trial_v3 import execute
from evaluation.text_bound_review import sha, write
from evaluation.text_bound_review_v2 import build_units

IDS = ['H-MIT-001-A05', 'H-MIT-001-A06'] + ['H-SI-001-A0'+str(i) for i in range(1,7)]


def validate(tasks):
    assert [t['sample_id'] for t in tasks] == IDS
    for t in tasks:
        assert t['answer_units'] == build_units(t['sample_id'], t['answer'])
        assert set(t) == {'sample_id','question','requirements','scenario_premises',
                          'answer','answer_units','unit_version','evidence'}
        assert {r['requirement_id'] for r in t['requirements']} == (
            {'R1','R2'} if t['sample_id'].startswith('H-MIT') else {'R1','R2','R3'})
        protocol.basis_catalog(t)


def preflight(directory):
    plan=json.loads((directory/'plan.json').read_text(encoding='utf-8'))
    assert plan['protocol']==protocol.VERSION
    assert plan['prompt_sha256']==sha(protocol.PROMPT.encode())
    assert plan['sample_ids']==IDS and plan['derived_max_calls']==16
    for name,h in plan['file_sha256'].items(): assert sha((directory/name).read_bytes())==h
    for name,h in plan['working_tree_sha256'].items(): assert sha(Path(name).read_bytes())==h
    tasks=json.loads((directory/'input.json').read_text(encoding='utf-8'));validate(tasks)
    preview=[[{'role':m.role,'content':m.content} for m in protocol.messages(t)] for t in tasks]
    assert preview==json.loads((directory/'messages-preview.json').read_text(encoding='utf-8'))
    return plan,tasks


def run(directory):
    plan,tasks=preflight(directory)
    # Credentials are loaded only after the explicit --run invocation and once gate.
    with (directory/'attempt.json').open('x',encoding='utf-8') as f:
        json.dump({'automatic_resume':False},f)
    from backend.config import ServiceConfig
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    from model_adapter.runtime import ModelClient
    from services.response_diagnostics import ResponseDiagnostics, LOCAL_ROOT
    ServiceConfig.from_environment()
    settings=ModelSettings(plan['model'],plan['timeout_seconds'],plan['max_output_tokens'],
                           plan['max_response_chars'],plan['endpoint'],'DEEPSEEK_API_KEY')
    adapter=create_adapter(settings)
    def persist(sid,kind,value):
        assert sid in IDS
        write(directory/(sid+'.'+kind+'.json'),value)
    try:
        result=asyncio.run(execute(tasks,ModelClient(adapter,settings),
            ResponseDiagnostics(LOCAL_ROOT/'reviewer-remaining8-v5'/directory.name),
            persist,plan['batch_deadline_seconds'],protocol=protocol))
        write(directory/'execution.json',result)
    finally: adapter.close()
    print(json.dumps({'calls':result['actual_calls'],'attempted':len(result['controls']),
                      'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--run',action='store_true')
    a=p.parse_args()
    if a.run: run(a.directory)
    else: preflight(a.directory);print('Offline preflight passed; no model client constructed.')
