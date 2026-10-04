"""Declarative state graph; no transition execution logic."""

from enum import Enum


class RunState(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    RETRIEVING = "retrieving"
    GENERATING = "generating"
    GENERATED = "generated"
    EVIDENCE_REVIEWED = "evidence_reviewed"
    EXTRACTING_CLAIMS = "extracting_claims"
    VERIFYING = "verifying"
    DECIDING = "deciding"
    REVISING = "revising"
    COMPLETED = "completed"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"
    CANCELLED = "cancelled"


NORMAL_TRANSITIONS = {
    RunState.RECEIVED: frozenset({RunState.VALIDATED}),
    RunState.VALIDATED: frozenset({RunState.RETRIEVING, RunState.EXTRACTING_CLAIMS}),
    RunState.RETRIEVING: frozenset({RunState.GENERATING, RunState.REVIEW_REQUIRED}),
    RunState.GENERATING: frozenset({RunState.EXTRACTING_CLAIMS, RunState.GENERATED}),
    RunState.EXTRACTING_CLAIMS: frozenset({RunState.VERIFYING}),
    RunState.VERIFYING: frozenset({RunState.DECIDING, RunState.EVIDENCE_REVIEWED}),
    RunState.DECIDING: frozenset({RunState.REVISING, RunState.COMPLETED, RunState.REVIEW_REQUIRED}),
    RunState.REVISING: frozenset({RunState.EXTRACTING_CLAIMS}),
    RunState.COMPLETED: frozenset(),
    RunState.GENERATED: frozenset(),
    RunState.EVIDENCE_REVIEWED: frozenset(),
    RunState.REVIEW_REQUIRED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.CANCELLED: frozenset(),
}

TERMINAL_STATES = frozenset({
    RunState.COMPLETED, RunState.GENERATED, RunState.EVIDENCE_REVIEWED, RunState.REVIEW_REQUIRED, RunState.FAILED, RunState.CANCELLED,
})

# Every nonterminal state may fail, be cancelled, or escalate on exhausted budget.
INTERRUPT_TARGETS = frozenset({RunState.FAILED, RunState.CANCELLED, RunState.REVIEW_REQUIRED})
