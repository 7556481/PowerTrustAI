"""Shared bounded scope execution; protocol/catalog owns semantic parsing.

No graph, provider, retriever, policy or independent resource lifetime here.
Historical compact and internal-flow candidate share this single request loop.
"""
from copy import deepcopy
from dataclasses import asdict,replace
import asyncio,json
from core.models import ExecutionIssue,ExecutionStatus
from core.validation import validate_review
from services.evidence_scope import citation_coverage
from services.validation_diagnostics import ErrorCollector
from services.review_isolation import WireIsolation
from services.structured_model import structured_request
from services.citation_workload import CitationWorkload,pack
from model_adapter.contracts import ModelMessage
from model_adapter.runtime import current_budget,model_scope,ModelBudget

async def execute(agent,inputs,*,catalog,prompt_version,contract_version,instruction):
    if current_budget() is None:
        with model_scope(ModelBudget((3 if hasattr(catalog,"prepare_stage") else 2)+len(inputs.answer.citations))):return await execute(agent,inputs,catalog=catalog,prompt_version=prompt_version,contract_version=contract_version,instruction=instruction)
    if catalog is None:
        from agents.verification_contract_v14 import ReviewCatalog
        cat=ReviewCatalog(inputs)
    else:cat=catalog
    start=len(current_budget().records);current=deepcopy(cat.rows);accepted=set();issues=[];corrected=False
    facts=[t for t,x in cat.targets.items() if x['kind']=='fact'];citations=[t for t,x in cat.targets.items() if x['kind']=='citation']
    groups,rejected=pack(citations,cat.payload,instruction,agent.citation_workload or CitationWorkload())
    if rejected:issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,'REVIEW_MESSAGE_CAPACITY_EXCEEDED','Complete citation scopes exceed capacity; no truncation'))
    for group in ([tuple(facts)] if facts else [])+list(groups):
        baseline={'judgments':[deepcopy(current[t]) for t in group]}
        def strict(value):
            ec=ErrorCollector(contract_version);ec.fields(value,{'judgments'},set(),'$');items=value.get('judgments') if isinstance(value,dict) else None
            ec.check(type(items) is list,'$.judgments','judgment_array_required');ids=[r.get('target_id') for r in items if isinstance(r,dict)] if isinstance(items,list) else []
            ec.check(len(ids)==len(group) and all(type(t) is str for t in ids) and set(ids)==set(group),'$.judgments','exact_target_coverage_required');ec.finish()
            rows=deepcopy(current)
            for r in items:rows[r['target_id']]=r
            return cat.project(rows)
        isolation=WireIsolation(baseline,strict,{'judgments':'target_id'},cat.mark);payload=cat.payload(group)
        path=None if agent.diagnostics is None else agent.diagnostics.save_scope(payload);before=len(current_budget().records)
        try:
            if group==tuple(facts) and hasattr(cat,'prepare_stage'):
                await cat.prepare_stage(agent,group,max_corrections=0 if corrected else 1)
                corrected=corrected or any(r.correction for r in current_budget().records[before:])
                payload=cat.payload(group)
            parse_response=(lambda value:isolation.parse(cat.decode_wire(value,group))) if hasattr(cat,'decode_wire') else isolation.parse
            await structured_request(agent.client,(ModelMessage('system',instruction),ModelMessage('user',json.dumps(payload,ensure_ascii=False))),prompt_version,parse_response,
                diagnostics=agent.diagnostics,response_contract_version=contract_version,candidate_catalog_path=path,max_corrections=0 if corrected else 1,
                correction_context=lambda value,diagnostic:cat.correction_context(group,value,diagnostic),
                correction_instruction=getattr(cat,"correction_instruction",None),
                max_message_chars=None if group==tuple(facts) else (agent.citation_workload or CitationWorkload()).max_correction_message_chars)
        except asyncio.CancelledError as exc:
            if catalog is not None:
                for (_,tid),row in isolation.accepted.items():current[tid]=row;accepted.add(tid)
                partial=cat.mark(cat.project(current),[('judgments',t) for t in cat.targets if t not in accepted],[])
                exc.partial_output=replace(partial,model_records=tuple(r for r in current_budget().records[start:] if r.prompt_version==prompt_version))
                if agent.diagnostics is not None:
                    agent.diagnostics.save_scope({'event':'fact_flow_cancelled','partial_output':asdict(exc.partial_output)})
            raise
        except Exception as exc:
            if not getattr(exc,'code',None):raise
            issues.append(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,exc.code,'Compact review incomplete; valid targets retained'))
            if exc.code in ('MODEL_AUTHENTICATION_FAILED','MODEL_INSUFFICIENT_BALANCE','MODEL_SERVICE_UNAVAILABLE','MODEL_CONNECTION_FAILED')+getattr(cat,'fatal_request_codes',()):break
        finally:
            corrected=corrected or any(r.correction and (catalog is None or r.prompt_version==prompt_version) for r in current_budget().records[before:])
            for (_,tid),row in isolation.accepted.items():current[tid]=row;accepted.add(tid)
    out=cat.mark(cat.project(current),[('judgments',t) for t in cat.targets if t not in accepted],[])
    out=replace(out,execution_issues=tuple(issues),model_records=tuple(r for r in current_budget().records[start:] if r.prompt_version==prompt_version),prompt_version=prompt_version)
    from services.quantity_checks import check_verification_quantities
    out=replace(out,consistency_checks=check_verification_quantities(out,version='quantity-enumeration-v1.2'),citation_reviews=tuple(replace(c,partial_claim_ids=citation_coverage(inputs.answer,inputs.claims,c.citation_index,out.findings)[0],coverage_issues=citation_coverage(inputs.answer,inputs.claims,c.citation_index,out.findings)[1]) for c in out.citation_reviews))
    validate_review(out,inputs.answer,inputs.claims,out.evidence,True);return out
