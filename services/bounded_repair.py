"""Validated v3 model proposals are eligibility hints, never verification results."""
import json
MARKER=' [source-support-relation-v3] '
def repair_proposals(finding):
    rows=getattr(finding,'component_reviews',())
    rationales=[r.rationale for r in rows if getattr(r,'status',None)==finding.status] if rows else [finding.rationale]
    proposals=[]
    for rationale in rationales:
        if MARKER not in rationale:return ()
        try:relation=json.loads(rationale.rsplit(MARKER,1)[1])
        except (ValueError,TypeError):return ()
        repair=relation.get('repair')
        if not isinstance(repair,dict) or not all(isinstance(repair.get(k),str) and repair[k].strip() for k in ('replacement','source_quote_id','source_excerpt')):return ()
        # Validate literal evidence again on the persisted parsed bases, not the hint alone.
        excerpts=[b.excerpt.text for b in getattr(finding,'bases',()) if b.type=='text_excerpt' and b.excerpt]
        if not any(repair['source_excerpt'] in t for t in excerpts):return ()
        proposals.append(repair)
    return tuple(proposals)
