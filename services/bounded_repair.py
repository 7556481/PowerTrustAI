"""Validated v3 model proposals are eligibility hints, never verification results."""
import json
MARKER=' [source-support-relation-v3] '
def repair_proposals(finding):
    rows=getattr(finding,'component_reviews',())
    rationales=[r.rationale for r in rows if getattr(r,'status',None)==finding.status] if rows else [finding.rationale]
    proposals=[]
    for rationale in rationales:
        marker=next((m for m in (MARKER,' [source-support-relation-v4] ',' [source-support-relation-v5] ',' [source-support-relation-v6] ',' [compact-support-assessment-v1] ') if m in rationale),None)
        if marker is None:return ()
        try:relation=json.loads(rationale.rsplit(marker,1)[1])
        except (ValueError,TypeError):return ()
        repair=relation.get('repair')
        if not isinstance(repair,dict) or not all(isinstance(repair.get(k),str) and repair[k].strip() for k in ('replacement','source_quote_id','source_excerpt')):return ()
        # Validate literal evidence again on the persisted parsed bases, not the hint alone.
        excerpts=[b.excerpt.text for b in getattr(finding,'bases',()) if b.type=='text_excerpt' and b.excerpt]
        if not any(repair['source_excerpt'] in t for t in excerpts):return ()
        proposals.append(repair)
    return tuple(proposals)

def eligible_repairs(finding):
    """At least one faithful adverse component; other gaps remain untouched."""
    from dataclasses import replace
    rows=getattr(finding,'component_reviews',())
    if not rows:return repair_proposals(finding)
    proposals=[]
    for row in rows:
        if row.status.value not in ('insufficient_evidence','contradicted'):continue
        if row.classification_issue or row.fidelity_status!='faithful':continue
        proposals.extend(repair_proposals(replace(finding,status=row.status,component_reviews=(row,))))
    return tuple(proposals)

GAP_MARKER=' [missing-information-applicability-v1] '
def missing_information_review(findings):
    for finding in findings:
        if finding.category=='analysis_scope' and GAP_MARKER in finding.rationale:
            try:
                text=finding.rationale.rsplit(GAP_MARKER,1)[1]
                value,end=json.JSONDecoder().raw_decode(text)
                suffix=text[end:]
                if suffix:
                    from services.task_applicability import MARKER
                    if not suffix.startswith(MARKER):return None
                    json.loads(suffix[len(MARKER):])
                return value
            except (ValueError,TypeError):return None
    return None
