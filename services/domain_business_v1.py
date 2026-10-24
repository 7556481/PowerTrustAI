"""Opt-in domain business flow: bound capabilities, one ordered review, disposition."""
from dataclasses import dataclass,replace,fields
from agents.contracts import SafetyDomainReviewOutput
from services.validation_diagnostics import ErrorCollector
VERSION='domain-business-v1'
PROMPT='power-domain-review-v3.6-business-v1'
INSTRUCTION='''
DOMAIN BUSINESS CANDIDATE: additionally include business_assessment in the analysis_scope check ONLY, EXACT
{scope,input_requirements,analysis_capability,constraints,summary}.
scope EXACT {kind,reason}: kind conceptual/engineering/uncertain, agrees with analysis_scope.task_scope.
input_requirements is an array of {name,necessity,availability,reason}; necessity required/irrelevant/uncertain; availability present/missing/unknown.
analysis_capability EXACT {status,reason}: status sufficient/insufficient/not_needed/uncertain.
constraints EXACT {applicable,reason}: applicable boolean. summary nonempty string.
Reason IN ORDER: actual question AND asserted answer scope; truly required inputs;
actual configured tools and their result states/capability; applicable registered constraints
and source-bounded hazard rules; summarize to existing checks. A concept needs no plant
parameters unless concrete guarantees are asserted. Missing inputs alone are not high risk.
Fact support is not site safety. Domain knowledge cannot repair facts without evidence.
No simulation tool is configured. Failed/missing tool records cannot mean an analysis was run;
even a successful scalar result proves only its declared scalar capability. Explain scope of
sources; never promote US source principles to local law. Negated/quoted-and-rejected
hazardous text is not endorsed advice. business_assessment and checks must be consistent;
uncertainty stays explicit. No extra tools, planning models, retries or correction allowance.
'''
from agents.contracts import BusinessDomainOutput as BusinessOutput

def wrap_parser(parser,inputs):
 def parse(value):
    from copy import deepcopy
    v=deepcopy(value);target=next((r for r in v.get('checks',[]) if r.get('check_id')=='analysis_scope'),{});a=target.pop('business_assessment',None);ec=ErrorCollector(VERSION)
    if not ec.fields(a,{'scope','input_requirements','analysis_capability','constraints','summary'},set(),'$.business_assessment'):ec.finish()
    for key,required in (('scope',{'kind','reason'}),('analysis_capability',{'status','reason'}),('constraints',{'applicable','reason'})):
        if ec.fields(a[key],required,set(),'$.'+key):ec.check(type(a[key]['reason']) is str and bool(a[key]['reason'].strip()),'$.'+key,'reason_required')
    ec.check(a['scope'].get('kind') in ('conceptual','engineering','uncertain'),'$','scope')
    ec.check(a['analysis_capability'].get('status') in ('sufficient','insufficient','not_needed','uncertain'),'$','capability')
    ec.check(type(a['constraints'].get('applicable')) is bool,'$','boolean')
    ec.check(type(a['summary']) is str and bool(a['summary'].strip()),'$','summary')
    req=a['input_requirements'];ec.check(type(req) is list,'$','requirements_array')
    for r in req if type(req) is list else []:
        if not ec.fields(r,{'name','necessity','availability','reason'},set(),'$.input_requirements'):continue
        ec.check(all(type(r[k]) is str and bool(r[k].strip()) for k in ('name','reason')),'$','text')
        ec.check(r['necessity'] in ('required','irrelevant','uncertain') and r['availability'] in ('present','missing','unknown'),'$','input_enums')
    scope=next((r for r in v.get('checks',[]) if r.get('check_id')=='analysis_scope'),{})
    ec.check(scope.get('task_scope')==a['scope'].get('kind'),'$','scope_consistency')
    ec.finish();out=parser(v)
    return BusinessOutput(**{f.name:getattr(out,f.name) for f in fields(out)},business_assessment=a)
 return parse

def create_agent(*args,**kwargs):
 from agents.power_domain_review import ModelPowerDomainReviewAgent
 kwargs.update(protocol_version=5,safety_review=True,task_applicability=True)
 a=ModelPowerDomainReviewAgent(*args,**kwargs);a.business_flow=True
 original=a.run
 async def run(inputs):
    from langgraph.graph import StateGraph,START,END
    from langsmith import tracing_context
    from typing import TypedDict
    from harness.graph_runtime_v1 import validate_versions
    validate_versions()
    class State(TypedDict,total=False):
        capabilities:dict
        output:object
    async def prepare(state):
        from core.validation import merge_evidence
        merge_evidence(inputs.evidence)
        return {'capabilities':{'configured':['scalar-si-conversion-v2'],'engineering_simulation':False,'tool_records':len(inputs.tool_results)}}
    async def review(state):return {'output':await original(inputs)}
    async def finish(state):
        out=state['output'];trace=({'step':'bind_actual_tool_capabilities',**state['capabilities']},{'step':'ordered_scope_inputs_capability_constraints','model_calls':len(out.model_records)},{'step':'existing_policy_handoff','new_policy':False})
        if isinstance(out,BusinessOutput):out=replace(out,business_trace=trace)
        return {'output':out}
    graph=StateGraph(State)
    for name,node in (('capabilities',prepare),('review',review),('handoff',finish)):graph.add_node(name,node,retry_policy=[],cache_policy=None)
    graph.add_edge(START,'capabilities');graph.add_edge('capabilities','review');graph.add_edge('review','handoff');graph.add_edge('handoff',END)
    with tracing_context(enabled=False,parent=False):result=await graph.compile().ainvoke({},config={'callbacks':[],'recursion_limit':6})
    return result['output']
 a.run=run
 return a
