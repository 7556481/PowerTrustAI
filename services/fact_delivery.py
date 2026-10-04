"""Versioned delivery scope, independent of semantic support requirements."""
from dataclasses import asdict, replace
from core.models import VerificationStatus
from core.validation import require
from services.validation_diagnostics import ErrorCollector

FAILED = {'failed', 'budget_exhausted', 'timed_out', 'cancelled', 'classification_unresolved'}

def payload(inputs, scope):
    mappings = inputs.fact_retrieval_bindings
    if not mappings: return None
    expected = {(c.claim_id, p.component_id) for c in inputs.claims for p in c.components}
    actual = {(m.claim_id, m.component_id) for m in mappings}
    require(actual == expected and len(actual) == len(mappings), 'Exact current component delivery mappings required')
    seed_ids = {e.evidence_id for e in inputs.seed_evidence}
    for m in mappings:
        require((m.answer_id, m.answer_version, m.knowledge_version) ==
                (inputs.answer.answer_id, inputs.answer.version, inputs.knowledge_version), 'Fact mapping version mismatch')
        require(set(m.delivered_evidence_ids) <= seed_ids, 'Fact mapping contains undelivered Evidence')
    quotes = scope.payload()['QUOTE_CANDIDATES']
    return {'contract_version': 'fact-evidence-delivery-v1', 'strategy': 'per_claim_v1',
            'components': [dict(asdict(m), allowed_quote_ids=[q['quote_id'] for q in quotes
                                if q['evidence_id'] in m.delivered_evidence_ids]) for m in mappings]}

def validate_result(result, inputs):
    if not inputs.fact_retrieval_bindings: return result
    lookup = {(m.claim_id, m.component_id): m for m in inputs.fact_retrieval_bindings}
    ec = ErrorCollector('fact_evidence_delivery_v1'); findings = []
    for f in result.findings:
        reviews = []
        for i, r in enumerate(f.component_reviews):
            mapping = lookup[(f.claim_id, r.component_id)]
            path = '$.findings.' + f.claim_id + '.component_reviews[' + str(i) + ']'
            if mapping.basis_target in ('document_body', 'technical_content'):
                for j in r.basis_indexes:
                    basis = f.bases[j]
                    if basis.type == 'text_excerpt':
                        ec.check(basis.evidence_id in mapping.delivered_evidence_ids, path + '.basis_indexes', 'basis_must_be_delivered_to_current_component')
            if mapping.outcome in FAILED:
                ec.check(r.status == VerificationStatus.NOT_ASSESSABLE and not r.basis_indexes,
                         path + '.status', 'incomplete_retrieval_is_not_a_factual_verdict')
                r = replace(r, origin='program_precondition', reason_code='fact_retrieval_' + mapping.outcome)
            reviews.append(r)
        findings.append(replace(f, component_reviews=tuple(reviews)))
    ec.finish()
    return replace(result, findings=tuple(findings))

INSTRUCTION = '''
FACT_EVIDENCE_DELIVERY contract v1 is program-owned current answer/version delivery.
For each component select text_excerpt ONLY from its allowed_quote_ids. Shared Evidence
is legal when explicitly delivered to both components. Do not borrow an undelivered ID
from another component or answer version. Existing metadata/input/answer/calculation
basis rules remain unchanged. No hit means this query did not retrieve material, NOT
that the assertion is false or no corpus evidence exists. For failed/budget_exhausted/
timed_out/cancelled/classification_unresolved delivery return not_assessable with [];
execution failure is not contradicted. Existing supported/contradicted requirements,
classification_issue and semantic-fidelity requirements still apply unchanged.
'''
