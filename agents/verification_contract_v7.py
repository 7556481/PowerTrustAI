"""Program-owned missing-snapshot premises; semantic judgments remain model-owned."""
from copy import deepcopy
from dataclasses import replace
from agents import verification_contract_v6 as v6
from core.validation import validate_review
from services.validation_diagnostics import ErrorCollector
from services.quantity_checks import check_verification_quantities

PROMPT_VERSION="evidence-verification-v7.1-full-input-preconditions"
CONTRACT_VERSION="evidence-verification-output-v7"


def missing_parts(inputs, *, legacy=False):
    return {} if inputs.generation_snapshot is not None and (legacy or inputs.generation_snapshot.snapshot_version=="generation-full-input-v2") else {
        c.claim_id:tuple(i for i,p in enumerate(c.components) if p.category=="input_evidence_coverage") for c in inputs.claims}


def prepare_payload(payload, inputs):
    missing=missing_parts(inputs)
    payload["PROGRAM_COMPONENT_RESULTS"]=[{"claim_id":c.claim_id,"component_index":i,"status":"not_assessable","reason_code":"missing_input_snapshot"}
        for c in inputs.claims for i in missing.get(c.claim_id,())]
    payload["MODEL_COMPONENT_INDEXES"]={c.claim_id:[i for i in range(len(c.components)) if i not in missing.get(c.claim_id,())] for c in inputs.claims}
    payload["claims"]=[dict(c,components=[dict(p,component_index=i) for i,p in enumerate(c["components"]) if i not in missing.get(c["claim_id"],())])
        for c in payload["claims"] if payload["MODEL_COMPONENT_INDEXES"][c["claim_id"]]]
    return payload


def system_prompt(rules):
    return v6.system_prompt(rules)+"""
V7 overrides component coverage for missing complete input snapshots:
Evidence-only-v1 snapshots retain original document input but not the full question,
user context, engineering quantities or answer requirements. They are NOT full-input-v2.
Return findings ONLY for claim IDs in claims. Cover ONLY MODEL_COMPONENT_INDEXES per
claim, using original component_index values (possibly sparse, never renumber).
PROGRAM_COMPONENT_RESULTS are deterministic premises, not model judgments. Do NOT
return them, change their statuses, classify them or assign any basis to them.
All other components/citations continue normally. The program explicitly merges its
missing_input_snapshot not_assessable results and aggregates all parts.
Full-input-v2 present: all components remain model-reviewed as before. Do not infer actual
computation from text support or user-provided data. Exact quote location is not support.
"""


def parse_v7(value, inputs, *, legacy=False):
    ec=ErrorCollector();ec.fields(value,{"findings","citation_reviews"},set(),"$")
    if not isinstance(value,dict):ec.finish()
    missing=missing_parts(inputs,legacy=legacy);allowed={c.claim_id:set(range(len(c.components)))-set(missing.get(c.claim_id,())) for c in inputs.claims}
    allowed={k:v for k,v in allowed.items() if v}
    items=value.get("findings");seen=set()
    if ec.check(type(items) is list,"$.findings","expected_array"):
        for i,f in enumerate(items):
            p=f"$.findings[{i}]"
            if not ec.fields(f,{"claim_id","rationale","applicability_conditions","bases","component_reviews"},{"dimension_findings"},p):continue
            cid=f["claim_id"]
            if not ec.check(type(cid) is str and cid in allowed,p+".claim_id","model_must_review_only_eligible_claims"):continue
            ec.check(cid not in seen,p,"duplicate_review_not_allowed");seen.add(cid)
            reviews=f["component_reviews"];indices=[]
            if not ec.check(type(reviews) is list,p+".component_reviews","expected_array"):continue
            for j,r in enumerate(reviews):
                rp=f"{p}.component_reviews[{j}]"
                if not ec.fields(r,{"component_index","status","basis_indexes","rationale"},{"classification_issue"},rp):continue
                ix=r["component_index"]
                if not ec.check(type(ix) is int and ix in allowed[cid],rp+".component_index","program_owned_missing_input_component_forbidden"):
                    ec.errors[-1].update(allowed_component_indexes=sorted(allowed[cid]),processing_options=["omit_program_owned_component","review_only_remaining_model_components"])
                indices.append(ix)
            ec.check(all(type(n) is int for n in indices) and len(indices)==len(set(str(n) for n in indices)) and set(str(n) for n in indices)==set(str(n) for n in allowed[cid]),p+".component_reviews","all_model_components_exactly_once")
        ec.check(seen==set(allowed),"$.findings","each_eligible_claim_exactly_once")
    ec.finish();expanded=deepcopy(value);byid={f["claim_id"]:f for f in expanded["findings"]}
    for c in inputs.claims:
        if c.claim_id not in byid:
            byid[c.claim_id]={"claim_id":c.claim_id,"rationale":"Program premise: missing_input_snapshot","applicability_conditions":[],"bases":[],"component_reviews":[]}
        for ix in missing.get(c.claim_id,()):
            byid[c.claim_id]["component_reviews"].append({"component_index":ix,"status":"not_assessable","basis_indexes":[],"rationale":"missing_input_snapshot: complete original generation input was not saved; later retrieval cannot replace it."})
    expanded["findings"]=[byid[c.claim_id] for c in inputs.claims]
    output=v6.parse_v6(expanded,inputs)
    findings=[];prompt_version="evidence-verification-v7-program-preconditions" if legacy else PROMPT_VERSION
    for f in output.findings:
        claim=next(c for c in inputs.claims if c.claim_id==f.claim_id)
        ids={claim.components[i].component_id for i in missing.get(f.claim_id,())}
        findings.append(replace(f,checker_version=prompt_version,component_reviews=tuple(replace(r,origin="program_precondition",reason_code="missing_input_snapshot") if r.component_id in ids else r for r in f.component_reviews)))
    output=replace(output,findings=tuple(findings),prompt_version=prompt_version)
    output=replace(output,consistency_checks=check_verification_quantities(output,version="quantity-enumeration-v1" if legacy else "quantity-enumeration-v1.1"))
    validate_review(output,inputs.answer,inputs.claims,output.evidence,True)
    return output


def execution_incomplete(inputs,issue):
    missing=missing_parts(inputs)
    findings=[{"claim_id":c.claim_id,"rationale":"Model review execution incomplete; no semantic support judgment inferred.",
        "applicability_conditions":[],"bases":[],"component_reviews":[{"component_index":i,"status":"not_assessable","basis_indexes":[],
        "rationale":"model_execution_incomplete: this part was not reviewed."} for i in range(len(c.components)) if i not in missing.get(c.claim_id,())]}
        for c in inputs.claims if len(missing.get(c.claim_id,()))<len(c.components)]
    output=parse_v7({"findings":findings,"citation_reviews":[{"citation_index":i,"status":"not_assessable",
        "rationale":"Model review execution incomplete; original citation not judged.","applicability_conditions":[],"bases":[]} for i in range(len(inputs.answer.citations))]},inputs)
    return replace(output,execution_issues=(issue,),findings=tuple(replace(f,component_reviews=tuple(
        r if r.origin=="program_precondition" else replace(r,origin="execution_incomplete",reason_code="model_execution_incomplete")
        for r in f.component_reviews)) for f in output.findings))
