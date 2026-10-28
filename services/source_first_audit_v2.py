"""One opt-in relation comparison candidate on the existing literal review path."""
from services.source_first_audit_v1 import SYSTEM as SOURCE_SYSTEM
from services.literal_review_v1 import LiteralReviewAgent,parse,ck,fields,nonempty

VERSION='source_first_audit_v2'
SYSTEM=SOURCE_SYSTEM+'''
Before judging each unit, explicitly compare the SOURCE relation with the ANSWER
relation, then reverse-check whether the source entails the answer's added force,
exclusion or condition. Topic overlap and mostly correct text are not entailment.
For EVERY unit add exactly relation_check with exactly source_relation,
answer_relation,entailment. Both relations are concise Chinese descriptions of the
complete relation and its subject/scope/condition, not invented verbatim quotations.
entailment is entailed,not_entailed,unknown. Bind the comparison to the same selected
legal quote_ids; only those locatable source texts may establish a repair boundary.
Write relation_check before status/reason. Keep all other existing fields unchanged.
Compare MUST vs recommendation/importance/possibility; necessary vs sufficient
conditions; some vs all; temporal/contextual when vs exclusive only; exception owners
and the scope of negation. Test the reverse implication: would the ANSWER forbid an
alternative or impose a duty the SOURCE leaves open? Absence of a use is not evidence
excluding that use. Preserve real mandatory requirements and real exclusive limits.
An explicit source that establishes weaker force or a different scoped relationship
can establish a concrete unsupported strengthening/exclusion defect even if the rest
of the unit is correct. Use adverse unit status and a precise source-bound defect,
not a vague doubt, a global downgrade, or silent supported. Missing/unrelated sources
remain evidence gaps, not fabricated contradictions or edit authority.
Preserve correct conditions and all requested content inside mixed units. Never turn
every duty into may; no keyword rule or automatic entailment inference is available.
Reasons, differences and boundaries should be Chinese. Do not output extra reviews,
replacement prose, a global pass, new source text, or another root object.
'''

def parse_relation(value,inputs):
    ck(type(value) is dict and type(value.get('units')) is list,'$','units_required')
    units=[]
    for i,row in enumerate(value['units']):
        p=f'$.units[{i}]';ck(type(row) is dict,p,'object_required')
        comparison=row.get('relation_check')
        fields(comparison,'source_relation answer_relation entailment',p+'.relation_check')
        for key in ('source_relation','answer_relation'):nonempty(comparison[key],p+'.relation_check.'+key)
        ent=comparison['entailment'];ck(ent in ('entailed','not_entailed','unknown'),p,'legal_entailment_required')
        ck(row.get('status')!='supported' or ent=='entailed',p,'supported_requires_entailed_relation')
        ck(row.get('status')!='contradicted' or ent=='not_entailed',p,'contradicted_requires_nonentailment')
        unit={k:v for k,v in row.items() if k!='relation_check'}
        nonempty(unit.get('reason'),p+'.reason')
        unit['reason']=unit['reason']+' 来源关系：'+comparison['source_relation']+'；回答关系：'+comparison['answer_relation']+'。'
        units.append(unit)
    return parse(dict(value,units=units),inputs)

class SourceFirstRelationReviewAgent(LiteralReviewAgent):
    source_first_review=True
    system=SYSTEM
    prompt_version=VERSION
    def parse_response(self,value,inputs):return parse_relation(value,inputs)
