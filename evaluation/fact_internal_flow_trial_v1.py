"""Authorized fact-only comparison; fixed inputs, exclusive attempt, no resume."""
import asyncio,json,hashlib,os
from pathlib import Path
from dataclasses import asdict
from time import perf_counter
from backend.serialization import wire
from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
from evaluation.public_review_object_trial_v1 import write,read
from model_adapter.contracts import ModelSettings,ModelOutputError
from model_adapter.runtime import ModelBudget,model_scope,model_invocation_scope
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.fact_flow_v1 import FactFlowAgent
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'docs/evaluation/fact-internal-flow-v1'
LOCAL=ROOT/'data/retrieval_local/fact-internal-flow-live-v1'
SETTINGS=ModelSettings('deepseek-flash',90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def message_hash(messages):return hashlib.sha256(json.dumps([asdict(m) for m in messages],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
class GateError(ModelOutputError):code='FROZEN_PAYLOAD_GATE_FAILED'
def preflight():
    f=read(PUBLIC/'live-freeze-v1.json')
    if (LOCAL/'attempt.json').exists():raise ValueError('Attempt exists; never resume')
    for r in f['files']:
        if digest(ROOT/r['path'])!=r['sha256']:raise ValueError('Frozen file changed')
    return f

def freeze():
    old=read(PUBLIC/'source-manifest-v1.json')
    paths=[r['path'] for r in old['files']]+['evaluation/fact_internal_flow_trial_v1.py','evaluation/public_review_object_trial_v1.py','tests/test_fact_internal_flow_trial_v1.py','docs/evaluation/fact-internal-flow-v1/preparation-v1.json','docs/evaluation/fact-internal-flow-v1/inputs-and-reference-v1.json','docs/evaluation/fact-internal-flow-v1/live-criteria-v1.md']
    for r in old['files']:
        if digest(ROOT/r['path'])!=r['sha256']:raise ValueError('Approved implementation changed')
    write(PUBLIC/'live-freeze-v1.json',{'version':'fact-internal-flow-live-v1','authorization':'User accepted all eight synthetic materials and authorized this fixed DeepSeek comparison on 2026-10-23; no production switch.',
        'model':asdict(SETTINGS),'max_sends':28,'files':[{'path':p,'sha256':digest(ROOT/p)} for p in sorted(set(paths))],
        'order':read(PUBLIC/'preparation-v1.json')['order']})

async def batch(f,root,factory):
    results=[];total=0;stopped=False
    for entry in f['order']:
        ident=entry['case']+'-'+entry['variant']
        if stopped:
            results.append({'id':ident,'status':'unexecuted'});continue
        case=next(c for c in CASES if c['id']==entry['case']);inp=fixed_input(case)
        budget=ModelBudget(40,deadline=perf_counter()+800);sent=[];start=perf_counter();delegate=None
        try:
            branch=root/ident
            write(branch/'input.json',wire(inp))
            delegate=factory()
            class Guard:
                async def complete(self,request):
                    nonlocal total
                    n=len(sent)
                    if n>=2 or total>=28 or n==0 and (entry['initial_calls']!=1 or request.correction or message_hash(request.messages)!=entry['message_sha256']) or n==1 and not request.correction:raise GateError({})
                    if request.model_id!=SETTINGS.model_id or request.prompt_version!=entry['prompt_version']:raise GateError({})
                    write(branch/f'messages-{n+1}.json',{'messages':[asdict(m) for m in request.messages],'correction':request.correction})
                    total+=1;sent.append({'sequence':total,'correction':request.correction,'message_sha256':message_hash(request.messages)})
                    response=await delegate.complete(request)
                    write(branch/f'response-{n+1}.json',wire(response))
                    return response
            agent=(FactFlowAgent(Guard(),SETTINGS,diagnostic_dir=branch/'diagnostics') if entry['variant']=='candidate' else ModelEvidenceVerificationAgent(Guard(),SETTINGS,diagnostic_dir=branch/'diagnostics',schema_version=13,support_relation_checks=True,support_relation_version=6,review_message_profile='lossless_v1'))
            with model_scope(budget),model_invocation_scope(ident,'evidence_verification',1):
                output=await asyncio.wait_for(agent.run(inp),110)
            value=wire(output);write(branch/'output.json',value)
            failure=bool(output.execution_issues) or any(r.origin=='execution_incomplete' for finding in output.findings for r in finding.component_reviews)
            known=entry['initial_calls']==0 and not sent and not output.execution_issues
            row={'id':ident,'status':'known_precondition' if known else 'execution_failed' if failure else 'complete','seconds':perf_counter()-start,'sent':sent,'model_records':wire(budget.records),'output':value}
            write(branch/'summary.json',row);results.append(row);stopped=failure and not known
        except Exception as exc:
            row={'id':ident,'status':'execution_failed','exception_type':type(exc).__name__,'seconds':perf_counter()-start,'sent':sent,'model_records':wire(budget.records)}
            results.append(row);stopped=True
            write(root/(ident+'-failure.json'),row)
        finally:
            if delegate is not None:delegate.close()
    summary={'version':'fact-internal-flow-live-v1','total_sends':total,'branches':results}
    write(root/'summary.json',summary)
    return summary

def execute():
    f=preflight()
    from harness.deepseek_trial import load_project_env
    load_project_env()
    from model_adapter.deepseek import create_adapter
    write(LOCAL/'attempt.json',{'version':f['version'],'freeze_sha256':digest(PUBLIC/'live-freeze-v1.json'),'resume_allowed':False})
    return asyncio.run(batch(f,LOCAL,lambda:create_adapter(SETTINGS)))
if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['freeze']:freeze()
    elif sys.argv[1:] == ['execute']:
        s=execute();print(json.dumps({'total_sends':s['total_sends'],'branches':[{k:r[k] for k in ('id','status')} for r in s['branches']]}))
    else:raise SystemExit('freeze or execute required')
