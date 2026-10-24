"""Fixed synthetic HTTP comparison, then conditional old-input regression. No Factory."""
import asyncio
import hashlib
import http.client
import json
import os
import socket
import ssl
import subprocess
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from backend.serialization import wire
from backend.store import RunStore
from evaluation.batch_control import run_fixed
from model_adapter.contracts import *
from model_adapter.deepseek import DeepSeekAdapter, parse_response
from model_adapter.runtime import ModelBudget, ModelClient, credential_from_environment, model_scope, model_invocation_scope
from model_adapter.strict_review_tool import NAME, NULL, obj, enum, specification, map_null
from model_adapter.wire_observation import request_view, response_view, digest
from services.structured_model import strict_json

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'data/retrieval_local/strict-interface-consistency-v1'
PUBLIC=ROOT/'docs/evaluation/strict-interface-consistency-v1'
VERSION='strict-interface-consistency-v1'
SETTINGS=ModelSettings('deepseek-flash',timeout_seconds=90,max_output_tokens=1024,max_response_chars=96000,credential_env='DEEPSEEK_API_KEY')
PATH='/beta/chat/completions'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(json.dumps(wire(value),ensure_ascii=False,indent=2)+'\n')


def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def schemas():
    s=dict(type='string');b=dict(type='boolean');record=obj(dict(name=s,enabled=b))
    nullable=lambda v:dict(anyOf=[enum(NULL),v])
    return [
        (obj(dict(name=s,enabled=b,kind=enum('sample','other'))),dict(name='alpha',enabled=False,kind='sample')),
        (obj(dict(record=record,state=enum('known','unknown'))),dict(record=dict(name='beta',enabled=True),state='unknown')),
        (obj(dict(records=dict(type='array',items=record))),dict(records=[dict(name='gamma1',enabled=False),dict(name='gamma2',enabled=True)])),
        (obj(dict(records=dict(type='array',items=obj(dict(state=enum('known','unknown'),objection=nullable(obj(dict(kind=enum('fidelity','classification','uncertain'),reason=s))),repair=nullable(obj(dict(basis_id=s,replacement=s)))))))),
         dict(records=[dict(state='unknown',objection=NULL,repair=dict(basis_id='r1',replacement='delta')),dict(state='known',objection=dict(kind='uncertain',reason='epsilon'),repair=NULL)]))]


def check_schema(s):
    """Static official subset check, not a general JSON Schema implementation."""
    if 'anyOf' in s:
        assert set(s)=={'anyOf'} and len(s['anyOf'])>=2
        for child in s['anyOf']:check_schema(child)
        return
    t=s['type'];assert t in ('object','array','string','boolean','number','integer')
    allowed={'type','enum'}
    if t=='object':
        allowed|={'properties','required','additionalProperties'}
        assert s['additionalProperties'] is False and set(s['required'])==set(s['properties']) and len(s['required'])==len(set(s['required']))
        for child in s['properties'].values():check_schema(child)
    if t=='array':allowed.add('items');check_schema(s['items'])
    assert not set(s)-allowed


def conforms(value,s):
    if 'anyOf' in s:return any(conforms(value,c) for c in s['anyOf'])
    t=s['type'];ok=type(value) is {'object':dict,'array':list,'string':str,'boolean':bool,'integer':int,'number':float}[t]
    if t=='number':ok=type(value) in (float,int)
    if not ok or ('enum' in s and value not in s['enum']):return False
    if t=='object':return set(value)==set(s['properties']) and all(conforms(value[k],v) for k,v in s['properties'].items())
    if t=='array':return all(conforms(v,s['items']) for v in value)
    return True


def tool(schema):return dict(type='function',function=dict(name=NAME,strict=True,description='Submit the supplied synthetic record. No external action.',parameters=schema))


def payload(schema,value):
    return dict(model=SETTINGS.model_id,messages=[dict(role='system',content='Submit the supplied synthetic record unchanged using the sole result tool exactly once. Preserve values and order. No commentary.'),dict(role='user',content=json.dumps(value,ensure_ascii=False))],max_tokens=SETTINGS.max_output_tokens,stream=False,thinking=dict(type='disabled'),tools=[tool(schema)],tool_choice=dict(type='function',function=dict(name=NAME)))


def minimal_cases():
    cases=[]
    for i,(s,v) in enumerate(schemas(),1):
        check_schema(s);assert conforms(v,s)
        for p in (('direct','adapter') if i%2 else ('adapter','direct')):
            cases.append(dict(id=f'S{i}-{p}',input=dict(schema=s,value=v,path=p,payload=payload(s,v))))
    return cases


def evaluate(t,s,expected):
    calls=t.get('tool_calls');one=type(calls) is list and len(calls)==1
    f=calls[0].get('function') if one and type(calls[0]) is dict else None
    args=f.get('arguments') if type(f) is dict else None
    result=dict(accepted=t.get('http_status')==200,tool_count=len(calls) if type(calls) is list else None,
        envelope_valid=bool(one and calls[0].get('id') and calls[0].get('type')=='function' and type(f) is dict and f.get('name')==NAME and t.get('finish_reason')=='tool_calls' and (t.get('content') is None or t.get('content').strip()=='')),
        raw_arguments_preserved=type(args) is str,json_syntax=None,duplicate_keys=None,schema_valid=None,input_values_correct=None)
    if type(args) is str:
        result['arguments_sha256']=digest(args.encode())
        try:
            # Preserve all pairs for syntax inspection; never select a duplicate value.
            json.loads(args,object_pairs_hook=lambda pairs:pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
            result['json_syntax']=True
        except (ValueError,RecursionError):result['json_syntax']=False
        try:value=strict_json(args)
        except Exception as exc:
            duplicate=getattr(exc,'diagnostic',{}).get('constraint')=='duplicate_object_keys_not_allowed'
            result.update(duplicate_keys=duplicate)
        else:result.update(json_syntax=True,duplicate_keys=False,schema_valid=conforms(value,s),input_values_correct=conforms(value,s) and value==expected)
    result['valid']=all(result.get(k) is True for k in ('accepted','envelope_valid','raw_arguments_preserved','json_syntax','schema_valid','input_values_correct')) and result['duplicate_keys'] is False
    return result


class Recorder:
    def __init__(self,directory,expected=None):self.directory,self.expected,self.events=directory,expected,[];self.failed=False
    def __call__(self,stage,value):
        try:
            save(self.directory/f'{len(self.events)+1:02d}-{stage}.json',value)
            self.events.append(dict(stage=stage,value=value))
            if stage=='request' and (value['url']!='https://api.deepseek.com'+PATH or self.expected is not None and value['body_sha256']!=self.expected):
                self.failed=True;raise ValueError('Serialized request identity mismatch; no send permitted')
        except Exception:self.failed=True;raise


class DirectHTTP:
    """One frozen stdlib POST; only the safe observer is shared with the adapter."""
    def __init__(self,settings,body,recorder):self.settings,self.body,self.recorder=settings,body,recorder
    async def complete(self,request):return await asyncio.to_thread(self._post)
    def _post(self):
        key=credential_from_environment(self.settings);context=ssl.create_default_context()
        self.recorder('request',request_view(self.body,PATH,context))
        connection=http.client.HTTPSConnection('api.deepseek.com',timeout=self.settings.timeout_seconds,context=context)
        stage='connect_tls'
        try:
            connection.connect();stage='send_request'
            connection.request('POST',PATH,body=self.body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','Accept':'application/json'})
            stage='receive_response';response=connection.getresponse();stage='read_response'
            raw=response.read(self.settings.max_response_chars*4+32769 if response.status==200 else 8193)
            if len(raw)>self.settings.max_response_chars*4+32768:raise ModelOutputError()
            capture=response_view(response.status,raw);self.recorder('response',capture)
            if response.status!=200:parse_response(response.status,raw,self.settings.model_id)
            calls=capture.get('tool_calls') or [];f=calls[0].get('function') if len(calls)==1 else None
            args=f.get('arguments') if type(f) is dict else None;u=capture.get('usage') or {}
            usage=ModelUsage(u.get('prompt_tokens'),u.get('completion_tokens'),u.get('total_tokens'),cache_hit_tokens=u.get('prompt_cache_hit_tokens'),cache_miss_tokens=u.get('prompt_cache_miss_tokens'))
            return ModelResponse(args if type(args) is str else '',capture.get('model_id'),usage,capture.get('finish_reason'),result_transport=capture)
        except (socket.timeout,TimeoutError):raise ModelTimeoutError() from None
        except (OSError,http.client.HTTPException) as exc:raise ModelConnectionError(dict(version='official-network-diagnostic-v1',stage=stage,exception_type=type(exc).__name__,errno=getattr(exc,'errno',None),winerror=getattr(exc,'winerror',None))) from None
        finally:connection.close()


def freeze():
    if (LOCAL/'freeze.json').exists() or (LOCAL/'attempt.json').exists():raise ValueError('No resume or overwrite')
    cases=minimal_cases();check_schema(specification()['function']['parameters'])
    probe={'judgments':[{'objection':None,'repair':None},{'objection':{'kind':'uncertain','reason':'x'},'repair':{'basis_id':'x','replacement':'y'}}]}
    assert map_null(map_null(probe,encode=True))==probe
    materials=load(ROOT/'data/retrieval_local/review-contract-simple-v1/materials.json')
    regressions=[dict(id=f'A{i+1}',input=dict(case=i)) for i in (0,2,6,1)]
    files=['model_adapter/deepseek.py','model_adapter/wire_observation.py','evaluation/strict_interface_probe_v1.py','evaluation/batch_control.py','model_adapter/runtime.py','model_adapter/strict_review_tool.py','services/review_simple_v1.py','services/review_simple_tool_v1.py','agents/evidence_verification.py','evaluation/production_review_v2.py']
    frozen=dict(version=VERSION,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources={f:digest((ROOT/f).read_bytes()) for f in files},settings=wire(SETTINGS),cases=cases,regressions=regressions,materials_sha256=digest((ROOT/'data/retrieval_local/review-contract-simple-v1/materials.json').read_bytes()),business_schema=specification(),business_mapping='strict-review-tool-v1 __NULL__ roundtrip; semantic simple_v1/projection-v1.1 unchanged',regression_adaptation='reuse-fixed-author-target-v2; program-bound targets, no natural extraction; references excluded from messages',regression_references={x['id']:materials['A'][x['input']['case']]['reference'] for x in regressions})
    save(LOCAL/'materials.json',materials);save(LOCAL/'freeze.json',frozen)
    return frozen


def admission(results,controls):
    return len(results)==8 and not any(x['stop'] for x in controls) and all(results.get(f'S{i}-adapter',{}).get('layers',{}).get('valid') and results[f'S{i}-adapter'].get('arguments_unchanged') for i in range(1,5))


async def execute_async():
    frozen=load(LOCAL/'freeze.json')
    assert all(digest((ROOT/f).read_bytes())==sha for f,sha in frozen['sources'].items())
    assert minimal_cases()==frozen['cases']
    from harness.deepseek_trial import load_project_env
    load_project_env();credential_from_environment(SETTINGS)
    save(LOCAL/'attempt.json',dict(id=uuid4().hex,version=VERSION,proxy_env_presence={k:bool(os.environ.get(k)) for k in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','SSL_CERT_FILE','SSL_CERT_DIR')},note='http.client consumes none of these proxy variables; trust store/network intermediaries not independently attested'))
    store=RunStore(LOCAL/'runs.sqlite3');minimal_budget=ModelBudget(limit=8,deadline=perf_counter()+800);results={};accepted={}
    def persist(cid,phase,data):save(LOCAL/'records'/f'{cid}-{phase}.json',data)
    async def submit(spec):
        rid=uuid4().hex;store.create(rid,spec,dict(profile=VERSION));accepted[rid]=spec;return dict(run_id=rid)
    async def collect(a):
        rid=a['run_id'];spec=accepted[rid];store.mark(rid,'running');start=perf_counter();cid=next(x['id'] for x in frozen['cases']+frozen['regressions'] if x['input']==spec)
        body=json.dumps(spec['payload'],ensure_ascii=False).encode() if 'payload' in spec else None
        rec=Recorder(LOCAL/'wire'/cid,digest(body) if body is not None else None)
        settings=SETTINGS if body is not None else replace(SETTINGS,max_output_tokens=8000)
        adapter=DeepSeekAdapter(settings,diagnostic_tool=tool(spec['schema']) if body is not None else None,wire_observer=rec) if spec.get('path')!='direct' else DirectHTTP(settings,body,rec)
        budget=minimal_budget if body is not None else ModelBudget(limit=40,deadline=perf_counter()+800)
        begin=len(budget.records);out={};response=None
        try:
            with model_scope(budget),model_invocation_scope(rid,'interface_probe' if body is not None else 'evidence_verification',1):
                if body is not None:
                    client=ModelClient(adapter,settings)
                    messages=tuple(ModelMessage(**m) for m in spec['payload']['messages'])
                    response,number=await client.complete(messages,VERSION,budget,result_tool=tool(spec['schema']))
                    capture=next(x['value'] for x in rec.events if x['stage']=='response')
                    layers=evaluate(capture,spec['schema'],spec['value'])
                    calls=capture.get('tool_calls');fn=calls[0].get('function') if type(calls) is list and len(calls)==1 else None
                    out=dict(layers=layers,arguments_unchanged=type(fn) is dict and type(fn.get('arguments')) is str and response.text==fn['arguments'])
                    if type(response.model_id) is str and response.model_id!=settings.model_id:out['error_code']='CONFIGURATION_UNAVAILABLE'
                    budget.annotate(number,'valid_structure' if layers['valid'] else 'invalid_structure')
                else:
                    from evaluation.production_review_v2 import request,fixed_input
                    from agents.evidence_verification import ModelEvidenceVerificationAgent
                    inp=fixed_input(request(load(LOCAL/'materials.json'),spec['case'],draft=True))
                    agent=ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=LOCAL/'diagnostics'/cid,schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1',review_message_profile='lossless_v1',support_relation_checks=True,support_relation_version=6)
                    verification=await asyncio.wait_for(agent.run(inp),110)
                    out=dict(verification=wire(verification),execution_issues=wire(verification.execution_issues))
        except Exception as exc:
            code=getattr(exc,'code','MODEL_CONNECTION_FAILED')
            out=dict(error_code=code,exception_type=type(exc).__name__)
            if code in ('MODEL_TIMEOUT','MODEL_CANCELLED') or rec.failed:out['error_code']='SERVICE_EXECUTION_FAILED'
        finally:
            active=getattr(adapter,'_active',None)
            if active is not None and not active.done():await asyncio.wrap_future(active)
            if hasattr(adapter,'close'):adapter.close()
        out.update(case_id=cid,run_id=rid,records=wire(budget.records[begin:]),wire_events=rec.events,elapsed_ms=round((perf_counter()-start)*1000))
        results[cid]=out;store.mark(rid,'completed',result=out);return out
    try:
        controls=await run_fixed(frozen['cases'],submit=submit,collect=collect,persist=persist)
        gate=admission(results,controls);save(LOCAL/'admission.json',dict(passed=gate,controls=controls,rule='All four adapter minimal results valid, exact wire identity, no shared failure; subset and null roundtrip checked before send.'))
        regression_controls=await run_fixed(frozen['regressions'],submit=submit,collect=collect,persist=persist) if gate else []
        final=dict(minimal_controls=controls,admission=gate,regression_controls=regression_controls,results=results,planned_minimal=8,planned_conditional_regressions=4)
        save(LOCAL/'summary.json',final);return final
    finally:store.close()


if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['freeze']:freeze();print('Frozen; no request sent.')
    elif sys.argv[1:]==['execute']:
        r=asyncio.run(execute_async());print(json.dumps(dict(minimal=len(r['minimal_controls']),admission=r['admission'],regressions=len(r['regression_controls'])),ensure_ascii=False))
    else:raise SystemExit('Use freeze or execute; no resume.')
