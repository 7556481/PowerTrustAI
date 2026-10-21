"""Single authorized baseline batch; existing controller, v7 prompt, v6 parser."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from evaluation import premise_bound_review_v7 as v7, premise_bound_review_v6 as v6
from evaluation.batch_control import run_fixed
from evaluation.text_bound_review import canonical, sha, write
from model_adapter.runtime import ModelBudget, model_scope, model_invocation_scope
from services.structured_model import structured_request

CARDS=Path('docs/evaluation/baseline-answer-drafts-v1/reviewed-cards-v2.json')
ANSWERS=Path('docs/evaluation/baseline-answer-drafts-v2/answers-v2.json')
PUBLIC=Path('docs/evaluation/baseline-batch-v1')
DIRECTORY=Path('data/evaluation_local/reviewer-baseline-v1/batch-v1')


def build_tasks(cards,answers):
    """Only input cards and actual answers; never inspect evaluator artifacts."""
    cs={c['card_id']:c for c in cards['cards']}
    aa={a['id']:a for a in answers['answers']}
    if len(cs)!=8 or len(cards['cards'])!=8 or len(aa)!=24 or len(answers['answers'])!=24:
        raise ValueError('Exact 8-family / 24-answer identity required')
    order=['H-BL-'+source+'-'+str(family).zfill(2)+'-A'+str(answer).zfill(2)
           for answer in (1,2,3) for family in (1,2)
           for source in ('NWS','USGS','NASA','CDC')]
    if set(aa)!=set(order):raise ValueError('Exact planned answer IDs required')
    tasks=[]
    for sid in order:
        a=aa[sid]
        if a['card_id']!=sid.rsplit('-A',1)[0]:raise ValueError('Card binding mismatch')
        task=v7.model_input(cs[a['card_id']],a)
        validate_task(task)
        tasks.append(task)
    return tasks


def validate_task(t):
    if set(t)!={'sample_id','question','requirements','scenario_premises','evidence',
                'answer','answer_units','unit_version'}:raise ValueError('Task whitelist')
    for r in t['requirements']:
        if set(r)!={'requirement_id','description'}:raise ValueError('Requirement whitelist')
    for e in t['evidence']:
        if set(e)!={'text','url','locator','text_basis','evidence_id','scope_context','source_role'}:
            raise ValueError('Evidence whitelist')
        if e['source_role']!='literature':raise ValueError('Frozen literature role')
        for s in e['scope_context']:
            if set(s)!={'text','url','locator','text_basis'}:raise ValueError('Context whitelist')
    from evaluation.text_bound_review_v2 import build_units
    if t['answer_units']!=build_units(t['sample_id'],t['answer']):raise ValueError('Program carriers')
    v6.basis_catalog(t)


def prepare_tasks():
    return build_tasks(json.loads(CARDS.read_text(encoding='utf-8')),
                       json.loads(ANSWERS.read_text(encoding='utf-8')))


def message_rows(task):return [{'role':m.role,'content':m.content} for m in v7.messages(task)]


def preflight(directory):
    if directory.resolve()!=DIRECTORY.resolve():raise ValueError('Fixed directory required')
    f=json.loads((directory/'freeze.json').read_text(encoding='utf-8'))
    if f!=json.loads((PUBLIC/'execution-freeze-v1.json').read_text(encoding='utf-8')):
        raise ValueError('Public/private freeze mismatch')
    if not f['owner_authorized'] or f['maximum_calls']!=48 or f['planned_items']!=24:
        raise ValueError('Authorization/budget')
    if len(f['order'])!=24 or f['budget_deadline_seconds']!=4320:
        raise ValueError('Exact order/deadline required')
    if f['model_settings']!={'model_id':'deepseek-flash','endpoint':'https://api.deepseek.com',
                            'timeout_seconds':90,'max_output_tokens':2000,'max_response_chars':24000}:
        raise ValueError('Frozen model settings required')
    if v7.parse is not v6.parse or sha(v7.PROMPT.encode())!=f['prompt_sha256_utf8']:
        raise ValueError('Frozen prompt/parser identity')
    for p,h in f['bound_file_hashes'].items():
        if sha(Path(p).read_bytes())!=h:raise ValueError('Frozen file changed: '+p)
    tasks=prepare_tasks()
    if tasks!=json.loads((directory/'input.json').read_text(encoding='utf-8')):
        raise ValueError('Prepared input mismatch')
    preview=[message_rows(t) for t in tasks]
    if preview!=json.loads((directory/'messages-preview.json').read_text(encoding='utf-8')):
        raise ValueError('Message preview mismatch')
    for t,item in zip(tasks,f['order']):
        if item['sample_id']!=t['sample_id'] or item['task_sha256_utf8']!=sha(canonical(t).encode()) or item['messages_sha256_utf8']!=sha(canonical(message_rows(t)).encode()):
            raise ValueError('Message/order hash mismatch')
        if sum(len(m['content']) for m in message_rows(t))>90000:raise ValueError('Input capacity')
    for name,key in [('input.json','input_file_sha256'),('messages-preview.json','messages_file_sha256')]:
        if sha((directory/name).read_bytes())!=f[key]:raise ValueError('Private input hash')
    return f,tasks


async def execute(tasks,client,diagnostics,persist):
    begin=perf_counter();budget=ModelBudget(limit=48,deadline=begin+4320)
    lookup={t['sample_id']:t for t in tasks}
    async def submit(t):return {'sample_id':t['sample_id']}
    async def collect(accepted):
        t=lookup[accepted['sample_id']];started=perf_counter()
        try:
            with model_invocation_scope(t['sample_id'],v7.VERSION,1):
                value,_=await structured_request(client,v7.messages(t),v7.VERSION,
                    lambda x:v6.parse(x,t),diagnostics=diagnostics,
                    response_contract_version=v6.VERSION,max_corrections=1,max_message_chars=90000)
            return {'sample_id':t['sample_id'],'status':'complete','prediction':value,
                    'elapsed_seconds':perf_counter()-started}
        except Exception as exc:
            return {'sample_id':t['sample_id'],'status':'failed','error_code':'SERVICE_EXECUTION_FAILED',
                    'issue_code':getattr(exc,'code',type(exc).__name__),
                    'elapsed_seconds':perf_counter()-started}
    with model_scope(budget):
        controls=await run_fixed([{'id':t['sample_id'],'input':t} for t in tasks],
                                submit=submit,collect=collect,persist=persist)
    return {'actual_calls':budget.used,'records':[asdict(r) for r in budget.records],
            'controls':controls,'elapsed_seconds':perf_counter()-begin}


def run(directory):
    f,tasks=preflight(directory)
    with (directory/'attempt.json').open('x',encoding='utf-8') as h:
        json.dump({'automatic_resume':False,'fixed_order':[t['sample_id'] for t in tasks]},h)
    from backend.config import ServiceConfig
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    from model_adapter.runtime import ModelClient
    from services.response_diagnostics import ResponseDiagnostics,LOCAL_ROOT
    ServiceConfig.from_environment() # Existing authorized loader only; never print secrets.
    s=f['model_settings']
    settings=ModelSettings(s['model_id'],s['timeout_seconds'],s['max_output_tokens'],
                           s['max_response_chars'],s['endpoint'],'DEEPSEEK_API_KEY')
    adapter=create_adapter(settings)
    def persist(sid,kind,v):
        if sid not in {t['sample_id'] for t in tasks}:raise ValueError('Unplanned persistence')
        write(directory/(sid+'.'+kind+'.json'),v)
    try:
        result=asyncio.run(execute(tasks,ModelClient(adapter,settings),
            ResponseDiagnostics(LOCAL_ROOT/'reviewer-baseline-v1'/directory.name),persist))
        write(directory/'execution.json',result)
    finally:adapter.close()
    print(canonical({'actual_calls':result['actual_calls'],'attempted':len(result['controls']),
                     'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run(DIRECTORY)
    else:preflight(DIRECTORY);print('Preflight passed; no API.')
