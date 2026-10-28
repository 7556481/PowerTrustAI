"""Opt-in source relation grounded in delivered literal text; no semantic rules."""
from services.source_first_audit_v1 import SYSTEM as SOURCE_SYSTEM
from services.source_first_audit_v2 import parse_relation
from services.literal_review_v1 import LiteralReviewAgent,catalog,unit_sources,ck,fields,nonempty
from services.answer_anchors import anchors

VERSION='source_first_audit_v3'
SYSTEM=SOURCE_SYSTEM+'''
Before each unit verdict compare actual SOURCE language with the ANSWER relation.
For EVERY unit add exactly relation_check with exactly source_relation,
answer_relation,entailment. No other new fields. Write this before status/reason.
source_relation is NOT a free paraphrase: copy one exact, contiguous, uniquely
locatable original-language passage from a selected legal quote_id for this unit.
Include the actual actor, modality, governing condition and scope, and surrounding
requirements needed to distinguish mixed relations. Quotes include identity and
context; never silently replace their language by a stronger Chinese summary.
Select sufficient quote_ids for the FULL unit, not just the erroneous clause.
If no locatable passage can establish the relation, source_relation is null and
entailment unknown; status insufficient_evidence or not_assessable, no repair defect.
answer_relation is a concise Chinese account of the answer's COMPLETE meaning,
including its subject, scope and condition. entailment: entailed,not_entailed,unknown.
Explain the comparison in Chinese reason against the ACTUAL cited source words.
Check each neighboring relationship separately: one true mandatory requirement does
not turn a nearby conditional recommendation or possible need into an unconditional
duty. Conversely, preserve genuine mandatory requirements and exclusive limits;
never downgrade an entire mixed unit to recommendations. Test whether the answer
adds a duty, exclusion or moves a condition that the actual source leaves open.
A faithful citation with a mistaken interpretation is still a semantic error.
Only source-established differences authorize precise defects. original_text and
correction_boundary must isolate the extra force/exclusion while explicitly retaining
correct adjacent duties, conditions, actors and requested points. Missing evidence
alone is not contradiction or edit authority. No keyword inference, case-specific
rules, extra judge, replacement prose or global pass. Supported requires entailed;
contradicted requires not_entailed. Leave all other existing contracts unchanged.
'''

def parse_grounded_relation(value,inputs):
    ck(type(value) is dict and type(value.get('units')) is list,'$','units_required')
    ac={a['anchor_id']:a for a in anchors(inputs.answer)};_,allowed,_=catalog(inputs)
    units=[]
    for i,row in enumerate(value['units']):
        p=f'$.units[{i}]';ck(type(row) is dict,p,'object_required')
        aid=row.get('anchor_id');ck(type(aid) is str and aid in ac,p,'current_anchor_required')
        relation=row.get('relation_check');fields(relation,'source_relation answer_relation entailment',p+'.relation_check')
        source=relation['source_relation'];ids=row.get('quote_ids')
        legal=unit_sources(inputs,ac[aid],allowed)
        ck(type(ids) is list and all(type(q) is str and q in legal for q in ids),p,'legal_local_source_ids_required')
        if source is None:
            ck(relation['entailment']=='unknown' and row.get('status') in ('insufficient_evidence','not_assessable'),p,'unlocated_relation_requires_unknown_gap')
            ck(type(value.get('defects')) is list and not any(type(d) is dict and d.get('anchor_id')==aid for d in value['defects']),p,'unlocated_relation_cannot_authorize_repair')
            description='未建立可定位的来源关系'
        else:
            nonempty(source,p+'.relation_check.source_relation')
            ck(any(legal[q].text.count(source)==1 for q in ids),p,'source_relation_requires_exact_selected_quote_span')
            description=source
        units.append(dict(row,relation_check=dict(relation,source_relation=description)))
    # Reuse all existing status consistency, source identity, unit/defect/citation
    # localization checks. This validates literal binding, not semantic entailment.
    return parse_relation(dict(value,units=units),inputs)

class SourceFirstGroundedReviewAgent(LiteralReviewAgent):
    source_first_review=True
    system=SYSTEM
    prompt_version=VERSION
    def parse_response(self,value,inputs):return parse_grounded_relation(value,inputs)
