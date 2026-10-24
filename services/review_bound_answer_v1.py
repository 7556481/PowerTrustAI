"""One change: target scope is program-bound, not repeated as condition answer IDs."""
from copy import deepcopy
from services.review_simple_tool_v1 import ToolCatalog,SYSTEM as OLD_SYSTEM
from model_adapter.strict_review_tool import specification as old_specification

CONTRACT='fact-review-simple-bound-answer-v1'
PROMPT='evidence-verification-v9.22.1-simple-bound-answer-v1'
SYSTEM=OLD_SYSTEM.replace('EXACT applicability,expression,instance,source_ids,\nanswer_ids,reason','EXACT applicability,expression,instance,source_ids,reason')
SYSTEM=SYSTEM.replace('source_ids: local source_unit IDs belonging to YOUR selected body bases. answer_ids:\nlocal answer_unit IDs. Both arrays may be [] when no corresponding condition is found;',
    'source_ids: local source_unit IDs belonging to YOUR selected body bases. This array\nmay be [] when no corresponding source condition is found;')
SYSTEM=SYSTEM.replace('"answer_ids":[],','').replace('six condition fields','five condition fields')
SYSTEM+='\nThe program binds this target to its complete local evaluated_text and answer_units. Do not output conditions.answer_ids: this repeats target identity, not a semantic check. Still explicitly judge expression and explain the condition object/state/conclusion relation in reason. A program target binding does not prove any condition preserved. gap_answer_ids remain required semantic gap locations.\n'


def specification():
    s=deepcopy(old_specification());c=s['function']['parameters']['properties']['judgments']['items']['properties']['conditions']
    del c['properties']['answer_ids'];c['required'].remove('answer_ids');return s


class BoundCatalog(ToolCatalog):
    contract_version=CONTRACT
    projection_version='simple-condition-projection-v1.2-target-bound'
    condition_answer_binding=False
    result_tool=specification()
    correction_instruction=ToolCatalog.correction_instruction.replace('six-field conditions','five-field conditions')+' Do not return conditions.answer_ids; the program owns target scope. Semantic expression and source IDs remain mandatory.'
    def __init__(self,inputs):
        super().__init__(inputs)
        for row in self.rows.values():row['conditions'].pop('answer_ids')
    def correction_context(self,group,value,diagnostic):
        result=super().correction_context(group,value,diagnostic);result['contract']=CONTRACT
        result['condition_answer_binding']='program_target_scope_not_model_output'
        return result


async def run(agent,inputs):
    from services.scoped_fact_execution import execute
    return await execute(agent,inputs,catalog=BoundCatalog(inputs),prompt_version=PROMPT,contract_version=CONTRACT,instruction=SYSTEM)
