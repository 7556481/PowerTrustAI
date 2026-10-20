"""Explicit paid-trial entry point for the frozen v3 development inputs only."""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
from time import perf_counter

from evaluation import requirement_review_v3 as protocol
from evaluation.batch_control import run_fixed
from evaluation.text_bound_review import canonical, sha, write
from evaluation.text_bound_review_v2 import build_units
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelBudget, ModelClient, model_scope, model_invocation_scope
from services.structured_model import structured_request


def freeze(prepared, output):
    offline=json.loads((prepared/'offline-manifest.json').read_text(encoding='utf-8'))
    assert offline['version']==protocol.VERSION
    for file,key in [('input.json','input_sha256'),('expectations-private.json','expectations_sha256'),
                     ('messages-preview.json','messages_preview_sha256')]:
        assert sha((prepared/file).read_bytes())==offline[key]
    for path,h in offline['working_tree_hashes'].items():assert sha(Path(path).read_bytes())==h
    tasks=json.loads((prepared/'input.json').read_text(encoding='utf-8'))
    preview=json.loads((prepared/'messages-preview.json').read_text(encoding='utf-8'))
    assert preview==[[{'role':m.role,'content':m.content} for m in protocol.messages(t)] for t in tasks]
    assert len(tasks)==3 and len({t['sample_id'] for t in tasks})==3
    output.mkdir(parents=True,exist_ok=False)
    # The same small literal inputs/labels; no PDFs, corpus or source archives.
    write(output/'input.json',tasks)
    write(output/'expectations-private.json',json.loads((prepared/'expectations-private.json').read_text(encoding='utf-8')))
    files=[Path(__file__),Path('evaluation/batch_control.py'),Path('model_adapter/runtime.py'),
           Path('model_adapter/contracts.py'),Path('model_adapter/deepseek.py'),
           Path('services/structured_model.py'),Path('services/response_diagnostics.py'),
           Path('backend/config.py'),Path('harness/deepseek_trial.py')]
    frozen={'protocol':protocol.VERSION,'execution':'requirement-trial-v3-once-v1',
            'parent_offline_manifest_sha256':sha((prepared/'offline-manifest.json').read_bytes()),
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'working_tree_hashes':dict(offline['working_tree_hashes'],**{str(p):sha(p.read_bytes()) for p in files}),
            'input_sha256':sha((output/'input.json').read_bytes()),
            'expectations_sha256':sha((output/'expectations-private.json').read_bytes()),
            'prompt_sha256':sha(protocol.PROMPT.encode()),'same_inputs_as_offline_preparation':True,
            'endpoint':'https://api.deepseek.com','model':'deepseek-flash',
            'planned_items':3,'maximum_calls':6,'max_corrections_per_item':1,
            'timeout_seconds':90,'total_timeout_seconds':600,'max_output_tokens':2000,
            'max_response_chars':24000,'max_message_chars':90000,'transient_retries':0,
            'stop':'first execution, transport or storage failure; no retry on semantic disagreement',
            'expected_labels_in_messages':False,'explicit_requirements_in_each_input':['R1','R2'],
            'per_requirement_output_required':True,'independent_test':False,
            'retrieval':False,'revision':False,'production_changed':False}
    write(output/'freeze.json',frozen)
    return frozen


async def execute(tasks,client,diagnostics,persist,total_timeout=600):
    started=perf_counter();budget=ModelBudget(limit=2*len(tasks),deadline=started+total_timeout)
    lookup={t['sample_id']:t for t in tasks}
    if len(lookup)!=len(tasks):raise ValueError('Unique samples required')
    async def submit(task):return {'sample_id':task['sample_id']}
    async def collect(accepted):
        task=lookup[accepted['sample_id']];begin=perf_counter()
        try:
            with model_invocation_scope(task['sample_id'],protocol.VERSION,1):
                prediction,_=await structured_request(client,protocol.messages(task),protocol.VERSION,
                    lambda value:protocol.parse(value,task),diagnostics=diagnostics,
                    response_contract_version=protocol.VERSION,max_corrections=1,max_message_chars=90000)
            return {'sample_id':task['sample_id'],'status':'complete','prediction':prediction,
                    'program_answer_units':task['answer_units'],'elapsed_seconds':perf_counter()-begin}
        except Exception as exc:
            return {'sample_id':task['sample_id'],'status':'failed','error_code':'SERVICE_EXECUTION_FAILED',
                    'issue_code':getattr(exc,'code',type(exc).__name__),'elapsed_seconds':perf_counter()-begin}
    with model_scope(budget):
        controls=await run_fixed([{'id':t['sample_id'],'input':t} for t in tasks],
            submit=submit,collect=collect,persist=persist)
    return {'protocol':protocol.VERSION,'actual_calls':budget.used,
            'records':[asdict(r) for r in budget.records],'elapsed_seconds':perf_counter()-started,
            'controls':controls}


def run(output):
    frozen=json.loads((output/'freeze.json').read_text(encoding='utf-8'))
    assert frozen['protocol']==protocol.VERSION and sha(protocol.PROMPT.encode())==frozen['prompt_sha256']
    for file,key in [('input.json','input_sha256'),('expectations-private.json','expectations_sha256')]:
        assert sha((output/file).read_bytes())==frozen[key]
    for path,h in frozen['working_tree_hashes'].items():assert sha(Path(path).read_bytes())==h
    tasks=json.loads((output/'input.json').read_text(encoding='utf-8'))
    assert len(tasks)==3 and frozen['maximum_calls']==6
    for task in tasks:
        assert task['answer_units']==build_units(task['sample_id'],task['answer'])
        assert {r['requirement_id'] for r in task['requirements']}=={'R1','R2'}
    with (output/'attempt.json').open('x',encoding='utf-8') as handle:
        json.dump({'started':True,'automatic_resume':False},handle)
    from backend.config import ServiceConfig
    from model_adapter.deepseek import create_adapter
    from services.response_diagnostics import ResponseDiagnostics,LOCAL_ROOT
    ServiceConfig.from_environment()  # Only this authorized runtime loads credentials.
    settings=ModelSettings(frozen['model'],frozen['timeout_seconds'],frozen['max_output_tokens'],
                           frozen['max_response_chars'],frozen['endpoint'],'DEEPSEEK_API_KEY')
    adapter=create_adapter(settings)
    def persist(sid,kind,value):
        assert sid in {t['sample_id'] for t in tasks}
        write(output/(sid+'.'+kind+'.json'),value)
    try:
        result=asyncio.run(execute(tasks,ModelClient(adapter,settings),
            ResponseDiagnostics(LOCAL_ROOT/'requirement-trial-v3'/output.name),persist,frozen['total_timeout_seconds']))
        write(output/'execution.json',result)
    finally:adapter.close()
    print(canonical({'actual_calls':result['actual_calls'],'attempted_items':len(result['controls']),
                     'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('freeze','run'))
    parser.add_argument('--prepared',type=Path,default=Path('data/evaluation_local/evidence-bound-v1/tr001-v3-offline-prepared'))
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.action=='freeze':print(canonical(freeze(args.prepared,args.output)))
    else:run(args.output)
