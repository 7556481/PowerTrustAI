"""Authorized paired trial using existing batch controller and structured client."""
import asyncio
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from evaluation import premise_bound_review_v6 as v6, premise_bound_review_v7 as v7
from evaluation.batch_control import run_fixed
from evaluation.format_stability_inputs_v1 import prepare
from evaluation.text_bound_review import sha, write
from model_adapter.runtime import ModelBudget, model_scope, model_invocation_scope
from services.structured_model import structured_request

BASE = Path('docs/evaluation/format-stability-v1')
ARMS = {'v6':v6, 'v7':v7}


def fields_complete(value, task):
    """Presence/expected-ID metric only, never a replacement acceptance parser."""
    errors = []
    def fields(obj, keys, path):
        if not isinstance(obj, dict):
            errors.append(path+':object_required'); return False
        errors.extend(path+'.'+k for k in sorted(keys-set(obj)))
        return True
    if not fields(value, {'sample_id','requirements','units','rationale'}, '$'):
        return {'complete':False,'errors':errors}
    for key, ident, expected, required in [
        ('requirements','requirement_id',[r['requirement_id'] for r in task['requirements']],
         {'requirement_id','coverage','unit_ids','rationale'}),
        ('units','unit_id',[u['unit_id'] for u in task['answer_units']],
         {'unit_id','judgments','rationale'})]:
        rows=value.get(key); path='$.'+key
        if not isinstance(rows,list):errors.append(path+':array_required');continue
        ids=[r.get(ident) for r in rows if isinstance(r,dict)]
        if not all(isinstance(i,str) for i in ids) or Counter(ids)!=Counter(expected):
            errors.append(path+':expected_unique_ids_required')
        for i,row in enumerate(rows):
            rp=path+'['+str(i)+']'
            if not fields(row,required,rp) or key!='units':continue
            js=row.get('judgments')
            if not isinstance(js,list) or not js:
                errors.append(rp+'.judgments:nonempty_array_required');continue
            for j,judgment in enumerate(js):
                fields(judgment,{'proposition','claim_type','support','basis_ids','rationale'},
                       rp+'.judgments['+str(j)+']')
    return {'complete':not errors,'errors':errors}


def preflight(directory):
    frozen=json.loads((directory/'freeze.json').read_text(encoding='utf-8'))
    if frozen.get('owner_authorized') is not True:raise ValueError('Authorization required')
    for name,h in frozen['bound_file_hashes'].items():
        if sha(Path(name).read_bytes())!=h:raise ValueError('Frozen file changed: '+name)
    plan=json.loads((BASE/'freeze.json').read_text(encoding='utf-8'))
    tasks=json.loads((BASE/'inputs.json').read_text(encoding='utf-8'))
    if prepare(tasks)!=plan['order']:raise ValueError('Order/messages changed')
    if plan['common_execution']['maximum_calls']!=16:raise ValueError('Budget changed')
    return plan,tasks


async def execute(plan,tasks,client,diagnostics,persist):
    started=perf_counter();budget=ModelBudget(limit=16,deadline=started+1440)
    lookup={t['sample_id']:t for t in tasks}
    async def submit(item):return {'request_id':item['request_id']}
    items={item['request_id']:item for item in plan['order']}
    async def collect(accepted):
        item=items[accepted['request_id']];task=lookup[item['sample_id']]
        protocol=ARMS[item['arm']];begin=perf_counter()
        try:
            with model_invocation_scope(item['request_id'],protocol.VERSION,1):
                result,_=await structured_request(client,protocol.messages(task),protocol.VERSION,
                    lambda value:v6.parse(value,task),diagnostics=diagnostics,
                    response_contract_version=v6.VERSION,max_corrections=1,max_message_chars=90000)
            return {'request_id':item['request_id'],'status':'complete',
                    'prediction':result,'elapsed_seconds':perf_counter()-begin}
        except Exception as exc:
            return {'request_id':item['request_id'],'status':'failed',
                    'error_code':'SERVICE_EXECUTION_FAILED',
                    'issue_code':getattr(exc,'code',type(exc).__name__),
                    'elapsed_seconds':perf_counter()-begin}
    with model_scope(budget):
        controls=await run_fixed([{'id':i['request_id'],'input':i} for i in plan['order']],
                                submit=submit,collect=collect,persist=persist)
    return {'actual_calls':budget.used,'records':[asdict(r) for r in budget.records],
            'controls':controls,'elapsed_seconds':perf_counter()-started}


def run(directory):
    plan,tasks=preflight(directory)
    with (directory/'attempt.json').open('x',encoding='utf-8') as handle:
        json.dump({'automatic_resume':False},handle)
    from backend.config import ServiceConfig
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    from model_adapter.runtime import ModelClient
    from services.response_diagnostics import ResponseDiagnostics,LOCAL_ROOT
    ServiceConfig.from_environment()
    s=plan['model_settings'];settings=ModelSettings(s['model_id'],s['timeout_seconds'],
        s['max_output_tokens'],s['max_response_chars'],s['endpoint'],'DEEPSEEK_API_KEY')
    adapter=create_adapter(settings)
    def persist(rid,kind,value):
        if rid not in {i['request_id'] for i in plan['order']}:raise ValueError('Unplanned ID')
        write(directory/(rid+'.'+kind+'.json'),value)
    try:
        result=asyncio.run(execute(plan,tasks,ModelClient(adapter,settings),
            ResponseDiagnostics(LOCAL_ROOT/'format-stability-v1'/directory.name),persist))
        write(directory/'execution.json',result)
    finally:adapter.close()
    print(json.dumps({'actual_calls':result['actual_calls'],'attempted':len(result['controls']),
                      'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--run',action='store_true')
    a=p.parse_args()
    if a.run:run(a.directory)
    else:preflight(a.directory);print('Preflight passed; no API.')
