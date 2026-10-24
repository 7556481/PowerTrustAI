"""Lossless output carrier over the unchanged simple_v1 catalog and projection."""
from services.review_simple_v1 import SimpleCatalog,SYSTEM as ORIGINAL,CONTRACT
from model_adapter.strict_review_tool import specification,map_null,NULL,VERSION
from services.validation_diagnostics import ErrorCollector
from copy import deepcopy

PROMPT='evidence-verification-v9.22.1-simple-strict-tool-v1'
SYSTEM=ORIGINAL.replace('Return JSON EXACT','Call submit_review_result exactly once with arguments JSON EXACT').replace('objection: null explicitly','objection: "__NULL__" explicitly').replace('repair: null or EXACT','repair: "__NULL__" or EXACT').replace('"objection":null','"objection":"__NULL__"').replace('"repair":null','"repair":"__NULL__"')
SYSTEM+='\nTransport '+VERSION+': only objection/repair business null use the exact string "'+NULL+'". Objects remain objects; unknown enums remain unknown. No ordinary text or other tool calls. The tool submits results only; no external operation or follow-up summary.\n'


class ToolCatalog(SimpleCatalog):
    result_tool=specification()
    correction_instruction=SimpleCatalog.correction_instruction.replace('Return the SAME','Call submit_review_result with the SAME')+' Use the same strict tool and __NULL__ transport markers, not text JSON; no summary.'

    def decode_wire(self,value,group):
        data=deepcopy(value)
        if type(data) is dict and type(data.get('judgments')) is list:
            for row in data['judgments']:
                if type(row) is dict and any(k in row and row[k] is None for k in ('objection','repair')):row['_native_null_transport_error']=True
        return super().decode_wire(map_null(data),group)

    def parse_one(self,row,target,path):
        if type(row) is dict and row.get('_native_null_transport_error'):
            ec=ErrorCollector(VERSION);ec.check(False,path,'explicit_null_transport_marker_required');ec.finish()
        return super().parse_one(row,target,path)


async def run(agent,inputs):
    from services.scoped_fact_execution import execute
    return await execute(agent,inputs,catalog=ToolCatalog(inputs),prompt_version=PROMPT,contract_version=CONTRACT,instruction=SYSTEM)
