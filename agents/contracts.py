"""Explicit input/output interfaces for the four agents."""

from dataclasses import dataclass
from typing import Protocol, Tuple

from core.models import (
    AnswerDraft, Claim, DomainFinding, Evidence, ExecutionIssue,
    TaskRequest, VerificationFinding, EvidenceBinding, CitationAssessment, GenerationEvidenceSnapshot, QuoteCandidate, ConsistencyCheck, DomainRule, EngineeringContext, FactRetrievalBinding,
)
from model_adapter.contracts import ModelCallRecord
from tools.contracts import ToolResult


@dataclass(frozen=True)
class GenerationInput:
    request: TaskRequest
    evidence: Tuple[Evidence, ...]
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()
    knowledge_version: str | None = None
    answer_requirements: Tuple[str, ...] = ()


@dataclass(frozen=True)
class GenerationOutput:
    answer: AnswerDraft
    execution_issues: Tuple[ExecutionIssue, ...] = ()
    evidence_sufficient: bool | None = None
    model_records: Tuple[ModelCallRecord, ...] = ()
    prompt_version: str | None = None
    evidence_snapshot: "GenerationEvidenceSnapshot | None" = None


@dataclass(frozen=True)
class EvidenceVerificationInput:
    request: TaskRequest
    answer: AnswerDraft
    claims: Tuple[Claim, ...]
    seed_evidence: Tuple[Evidence, ...]
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()
    knowledge_version: str | None = None
    original_evidence: Tuple[Evidence, ...] = ()
    generation_snapshot: "GenerationEvidenceSnapshot | None" = None


@dataclass(frozen=True)
class ReliabilityVerificationInput(EvidenceVerificationInput):
    tool_results: Tuple[ToolResult, ...] = ()
    delivery_summary: str = ""
    fact_retrieval_bindings: Tuple["FactRetrievalBinding", ...] = ()


@dataclass(frozen=True)
class EvidenceVerificationOutput:
    answer_id: str
    answer_version: int
    claims: Tuple[Claim, ...]
    findings: Tuple[VerificationFinding, ...]
    evidence: Tuple[Evidence, ...]
    execution_issues: Tuple[ExecutionIssue, ...] = ()
    citation_reviews: Tuple[CitationAssessment, ...] = ()
    model_records: Tuple[ModelCallRecord, ...] = ()
    prompt_version: str | None = None
    generation_snapshot: "GenerationEvidenceSnapshot | None" = None
    quote_candidates: Tuple[QuoteCandidate, ...] = ()
    consistency_checks: Tuple[ConsistencyCheck, ...] = ()


@dataclass(frozen=True)
class ReliabilityVerificationOutput(EvidenceVerificationOutput):
    tool_results: Tuple[ToolResult, ...] = ()
    delivery_summary: str = ""
    input_body_delivered: bool = False


@dataclass(frozen=True)
class PowerDomainReviewInput:
    request: TaskRequest
    answer: AnswerDraft
    claims: Tuple[Claim, ...]
    evidence: Tuple[Evidence, ...]
    rule_set_version: str
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()
    knowledge_version: str | None = None


@dataclass(frozen=True)
class ReliabilityDomainInput(PowerDomainReviewInput):
    tool_results: Tuple[ToolResult, ...] = ()
    delivery_summary: str = ""


@dataclass(frozen=True)
class PowerDomainReviewOutput:
    answer_id: str
    answer_version: int
    findings: Tuple[DomainFinding, ...]
    evidence: Tuple[Evidence, ...]
    execution_issues: Tuple[ExecutionIssue, ...] = ()
    rules: Tuple[DomainRule, ...] = ()
    quote_candidates: Tuple[QuoteCandidate, ...] = ()
    consistency_checks: Tuple[ConsistencyCheck, ...] = ()
    model_records: Tuple[ModelCallRecord, ...] = ()
    prompt_version: str | None = None
    engineering_context: EngineeringContext | None = None


@dataclass(frozen=True)
class RevisionInput:
    request: TaskRequest
    answer: AnswerDraft
    verification: EvidenceVerificationOutput
    domain_review: PowerDomainReviewOutput
    allowed_evidence: Tuple[Evidence, ...]
    revision_instructions: Tuple[str, ...]
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()
    knowledge_version: str | None = None


@dataclass(frozen=True)
class RevisionChange:
    finding_ids: Tuple[str, ...]
    description: str


@dataclass(frozen=True)
class FindingAction:
    finding_id: str
    action: str
    explanation: str


@dataclass(frozen=True)
class RevisionOutput:
    answer: AnswerDraft
    changes: Tuple[RevisionChange, ...]
    unresolved_finding_ids: Tuple[str, ...]
    evidence: Tuple[Evidence, ...]
    execution_issues: Tuple[ExecutionIssue, ...] = ()
    model_records: Tuple[ModelCallRecord, ...] = ()
    prompt_version: str | None = None
    evidence_snapshot: GenerationEvidenceSnapshot | None = None
    finding_actions: Tuple[FindingAction, ...] = ()


class GenerationAgent(Protocol):
    async def run(self, inputs: GenerationInput) -> GenerationOutput: ...


class EvidenceVerificationAgent(Protocol):
    async def run(self, inputs: EvidenceVerificationInput) -> EvidenceVerificationOutput: ...


class PowerDomainReviewAgent(Protocol):
    async def run(self, inputs: PowerDomainReviewInput) -> PowerDomainReviewOutput: ...


class RevisionAgent(Protocol):
    async def run(self, inputs: RevisionInput) -> RevisionOutput: ...
