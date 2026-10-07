"""Versioned, stable packing of complete citation scopes; never truncate Evidence."""
from dataclasses import dataclass
import json

VERSION = 'citation-review-workload-v1'

@dataclass(frozen=True)
class CitationWorkload:
    max_items: int = 32
    max_message_chars: int = 64000
    max_correction_message_chars: int = 192000

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in
               (self.max_items, self.max_message_chars, self.max_correction_message_chars)):
            raise ValueError('Positive citation workload limits required')
        if self.max_correction_message_chars < self.max_message_chars:
            raise ValueError('Correction capacity must cover initial capacity')

class ReviewCapacityError(RuntimeError):
    code = 'REVIEW_MESSAGE_CAPACITY_EXCEEDED'

def messages_size(messages):
    return sum(len(m.content) for m in messages)

def pack(items, payload, instruction, limits):
    """Greedy stable groups; unplaceable items are returned explicitly, not omitted."""
    groups, rejected, current = [], [], []
    def size(group):
        return len(instruction) + len(json.dumps(payload(group), ensure_ascii=False))
    for item in items:
        if size([item]) > limits.max_message_chars:
            if current: groups.append(tuple(current)); current = []
            rejected.append(item)
            continue
        trial = current + [item]
        if len(trial) > limits.max_items or size(trial) > limits.max_message_chars:
            groups.append(tuple(current)); current = [item]
        else: current = trial
    if current: groups.append(tuple(current))
    return tuple(groups), tuple(rejected)

def submission_rejections(request,knowledge_version,schema,limits):
    """Capacity preflight uses the same protocol payload as the actual reviewer."""
    answer=request.existing_answer
    if schema==14:
        from agents.contracts import ReliabilityVerificationInput
        from agents.verification_contract_v14 import ReviewCatalog,SYSTEM
        catalog=ReviewCatalog(ReliabilityVerificationInput(request,answer,(),(),
            knowledge_version=knowledge_version,original_evidence=request.provided_evidence))
        _,rejected=pack(tuple(catalog.targets),catalog.payload,SYSTEM,limits)
        return tuple(catalog.targets[t]['citation_index'] for t in rejected)
    if schema!=13:raise ValueError('Unsupported service verification protocol')
    from services.scoped_candidates import CandidateScope
    from agents.verification_contract_v10_batched import citation_payload,original_template,CONTRACT_VERSION
    original={e.evidence_id:e for e in request.provided_evidence}
    scopes=[None]+[CandidateScope(answer,knowledge_version,'original_citation',
        tuple(original[e] for e in c.evidence_ids),check_id=i,protocol_version=CONTRACT_VERSION) for i,c in enumerate(answer.citations)]
    _,rejected=pack(range(len(answer.citations)),lambda g:citation_payload(answer,request.question,scopes,g),original_template(),limits)
    return rejected
