"""Fixed old-input model comparison, using the existing reviewer and run_fixed."""
import asyncio,json,subprocess
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from evaluation.strict_interface_probe_v1 import ROOT,save,load,digest,check_schema,Recorder
from evaluation.batch_control import run_fixed
from backend.serialization import wire
from backend.store import RunStore
from model_adapter.contracts import ModelSettings
from model_adapter.deepseek import DeepSeekAdapter
from model_adapter.runtime import ModelBudget,model_scope,model_invocation_scope,credential_from_environment
from model_adapter.strict_review_tool import specification,NAME
from services.review_simple_tool_v1 import ToolCatalog,SYSTEM,PROMPT
from services.citation_workload import CitationWorkload,pack

VERSION='fact-review-model-fit-v1'
LOCAL=ROOT/'data/retrieval_local'/VERSION
PUBLIC=ROOT/'docs/evaluation'/VERSION
MODELS={'flash':'deepseek-flash','pro':'deepseek-v4-pro'}
SETTINGS=ModelSettings('deepseek-flash',90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')


def order():
    return [dict(id=f'A{i+1}-{v}',input=dict(case=i,variant=v)) for i in range(8) for v in (('flash','pro') if i%2==0 else ('pro','flash'))]


def inputs(materials,index):
    from evaluation.production_review_v2 import request,fixed_input
    return fixed_input(request(materials,index,draft=True))


def groups(inp):
    cat=ToolCatalog(inp);facts=[t for t,x in cat.targets.items() if x['kind']=='fact'];cites=[t for t,x in cat.targets.items() if x['kind']=='citation']
    packed,rejected=pack(cites,cat.payload,SYSTEM+json.dumps(specification(),ensure_ascii=False),CitationWorkload())
    assert not rejected
    return [[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(cat.payload(g),ensure_ascii=False))] for g in ([tuple(facts)] if facts else [])+list(packed)]


def payload(model,messages):
    return dict(model=model,messages=messages,max_tokens=8000,stream=False,thinking=dict(type='disabled'),tools=[specification()],tool_choice=dict(type='function',function=dict(name=NAME)))


def freeze():
    if (LOCAL/'freeze.json').exists() or (LOCAL/'attempt.json').exists():raise ValueError('No resume or overwrite')
    selection=load(LOCAL/'selection.json');assert selection['selected']=='deepseek-v4-pro'
    m=load(ROOT/'data/retrieval_local/review-contract-simple-v1/materials.json');check_schema(specification()['function']['parameters'])
    messages={};frozen_inputs={}
    for i in range(8):
        inp=inputs(m,i);messages[f'A{i+1}']=groups(inp);frozen_inputs[f'A{i+1}']=wire(inp)
    # References reviewed before prediction; no changes to the existing labels.
    reasons=[
        ['Source directly describes dynamic regulation, bandwidth and set-point/droop alternatives.','Source directly describes nominal-voltage contribution, voltage-squared capability and switching.'],
        ['Source explicitly models MW/Mvar at the two alternative boundary locations.','Source explicitly states the two directions of avoiding excessive reactive-support dependence.'],
        ['N-1 clause explicitly binds immediate performance and no operator intervention.','N-2 clause does not impose the N-1 no-operator/immediate/same-limits requirement; silence is insufficient, not an opposite engineering rule.'],
        ['Answer says the formula explicitly retains R and B; source explicitly neglects both in this model: direct conflict.','Short-line derivation does not establish validity for arbitrary line lengths; insufficient, not contradiction.'],
        ['N-1 immediately/no operator/limits and both steady-state and stability are explicitly present.'],
        ['Short-line, neglect R/B and voltage/angle/reactance relations directly match the source.'],
        ['Dynamic regulation description matches the text.','Descriptive behavior does not establish an all-fault plant guarantee; no given counterexample or negative theorem, so insufficient rather than contradicted.'],
        ['Explicit MW/Mvar load representation is directly described.','No plant transformer capacity record or calculation fixes 100MVA; insufficient rather than contradicted.']]
    references=[dict(case_id=f'A{i+1}',labels=x['reference'],basis=reasons[i],judgeability='All current labels usable within supplied-text support scope; not universal engineering truth.') for i,x in enumerate(m['A'])]
    critical=['model_adapter/deepseek.py','model_adapter/wire_observation.py','model_adapter/runtime.py','model_adapter/strict_review_tool.py','evaluation/fact_review_model_fit_v1.py','evaluation/strict_interface_probe_v1.py','evaluation/batch_control.py','evaluation/production_review_v2.py','agents/evidence_verification.py','services/review_simple_v1.py','services/review_simple_tool_v1.py','services/scoped_fact_execution.py','services/structured_model.py']
    f=dict(version=VERSION,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),selection=selection,settings=wire(SETTINGS),models=MODELS,cases=order(),sources={p:digest((ROOT/p).read_bytes()) for p in critical},initial_messages=messages,inputs=frozen_inputs,references=references,reference_revision='unchanged-old-labels-reviewed-v1',schema=specification(),semantic_prompt_sha256=digest(SYSTEM.encode()),projection='simple-condition-projection-v1.1',adaptation='reuse-fixed-author-target-v2; program-bound old author drafts; not generation/extraction scores',stop_scope='Both models share provider/account/storage/controller: any shared or unknown-acceptance fault stops all remaining tasks. Output contract failures remain case-local.',planned_tasks=16,expected_initial_requests=32,correction_rule='At most one correction shared by fact/citation per task; no node allowance added; existing40 calls/800s/110s stage/90s request limits.')
    save(LOCAL/'materials.json',m);save(LOCAL/'freeze.json',f);return f


class BoundRecorder(Recorder):
    """Validate actual serialized boundary against saved messages before every POST."""
    def __init__(self,directory,model,diagnostics,frozen_messages):
        super().__init__(directory);self.model,self.diagnostics,self.frozen_messages=model,diagnostics,frozen_messages
    def __call__(self,stage,value):
        if stage=='request':
            try:
                candidates=[]
                for p in self.diagnostics.glob('scope-*.json'):
                    v=load(p)
                    if 'messages' in v and digest(json.dumps(v['messages'],ensure_ascii=False).encode())==value['field_sha256']['messages']:candidates.append(v)
                assert len(candidates)==1
                v=candidates[0];msgs=v['messages'];assert digest(json.dumps(payload(self.model,msgs),ensure_ascii=False).encode())==value['body_sha256']
                if not v['correction']:assert msgs in self.frozen_messages
                else:assert msgs[:-1] in self.frozen_messages and len(msgs)==3
                assert value['ssl_check_hostname'] and value['ssl_verify_mode']==2 and value['unknown_field_count']==0
            except Exception:self.failed=True;raise
        super().__call__(stage,value)


async def execute_async():
    f=load(LOCAL/'freeze.json');assert order()==f['cases']
    assert all(digest((ROOT/p).read_bytes())==h for p,h in f['sources'].items())
    from harness.deepseek_trial import load_project_env
    load_project_env();credential_from_environment(SETTINGS)
    save(LOCAL/'attempt.json',dict(id=uuid4().hex,version=VERSION,no_resume=True))
    store=RunStore(LOCAL/'runs.sqlite3');accepted={};results={}
    def persist(cid,phase,data):save(LOCAL/'records'/f'{cid}-{phase}.json',data)
    async def submit(spec):
        rid=uuid4().hex;store.create(rid,spec,dict(profile=VERSION));accepted[rid]=spec;return dict(run_id=rid)
    async def collect(a):
        rid=a['run_id'];spec=accepted[rid];cid=f'A{spec["case"]+1}-{spec["variant"]}';key=f'A{spec["case"]+1}';model=MODELS[spec['variant']]
        store.mark(rid,'running');start=perf_counter();inp=inputs(load(LOCAL/'materials.json'),spec['case']);assert wire(inp)==f['inputs'][key]
        diagnostics=LOCAL/'diagnostics'/cid;rec=BoundRecorder(LOCAL/'wire'/cid,model,diagnostics,f['initial_messages'][key]);settings=replace(SETTINGS,model_id=model)
        adapter=DeepSeekAdapter(settings,strict_model_id=model,wire_observer=rec);budget=ModelBudget(40,deadline=start+800);out={}
        try:
            from agents.evidence_verification import ModelEvidenceVerificationAgent
            agent=ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=diagnostics,schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1',review_message_profile='lossless_v1',support_relation_checks=True,support_relation_version=6)
            with model_scope(budget),model_invocation_scope(rid,'evidence_verification',1):v=await asyncio.wait_for(agent.run(inp),110)
            out=dict(verification=wire(v),execution_issues=wire(v.execution_issues))
            if any(type(x.returned_model_id) is str and x.returned_model_id!=model for x in budget.records):out['error_code']='CONFIGURATION_UNAVAILABLE'
        except Exception as exc:
            code=getattr(exc,'code','SERVICE_EXECUTION_FAILED');out=dict(error_code=code,exception_type=type(exc).__name__)
            if code in ('MODEL_TIMEOUT','MODEL_CANCELLED'):out['error_code']='SERVICE_EXECUTION_FAILED'
            if getattr(exc,'partial_output',None) is not None:out['partial_output']=wire(exc.partial_output)
        finally:
            if adapter._active is not None and not adapter._active.done():
                try:await asyncio.wrap_future(adapter._active)
                except Exception:pass
            adapter.close()
        if rec.failed:out['error_code']='DIAGNOSTIC_STORAGE_FAILED'
        out.update(case_id=cid,model_id=model,run_id=rid,records=wire(budget.records),wire_events=rec.events,elapsed_ms=round((perf_counter()-start)*1000))
        results[cid]=out;store.mark(rid,'completed',result=out);print(cid,'calls',len(budget.records),'complete',not(out.get('execution_issues') or out.get('error_code')),flush=True);return out
    try:
        controls=await run_fixed(f['cases'],submit=submit,collect=collect,persist=persist)
        result=dict(version=VERSION,controls=controls,results=results,planned=16,unexecuted=[x['id'] for x in f['cases'] if x['id'] not in results]);save(LOCAL/'summary.json',result);return result
    finally:store.close()


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['freeze']:freeze();print('Frozen16 tasks; zero completions sent.')
    elif sys.argv[1:]==['execute']:asyncio.run(execute_async())
    else:raise SystemExit('freeze or execute only; no resume')
