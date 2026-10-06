"""Shared immutable data contracts; boundary validation is in core.validation."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class TaskMode(str, Enum):
    QUESTION_ANSWER = "question_answer"
    ASSESS_EXISTING = "assess_existing"


class VerificationStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_ASSESSABLE = "not_assessable"


class ExecutionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionKind(str, Enum):
    PASS = "pass"
    REVISE = "revise"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REVIEW_REQUIRED = "review_required"
    REJECT = "reject"
    NEEDS_INFORMATION = "needs_information"
    EXECUTION_INCOMPLETE = "execution_incomplete"


@dataclass(frozen=True)
class EvidenceProvenance:
    document_id: str
    document_version: str
    file_sha256: str
    fragment_id: str
    knowledge_version: str
    start_offset: int
    end_offset: int
    start_line: int
    end_line: int
    heading_path: Tuple[str, ...] = ()
    source_uri: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    document_title: Optional[str] = None
    heading_levels: Tuple[int, ...] = ()
    file_page: Optional[int] = None
    printed_page: Optional[str] = None
    section: Optional[str] = None
    parser_version: Optional[str] = None
    page_text_sha256: Optional[str] = None
    extraction_sha256: Optional[str] = None
    text_basis: str = "source_text"
    previous_fragment_id: Optional[str] = None
    next_fragment_id: Optional[str] = None
    quality_status: Optional[str] = None
    quality_warnings: Tuple[str, ...] = ()
    splitter_version: Optional[str] = None
    split_method: Optional[str] = None
    split_warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_id: str
    source_version: str
    locator: str
    text: str
    source_type: str
    applicability: Tuple[str, ...] = ()
    provenance: Optional[EvidenceProvenance] = None


@dataclass(frozen=True)
class EvidenceBinding:
    evidence_id: str
    origin: str
    purpose: Optional[str] = None
    answer_version: Optional[int] = None
    retrieval_id: Optional[str] = None
    core_evidence_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimComponent:
    component_id: str
    category: str
    proposition: str


@dataclass(frozen=True)
class FactRetrievalBinding:
    answer_id: str
    answer_version: int
    claim_id: str
    component_id: str
    category: str
    basis_target: str
    query: str
    query_method: str
    retrieval_id: Optional[str]
    knowledge_version: str
    outcome: str
    core_hit_ids: Tuple[str, ...] = ()
    delivered_evidence_ids: Tuple[str, ...] = ()
    context_evidence_ids: Tuple[str, ...] = ()
    omissions: Tuple[Tuple[str, str], ...] = ()
    reused_from_retrieval_id: Optional[str] = None
    offered_context_links: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class Claim:
    claim_id: str
    answer_id: str
    answer_version: int
    text: str
    start_offset: int
    end_offset: int
    claim_type: str
    proposition: Optional[str] = None
    qualifiers: Tuple[str, ...] = ()
    components: Tuple[ClaimComponent, ...] = ()
    anchor_group_id: Optional[str] = None
    @property
    def assertion_role(self):return 'legacy_unspecified'

    @property
    def semantic_qualifiers(self):return ()

    @property
    def semantic_origin(self):return 'legacy_model'


@dataclass(frozen=True)
class ContextualClaim(Claim):
    assertion_role: str = 'legacy_unspecified'
    semantic_qualifiers: Tuple[str, ...] = ()
    semantic_origin: str = 'legacy_model'


@dataclass(frozen=True)
class BasisAwareClaim(ContextualClaim):
    component_basis_targets: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ObligationClaim(BasisAwareClaim):
    component_obligations: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CitationBinding:
    start_offset: int
    end_offset: int
    evidence_ids: Tuple[str, ...]


@dataclass(frozen=True)
class AnswerDraft:
    answer_id: str
    version: int
    text: str
    assumptions: Tuple[str, ...] = ()
    missing_information: Tuple[str, ...] = ()
    citations: Tuple[CitationBinding, ...] = ()


@dataclass(frozen=True)
class EngineeringQuantity:
    quantity_id: str
    kind: str
    value: float
    unit: str
    reference: str


@dataclass(frozen=True)
class EngineeringContext:
    goal: str = "conceptual"
    network_model: Optional[str] = None
    operating_point: Optional[str] = None
    limits: Optional[str] = None
    contingencies: Tuple[str, ...] = ()
    quantities: Tuple[EngineeringQuantity, ...] = ()
    origin: str = "user_input_unverified"


@dataclass(frozen=True)
class ConsistencyCheck:
    check_id: str
    status: str
    method_version: str
    reason_code: str
    rationale: str
    claim_id: Optional[str] = None
    basis_quote_ids: Tuple[str, ...] = ()
    expected_count: Optional[int] = None
    observed_count: Optional[int] = None
    observed_items: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    mode: TaskMode
    scenario_id: str
    question: str
    user_context: str = ""
    existing_answer: Optional[AnswerDraft] = None
    provided_evidence: Tuple[Evidence, ...] = ()
    engineering_context: Optional[EngineeringContext] = None


@dataclass(frozen=True)
class ExecutionIssue:
    component: str
    status: ExecutionStatus
    code: str
    message: str


@dataclass(frozen=True)
class VerificationFinding:
    finding_id: str
    claim_id: str
    status: VerificationStatus
    evidence_ids: Tuple[str, ...]
    rationale: str
    checker_version: str
    tool_result_ids: Tuple[str, ...] = ()
    excerpts: Tuple["EvidenceExcerpt", ...] = ()
    applicability_conditions: Tuple[str, ...] = ()
    check_method: Optional[str] = None
    checked_dimensions: Tuple[str, ...] = ()
    claim_category: str = "unclassified"
    assessment_basis: str = "text_evidence"
    metadata_refs: Tuple["MetadataReference", ...] = ()
    scope_id: Optional[str] = None
    required_dimensions: Tuple[str, ...] = ()
    dimension_findings: Tuple["DimensionObservation", ...] = ()
    bases: Tuple["TypedBasis", ...] = ()
    component_reviews: Tuple["ComponentReview", ...] = ()


@dataclass(frozen=True)
class QuoteCandidate:
    quote_id: str
    evidence_id: str
    start_offset: int
    end_offset: int
    text: str
    context_start_offset: int
    context_end_offset: int
    context_text: str
    candidate_version: str
    method: str
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TypedBasis:
    type: str
    evidence_id: Optional[str] = None
    excerpt: Optional["EvidenceExcerpt"] = None
    metadata_reference: Optional["MetadataReference"] = None
    snapshot_id: Optional[str] = None
    answer_excerpt: Optional["AnswerSpan"] = None
    quote_id: Optional[str] = None
    @property
    def calculation_result_id(self):return None


@dataclass(frozen=True)
class CalculationBasis(TypedBasis):
    calculation_result_id: Optional[str] = None


@dataclass(frozen=True)
class ClassificationIssue:
    suggested_category: str
    rationale: str


@dataclass(frozen=True)
class ComponentReview:
    component_id: str
    status: VerificationStatus
    basis_indexes: Tuple[int, ...]
    rationale: str
    classification_issue: Optional[ClassificationIssue] = None
    origin: str = "model_judgment"
    reason_code: Optional[str] = None


@dataclass(frozen=True)
class FidelityComponentReview(ComponentReview):
    fidelity_status: str = 'uncertain'
    reviewed_assertion_role: str = 'legacy_unspecified'
    verification_obligation: str = ''
    fidelity_rationale: str = ''
    raw_support_status: str = ''
    review_disposition: str = ''
    review_projection_version: str = ''


@dataclass(frozen=True)
class DimensionObservation:
    dimension: str
    observation: str


@dataclass(frozen=True)
class MetadataReference:
    evidence_id: str
    field_path: str
    value_json: str


@dataclass(frozen=True)
class GenerationEvidenceSnapshot:
    answer_id: str
    answer_version: int
    evidence: Tuple[Evidence, ...]
    snapshot_id: str
    knowledge_version: Optional[str] = None
    snapshot_version: str = "generation-evidence-only-v1"
    question: Optional[str] = None
    user_context: Optional[str] = None
    engineering_context: Optional[EngineeringContext] = None
    answer_requirements: Tuple[str, ...] = ()
    input_prompt_version: Optional[str] = None
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()


@dataclass(frozen=True)
class EvidenceExcerpt:
    evidence_id: str
    text: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class CitationAssessment:
    citation_index: int
    status: VerificationStatus
    evidence_ids: Tuple[str, ...]
    excerpts: Tuple[EvidenceExcerpt, ...]
    rationale: str
    applicability_conditions: Tuple[str, ...]
    check_method: str
    binding_warnings: Tuple[str, ...] = ()
    claim_ids: Tuple[str, ...] = ()
    partial_claim_ids: Tuple[str, ...] = ()
    coverage_issues: Tuple[str, ...] = ()
    bases: Tuple[TypedBasis, ...] = ()


@dataclass(frozen=True)
class AnswerSpan:
    text: str
    start_offset: int
    end_offset: int
    reason: str


@dataclass(frozen=True)
class ClaimExtractionOutput:
    answer_id: str
    answer_version: int
    claims: Tuple[Claim, ...]
    non_claim_spans: Tuple[AnswerSpan, ...]
    uncovered_spans: Tuple[AnswerSpan, ...]
    warnings: Tuple[str, ...] = (
        "Semantic atomicity and completeness require human review",
        "Only answer.text is claim-anchored; assumptions and missing_information remain outside separate claim review",
    )


@dataclass(frozen=True)
class DomainRule:
    rule_id: str
    version: str
    source: str
    applicable_scope: str
    description: str
    demonstration_only: bool = True


@dataclass(frozen=True)
class DomainFinding:
    finding_id: str
    answer_id: str
    answer_version: int
    claim_ids: Tuple[str, ...]
    severity: Severity
    category: str
    rationale: str
    rule_ids: Tuple[str, ...] = ()
    evidence_ids: Tuple[str, ...] = ()
    tool_result_ids: Tuple[str, ...] = ()
    missing_prerequisites: Tuple[str, ...] = ()
    check_status: Optional[str] = None
    basis_kind: Optional[str] = None
    origin: Optional[str] = None
    bases: Tuple[TypedBasis, ...] = ()


@dataclass(frozen=True)
class AuditDecision:
    kind: DecisionKind
    reasons: Tuple[str, ...]
    policy_version: str
    unresolved_finding_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ProductDecision(AuditDecision):
    execution_integrity: str = "incomplete"
    risk_level: str = "unknown"
    resolution: str = "unable_to_answer"
    reason_codes: Tuple[str, ...] = ()
    applicable_checks: Tuple[Tuple[str, str, str], ...] = ()
    classification_basis: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditReport:
    report_id: str
    task_id: str
    answer: AnswerDraft
    claims: Tuple[Claim, ...]
    evidence: Tuple[Evidence, ...]
    verification_findings: Tuple[VerificationFinding, ...]
    domain_findings: Tuple[DomainFinding, ...]
    execution_issues: Tuple[ExecutionIssue, ...]
    decision: AuditDecision
    evidence_bindings: Tuple[EvidenceBinding, ...] = ()


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    timestamp_utc: str
    component: str
    status: ExecutionStatus
    input_refs: Tuple[str, ...]
    output_refs: Tuple[str, ...]
    duration_ms: int
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    rule_version: Optional[str] = None
    knowledge_version: Optional[str] = None
    answer_version: Optional[int] = None
    state: Optional[str] = None
    detail: str = ""


@dataclass(frozen=True)
class RunTrace:
    run_id: str
    task_id: str
    events: Tuple[TraceEvent, ...] = ()
