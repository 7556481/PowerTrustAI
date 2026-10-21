"""Single frozen EIA/NRC batch, using the existing bounded execution engine."""
import asyncio
import json
from pathlib import Path

from evaluation import premise_bound_review_v5 as protocol
from evaluation.requirement_trial_v3 import execute
from evaluation.text_bound_review import sha, write
from evaluation.text_bound_review_v2 import build_units

ORDER = [cid+'-A0'+str(i) for i in range(1,5)
         for cid in ('H-EIA-001','H-NRC-001')]


def validate(tasks):
    if [t['sample_id'] for t in tasks] != ORDER:
        raise ValueError('Exact interleaved frozen order required')
    for t in tasks:
        if set(t) != {'sample_id','question','requirements','scenario_premises',
                       'answer','answer_units','unit_version','evidence'}:
            raise ValueError('Only allowlisted task fields accepted')
        if t['answer_units'] != build_units(t['sample_id'],t['answer']):
            raise ValueError('Unchanged mechanical answer units required')
        if [r['requirement_id'] for r in t['requirements']] != ['R1','R2']:
            raise ValueError('Both requirements required')
        if any(set(r) != {'requirement_id','description'} for r in t['requirements']):
            raise ValueError('Reference metadata forbidden')
        protocol.basis_catalog(t)


def preflight(directory):
    f=json.loads((directory/'freeze.json').read_text(encoding='utf-8'))
    assert f['protocol']==protocol.VERSION and f['order']==ORDER
    assert f['maximum_calls']==16 and f['max_corrections']==1
    assert f['prompt_sha256']==sha(protocol.PROMPT.encode())
    for name,h in f['bound_file_hashes'].items(): assert sha(Path(name).read_bytes())==h
    for name,h in f['batch_file_hashes'].items(): assert sha((directory/name).read_bytes())==h
    tasks=json.loads((directory/'input.json').read_text(encoding='utf-8'));validate(tasks)
    preview=[[{'role':m.role,'content':m.content} for m in protocol.messages(t)] for t in tasks]
    assert preview==json.loads((directory/'messages-preview.json').read_text(encoding='utf-8'))
    return f,tasks


def run(directory):
    f,tasks=preflight(directory)
    with (directory/'attempt.json').open('x',encoding='utf-8') as handle:
        json.dump({'automatic_resume':False,'order':ORDER},handle)
    from backend.config import ServiceConfig
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    from model_adapter.runtime import ModelClient
    from services.response_diagnostics import ResponseDiagnostics, LOCAL_ROOT
    ServiceConfig.from_environment()
    s=f['model_settings'];settings=ModelSettings(s['model_id'],s['timeout_seconds'],
        s['max_output_tokens'],s['max_response_chars'],s['endpoint'],'DEEPSEEK_API_KEY')
    adapter=create_adapter(settings)
    def persist(sid,kind,value):
        assert sid in ORDER
        write(directory/(sid+'.'+kind+'.json'),value)
    try:
        result=asyncio.run(execute(tasks,ModelClient(adapter,settings),
            ResponseDiagnostics(LOCAL_ROOT/'eia-nrc-trial-v1'/directory.name),
            persist,f['budget_deadline_seconds'],protocol=protocol))
        write(directory/'execution.json',result)
    finally:adapter.close()
    print(json.dumps({'actual_calls':result['actual_calls'],'attempted':len(result['controls']),
                      'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--run',action='store_true')
    a=p.parse_args()
    if a.run:run(a.directory)
    else:preflight(a.directory);print('Frozen preflight passed, no API call.')
