from dataclasses import dataclass
from typing import Protocol, Tuple

from core.models import (
    AnswerDraft, AuditDecision, AuditReport, Claim, Evidence, EvidenceBinding,
    ExecutionIssue, ExecutionStatus, RunTrace, TaskRequest, ClaimExtractionOutput, FactRetrievalBinding,
)
from rag.contracts import ContextOptions, RetrievalHit
from agents.contracts import EvidenceVerificationOutput, PowerDomainReviewOutput, GenerationOutput, RevisionOutput
from model_adapter.contracts import ModelCallRecord
from tools.contracts import ToolResult
from harness.states import RunState


@dataclass(frozen=True)
class RunBudget:
    max_revision_rounds: int = 2
    max_model_calls: int = 20
    max_tool_calls: int = 40
    max_retrieval_calls: int = 12
    max_duration_seconds: float = 180.0
    max_transient_retries: int = 1
    step_timeout_seconds: float = 10.0
    max_retrieval_chars_per_call: int = 16000
    max_retrieval_chars_total: int = 64000


@dataclass(frozen=True)
class RetrievalSettings:
    max_results: int = 3
    context_options: ContextOptions | None = ContextOptions()
    fact_strategy: str = "aggregate"


@dataclass(frozen=True)
class RetrievalRecord:
    retrieval_id: str
    purpose: str
    query: str
    query_method: str
    answer_version: int | None
    knowledge_version: str
    status: ExecutionStatus
    outcome: str
    hits: Tuple[RetrievalHit, ...] = ()
    core_evidence_ids: Tuple[str, ...] = ()
    context_evidence_ids: Tuple[str, ...] = ()
    omitted_evidence_ids: Tuple[str, ...] = ()
    offered_chars: int = 0
    accepted_chars: int = 0
    cumulative_chars: int = 0
    calls_used: int = 0
    duration_ms: int = 0
    reason: str = ""
    context_omissions: Tuple[str, ...] = ()
    answer_id: str | None = None
    reused_from_retrieval_id: str | None = None
    fact_bindings: Tuple["FactRetrievalBinding", ...] = ()
    omission_reasons: Tuple[Tuple[str, str], ...] = ()
    offered_context_links: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class ReviewRound:
    answer: AnswerDraft
    extraction: ClaimExtractionOutput | None
    verification: EvidenceVerificationOutput
    domain_review: PowerDomainReviewOutput
    report: AuditReport


@dataclass(frozen=True)
class HarnessResult:
    run_id: str
    state: RunState
    trace: RunTrace
    report: AuditReport | None = None
    termination_reason: str = ""
    execution_issues: Tuple[ExecutionIssue, ...] = ()
    evidence: Tuple[Evidence, ...] = ()
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()
    retrieval_records: Tuple[RetrievalRecord, ...] = ()
    duration_ms: int = 0
    answer: AnswerDraft | None = None
    generation_output: GenerationOutput | None = None
    model_records: Tuple[ModelCallRecord, ...] = ()
    extraction_output: ClaimExtractionOutput | None = None
    verification_output: EvidenceVerificationOutput | None = None
    domain_output: PowerDomainReviewOutput | None = None
    review_rounds: Tuple[ReviewRound, ...] = ()
    revision_outputs: Tuple[RevisionOutput, ...] = ()


@dataclass(frozen=True)
class ToolHarnessResult(HarnessResult):
    tool_results: Tuple[ToolResult, ...] = ()


class ClaimExtractor(Protocol):
    async def extract(self, answer: AnswerDraft) -> Tuple[Claim, ...] | ClaimExtractionOutput: ...


class AuditPolicy(Protocol):
    def decide(
        self,
        verification: EvidenceVerificationOutput,
        domain_review: PowerDomainReviewOutput,
        budget: RunBudget,
        revision_round: int,
    ) -> AuditDecision: ...


class Harness(Protocol):
    async def run(self, request: TaskRequest, budget: RunBudget, *, knowledge_version: str | None = None,
                  generation_only: bool = False, answer_requirements: Tuple[str, ...] = (),
                  evidence_only: bool = False, indexed_reference_ids: Tuple[str, ...] = (),
                  generation_snapshot=None, run_id: str | None = None) -> HarnessResult: ...

    async def cancel(self, run_id: str) -> None: ...


class TraceStore(Protocol):
    async def save(self, trace: RunTrace) -> None: ...
