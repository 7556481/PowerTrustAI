"""Read-only output-carrier accounting, separate from the frozen business reference."""
from collections import Counter
from evaluation.public_review_validation_trial_v1 import read,write
from evaluation.review_simple_analysis_v1 import analyze
from services.review_simple_tool_v1 import PROMPT
from model_adapter.strict_review_tool import VERSION,specification,NAME


def mechanism(summary):
    records=[r for out in summary['outputs'].values() for r in out.get('model_records',[]) if r['prompt_version']==PROMPT]
    sent=[s for s in summary['send_log'] if s['parameters'].get('result_tool') is not None]
    values=Counter(sent_tool_requests=len(sent),recorded_tool_attempts=len(records))
    constraints=Counter();raw=[]
    for r in records:
        values['initial_requests']+=not r['correction'];values['corrections']+=r['correction']
        values['initial_valid']+=not r['correction'] and r['output_status']=='valid_structure'
        values['finally_valid_responses']+=r['output_status']=='valid_structure'
        values['invalid_output_attempts']+=r['output_status'] in ('invalid_structure','invalid_model_response')
        values['request_rejections']+=r.get('error_code')=='MODEL_REQUEST_REJECTED'
        values['truncated']+=r.get('finish_reason') in ('length','max_tokens')
        diagnostic=r.get('validation_error')
        if diagnostic:constraints.update({x['constraint'] for x in diagnostic.get('errors',[diagnostic])})
        t=r.get('result_transport')
        if not t:continue
        values['returned_tool_envelopes']+=1;calls=t.get('tool_calls')
        fn=calls[0].get('function') if type(calls) is list and len(calls)==1 else None
        good=type(fn) is dict and fn.get('name')==NAME and r['finish_reason']=='tool_calls' and not (t.get('content') or '').strip() and not t.get('envelope_error')
        values['expected_single_tool_envelopes']+=good
        values['identifiable_raw_parameters_saved']+=type(calls) is list and bool(calls) and all(type(c.get('function')) is dict and type(c['function'].get('arguments')) is str for c in calls)
        raw.append(dict(invocation_id=r.get('invocation_id'),call=r['call_number'],request_id=t.get('request_id'),tool_ids=[c.get('id') for c in calls] if type(calls) is list else [],finish_reason=r.get('finish_reason'),envelope_error=t.get('envelope_error'),diagnostic_gap=t.get('diagnostic_gap')))
    values['all_sent_tools_match_frozen_schema']=all(s['parameters']['result_tool']==specification() for s in sent)
    return dict(version=VERSION,counts=values,constraint_failed_request_counts=constraints,request_associations=raw,note='Counts are requests/envelopes, not semantic correctness. Raw parameters remain in predictions and private archives. No labels extracted from invalid arguments.')


def report(local,public):
    business=analyze(local,public)
    write(public/'output-mechanism.json',mechanism(read(local/'batch/summary.json')))
    return business
