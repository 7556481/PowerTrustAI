"""Opt-in v2 instructions; v1 typed representation and strict basis gates reused."""
from services.premise_review_protocol_v1 import *
from services.premise_review_protocol_v1 import INSTRUCTION as V1_INSTRUCTION

PROFILE = "public-review-object-boundary-v2-dev"
PROMPT = "evidence-verification-v9.22-object-boundary-v2-dev"
INSTRUCTION = V1_INSTRUCTION + """
OBJECT CLASSIFICATION REVIEW v2:
Rule restatement is literature even when conditional or beside an instance application.
An instance application asserts that this task satisfies a rule, so definitive support
or contradiction still requires rule body PLUS all relevant declared premises.
Do not select an unrelated premise merely to satisfy an extractor's mistaken object.
For a SAME-CATEGORY object disagreement, use existing semantic_review.fidelity=disputed
(or uncertain) and give a concrete rationale: original object, proposed object, literal
answer clause and why the premise is irrelevant/required. Return status not_assessable;
select only bases allowed by the frozen object, or [] when no compatible basis exists.
This records an unresolved extraction-object objection, NOT evidence insufficiency.
It cannot approve or silently relabel the component. Other valid components continue.
Do not invent a new JSON field for this objection. The existing classification_issue
is ONLY for a genuinely DIFFERENT category, EXACT suggested_category,rationale, and
is a SIBLING of semantic_review in component_reviews[i], NEVER nested inside it.
semantic_review remains EXACT fidelity,assertion_role,verification_obligation,rationale.
If the category is unchanged (literature versus application are both technical_fact),
DO NOT emit classification_issue suggesting technical_fact. Use disputed fidelity and
the explicit object rationale above. Frozen basis TYPES, IDs, snapshot restrictions,
original citation scope and external actual-record requirements remain unchanged.
An actual application cannot become supported with only a rule, only a premise, or
an objection. The program derives review_required for unresolved semantic judgments.
"""
