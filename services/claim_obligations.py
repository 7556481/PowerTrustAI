"""Semantic obligations are model judgments, never proof of equivalence."""
from copy import deepcopy
from dataclasses import fields,replace
import re
from services.answer_basis_targets import parse as parse_v6,SYSTEM as V6_SYSTEM
from services.validation_diagnostics import ErrorCollector
from core.models import ObligationClaim

TARGET_OBLIGATIONS={
    'document_body':'technical_truth','technical_content':'technical_truth',
    'mathematical_relation':'technical_truth','index_metadata':'metadata_value',
    'input_snapshot':'input_provided','answer_text':'answer_scope',
    'recommendation':'recommendation'}

def direct_rating_declaration(text):
    # A closed, positive declaration grammar, not arbitrary polarity detection.
    # Anything outside it is unknown, including nested reporting and rebuttals.
    return re.match(r'^\s*There are (?:[0-9]+|one|two|three|four|five|six|seven|eight|nine|ten) equipment ratings(?:\s*[:.]|\s*$)',text,re.I) is not None

def validate_obligations(claim,path='$.claim'):
    from core.validation import require
    require(len(claim.component_obligations)==len(claim.components),'one explicit semantic obligation per component required',path=path+'.component_obligations')
    for i,(target,obligation) in enumerate(zip(claim.component_basis_targets,claim.component_obligations)):
        require(TARGET_OBLIGATIONS.get(target)==obligation,'obligation must match assessment target; existence cannot verify technical truth',path=f'{path}.component_obligations[{i}]')

def parse(value,answer):
    wire=deepcopy(value);ec=ErrorCollector('claim_extraction_v7');obligations=[]
    ec.fields(wire,{'claims','non_claims'},set(),'$')
    items=wire.get('claims') if type(wire) is dict else None
    if ec.check(type(items) is list,'$.claims','array_required'):
        from services.answer_anchors import anchors
        anchor_map={a['anchor_id']:a for a in anchors(answer)}
        for i,item in enumerate(items):
            p=f'$.claims[{i}]';values=[]
            components=item.get('components') if type(item) is dict else None
            if not ec.check(type(components) is list,p+'.components','array_required'):continue
            for j,c in enumerate(components):
                cp=f'{p}.components[{j}]'
                if not ec.fields(c,{'category','proposition','basis_target','verification_obligation'},set(),cp):continue
                obligation=c['verification_obligation'];values.append(obligation)
                ec.check(TARGET_OBLIGATIONS.get(c['basis_target'])==obligation,cp+'.verification_obligation','truth_existence_transcription_targets_must_not_be_interchanged')
                del c['verification_obligation']
            obligations.append(tuple(values))
        # Finite declaration safeguard. It proves only a literal positive
        # declaration is present, not arbitrary normalized semantic equivalence.
        grouped={}
        for item in items:
            if type(item) is dict:grouped.setdefault(item.get('anchor_id'),[]).append(item)
        for aid,anchor_items in grouped.items():
            if aid in anchor_map and direct_rating_declaration(anchor_map[aid]['text']):
                ec.check(any(c.get('basis_target') in ('document_body','technical_content') and
                    re.search(r'\bratings?\b',c.get('proposition',''),re.I)
                    for item in anchor_items for c in item.get('components',[]) if type(c) is dict),
                    '$.claims','positive_rating_declaration_requires_technical_verification_component_not_answer_existence')
    ec.finish();out=parse_v6(wire,answer)
    out=replace(out,claims=tuple(ObligationClaim(**{f.name:getattr(c,f.name) for f in fields(c)},component_obligations=o,
        ) for c,o in zip(out.claims,obligations)))
    out=replace(out,claims=tuple(replace(c,semantic_origin='model-claims-v7-obligations') for c in out.claims))
    for c in out.claims:validate_obligations(c)
    return out

SYSTEM=V6_SYSTEM+'''
CURRENT V7: every component ALSO requires verification_obligation.
technical_truth for document_body/technical_content/mathematical_relation;
metadata_value for index_metadata; input_provided for input_snapshot;
answer_scope for answer_text; recommendation for recommendation.
Original anchor, normalized proposition, assertion_role and verification obligation are different.
Do NOT turn endorsed X into "the answer states X". Technical correctness remains obligatory
even when unsupported. Genuine refusal/scope/source/coverage statements remain legitimate.
For "There are four equipment ratings: ...", extract the four-rating technical assertion,
NOT only an answer_scope fact. Do not repair it while extracting.
A rebuttal quoting an erroneous four-count is correction/reported_error, not endorsement.
Split corrected technical assertions from reports of the old error. A user's supplied data
prove only they provided it, not that their plant really has those properties.
The assertion_role and normalized qualifiers are model judgments, not program-proven semantics.
Use separate atomic propositions for input presence, real-world truth and engineering sufficiency.
Full component example: {"category":"technical_fact","proposition":"230 kV = 230,000 V",
"basis_target":"mathematical_relation","verification_obligation":"technical_truth"}.
Retain grouped numeric strings; the program owns numeric parsing. Do not invent tool evidence.
'''
