"""Source supply/gap handling inside shared stages, never a second scheduler."""
import asyncio
import json
from dataclasses import asdict, replace
from time import perf_counter
from uuid import uuid4
from core.models import EvidenceBinding, FactRetrievalBinding, ExecutionStatus
from core.validation import require, merge_evidence
from harness.contracts import RetrievalRecord
from harness.retrieval import Delivery
from harness.fact_retrieval import objects
from rag.contracts import ContextOptions, RetrievalPurpose
from services.source_first_audit_v1 import VERSION


def enabled(execution):
    return execution.harness.audit_strategy in (VERSION,'source_first_audit_v2')


def strategy(execution):
    return getattr(getattr(execution,'harness',None),'audit_strategy',VERSION)


def mappings(execution, evidence):
    return tuple(FactRetrievalBinding(execution.answer.answer_id,execution.answer.version,
        c.claim_id,component,category,target,'',strategy(execution),None,execution.knowledge_version,
        'source_scope',delivered_evidence_ids=tuple(e.evidence_id for e in evidence))
        for c,component,category,target,query in objects(execution.claims))


async def prepare(ex):
    require(ex.retrieval is not None,'Source-first requires validating indexed Retriever')
    if not hasattr(ex,'source_first_roots'):
        require(ex.active_snapshot is not None,'Source-first requires actual or explicitly authored frozen input snapshot')
        ex.source_first_roots=ex.active_snapshot.evidence
        ex.source_first_original_snapshot=ex.active_snapshot.snapshot_id
    roots=ex.source_first_roots
    require(all(e.provenance is not None and e.provenance.knowledge_version==ex.knowledge_version for e in roots),
        'Source-first requires fixed index identity for each original source')
    # Whole fragments only. Reject oversized original delivery rather than silently
    # exposing unbounded original_citation bodies outside the source budget.
    limit=min(16000,ex.budget.max_retrieval_chars_per_call,
        ex.budget.max_retrieval_chars_total-ex.retrieval.chars)
    require(len(roots)<=12 and sum(len(e.text) for e in roots)<=limit,'Original source delivery exceeds frozen source budget')
    options=ContextOptions(min(2400,limit-sum(len(e.text) for e in roots)),6,1,True,'storage_order')
    started=perf_counter()
    remaining=min(ex.budget.step_timeout_seconds,ex.deadline-started)
    require(remaining>0,'Source supply deadline exhausted')
    context=await asyncio.wait_for(ex.harness.retriever.source_context(roots,ex.knowledge_version,options),remaining)
    # Reuse already acquired gap evidence across revision by identity only; a new
    # binding and new support judgment are always constructed for the new version.
    extra=getattr(ex,'source_first_extra',())
    bodies=merge_evidence(roots,tuple(i.evidence for i in context.items),extra)
    require(len(bodies)<=21 and sum(len(e.text) for e in bodies)<=limit,'Source supply including prior gaps exceeds frozen budget')
    await asyncio.wait_for(ex.harness.retriever.validate_evidence(bodies,ex.knowledge_version),
        min(ex.budget.step_timeout_seconds,max(.001,ex.deadline-perf_counter())))
    validated_ids={e.evidence_id for e in roots}
    ex.retrieval.user_ids-=validated_ids
    ex.bindings=tuple(replace(b,origin='index_saved_reference') if b.evidence_id in validated_ids and b.origin=='user_reference' else b for b in ex.bindings)
    ex.retrieval.chars+=sum(len(e.text) for e in bodies)
    ex.retrieval.known_evidence.update((e.evidence_id,e) for e in bodies)
    rid=uuid4().hex
    adjacent={i.evidence.evidence_id:i for i in context.items}
    prior={b.evidence_id:b for b in getattr(ex,'source_first_extra_bindings',())}
    bindings=[]
    for e in bodies:
        if e in roots:
            b=EvidenceBinding(e.evidence_id,'index_saved_reference','source_fidelity',ex.answer.version,rid)
        elif e.evidence_id in adjacent:
            b=EvidenceBinding(e.evidence_id,'index_adjacent_context','source_fidelity',ex.answer.version,rid,
                tuple(dict.fromkeys(link.core_evidence_id for link in adjacent[e.evidence_id].links)))
        else:
            require(e.evidence_id in prior,'Prior gap evidence lacks actual retrieval binding')
            b=replace(prior[e.evidence_id],answer_version=ex.answer.version)
        bindings.append(b)
    bindings=tuple(bindings)
    summary=RetrievalRecord(rid,'verification','',strategy(ex),ex.answer.version,ex.knowledge_version,
        ExecutionStatus.SUCCEEDED,'source_scope',core_evidence_ids=tuple(e.evidence_id for e in roots),
        context_evidence_ids=tuple(i.evidence.evidence_id for i in context.items),
        offered_chars=sum(len(e.text) for e in bodies),accepted_chars=sum(len(e.text) for e in bodies),
        cumulative_chars=ex.retrieval.chars,calls_used=ex.retrieval.calls,
        duration_ms=int((perf_counter()-started)*1000),context_omissions=context.omitted,
        reason=json.dumps(dict(scope='source_fidelity_and_task_completeness',external_cross_check='not_executed',
            original_snapshot=ex.source_first_original_snapshot,source_truth_verified=False)),
        answer_id=ex.answer.answer_id,fact_bindings=mappings(ex,bodies))
    ex.retrieval.records.append(summary)
    ex.evidence=merge_evidence(ex.evidence,bodies);ex.bindings+=bindings
    ex.vd=ex.dd=Delivery(bodies,bindings,None,summary)
    ex.v_evidence=ex.d_evidence=bodies;ex.v_bindings=ex.d_bindings=bindings
    ex.record('source_first_supply',ExecutionStatus.SUCCEEDED,started,summary.reason)


def gap_plan(ex):
    """Stable unit then existing component order; exact-query dedup, no big OR."""
    established={d.anchor_id for d in ex.verification.literal_defects}
    gaps=[]
    for unit in ex.verification.literal_reviews:
        if unit.status not in ('insufficient_evidence','not_assessable') or unit.anchor_id in established:continue
        found=False
        for c,component,category,target,query in objects(ex.claims):
            if c.start_offset>=unit.end_offset or c.end_offset<=unit.start_offset:continue
            if target not in ('technical_content','document_body'):continue
            found=True
            gaps.append(dict(anchor_id=unit.anchor_id,claim_id=c.claim_id,component_id=component,
                claim=c.text,qualifiers=list(c.qualifiers)+list(c.semantic_qualifiers),
                gap_type=unit.status,reason=unit.reason,query=query,
                source_scope=[e.evidence_id for e in ex.v_evidence],outcome='pending'))
        if not found:gaps.append(dict(anchor_id=unit.anchor_id,claim_id=None,component_id=None,
            claim=unit.text,qualifiers=[],gap_type=unit.status,reason=unit.reason,query=None,
            source_scope=[e.evidence_id for e in ex.v_evidence],outcome='no_eligible_component'))
    return gaps


async def supplement(ex):
    if ex.v_issue or ex.verification.execution_issues:return
    started=perf_counter();gaps=gap_plan(ex);queries={};deliveries=[]
    for gap in gaps:
        q=gap['query']
        if q is None:continue
        if q not in queries:
            if len(queries)>=3:
                gap['outcome']='query_limit';continue
            delivery=await ex.retrieval.retrieve(RetrievalPurpose.VERIFICATION,ex.request,ex.answer,
                ex.claims,query_override=q,fact_query=True)
            queries[q]=delivery;deliveries.append(delivery)
        d=queries[q];gap.update(outcome=d.record.outcome,retrieval_id=d.record.retrieval_id,
            delivered_ids=[e.evidence_id for e in d.evidence])
        if d.issue:
            ex.verification=replace(ex.verification,execution_issues=ex.verification.execution_issues+(d.issue,))
            break
    for gap in gaps:
        if gap['outcome']=='pending':gap['outcome']='stopped_after_failure'
    external='failed' if any(d.issue for d in deliveries) else 'executed' if deliveries else 'not_executed'
    ex.record('source_first_gaps',ExecutionStatus.SUCCEEDED if external!='failed' else ExecutionStatus.FAILED,
        started,json.dumps(dict(version=strategy(ex),external_cross_check=external,gaps=gaps),ensure_ascii=False))
    ex.retrieval.records.append(RetrievalRecord(uuid4().hex,'verification','',strategy(ex),
        ex.answer.version,ex.knowledge_version,ExecutionStatus.FAILED if external=='failed' else ExecutionStatus.SUCCEEDED,
        'gap_summary',calls_used=ex.retrieval.calls,cumulative_chars=ex.retrieval.chars,
        duration_ms=int((perf_counter()-started)*1000),answer_id=ex.answer.answer_id,
        reason=json.dumps(dict(scope='source_fidelity_and_task_completeness',external_cross_check=external,
            source_truth_verified=False,gaps=gaps),ensure_ascii=False)))
    if external=='failed':return
    added=merge_evidence(*(d.evidence for d in deliveries))
    if not added:return
    ex.source_first_extra=merge_evidence(getattr(ex,'source_first_extra',()),added)
    ex.evidence=merge_evidence(ex.evidence,added)
    extra_bindings=tuple(b for d in deliveries for b in d.bindings);ex.bindings+=extra_bindings
    ex.source_first_extra_bindings=tuple({b.evidence_id:b for b in getattr(ex,'source_first_extra_bindings',())+extra_bindings}.values())
    evidence=merge_evidence(ex.v_evidence,added)
    # Per-component extension: only mapped gaps receive their delivered query.
    # Original source supply remains available to all objects; unrelated gap hits do not.
    bindings=[]
    for old in ex.v_input.fact_retrieval_bindings:
        ids=tuple(eid for g in gaps if (g['claim_id'],g['component_id'])==(old.claim_id,old.component_id)
            for eid in g.get('delivered_ids',()))
        bindings.append(replace(old,delivered_evidence_ids=tuple(dict.fromkeys(old.delivered_evidence_ids+ids))))
    inputs=replace(ex.v_input,seed_evidence=evidence,evidence_bindings=ex.v_bindings+extra_bindings,
        fact_retrieval_bindings=tuple(bindings))
    ex.v_input=inputs;ex.v_evidence=evidence;ex.v_bindings=inputs.evidence_bindings
    ex.retrieval.records[-1]=replace(ex.retrieval.records[-1],fact_bindings=tuple(bindings))
    inputs=replace(inputs,delivery_summary=json.dumps(asdict(ex.retrieval.records[-1]),ensure_ascii=False))
    ex.v_input=inputs
    previous=ex.verification
    second,issue=await ex.review('evidence_verification',ex.harness.verification,inputs,
        merge_evidence(evidence,ex.original_evidence),True,None)
    if issue:
        ex.verification=replace(previous,execution_issues=previous.execution_issues+(issue,));return
    # Established findings cannot vanish on gap re-review. No synthetic supported
    # status is introduced; retain their original adverse unit as authority.
    protected={d.anchor_id for d in previous.literal_defects}
    rows=tuple(next(r for r in previous.literal_reviews if r.anchor_id==u.anchor_id)
        if u.anchor_id in protected else u for u in second.literal_reviews)
    defects={d.finding_id:d for d in second.literal_defects}
    defects.update((d.finding_id,d) for d in previous.literal_defects)
    ex.verification=replace(second,literal_reviews=rows,literal_defects=tuple(defects.values()))
    ex.record('source_first_recheck',ExecutionStatus.SUCCEEDED,started,
        json.dumps(dict(retained_defects=[d.finding_id for d in previous.literal_defects],
            new_defects=[d.finding_id for d in second.literal_defects],replacement='non-established unit judgments only')))
    # New actually delivered gap evidence affects the domain supply as well.
    # Reuse the same reviewer on this bounded expanded supply; the earlier stage
    # output remains in observer/Store history, with an explicit supersession event.
    if any(e.evidence_id not in {x.evidence_id for x in ex.d_evidence} for e in added):
        old_domain=ex.domain
        domain_evidence=merge_evidence(ex.d_evidence,added)
        domain_input=replace(ex.d_input,evidence=domain_evidence,evidence_bindings=ex.d_bindings+extra_bindings,
            delivery_summary=inputs.delivery_summary)
        updated,domain_issue=await ex.review('power_domain_review',ex.harness.domain_review,domain_input,domain_evidence,False,None)
        if domain_issue or updated.execution_issues:
            ex.domain=replace(old_domain,execution_issues=old_domain.execution_issues+((domain_issue,) if domain_issue else updated.execution_issues))
        else:
            ex.domain=updated;ex.d_input=domain_input;ex.d_evidence=domain_evidence;ex.d_bindings=domain_input.evidence_bindings
        ex.record('source_first_domain_recheck',ExecutionStatus.FAILED if domain_issue or updated.execution_issues else ExecutionStatus.SUCCEEDED,
            started,json.dumps(dict(added_ids=[e.evidence_id for e in added],old_finding_ids=[f.finding_id for f in old_domain.findings],
                final_finding_ids=[f.finding_id for f in ex.domain.findings],supersedes='prior domain stage for same answer version; original persisted')))
