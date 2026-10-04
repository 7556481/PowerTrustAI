"""Explicit model-selected assessment target, program-checked category compatibility."""
from copy import deepcopy
from dataclasses import fields,replace
from services.answer_anchors import parse as parse_anchors,SYSTEM as ANCHOR_SYSTEM
from services.validation_diagnostics import ErrorCollector
from core.models import BasisAwareClaim
from core.validation import validate_extraction

TARGETS={
    'document_body':'technical_fact',
    'technical_content':'technical_fact',
    'mathematical_relation':'technical_fact',
    'index_metadata':'source_quality_metadata',
    'input_snapshot':'input_evidence_coverage',
    'answer_text':'answer_scope',
    'recommendation':'review_recommendation',
}

def validate_targets(claim,path='$.claim'):
    from core.validation import require
    require(len(claim.component_basis_targets)==len(claim.components),'each component requires an assessment target',path=path+'.component_basis_targets')
    for i,(target,component) in enumerate(zip(claim.component_basis_targets,claim.components)):
        require(target in TARGETS and TARGETS[target]==component.category,'target/category mismatch; document statements require body evidence, not index metadata',path=f'{path}.components[{i}].basis_target')

def parse(value,answer):
    ec=ErrorCollector('claim_extraction_v6');translated=deepcopy(value);targets=[]
    ec.fields(translated,{'claims','non_claims'},set(),'$')
    claims=translated.get('claims',[]) if type(translated) is dict else []
    if not ec.check(type(claims) is list,'$.claims','array_required'):ec.finish()
    for i,claim in enumerate(claims):
        path=f'$.claims[{i}]';selected=[];components=claim.get('components') if type(claim) is dict else None
        if not ec.check(type(components) is list,path+'.components','array_required'):continue
        for j,component in enumerate(components):
            p=f'{path}.components[{j}]'
            if not ec.fields(component,{'category','proposition','basis_target'},set(),p):continue
            target=component['basis_target'];selected.append(target)
            if not ec.check(type(target) is str and target in TARGETS and TARGETS[target]==component['category'],p+'.basis_target','declared_target_category_must_agree'):
                ec.errors[-1].update(legal_target_categories=TARGETS,processing_options=['identify whether the assertion concerns official body, maintained metadata, supplied input, or mathematics','keep literal anchor unchanged','split mixed assertions; never convert a body assertion into an index-field assertion to obtain support'])
            # Explicitly declared and validated field; retained in extension, not silently dropped.
            component.pop('basis_target')
        targets.append(tuple(selected))
    ec.finish();output=parse_anchors(translated,answer)
    output=replace(output,claims=tuple(BasisAwareClaim(**{f.name:getattr(c,f.name) for f in fields(c)},component_basis_targets=t) for c,t in zip(output.claims,targets)))
    output=replace(output,claims=tuple(replace(c,semantic_origin="model-claims-v6") for c in output.claims))
    for c in output.claims:validate_targets(c)
    validate_extraction(output,answer);return output

SYSTEM=ANCHOR_SYSTEM+'''
CURRENT V6 COMPONENT SHAPE: each component EXACT category,proposition,basis_target.
basis_target is an explicit semantic judgment: document_body or technical_content or
mathematical_relation require technical_fact; index_metadata requires source_quality_metadata;
input_snapshot requires input_evidence_coverage; answer_text requires answer_scope;
recommendation requires review_recommendation. These targets are not proofs of truth.
Distinguish an official statement printed under Applicability from a maintained index field.
"VAR-001 body states its Applicability is Operators within region R" -> document_body,
technical_fact, needing actual body. "The index applicability field equals R" -> index_metadata.
"Guideline explicitly says it is not Chinese" is a document_body claim, even when it is FALSE.
Do not turn false attribution into a true index metadata claim. Preserve the incorrect assertion.
For a mixed original sentence, split the math relation and other premises. Normalized mathematical
components use only exact standalone relation A unit = B unit or A unit does not equal B unit.
"230 kV equals 230 V at the same bus" exposes mathematical component "230 kV = 230 V",
and any asserted bus identity separately; never assume an engineering state is verified.
"Reactive power Q=30 MW has correct unit" is technical_content (physical quantity category),
NOT mathematical_relation. MW to W conversion cannot prove that MW is a reactive-power unit.
Each component preserves the original answer's polarity; do not correct wrong claims during extraction.
Full legal example: {"claims":[{"anchor_id":"actual-anchor","proposition":"Source says applicability is R.",
"claim_type":"technical_fact","assertion_role":"asserted","semantic_qualifiers":[],
"components":[{"category":"technical_fact","proposition":"Source body says applicability is R.",
"basis_target":"document_body"}]}],"non_claims":[]}.
'''
