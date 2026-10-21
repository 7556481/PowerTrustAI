"""Evaluation-only frozen batch; reuse the existing v4 protocol and trial engine."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess

from evaluation import premise_bound_review_v4 as protocol
from evaluation.requirement_trial_v3 import execute
from evaluation.text_bound_review import sha, write
from evaluation.text_bound_review_v2 import build_units, UNIT_VERSION


def make_task(card, answer):
    e = card['evidence_snapshot']
    return {'sample_id': answer['candidate_id'], 'question': card['question'],
            'requirements': [{'requirement_id': r['id'], 'description': r['requirement']}
                             for r in card['requirements']],
            'scenario_premises': [], 'answer': answer['answer'],
            'answer_units': build_units(answer['candidate_id'], answer['answer']),
            'unit_version': UNIT_VERSION,
            'evidence': [{'evidence_id': e['candidate_excerpt_id'],
                          'text': e['normalized_text'], 'url': card['source_url'],
                          'locator': {'pdf_page': e['pdf_page_1based'],
                                      'printed_page': e['printed_page'],
                                      'description': e['locator'],
                                      'source_sha256': e['source_sha256']},
                          'text_basis': 'visually_checked_whitespace_normalized',
                          'scope_context': []}]}


def validate(tasks):
    assert len(tasks) == 12 and len({t['sample_id'] for t in tasks}) == 12
    for t in tasks:
        assert t['answer_units'] == build_units(t['sample_id'], t['answer'])
        assert set(t) == {'sample_id','question','requirements','scenario_premises',
                         'answer','answer_units','unit_version','evidence'}
        assert len(t['requirements']) in (2, 3)
        protocol.basis_catalog(t)


def freeze(prepared, output):
    tasks = json.loads((prepared/'input.json').read_text(encoding='utf-8'))
    validate(tasks)
    output.mkdir(exist_ok=False, parents=True)
    write(output/'input.json', tasks)
    write(output/'expectations-private.json', json.loads(
        (prepared/'expectations-private.json').read_text(encoding='utf-8')))
    write(output/'alignment-policy.json', json.loads(
        (prepared/'alignment-policy.json').read_text(encoding='utf-8')))
    write(output/'messages-preview.json', [[{'role':m.role,'content':m.content}
          for m in protocol.messages(t)] for t in tasks])
    paths = [Path(__file__), Path(protocol.__file__),
             Path('evaluation/requirement_review_v3.py'),
             Path('evaluation/text_bound_review.py'), Path('evaluation/text_bound_review_v2.py'),
             Path('evaluation/requirement_trial_v3.py'), Path('evaluation/batch_control.py'),
             Path('model_adapter/runtime.py'), Path('model_adapter/contracts.py'),
             Path('model_adapter/deepseek.py'), Path('backend/config.py'),
             Path('services/structured_model.py'), Path('services/response_diagnostics.py'),
             Path('services/validation_diagnostics.py')]
    frozen = {'protocol':protocol.VERSION, 'execution_version':'reviewer-fixed-batch-v1',
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'working_tree_hashes':{str(p):sha(p.read_bytes()) for p in paths},
              'file_hashes':{p.name:sha(p.read_bytes()) for p in output.iterdir()},
              'prompt_sha256':sha(protocol.PROMPT.encode()),
              'endpoint':'https://api.deepseek.com', 'model':'deepseek-flash',
              'planned_items':12, 'max_corrections_per_item':1, 'maximum_calls':24,
              'timeout_seconds':90, 'total_timeout_seconds':2400,
              'max_output_tokens':2000, 'max_response_chars':24000,
              'max_message_chars':90000, 'retries':0,
              'provider_sampling_parameters':'omitted; provider defaults, not fixed temperature',
              'stop':'first execution/transport/storage/contract failure, no semantic reruns',
              'independent_holdout_claim':False, 'production_changed':False}
    write(output/'freeze.json',frozen)


def run(output):
    f=json.loads((output/'freeze.json').read_text(encoding='utf-8'))
    for name,h in f['file_hashes'].items(): assert sha((output/name).read_bytes())==h
    for name,h in f['working_tree_hashes'].items(): assert sha(Path(name).read_bytes())==h
    assert sha(protocol.PROMPT.encode())==f['prompt_sha256']
    tasks=json.loads((output/'input.json').read_text(encoding='utf-8')); validate(tasks)
    # Fail closed before credential loading or network on a second invocation.
    with (output/'attempt.json').open('x',encoding='utf-8') as handle:
        json.dump({'started':True,'resume':False},handle)
    from backend.config import ServiceConfig
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    from model_adapter.runtime import ModelClient
    from services.response_diagnostics import ResponseDiagnostics, LOCAL_ROOT
    ServiceConfig.from_environment()
    settings=ModelSettings(f['model'],f['timeout_seconds'],f['max_output_tokens'],
                           f['max_response_chars'],f['endpoint'],'DEEPSEEK_API_KEY')
    adapter=create_adapter(settings)
    def persist(sid,kind,value):
        assert sid in {t['sample_id'] for t in tasks}
        write(output/(sid+'.'+kind+'.json'),value)
    try:
        result=asyncio.run(execute(tasks,ModelClient(adapter,settings),
            ResponseDiagnostics(LOCAL_ROOT/'reviewer-fixed-batch-v1'/output.name),
            persist,f['total_timeout_seconds'],protocol=protocol))
        write(output/'execution.json',result)
    finally:
        adapter.close()
    print(json.dumps({'actual_calls':result['actual_calls'],
                      'attempted':len(result['controls']),
                      'elapsed_seconds':result['elapsed_seconds']}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['freeze','run'])
    p.add_argument('--prepared',type=Path); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.action=='freeze': freeze(a.prepared,a.output)
    else: run(a.output)
