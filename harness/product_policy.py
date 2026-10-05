"""Product disposition v1. Evidence judgments remain model judgments, not certification.

No production high-risk rule is registered: demonstration severity cannot certify risk.
The explicit high-risk mechanism accepts only a caller-owned reviewed rule registry,
bound current claims and literal body bases. Synthetic tests register fixture rules only.
"""
from core.models import ProductDecision, DecisionKind as D, VerificationStatus as V, Severity

VERSION = 'product-decision-v1.1'


class ProductAuditPolicy:
    product_policy = True
    allows_bounded_real_revision = True

    def __init__(self, *, high_risk_rules=(), synthetic_fixture=False):
        self.high_risk_rules = frozenset(high_risk_rules)
        self.synthetic_fixture = synthetic_fixture

    def decide_context(self, verification, domain, budget, revision_round, *, request,
                       answer, claims, extraction, issues, retrieval):
        facts, findings = verification.findings, domain.findings
        ids = tuple(f.finding_id for f in facts if f.status != V.SUPPORTED) + tuple(
            f.finding_id for f in findings if f.check_status in ('warning', 'not_assessable')
            or f.severity == Severity.HIGH)
        context = request.engineering_context
        scope = context.goal if context else 'unknown'
        basis = ('User requested scope: ' + scope,
                 'Claim components and independent analysis_scope check retain technical truth obligations',
                 'Classification is fallible; scope alone never overrides an adverse finding')
        checks = [('fact_support', 'applicable', 'Every extracted claim must have independent verification'),
                  ('original_citations', 'applicable' if answer.citations else 'not_applicable',
                   'Separate original citation judgments' if answer.citations else 'No original citations')]
        for claim in claims:
            basis += (f'{claim.claim_id}: type={claim.claim_type}; assertion_role={claim.assertion_role}; model classification is not proof',)
            for component, target in zip(claim.components, getattr(claim, 'component_basis_targets', ())):
                checks.append((claim.claim_id+'/'+component.component_id, 'applicable',
                    'Required basis target: '+target+'; original technical truth obligation cannot be bypassed'))
                category = ('numerical_calculation' if target=='mathematical_relation' else
                    'document_summary' if claim.assertion_role in ('attributed','input_report') and target=='document_body' else
                    'conceptual_or_literature_fact' if target in ('document_body','technical_content') else target)
                basis += (component.component_id+': task hint='+category+'; regional rules/settings and plant guarantees require independently assessed scope, never inferred safe from this hint',)
        for f in findings:
            checks.append((f.category, f.check_status or ('no_issue' if self.synthetic_fixture else 'unknown'), f.rationale))

        def result(kind, code, reason, risk='unknown', execution='complete', resolution='partial'):
            return ProductDecision(kind, (reason, 'Automatic approval is bounded to this task; not engineering safety certification'),
                VERSION, ids, execution, risk, resolution, (code,), tuple(checks), basis)

        if issues or verification.execution_issues or domain.execution_issues or (
                retrieval and any(r.status.value != 'succeeded' for r in retrieval.records)):
            return result(D.EXECUTION_INCOMPLETE, 'REQUIRED_EXECUTION_FAILED',
                          'Required execution failed; this is not a factual contradiction', execution='incomplete')
        if not claims or not facts or not findings or {c.claim_id for c in claims} != {f.claim_id for f in facts}:
            return result(D.EXECUTION_INCOMPLETE, 'EMPTY_OR_MISSING_REVIEW', 'Empty or missing required review', execution='incomplete', resolution='unable_to_answer')
        if extraction and extraction.uncovered_spans:
            return result(D.EXECUTION_INCOMPLETE, 'UNCOVERED_ANSWER', 'Answer has unreviewed text', execution='incomplete')
        # Non-claim classifications are model assertions, not a bypass for technical text.
        if extraction and extraction.non_claim_spans:
            return result(D.REVIEW_REQUIRED, 'NONCLAIM_CLASSIFICATION_UNCERTAIN', 'Non-claim classification needs review; cannot silently omit text')
        if not self.synthetic_fixture:
            required = {'answer_units', 'analysis_scope', 'operating_prerequisites', 'engineering_inputs', 'simulation_boundary'}
            if not required <= {f.category for f in findings} or any(f.check_status is None for f in findings):
                return result(D.EXECUTION_INCOMPLETE, 'MISSING_DOMAIN_CHECK', 'Required domain checks are absent', execution='incomplete')
            for f in facts:
                c = next(c for c in claims if c.claim_id == f.claim_id)
                if c.components and len(f.component_reviews) != len(c.components):
                    return result(D.EXECUTION_INCOMPLETE, 'MISSING_COMPONENT_CHECK', 'Component coverage incomplete', execution='incomplete')
                if any(r.classification_issue or getattr(r, 'fidelity_status', 'uncertain') != 'faithful' for r in f.component_reviews):
                    return result(D.REVIEW_REQUIRED, 'COMPONENT_CLASSIFICATION_UNCERTAIN', 'Component classification or literal fidelity is uncertain')
        # A severity label/topic/contradiction alone is never the high-risk criterion.
        rules = {r.rule_id: r for r in domain.rules}
        for f in findings:
            if f.severity == Severity.HIGH:
                verified = f.rule_ids and all(r in self.high_risk_rules and r in rules and not rules[r].demonstration_only for r in f.rule_ids)
                verified = verified and bool(f.claim_ids) and set(f.claim_ids) <= {c.claim_id for c in claims}
                verified = verified and bool(f.bases) and all(b.type == 'text_excerpt' and b.excerpt for b in f.bases)
                if verified:
                    return result(D.REJECT, 'REVIEWED_HIGH_RISK_RULE', 'Reviewed high-severity rule with current literal evidence; no automatic revision', risk='high')
                return result(D.REVIEW_REQUIRED, 'UNVALIDATED_HIGH_SEVERITY', 'Severity is unvalidated; no registered authoritative production high-risk criterion')
        citations = verification.citation_reviews
        if {c.citation_index for c in citations} != set(range(len(answer.citations))):
            return result(D.EXECUTION_INCOMPLETE, 'MISSING_CITATION_CHECK', 'Original citation coverage incomplete', execution='incomplete')
        if any(f.status in (V.INSUFFICIENT_EVIDENCE, V.NOT_ASSESSABLE) for f in facts + citations):
            return result(D.NEEDS_INFORMATION, 'FACT_BASIS_MISSING', 'Evidence or required factual inputs are insufficient')
        # A located contradiction can be repaired even when a separate domain
        # prerequisite remains unknown. The subsequent full re-review must still
        # resolve/retain that gap; this does not make an incomplete answer pass.
        if any(f.status == V.CONTRADICTED for f in facts + citations):
            if revision_round < min(1, budget.max_revision_rounds):
                return result(D.REVISE, 'REPAIRABLE_ERROR', 'Located contradiction; one bounded repair, all other gaps remain and full re-review is mandatory', risk='medium')
            return result(D.REJECT, 'UNRESOLVED_ORDINARY_ERROR', 'Located ordinary contradiction remains after bounded repair', risk='medium')
        incomplete = [f for f in findings if f.check_status == 'not_assessable' or f.missing_prerequisites]
        if incomplete:
            return result(D.NEEDS_INFORMATION, 'REQUIRED_INPUT_MISSING', 'Required domain input/analysis is missing: ' + '; '.join(f.category for f in incomplete))
        consistency = verification.consistency_checks + domain.consistency_checks
        if any(c.status == 'incomplete' for c in consistency):
            return result(D.NEEDS_INFORMATION, 'CONSISTENCY_NOT_ASSESSABLE', 'Required quantity/enumeration check cannot be evaluated')
        if any(c.status == 'warning' for c in consistency) or any(f.status == V.CONTRADICTED for f in facts + citations):
            if revision_round < min(1, budget.max_revision_rounds):
                return result(D.REVISE, 'REPAIRABLE_ERROR', 'Located ordinary factual/citation/consistency error; one revision and complete re-review', risk='medium')
            return result(D.REJECT, 'UNRESOLVED_ORDINARY_ERROR', 'Located error remains after bounded repair; not an automatic high-risk classification', risk='medium')
        if any(f.check_status == 'warning' for f in findings):
            # Demo engineering rules are advice, not authoritative rejection standards.
            return result(D.REVIEW_REQUIRED, 'DOMAIN_JUDGMENT_DISPUTE', 'Domain warning requires review; demonstration rules cannot certify severity')
        if answer.missing_information:
            return result(D.NEEDS_INFORMATION, 'ANSWER_DECLARED_MISSING_INFORMATION', 'Answer explicitly declares missing information')
        if scope == 'unknown' and not self.synthetic_fixture:
            return result(D.REVIEW_REQUIRED, 'TASK_SCOPE_UNKNOWN', 'Task engineering scope is unspecified; preserve uncertainty')
        if scope == 'plant_assessment':
            return result(D.NEEDS_INFORMATION, 'ENGINEERING_ANALYSIS_NOT_EXECUTED', 'Plant performance cannot be approved by literature and scalar conversions')
        # Current registered tool covers bounded scalar SI conversions, not general mathematics.
        # Text/model reasoning alone cannot certify a requested numerical calculation.
        tools={t.result_id for t in getattr(verification,'tool_results',()) if t.status.value=='succeeded'}
        for claim, finding in ((c,next(f for f in facts if f.claim_id==c.claim_id)) for c in claims):
            reviews={r.component_id:r for r in finding.component_reviews}
            for component,target in zip(claim.components,getattr(claim,'component_basis_targets',())):
                if target=='mathematical_relation':
                    review=reviews.get(component.component_id)
                    indexes=() if review is None else review.basis_indexes
                    if not any(0<=i<len(finding.bases) and finding.bases[i].type=='calculation_result' and
                               finding.bases[i].calculation_result_id in tools for i in indexes):
                        return result(D.NEEDS_INFORMATION,'REGISTERED_CALCULATION_REQUIRED','Numerical relation lacks a bound successful registered calculation; formula/tool coverage remains limited')
        return result(D.PASS, 'ALL_REQUIRED_CHECKS_COMPLETE', 'All applicable checks complete with supported claims and no blocking findings', risk='low', resolution='complete')
