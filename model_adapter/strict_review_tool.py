"""Transport only: strict result submission, not a business tool or new reviewer."""
from copy import deepcopy
from services.validation_diagnostics import ErrorCollector

VERSION='strict-review-tool-v1'
NAME='submit_review_result'
NULL='__NULL__'


def obj(properties):
    return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)


def enum(*values):return dict(type='string',enum=list(values))


def schema():
    string=dict(type='string');ids=dict(type='array',items=string)
    condition=obj(dict(applicability=enum('none','present','unknown'),expression=enum('not_applicable','preserved','missing','misattached','extended','uncertain'),instance=enum('not_claimed','satisfied','missing','uncertain'),source_ids=ids,answer_ids=ids,reason=string))
    nullable=lambda value:dict(anyOf=[enum(NULL),value])
    row=obj(dict(status=enum('supported','contradicted','insufficient_evidence','not_assessable'),basis_ids=ids,reason=string,gap_answer_ids=ids,conditions=condition,inference=enum('preserved','unsupported','uncertain'),objection=nullable(obj(dict(kind=enum('fidelity','classification','uncertain'),reason=string))),repair=nullable(obj(dict(basis_id=string,replacement=string))),requires_authoritative_source=dict(type='boolean')))
    return obj(dict(judgments=dict(type='array',items=row)))


def specification():
    return dict(type='function',function=dict(name=NAME,strict=True,description='Submit this review result only; this function performs no external action.',parameters=schema()))


def map_null(value,*,encode=False):
    """Bijection on valid business rows; never fill missing fields or repair invalid rows."""
    result=deepcopy(value)
    if type(result) is dict and type(result.get('judgments')) is list:
        for row in result['judgments']:
            if type(row) is not dict:continue
            for key in ('objection','repair'):
                if key not in row:continue
                if encode and row[key] is None:row[key]=NULL
                elif not encode and row[key]==NULL:row[key]=None
    return result


def validate_response(response):
    ec=ErrorCollector(VERSION);t=response.result_transport
    if not ec.check(type(t) is dict and t.get('version')==VERSION,'$.result_transport','result_tool_transport_required'):ec.finish()
    ec.check(not t.get('envelope_error'),'$.response','unambiguous_tool_envelope_required')
    calls=t.get('tool_calls');single=type(calls) is list and len(calls)==1
    ec.check(single,'$.tool_calls','exactly_one_result_tool_required')
    ec.check(response.finish_reason=='tool_calls','$.finish_reason','tool_calls_finish_required')
    content=t.get('content');ec.check(content is None or type(content) is str and not content.strip(),'$.content','mixed_text_and_tool_arguments_forbidden')
    if single:
        c=calls[0];f=c.get('function') if type(c) is dict else None
        ec.check(type(c) is dict and type(c.get('id')) is str and bool(c['id']) and c.get('type')=='function','$.tool_calls[0]','tool_call_identity_required')
        ec.check(type(f) is dict and f.get('name')==NAME,'$.tool_calls[0].function.name','fixed_result_tool_required')
        ec.check(type(f) is dict and type(f.get('arguments')) is str and f['arguments']==response.text,'$.tool_calls[0].function.arguments','raw_arguments_required')
    ec.finish()
