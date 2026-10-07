"""Explicit reviewer input capabilities, with centralized historical fallback."""
from dataclasses import fields
from agents.contracts import (EvidenceVerificationInput,PowerDomainReviewInput,
    ReliabilityVerificationInput,ReliabilityDomainInput)

class ReviewInputContractError(TypeError):
    code='REVIEW_INPUT_CONTRACT_ERROR'

def input_type(agent,base_type):
    declared=getattr(agent,'review_input_type',None)
    if declared is not None:return declared
    # Historical injected reviewers did not declare capabilities. Preserve their
    # existing 9..13 / domain3..5 behavior here; new models declare explicitly.
    if base_type is EvidenceVerificationInput:
        return ReliabilityVerificationInput if getattr(agent,'schema_version',None) in (9,10,11,12,13) else base_type
    if base_type is PowerDomainReviewInput:
        return ReliabilityDomainInput if getattr(agent,'protocol_version',None) in (3,4,5) else base_type
    raise ReviewInputContractError('Unknown base reviewer input contract')

def build(agent,base,*,tool_results=(),delivery_summary='',fact_retrieval_bindings=()):
    base_type=type(base);wanted=input_type(agent,base_type)
    extended=ReliabilityVerificationInput if base_type is EvidenceVerificationInput else ReliabilityDomainInput if base_type is PowerDomainReviewInput else None
    if wanted not in (base_type,extended) or extended is None:
        raise ReviewInputContractError('Reviewer declared incompatible input capability')
    if wanted is base_type:return base
    values={f.name:getattr(base,f.name) for f in fields(base)}
    values.update(tool_results=tuple(tool_results),delivery_summary=delivery_summary)
    if wanted is ReliabilityVerificationInput:values['fact_retrieval_bindings']=tuple(fact_retrieval_bindings)
    return wanted(**values)
