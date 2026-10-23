"""Opt-in fact Agent internal graph; reuses scoped request/parse infrastructure."""
from dataclasses import replace
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from agents.evidence_verification import ModelEvidenceVerificationAgent
from services.fact_flow_protocol_v1 import Catalog, VERSION, PROMPT, SYSTEM

class State(TypedDict, total=False):
    inputs: object
    catalog: object
    output: object
    trace: list

class FactFlowAgent(ModelEvidenceVerificationAgent):
    catalog_type = Catalog
    protocol_version = VERSION
    prompt_version_flow = PROMPT
    instruction = SYSTEM

    def __init__(self,*args,**kwargs):
        kwargs['schema_version']=13
        kwargs['correction_accounting']='invocation_scoped_v1'
        super().__init__(*args,**kwargs)

    async def run(self,inputs):
        from harness.graph_runtime_v1 import validate_versions
        validate_versions()
        from core.validation import merge_evidence, require
        from services.evidence_scope import validate_snapshot
        merge_evidence(inputs.seed_evidence,inputs.original_evidence)
        if inputs.generation_snapshot is not None:
            validate_snapshot(inputs.generation_snapshot,inputs.answer)
            merge_evidence(inputs.seed_evidence,inputs.original_evidence,inputs.generation_snapshot.evidence)
            require(inputs.knowledge_version is None or inputs.generation_snapshot.knowledge_version==inputs.knowledge_version,'knowledge version mismatch')
        async def prepare(state):
            # Existing binder rejects stale source identities and scopes.
            cat=self.catalog_type(state['inputs'])
            return {'catalog':cat,'trace':[{'node':'prepare_objects_and_legal_basis','targets':len(cat.targets),
                'answer_version':inputs.answer.version,'protocol':self.protocol_version}]}
        async def review(state):
            from services.scoped_fact_execution import execute
            out=await execute(self,inputs,catalog=state['catalog'],prompt_version=self.prompt_version_flow,contract_version=self.protocol_version,instruction=self.instruction)
            return {'output':out,'trace':state['trace']+[{'node':'classify_dependencies_and_support',
                'calls':len(out.model_records),'execution_issues':len(out.execution_issues)}]}
        async def gap(state):
            # Outer shared stage already owns bounded supplementary retrieval.
            # No tool is fabricated and no graph-level resend is possible.
            return {'trace':state['trace']+[{'node':'bounded_gap_disposition',
                'action':'return_to_existing_shared_stage','new_tool_calls':0,
                'reason':'only_existing_retrieval_and_scalar_conversion_capabilities'}]}
        async def finish(state):
            trace=state['trace']+[{'node':'validate_and_summarize','policy':'existing_policy_unchanged'}]
            return {'output':replace(state['output'],flow_trace=tuple(trace)),'trace':trace}
        graph=StateGraph(State)
        for name,node in [('prepare',prepare),('review',review),('gap',gap),('summarize',finish)]:graph.add_node(name,node,retry_policy=[],cache_policy=None)
        graph.add_edge(START,'prepare');graph.add_edge('prepare','review');graph.add_edge('review','gap');graph.add_edge('gap','summarize');graph.add_edge('summarize',END)
        from langgraph.errors import NodeCancelledError
        import asyncio
        with tracing_context(enabled=False,parent=False):
            try:result=await graph.compile().ainvoke({'inputs':inputs},config={'recursion_limit':8,'callbacks':[]})
            except NodeCancelledError as exc:
                cancelled=asyncio.CancelledError()
                if hasattr(exc.__cause__,'partial_output'):cancelled.partial_output=exc.__cause__.partial_output
                raise cancelled from exc
        return result['output']
