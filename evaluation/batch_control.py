"""Submission-only batch safety; execution remains in the existing backend/Harness."""
import re

SHARED_CODES={'CONFIGURATION_UNAVAILABLE','SERVICE_UNAVAILABLE','SERVICE_EXECUTION_FAILED',
    'RUN_STORAGE_FAILED','DIAGNOSTIC_STORAGE_FAILED','REVIEW_INPUT_CONTRACT_ERROR',
    'MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED'}
ENGINE_STAGES={'harness','service','generation','claim_extraction','evidence_verification','power_domain_review','revision'}
PROGRAM_EXCEPTIONS={'AttributeError','ImportError','ModuleNotFoundError','NameError','ReviewInputContractError'}

def classify(result,*,configuration_matches=True):
    if not configuration_matches:return {'shared':True,'reason':'frozen_configuration_mismatch','evidence':[]}
    execution=result.get('execution',result)
    issues=execution.get('execution_issues',result.get('execution_issues',[]))
    if execution.get('error_code') in SHARED_CODES:
        return {'shared':True,'reason':'shared_service_failure','evidence':[{'code':execution['error_code']}]}
    for issue in issues:
        code=issue.get('code');stage=issue.get('component');message=issue.get('message','')
        match=re.match(r'^([A-Za-z]+(?:Error|Exception)):',message);exception=match[1] if match else None
        if code in SHARED_CODES:
            return {'shared':True,'reason':'shared_configuration_or_service_failure','evidence':[{'stage':stage,'code':code,'exception_type':exception}]}
        if code=='EXECUTION_FAILURE' and stage in ENGINE_STAGES and (exception in PROGRAM_EXCEPTIONS or exception=='TypeError' and any(s in message for s in ('input contract','unexpected keyword argument','required positional argument'))):
            return {'shared':True,'reason':'shared_assembly_or_input_contract_failure','evidence':[{'stage':stage,'code':code,'exception_type':exception}]}
    return {'shared':False,'reason':'case_local_result','evidence':[]}

async def run_fixed(cases,*,submit,collect,persist,configuration_matches=lambda result:True):
    """Never resubmit. Persist acceptance/partial result before the stop decision.

    Unknown submit/collect errors stop because acceptance or shared service state
    cannot be established. No cap is introduced; existing per-run limits apply.
    """
    records=[]
    for case in cases:
        ident=case['id']
        try:
            accepted=await submit(case['input'])
        except Exception as exc:
            record={'case_id':ident,'phase':'submit','stop':True,'reason':'submission_state_unknown','exception_type':type(exc).__name__}
            persist(ident,'control',record);records.append(record);break
        try:persist(ident,'accepted',accepted)
        except Exception as exc:
            records.append({'case_id':ident,'accepted':accepted,'phase':'persist_acceptance','stop':True,
                'reason':'collection_persistence_failure','exception_type':type(exc).__name__})
            break # Acceptance remains in the returned record; never submit again.

        try:
            result=await collect(accepted)
        except Exception as exc:
            record={'case_id':ident,'accepted':accepted,'phase':'collect','stop':True,'reason':'shared_service_or_collection_failure','exception_type':type(exc).__name__}
            persist(ident,'control',record);records.append(record);break
        try:persist(ident,'result',result)
        except Exception as exc:
            records.append({'case_id':ident,'accepted':accepted,'partial_result':result,'phase':'persist_result','stop':True,
                'reason':'collection_persistence_failure','exception_type':type(exc).__name__})
            break # Preserve the result for the caller's fallback archive.

        decision=classify(result,configuration_matches=configuration_matches(result))
        record={'case_id':ident,'accepted':accepted,'stop':decision['shared'],'decision':decision}
        persist(ident,'control',record);records.append(record)
        if record['stop']:break
    return records
