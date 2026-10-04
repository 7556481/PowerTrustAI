"""V9.2: one selectable namespace per request, one correction for the whole stage."""
from copy import deepcopy
from dataclasses import asdict,replace
import json
import hashlib
from agents import verification_contract_v9 as joint
from agents.verification_contract_v8 import baseline,mark,system_for,projected_snapshot
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

PROMPT_VERSION='evidence-verification-v9.2-single-namespace-basis-target'
CONTRACT_VERSION='evidence-verification-output-v9.2'

def body_snapshot(inputs):
    """Full original Evidence body, but explicitly omit prior-review request context."""
    value=asdict(inputs.generation_snapshot) if joint.full_delivered(inputs) else projected_snapshot(inputs)
    if value is None:return None
    omitted=[];kept=[]
    for i,text in enumerate(value['answer_requirements']):
        if text.lstrip().startswith('{'):
            omitted.append({'requirement_index':i,'sha256':hashlib.sha256(text.encode()).hexdigest(),
                'reason':'prior_review_context_not_current_selectable_evidence','chars':len(text)})
        else:kept.append(text)
    value['answer_requirements']=kept
    value['nonbody_context_omissions']=omitted
    value['delivery_scope']='original_evidence_bodies_and_input_fields; NOT complete prior reviewer/model context'
    return value

def model_wire(inputs):
    wire=baseline(inputs)
    missing={} if joint.full_delivered(inputs) else {c.claim_id:tuple(i for i,p in enumerate(c.components) if p.category=='input_evidence_coverage') for c in inputs.claims}
    wire['findings']=[f for f in wire['findings'] if len(missing.get(f['claim_id'],()))<len(f['component_reviews'])]
    for f in wire['findings']:f['component_reviews']=[r for r in f['component_reviews'] if r['component_index'] not in missing.get(f['claim_id'],())]
    return wire,missing

async def run(agent,inputs):
    if current_budget() is None:
        with model_scope(ModelBudget(2*(1+len(inputs.answer.citations)))):return await run(agent,inputs)
    version3=agent.schema_version in (11,12)
    standalone=agent.schema_version==12
    prompt_version='evidence-verification-v9.3-target-fidelity' if version3 else PROMPT_VERSION
    contract_version='evidence-verification-output-v9.3' if version3 else CONTRACT_VERSION
    if standalone:
        from agents.review_templates_v3 import PROMPT_VERSION as prompt_version,CONTRACT_VERSION as contract_version
    start=len(current_budget().records);scopes=joint.catalog(inputs,contract_version);wire,missing=model_wire(inputs)
    base_parse=lambda v:joint.parse(v,inputs,scopes,prompt_version='evidence-verification-v9.3-target-fidelity' if standalone else prompt_version)
    def parse(v):
        if not version3:return base_parse(v)
        from services.review_fidelity import parse as fidelity_parse
        result=fidelity_parse(v,inputs,base_parse,strict_bindings=standalone)
        if standalone:
            result=replace(result,prompt_version=prompt_version)
            result=replace(result,consistency_checks=check_verification_quantities(result,version='quantity-enumeration-v1.2'))
            validate_review(result,inputs.answer,inputs.claims,result.evidence,True)
        return result
    if version3:
        for f in wire['findings']:
            claim=next(c for c in inputs.claims if c.claim_id==f['claim_id'])
            for r in f['component_reviews']:
                r['semantic_review']={'fidelity':'uncertain','assertion_role':claim.assertion_role,
                    'verification_obligation':claim.component_obligations[r['component_index']],
                    'rationale':'model_execution_incomplete; equivalence not established'}
    combined=parse(wire);issues=[];correction_used=False
    for index,scope in enumerate(scopes):
        citation=None if index==0 else index-1;group='findings' if citation is None else 'citation_reviews'
        if citation is None and not wire[group]:continue
        selected={group:deepcopy(wire[group] if citation is None else [wire[group][citation]])}
        def strict(value):
            ec=ErrorCollector('evidence_verification_v9_2');ec.fields(value,{group},set(),'$')
            if not ec.check(type(value.get(group)) is list,'$.'+group,'array_required'):ec.finish()
            if citation is not None:
                ec.check(len(value[group])==1 and value[group][0].get('citation_index')==citation,'$.citation_reviews','only_this_original_citation_allowed')
            ec.finish();expanded=deepcopy(wire)
            if citation is None:expanded[group]=value[group]
            else:expanded[group][citation]=value[group][0]
            return parse(expanded)
        isolation=WireIsolation(selected,strict,{group:'claim_id' if citation is None else 'citation_index'},mark)
        payload={'section':'SCOPED_REVIEW_DATA_UNTRUSTED','question':inputs.request.question,'answer':asdict(inputs.answer),**scope.payload()}
        if citation is None:
            payload.update(claims=[asdict(c) for c in inputs.claims if c.claim_id in {f["claim_id"] for f in wire["findings"]}],ANSWER_ANCHORS=anchors(inputs.answer),
                MODEL_COMPONENT_INDEXES={c.claim_id:[i for i in range(len(c.components)) if i not in missing.get(c.claim_id,())] for c in inputs.claims},
                PROGRAM_OWNED_MISSING_COMPONENTS=missing,METADATA_FIELDS={e.evidence_id:metadata_fields(e) for e in inputs.seed_evidence},
                METADATA_ORIGINS={e.evidence_id:{k:('index_maintenance_information' if k in ('applicability','source_type') else 'index_or_user_source_manifest_unverified_against_body') for k in metadata_fields(e)} for e in inputs.seed_evidence},
                TOOL_RESULTS=[asdict(t) for t in inputs.tool_results],DELIVERY_RECORD=inputs.delivery_summary,
                FULL_INPUT_DELIVERY={'snapshot_saved':inputs.generation_snapshot is not None,'full_body_delivered':joint.full_delivered(inputs),'metadata_only':inputs.generation_snapshot is not None and not joint.full_delivered(inputs)},
                GENERATION_INPUT_SNAPSHOT=body_snapshot(inputs))
            instruction=joint.SYSTEM+'''
CURRENT V9.2 request overrides joint root: root EXACT findings ONLY. The ONLY body IDs
are this request's QUOTE_CANDIDATES, one namespace. No original citations are reviewed here.
component_basis_targets are frozen extractor judgments; if a target/category is semantically wrong,
return explicit classification_issue and not_assessable, never supported/contradicted.
Document-body applicability, including a document's voluntary disclaimer, needs body evidence.
An index field may support an INDEX statement, not "PDF explicitly states ...".
Complete legal disagreement example:
{"findings":[{"claim_id":"actual-claim","rationale":"Assigned category cannot represent the assertion.",
"applicability_conditions":[],"bases":[],"component_reviews":[{"component_index":0,"status":"not_assessable",
"basis_indexes":[],"rationale":"Body content was categorized as index metadata.",
"classification_issue":{"suggested_category":"technical_fact","rationale":"This asserts a printed body statement."}}]}]}.
For mathematical_relation, choose current successful calculation result ID only if it verifies the
exact normalized scalar equality. A unit-category assertion is NOT a unit conversion.
Full original Evidence bodies may be delivered while prior reviewer request context is omitted.
The snapshot delivery_scope and nonbody_context_omissions bound coverage; do not claim the
complete original MODEL MESSAGE was delivered or reviewed, or reuse old reviewer basis IDs.
Unsupported or nonmatching evidence permits insufficient_evidence with [].
'''
            if version3:
                from services.review_fidelity import SYSTEM as fidelity_system
                instruction+=fidelity_system
        else:
            c=inputs.answer.citations[citation];payload['original_citation']={'citation_index':citation,'answer_text':inputs.answer.text[c.start_offset:c.end_offset],'evidence_ids':c.evidence_ids}
            instruction=system_for('original_citation')+'''
CURRENT V9.2 root EXACT citation_reviews, ONLY this index. Only text_excerpt with supplied
quote_id is allowed, [] legal. There are NO input_snapshot_reference, calculation_result_reference,
metadata_reference or answer_text_reference choices in this original-citation request.
Whole-answer statements may be correct via other evidence while THIS citation is insufficient.
No extra fields, no classification_issue on citation items. Legal response:
{"citation_reviews":[{"citation_index":0,"status":"insufficient_evidence","rationale":"Bound body does not support this qualified substring.","applicability_conditions":[],"bases":[]}]}.
'''
        if standalone:
            from agents.review_templates_v3 import template
            instruction=template('independent' if citation is None else 'original_citation')
        path=None if agent.diagnostics is None else agent.diagnostics.save_scope(payload);before=len(current_budget().records)
        result=None
        try:
            result,_=await structured_request(agent.client,(ModelMessage('system',instruction),ModelMessage('user',json.dumps(payload,ensure_ascii=False))),
                prompt_version,isolation.parse,diagnostics=agent.diagnostics,response_contract_version=contract_version,candidate_catalog_path=path,max_corrections=0 if correction_used else 1)
        except Exception as exc:
            if not getattr(exc,'code',None):raise
            result=getattr(exc,'partial_output',None);issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,exc.code,'Scoped semantic check incomplete; valid peers retained'))
            if exc.code in ('MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED'):break
        finally:
            correction_used=correction_used or any(r.correction for r in current_budget().records[before:])
        if result is None:continue
        if citation is None:combined=replace(combined,findings=result.findings)
        else:combined=replace(combined,citation_reviews=tuple(result.citation_reviews[i] if i==citation else c for i,c in enumerate(combined.citation_reviews)))
    from services.evidence_scope import citation_coverage
    combined=replace(combined,execution_issues=tuple(issues),citation_reviews=tuple(replace(c,
        partial_claim_ids=citation_coverage(inputs.answer,inputs.claims,c.citation_index,combined.findings)[0],
        coverage_issues=citation_coverage(inputs.answer,inputs.claims,c.citation_index,combined.findings)[1]) for c in combined.citation_reviews))
    combined=replace(combined,consistency_checks=check_verification_quantities(combined,version='quantity-enumeration-v1.2'),
        model_records=tuple(r for r in current_budget().records[start:] if r.prompt_version==prompt_version))
    validate_review(combined,inputs.answer,inputs.claims,combined.evidence,True);return combined
