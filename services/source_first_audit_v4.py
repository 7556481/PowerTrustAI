"""Versioned per-unit quote choices; programs restore text, models judge meaning."""
import hashlib,json
from services.source_first_audit_v1 import SYSTEM as SOURCE_SYSTEM
from services.source_first_audit_v2 import parse_relation
from services.literal_review_v1 import LiteralReviewAgent,catalog,unit_sources,ck,fields,selected
from services.answer_anchors import anchors
VERSION='source_first_audit_v4'
SELECTION='source-relation-selection-v1'
SYSTEM=SOURCE_SYSTEM+'''
CURRENT units also include exactly relation_check with exactly source_relation,
answer_relation,entailment. source_relation is an ARRAY of reference_ref values
selected ONLY from THIS unit's source_relation_choices. Do not copy source text,
generate offsets, normalize quotes, invent IDs, or use reference_ref as a quote_id.
Each choice points to an existing quote_id in the unchanged quotes/sources catalog;
read that ACTUAL original text, identity and context. Several choices remain separate
source spans, never one fabricated continuous quotation. Also select their quote_ids
in the unit's quote_ids. [] is legal only for unknown + insufficient_evidence or
not_assessable without a source-bound defect. No auto-support from selecting a quote.
answer_relation is concise Chinese FULL answer meaning: actor, scope, condition,
modality and exclusion. entailment entailed,not_entailed,unknown. Explain actual SOURCE
relations vs answer in Chinese reason, separating neighboring relationships. A genuine
mandatory requirement cannot turn a nearby recommendation/possible need into a duty;
conversely never downgrade real mandatory duties or real exclusive limits to may.
Use concrete defects only for extra force/exclusion/shifted conditions established by
the chosen sources. Preserve correct adjacent requirements and all requested points.
Defect quote_ids must belong to its unit's selected relation choices. Missing evidence
is not contradiction or edit authority. No case/keyword rules or extra judge.
Supported requires entailed; contradicted requires not_entailed. Write relation_check
before the verdict. All unchanged unit/defect/citation contracts still apply.
IMPORTANT original citations are a DIFFERENT scope: each citation may choose ONLY
its own original_citations.allowed_quote_ids, even after gap retrieval. Never borrow
a new review/gap quote for an old citation. Use [] + insufficient_evidence when that
original citation does not establish the answer; do not repair its ID by guessing.
'''

def choices(inputs,anchor,legal):
    return {('relation-'+hashlib.sha256(json.dumps([SELECTION,inputs.answer.answer_id,inputs.answer.version,anchor['anchor_id'],inputs.knowledge_version,qid],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24]):q for qid,q in legal.items()}

def prepare(data,inputs):
    _,allowed,_=catalog(inputs)
    for unit in data['units']:
        refs=choices(inputs,unit,unit_sources(inputs,unit,allowed))
        unit['source_relation_choices']=[dict(reference_ref=ref,quote_id=q.quote_id) for ref,q in refs.items()]
    data['SOURCE_RELATION_SELECTION_VERSION']=SELECTION
    data['QUOTE_ID_RULES']=dict(units='each unit.allowed_quote_ids only',defects='same unit selected source_relation choices only',citations='each original_citations.allowed_quote_ids only, never gap/new review quotes')
    return data

def parse_references(value,inputs):
    ck(type(value) is dict and type(value.get('units')) is list,'$','units_required')
    ac={a['anchor_id']:a for a in anchors(inputs.answer)};_,allowed,_=catalog(inputs);units=[];selected_by_unit={}
    for i,row in enumerate(value['units']):
        p=f'$.units[{i}]';ck(type(row) is dict,p,'object_required');aid=row.get('anchor_id')
        ck(type(aid) is str and aid in ac,p,'current_anchor_required')
        relation=row.get('relation_check');fields(relation,'source_relation answer_relation entailment',p+'.relation_check')
        available=choices(inputs,ac[aid],unit_sources(inputs,ac[aid],allowed))
        resolved=selected(relation['source_relation'],available,p+'.relation_check.source_relation')
        ids=[q.quote_id for q in resolved];qs=row.get('quote_ids')
        ck(type(qs) is list and all(type(q) is str for q in qs),p,'quote_id_array_required')
        ck(set(ids)<=set(qs),p,'relation_sources_must_be_selected_unit_quotes')
        if not ids:ck(relation['entailment']=='unknown' and row.get('status') in ('insufficient_evidence','not_assessable'),p,'unlocated_relation_requires_unknown_gap')
        selected_by_unit[aid]=set(ids)
        # parse_relation/literal parse bind every selected quote to its exact text,
        # offsets and source identity. The raw choice manifest is archived in wire;
        # do not duplicate the source pool or dump transport IDs into user reasons.
        description=f'已按程序引用选择核对{len(ids)}段独立原文；各原区间分别保留' if ids else '未建立可定位来源关系'
        units.append(dict(row,relation_check=dict(relation,source_relation=description)))
    ck(type(value.get('defects')) is list,'$.defects','array_required')
    for defect in value['defects']:
        ck(type(defect) is dict and type(defect.get('anchor_id')) is str and type(defect.get('quote_ids')) is list and all(type(q) is str for q in defect['quote_ids']),'$.defects','object_with_quote_ids_required')
        ck(bool(defect['quote_ids']) and set(defect['quote_ids'])<=selected_by_unit.get(defect.get('anchor_id'),set()),'$.defects','defect_requires_selected_relation_sources')
    return parse_relation(dict(value,units=units),inputs)

class SourceFirstReferenceReviewAgent(LiteralReviewAgent):
    source_first_review=True
    system=SYSTEM
    prompt_version=VERSION
    def prepare_payload(self,data,inputs):return prepare(data,inputs)
    def parse_response(self,value,inputs):return parse_references(value,inputs)
