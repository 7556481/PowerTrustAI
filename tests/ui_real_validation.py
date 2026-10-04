"""Explicitly authorized two-case API validation tooling, never imported by tests.

Freeze loads configuration through the existing real entrypoint only. Collect is
read-only HTTP; the browser submits frozen inputs. No POST replay or model CLI.
Credentials/headers are held internally and never printed or archived.
"""
import argparse
import hashlib
import json
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from backend.config import ROOT,ServiceConfig
from backend.assembly import ComponentFactory
from backend.local_access import token_for

DIRECTORY=ROOT/'data/runtime_local/ui-v1-real-validation'
INPUTS=[
 {'mode':'question_answer','question':'What role does reactive power play in voltage control?',
  'user_context':'Conceptual explanation only; no plant operation or engineering safety claim.',
  'answer_requirements':['用中文最多两句，解释基本概念。','仅依据已有资料；证据不足时明确说明，不给厂站操作建议。']},
 {'mode':'assess_existing','question':'Is this conceptual statement about reactive power and voltage supported?',
  'existing_answer':'Reactive power resources help regulate voltage.',
  'user_context':'Short user-supplied conceptual statement; no plant inputs or engineering safety claim.'},
]

def write_new(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

def freeze():
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    config=ServiceConfig.from_environment() # authorized real preflight, existing .env loader
    factory=ComponentFactory(config);manifest=factory.manifest(factory.preflight())
    value={'scope':'two real API runs submitted by browser; no automatic rerun','inputs':INPUTS,'manifest':manifest,
      'request_bound':{'per_run_server_cap':40,'two_run_hard_cap':80,'preferred_actual_total':40,
       'question_answer_structural_worst':'16 + C_v1 + C_v2, capped by existing 40-call RunBudget',
       'assess_existing_structural_worst':'14 + C_v1 + C_v2 (frozen C_v1=0), capped at 40',
       'reason':'includes generation(2 QA only), extraction(2 per round), domain(2 per round), revision(2), independent fact+original citation requests plus one format correction per fact stage; max one revision. Citation count is model output, so no fabricated fixed count.',
       'no_new_budget_or_protocol':True},
      'stop_conditions':['model/network/auth/balance/rate-limit/timeout/service unavailability: no next case',
        'no POST retry, no failed-case rerun, no mid-batch protocol changes',
        'configuration/source mismatch: stop; keep actual failure/partial results'],
      'pricing_checked_date':'2026-10-04','price_source':'https://api-docs.deepseek.com/quick_start/pricing/',
      'client_sha256':hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()}
    write_new(DIRECTORY/'plan-v1.json',value)
    print(json.dumps({'frozen':True,'profile':manifest['profile'],'model_id':manifest['model_id'],
                      'knowledge_version':manifest['knowledge_version'],'hard_cap':80,'preferred_actual':40}))

class Client:
    def __init__(self,port):self.base=f'http://127.0.0.1:{port}';self.token=token_for(ServiceConfig().token_file)
    def get(self,path,authorized=True):
        headers={'Authorization':'Bearer '+self.token} if authorized else {}
        try:
            with urlopen(Request(self.base+path,headers=headers),timeout=15) as r:return r.status,json.loads(r.read())
        except HTTPError as r:return r.code,json.loads(r.read())

def summary(result):
    records=result.get('model_usage',[]);usage=[r['usage'] for r in records if r.get('usage')]
    cost=[r['cost_estimate'] for r in records if r.get('cost_estimate') and r['cost_estimate'].get('usd_lower') is not None]
    totals={key:sum(u[key] for u in usage if u.get(key) is not None) for key in
            ('input_tokens','output_tokens','total_tokens','cache_hit_tokens','cache_miss_tokens')}
    stages={}
    for r in records:
        stage=stages.setdefault(r['prompt_version'],{'requests':0,'corrections':0,'valid_structure':0,'errors':[]})
        stage['requests']+=1;stage['corrections']+=int(r['correction']);stage['valid_structure']+=int(r.get('output_status')=='valid_structure')
        if r.get('error_code'):stage['errors'].append(r['error_code'])
    return {'run_id':result['execution']['run_id'],'status':result['execution']['status'],
            'decision':result.get('decision'),'execution':result['execution'],
            'versions':[a['version'] for a in result.get('answer',{}).get('versions',[])],
            'actual_requests':len(records),'corrections':sum(r['correction'] for r in records),
            'known_usage_subtotal':totals,'requests_without_usage':len(records)-len(usage),
            'known_cost_subtotal_usd':[sum(c['usd_lower'] for c in cost),sum(c['usd_upper'] for c in cost)],
            'requests_without_cost_estimate':len(records)-len(cost),'stages':stages,
            'fact_statuses':[f['status'] for f in result.get('findings',{}).get('model_fact',[])],
            'evidence_count':len(result.get('evidence',[]))}

def collect(port,rid,verify=False):
    plan=json.loads((DIRECTORY/'plan-v1.json').read_text(encoding='utf-8'));client=Client(port)
    status,health=client.get('/health',False)
    if status!=200 or health['profile']!='real':raise RuntimeError('Expected real service; no model task submitted')
    prefix='/runs/'+rid;started=time.monotonic();previous=None
    while True:
        status,state=client.get(prefix)
        if status!=200:raise RuntimeError('State unavailable; no requests replayed')
        if state['status']!=previous:print(json.dumps({'run_id':rid,'status':state['status']}),flush=True);previous=state['status']
        if state['status'] not in ('queued','running'):break
        if time.monotonic()-started>920:raise RuntimeError('Read-only monitoring deadline exceeded; no POST replay')
        time.sleep(2)
    status,result=client.get(prefix+'/result')
    if status!=200 or not result.get('answer'): # preserve genuine early execution failure
        result=dict(result);result.setdefault('model_usage',[])
    if result.get('configuration'):
        for key in ('source_sha256','template_sha256','knowledge_version','protocols','prompts','contracts','budget','model_id'):
            if result['configuration'][key]!=plan['manifest'][key]:raise RuntimeError('Frozen configuration mismatch; stop batch')
    if verify:
        before=json.loads((DIRECTORY/(rid+'.json')).read_text(encoding='utf-8'))
        _,reviews=client.get(prefix+'/reviews')
        value={'run_id':rid,'result_exact_equal':result==before['result'],'reviews_exact_equal':reviews==before['reviews'],
               'actual_request_records_before':len(before['result'].get('model_usage',[])),
               'actual_request_records_after':len(result.get('model_usage',[])),'no_post':True}
        write_new(DIRECTORY/(rid+'-restart.json'),value);print(json.dumps(value));return
    _,trace=client.get(prefix+'/trace');_,reviews=client.get(prefix+'/reviews')
    evidence=[]
    for e in result.get('evidence',[]):
        code,body=client.get(prefix+'/evidence/'+e['evidence_id']);evidence.append({'status':code,'body':body,'text_equal':body.get('text')==e['text']})
    unauth,_=client.get(prefix,False)
    value={'profile':'real','run_id':rid,'health':health,'state':state,'result':result,'trace':trace,
           'reviews':reviews,'evidence_roundtrip':evidence,'unauthorized_status':unauth,'summary':summary(result)}
    write_new(DIRECTORY/(rid+'.json'),value);print(json.dumps(value['summary'],ensure_ascii=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-real',action='store_true');parser.add_argument('--run-id')
    parser.add_argument('--verify-restart',action='store_true');parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    if args.freeze_real:freeze()
    elif args.run_id:collect(args.port,args.run_id,args.verify_restart)
    else:parser.error('Choose explicit real freeze or read-only API collection')
