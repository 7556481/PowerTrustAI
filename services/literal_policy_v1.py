"""Candidate disposition: original units, old safety/execution/one-attempt bottom lines."""
from core.models import ProductDecision, DecisionKind as D, Severity
from services.literal_review_v1 import POLICY


def decide(policy,v,domain,budget,round,*,request,answer,claims,extraction,issues,retrieval):
    fs=domain.findings;rows=v.literal_reviews
    ids=tuple(d.finding_id for d in v.literal_defects)+tuple(f.finding_id for f in fs if f.check_status in ('warning','not_assessable'))
    checks=tuple(('literal:'+r.anchor_id,'applicable',r.reason) for r in rows)+tuple((f.category,f.check_status or 'unknown',f.rationale) for f in fs)
    def result(kind,code,reason,risk='unknown',execution='complete'):
        return ProductDecision(kind,(reason,'Candidate original-text review; not engineering safety certification'),POLICY,ids,execution,risk,'complete' if kind==D.PASS else 'partial',(code,),checks,('Literal units, independent support, original citations and task engineering scope reviewed separately',))
    incomplete=bool(issues or v.execution_issues or domain.execution_issues or retrieval and any(r.status.value!='succeeded' for r in retrieval.records))
    safety=getattr(domain,'safety_reviews',())
    if any(s.verdict=='dangerous' and s.source_ids for s in safety):return result(D.EXECUTION_INCOMPLETE if incomplete else D.REJECT,'MODEL_BOUND_OPERATIONAL_HAZARD','Source-bound operational hazard; do not adopt',risk='high',execution='incomplete' if incomplete else 'complete')
    if incomplete:return result(D.EXECUTION_INCOMPLETE,'REQUIRED_EXECUTION_FAILED','Required execution failed; original text does not mask extraction failure',execution='incomplete')
    required={'answer_units','analysis_scope','operating_prerequisites','engineering_inputs','simulation_boundary'}
    if not claims or not rows or not required<={f.category for f in fs} or any(f.check_status is None for f in fs):return result(D.EXECUTION_INCOMPLETE,'MISSING_REQUIRED_REVIEW','Required original-text/domain review missing',execution='incomplete')
    if any(s.verdict=='uncertain' for s in safety):return result(D.REVIEW_REQUIRED,'OPERATIONAL_HAZARD_UNCERTAIN','Operational safety uncertain')
    if any(f.severity==Severity.HIGH for f in fs):return result(D.REVIEW_REQUIRED,'UNVALIDATED_HIGH_SEVERITY','High-severity domain concern; no automatic repair or approval')
    # No fabricated component/fidelity statuses. Extraction still supplies retrieval
    # and domain inputs; positional omission is fully audited by literal units.
    if v.literal_defects and round<min(1,budget.max_revision_rounds):return result(D.REVISE,'LITERAL_SOURCE_BOUND_REPAIR','Concrete located difference with delivered body source; one local attempt and full re-review',risk='medium')
    if v.literal_defects:return result(D.REJECT,'UNRESOLVED_LITERAL_DEFECT','Concrete original-text defects remain after bounded attempt',risk='medium')
    if any(r.status=='not_assessable' or r.source_reliability!='adequate' for r in rows):return result(D.REVIEW_REQUIRED,'LITERAL_UNCERTAIN','Original meaning or source reliability uncertain')
    if any(r.status!='supported' for r in rows) or any(c.status.value!='supported' for c in v.citation_reviews):return result(D.NEEDS_INFORMATION,'LITERAL_BASIS_MISSING','Original unit/citation has unresolved support gap; no unsupported forced repair')
    if any(f.check_status=='not_assessable' or f.missing_prerequisites for f in fs):return result(D.NEEDS_INFORMATION,'REQUIRED_INPUT_MISSING','Domain input/analysis remains missing')
    if any(f.check_status=='warning' for f in fs):return result(D.REVIEW_REQUIRED,'DOMAIN_JUDGMENT_DISPUTE','Domain warning remains')
    if any(c.status!='succeeded' and c.status in ('warning','incomplete') for c in domain.consistency_checks):return result(D.NEEDS_INFORMATION,'CONSISTENCY_NOT_ASSESSABLE','Domain consistency remains unresolved')
    from services.task_applicability import read,effective
    a=read(fs);scope=effective(request.engineering_context,a) if a else None
    if scope!='conceptual':return result(D.NEEDS_INFORMATION if scope=='engineering' else D.REVIEW_REQUIRED,'TASK_ENGINEERING_BOUNDARY','Engineering scope requires inputs and registered analysis; text review cannot certify')
    if answer.missing_information:
        from services.bounded_repair import missing_information_review
        reviewed=missing_information_review(fs)
        if reviewed is None or len(reviewed)!=len(answer.missing_information) or any(x['applicability'] in ('required','uncertain') for x in reviewed):return result(D.NEEDS_INFORMATION,'REQUIRED_ANSWER_INFORMATION_MISSING','Declared required/uncertain answer gap remains')
    # Registered calculation obligations from original extraction cannot be waived.
    if any(t=='mathematical_relation' for c in claims for t in getattr(c,'component_basis_targets',())):return result(D.NEEDS_INFORMATION,'REGISTERED_CALCULATION_REQUIRED','Literal text support does not certify calculations')
    return result(D.PASS,'LITERAL_ALL_REQUIRED_CHECKS_COMPLETE','Every original unit and citation supported; domain checks complete',risk='low')
