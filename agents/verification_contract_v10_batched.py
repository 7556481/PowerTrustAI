"""Schema13: bounded original-citation groups, isolated items, one stage correction."""
from copy import deepcopy
from dataclasses import asdict,replace
import json
from agents import verification_contract_v9 as joint
from agents.verification_contract_v8 import mark
from services.review_isolation import WireIsolation
from services.structured_model import structured_request
from services.validation_diagnostics import ErrorCollector
from services.answer_anchors import anchors
from services.evidence_scope import metadata_fields
from services.quantity_checks import check_verification_quantities
from model_adapter.contracts import ModelMessage
from model_adapter.runtime import current_budget,ModelBudget,model_scope
from core.models import ExecutionIssue,ExecutionStatus
from core.validation import validate_review

PROMPT_VERSION='evidence-verification-v9.6-explicit-frozen-stance'
CONTRACT_VERSION='evidence-verification-output-v9.5'

def original_template():
    from agents.review_templates_v3 import ORIGINAL
    return ORIGINAL.replace('EXACTLY one item for this index.',
        'EXACTLY one item for EVERY supplied citation_index, in supplied order.')+"""
Multiple ORIGINAL_CITATION_SCOPES may share this request. Each has its own citation_index,
bound answer substring and QUOTE_CANDIDATES. Select IDs ONLY from THAT item's scope.
Never borrow a candidate from any other item, even if its Evidence or text is identical.
Keep each rationale concise; cover every item. Other/new independent support does not cure it.
"""

def citation_payload(answer,question,scopes,indexes):
    return {'section':'BOUNDED_ORIGINAL_CITATIONS_UNTRUSTED','question':question,
        'answer_id':answer.answer_id,'answer_version':answer.version,
        'ORIGINAL_CITATION_SCOPES':[dict(scopes[i+1].payload(),citation_index=i,
            answer_text=answer.text[answer.citations[i].start_offset:answer.citations[i].end_offset]) for i in indexes]}

from agents.verification_contract_v9_scoped import body_snapshot, model_wire

async def run(agent,inputs):
    if current_budget() is None:
        with model_scope(ModelBudget(2+len(inputs.answer.citations))):return await run(agent,inputs)
    from services.citation_workload import CitationWorkload, pack, messages_size
    from agents.review_templates_v3 import INDEPENDENT
    from services.review_fidelity import FROZEN_BINDING_INSTRUCTIONS
    limits=agent.citation_workload or CitationWorkload()
    prompt_version= PROMPT_VERSION+'-fact-delivery-v1' if inputs.fact_retrieval_bindings else PROMPT_VERSION
    contract_version=CONTRACT_VERSION
    original_instruction=original_template()
    start=len(current_budget().records);scopes=joint.catalog(inputs,contract_version);wire,missing=model_wire(inputs)
    base_parse=lambda v:joint.parse(v,inputs,scopes,prompt_version='evidence-verification-v9.3-target-fidelity')
    def parse(v):
        from services.review_fidelity import parse as fidelity_parse
        result=fidelity_parse(v,inputs,base_parse,strict_bindings=True)
        from services.fact_delivery import validate_result
        result=validate_result(result,inputs)
        result=replace(result,prompt_version=prompt_version)
        result=replace(result,consistency_checks=check_verification_quantities(result,version='quantity-enumeration-v1.2'))
        validate_review(result,inputs.answer,inputs.claims,result.evidence,True)
        return result
    for f in wire['findings']:
        claim=next(c for c in inputs.claims if c.claim_id==f['claim_id'])
        for r in f['component_reviews']:
            r['semantic_review']={'fidelity':'uncertain','assertion_role':claim.assertion_role,
                'verification_obligation':claim.component_obligations[r['component_index']],
                'rationale':'model_execution_incomplete; equivalence not established'}
    combined=parse(wire);issues=[];correction_used=False;shortfall_reported=False
    def batch_payload(indexes):
        return citation_payload(inputs.answer,inputs.request.question,scopes,indexes)
    groups,rejected=pack(range(len(inputs.answer.citations)),batch_payload,original_instruction,limits)
    if rejected:
        issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,
            'REVIEW_MESSAGE_CAPACITY_EXCEEDED',
            'Complete original citation scope exceeds capacity; unprocessed citation_indexes='+str(list(rejected))))
    work=[None]+list(groups)
    for citation in work:
        group='findings' if citation is None else 'citation_reviews'
        if citation is None and not wire[group]:continue
        selected={group:deepcopy(wire[group] if citation is None else [wire[group][i] for i in citation])}
        def strict(value):
            ec=ErrorCollector('evidence_verification_v9_2');ec.fields(value,{group},set(),'$')
            if not ec.check(type(value.get(group)) is list,'$.'+group,'array_required'):ec.finish()
            if citation is not None:
                ec.check(len(value[group])==len(citation) and {v.get('citation_index') for v in value[group] if type(v) is dict}==set(citation),'$.citation_reviews','exact_batch_original_citation_indexes_required')
            ec.finish();expanded=deepcopy(wire)
            if citation is None:expanded[group]=value[group]
            else:
                for item in value[group]:expanded[group][item['citation_index']]=item
            return parse(expanded)
        isolation=WireIsolation(selected,strict,{group:'claim_id' if citation is None else 'citation_index'},mark)
        payload={'section':'SCOPED_REVIEW_DATA_UNTRUSTED','question':inputs.request.question,'answer':asdict(inputs.answer),**scopes[0].payload()}
        if citation is None:
            payload.update(claims=[asdict(c) for c in inputs.claims if c.claim_id in {f["claim_id"] for f in wire["findings"]}],ANSWER_ANCHORS=anchors(inputs.answer),
                MODEL_COMPONENT_INDEXES={c.claim_id:[i for i in range(len(c.components)) if i not in missing.get(c.claim_id,())] for c in inputs.claims},
                PROGRAM_OWNED_MISSING_COMPONENTS=missing,METADATA_FIELDS={e.evidence_id:metadata_fields(e) for e in inputs.seed_evidence},
                METADATA_ORIGINS={e.evidence_id:{k:('index_maintenance_information' if k in ('applicability','source_type') else 'index_or_user_source_manifest_unverified_against_body') for k in metadata_fields(e)} for e in inputs.seed_evidence},
                TOOL_RESULTS=[asdict(t) for t in inputs.tool_results],DELIVERY_RECORD=inputs.delivery_summary,
                FULL_INPUT_DELIVERY={'snapshot_saved':inputs.generation_snapshot is not None,'full_body_delivered':joint.full_delivered(inputs),'metadata_only':inputs.generation_snapshot is not None and not joint.full_delivered(inputs)},
                GENERATION_INPUT_SNAPSHOT=body_snapshot(inputs))
        else:
            payload=batch_payload(citation);instruction=original_instruction
        if citation is None:
            instruction=INDEPENDENT + FROZEN_BINDING_INSTRUCTIONS
            from services.fact_delivery import payload as fact_payload, INSTRUCTION
            mapping=fact_payload(inputs,scopes[0])
            if mapping is not None:
                payload['FACT_EVIDENCE_DELIVERY']=mapping
                instruction+=INSTRUCTION
        messages=(ModelMessage('system',instruction),ModelMessage('user',json.dumps(payload,ensure_ascii=False)))
        if citation is not None and messages_size(messages)>limits.max_message_chars:
            issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,
                'REVIEW_MESSAGE_CAPACITY_EXCEEDED','Complete original citation group exceeds capacity; items remain unassessed'))
            continue
        remaining=current_budget().limit-current_budget().used
        # Known outstanding initial calls, NOT a guarantee about correction or later Revision.
        outstanding=sum(1 for item in work[work.index(citation):] if item is not None or wire['findings'])
        if remaining<outstanding and not shortfall_reported:
            issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,
                'REVIEW_WORKLOAD_BUDGET_SHORTFALL',
                'Known remaining initial review requests='+str(outstanding)+'; available calls='+str(remaining)+
                '; validated partial results retained; correction/Revision cost not yet known'))
            shortfall_reported=True
        if remaining==0:break
        path=None if agent.diagnostics is None else agent.diagnostics.save_scope(payload);before=len(current_budget().records)
        result=None
        try:
            result,_=await structured_request(agent.client,messages,
                prompt_version,isolation.parse,diagnostics=agent.diagnostics,response_contract_version=contract_version,candidate_catalog_path=path,max_corrections=0 if correction_used else 1,max_message_chars=None if citation is None else limits.max_correction_message_chars)
        except Exception as exc:
            if not getattr(exc,'code',None):raise
            result=getattr(exc,'partial_output',None);issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,exc.code,'Scoped semantic check incomplete; valid peers retained'))
            if exc.code in ('MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED'):break
        finally:
            correction_used=correction_used or any(r.correction for r in current_budget().records[before:])
        if result is None:continue
        if citation is None:combined=replace(combined,findings=result.findings)
        else:combined=replace(combined,citation_reviews=tuple(result.citation_reviews[i] if i in citation else c for i,c in enumerate(combined.citation_reviews)))
    from services.evidence_scope import citation_coverage
    combined=replace(combined,execution_issues=tuple(issues),citation_reviews=tuple(replace(c,
        partial_claim_ids=citation_coverage(inputs.answer,inputs.claims,c.citation_index,combined.findings)[0],
        coverage_issues=citation_coverage(inputs.answer,inputs.claims,c.citation_index,combined.findings)[1]) for c in combined.citation_reviews))
    combined=replace(combined,consistency_checks=check_verification_quantities(combined,version='quantity-enumeration-v1.2'),
        model_records=tuple(r for r in current_budget().records[start:] if r.prompt_version==prompt_version))
    validate_review(combined,inputs.answer,inputs.claims,combined.evidence,True);return combined
