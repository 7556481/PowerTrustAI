"""Per verification object delivery; uses the existing indexed retrieval session."""
from dataclasses import replace
from time import perf_counter
from uuid import uuid4
from core.models import FactRetrievalBinding, ExecutionIssue, ExecutionStatus
from core.validation import merge_evidence, require
from harness.contracts import RetrievalRecord
from harness.retrieval import Delivery
from rag.contracts import RetrievalPurpose

METHOD = 'normalized-component-proposition-qualifiers-v1'
CONTRACT = 'fact-evidence-delivery-v1'


def objects(claims):
    for claim in claims:
        for index, component in enumerate(claim.components or (None,)):
            category = component.category if component else claim.claim_type
            targets = getattr(claim, 'component_basis_targets', ())
            target = targets[index] if index < len(targets) else ('technical_content' if category in ('technical_fact', 'technical') else 'unknown')
            proposition = component.proposition if component else (claim.proposition or claim.text)
            # Deduplicate identical strings, never normalize polarity or units.
            parts = (proposition,) + tuple(claim.qualifiers) + tuple(claim.semantic_qualifiers)
            query = '\n'.join(dict.fromkeys(part.strip() for part in parts if part.strip()))
            yield claim, component.component_id if component else claim.claim_id, category, target, query


async def retrieve_facts(session, request, answer, claims):
    started = perf_counter(); deliveries = {}; mappings = []; all_evidence = (); bindings = (); failures = []
    for claim, component_id, category, target, query in objects(claims):
        require(claim.answer_id == answer.answer_id and claim.answer_version == answer.version, 'Fact query answer version mismatch')
        if target not in ('document_body', 'technical_content'):
            mappings.append(FactRetrievalBinding(answer.answer_id, answer.version, claim.claim_id, component_id,
                category, target, '', METHOD, None, session.knowledge_version,
                'classification_unresolved' if target == 'unknown' else 'existing_basis_type'))
            if target == 'unknown':
                failures.append(ExecutionIssue('retrieval_verification',ExecutionStatus.FAILED,'FACT_QUERY_CLASSIFICATION_UNRESOLVED','No body/other-basis target assigned for '+component_id+'; classification not changed'))
            continue
        reused = query in deliveries
        if not reused:
            delivery = await session.retrieve(RetrievalPurpose.VERIFICATION, request, answer, (claim,), query_override=query, fact_query=True)
            updated = replace(delivery.record, query_method=METHOD)
            session.records[-1] = updated
            deliveries[query] = replace(delivery, record=updated)
        delivery = deliveries[query]; record = delivery.record
        all_evidence = merge_evidence(all_evidence, delivery.evidence)
        if not reused: bindings += delivery.bindings
        if delivery.issue and not reused: failures.append(delivery.issue)
        omissions = record.omission_reasons
        mappings.append(FactRetrievalBinding(answer.answer_id, answer.version, claim.claim_id, component_id,
            category, target, query, METHOD, record.retrieval_id, session.knowledge_version, record.outcome,
            tuple(hit.evidence_id for hit in record.hits), tuple(e.evidence_id for e in delivery.evidence),
            record.context_evidence_ids, omissions,
            record.retrieval_id if reused else record.reused_from_retrieval_id, record.offered_context_links))
    # References are explicitly delivered to every object. No old indexed
    # generation evidence is silently introduced into the current fact pool.
    user_ids = tuple(e.evidence_id for e in request.provided_evidence if e.evidence_id in session.user_ids)
    mappings = tuple(replace(m, delivered_evidence_ids=tuple(dict.fromkeys(m.delivered_evidence_ids + user_ids))) for m in mappings)
    summary = RetrievalRecord(uuid4().hex, 'verification', '', METHOD, answer.version, session.knowledge_version,
        ExecutionStatus.FAILED if failures else ExecutionStatus.SUCCEEDED, 'partial' if failures else 'mapped',
        offered_chars=sum(d.record.offered_chars for d in deliveries.values()),
        accepted_chars=sum(len(e.text) for e in all_evidence), cumulative_chars=session.chars, calls_used=session.calls,
        duration_ms=int((perf_counter()-started)*1000), reason=CONTRACT, answer_id=answer.answer_id, fact_bindings=mappings)
    session.records.append(summary)
    return Delivery(all_evidence, bindings, failures[0] if failures else None, summary, tuple(failures))
