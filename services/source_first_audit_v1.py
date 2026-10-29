"""Opt-in source fidelity semantics, reusing literal contracts and repair authority."""
from services.literal_review_v1 import LiteralReviewAgent, SYSTEM as LITERAL_SYSTEM

VERSION='source_first_audit_v1'
SYSTEM=LITERAL_SYSTEM+'''
SCOPE: source fidelity and task completeness, NOT independent external fact truth.
The legacy field INDEPENDENT_QUOTE_IDS means delivered review supply in this candidate:
original generation sources, their identity-validated neighbors, and explicit gap retrieval.
Original source support does NOT establish independent corroboration, source truth or
engineering safety. Assess source reliability and applicability separately.
Distinguish important/may from unconditional must/need. A discussion introduced by
when does not justify only/not used for other purposes. Check actual condition owners.
Do not mark absent evidence contradicted. insufficient_evidence/not_assessable units
without established defects are explicit evidence gaps; the existing program may fetch
at most three distinct component queries once. No confidence-based bypass is permitted.
Find an established, precisely located defect now when original sources suffice; do not
request a global search merely to correct modality. Supported first-round mistakes can
remain undetected; never claim exhaustive independent truth checking.
'''

class SourceFirstReviewAgent(LiteralReviewAgent):
    source_first_review=True
    system=SYSTEM
    prompt_version=VERSION
