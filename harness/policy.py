"""Deterministic offline policy; scores and agent votes are not used."""
from core.models import AuditDecision, DecisionKind, Severity, VerificationStatus


class DeterministicAuditPolicy:
    def decide(self, verification, domain_review, budget, revision_round):
        findings = verification.findings + domain_review.findings
        unresolved = tuple(f.finding_id for f in findings if
                           (getattr(f, "status", None) != VerificationStatus.SUPPORTED
                            if hasattr(f, "status") else f.severity != Severity.NONE))

        def result(kind, reason):
            return AuditDecision(kind, (reason,), "offline-policy-v1", unresolved)

        if verification.execution_issues or domain_review.execution_issues:
            return result(DecisionKind.REVIEW_REQUIRED, "Required review did not complete successfully")
        if any(f.check_status == "not_assessable" for f in domain_review.findings):
            return result(DecisionKind.REVIEW_REQUIRED, "Required domain checks remain incomplete; no engineering certification")
        if any(c.status in ("warning","incomplete") for c in verification.consistency_checks):
            return result(DecisionKind.REVIEW_REQUIRED, "Quantity/enumeration checks contain warnings or incomplete checks")
        if any(f.severity == Severity.HIGH for f in domain_review.findings):
            return result(DecisionKind.REVIEW_REQUIRED, "Unresolved high-severity domain finding")
        if any(f.missing_prerequisites for f in domain_review.findings):
            return result(DecisionKind.REVIEW_REQUIRED, "Engineering prerequisites are missing")
        if any(f.status in (VerificationStatus.INSUFFICIENT_EVIDENCE, VerificationStatus.NOT_ASSESSABLE)
               for f in verification.findings):
            return result(DecisionKind.INSUFFICIENT_EVIDENCE, "Evidence is insufficient to verify all claims")
        repairable = any(f.status == VerificationStatus.CONTRADICTED for f in verification.findings) or bool(unresolved)
        if repairable:
            if revision_round >= budget.max_revision_rounds:
                return result(DecisionKind.REVIEW_REQUIRED, "Revision limit reached with unresolved findings")
            return result(DecisionKind.REVISE, "Repairable contradictions or domain findings require revision")
        return result(DecisionKind.PASS, "All claims supported and domain review completed without unresolved findings")


class LimitedRepairPolicy(DeterministicAuditPolicy):
    """Opt-in repair of observed findings, never certification or a pass."""
    allows_bounded_real_revision = True

    def decide(self, verification, domain_review, budget, revision_round):
        base=super().decide(verification,domain_review,budget,revision_round)
        if verification.execution_issues or domain_review.execution_issues:
            return base
        actionable=any(f.status in (VerificationStatus.CONTRADICTED,VerificationStatus.INSUFFICIENT_EVIDENCE)
            for f in verification.findings) or any(f.check_status=="warning" for f in domain_review.findings)
        actionable=actionable or any(c.status=="warning" for c in verification.consistency_checks)
        if actionable and revision_round < min(1,budget.max_revision_rounds):
            return AuditDecision(DecisionKind.REVISE,("One bounded repair of observed issues; incomplete checks remain unresolved; full re-review required",),
                "limited-repair-policy-v1",base.unresolved_finding_ids)
        return AuditDecision(DecisionKind.REVIEW_REQUIRED,
            ("Limited reviews completed or stopped; unresolved findings and unperformed engineering analysis remain; no safety certification",)+base.reasons,
            "limited-repair-policy-v1",base.unresolved_finding_ids)
