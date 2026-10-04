from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, Tuple

from core.models import Evidence, ExecutionIssue


class RetrievalPurpose(str, Enum):
    GENERATION = "generation"
    VERIFICATION = "verification"
    DOMAIN_REVIEW = "domain_review"
    REVISION = "revision"


@dataclass(frozen=True)
class ContextOptions:
    max_chars: int = 2400
    max_fragments: int = 6
    depth: int = 1
    allow_cross_page: bool = True
    priority: str = "storage_order"


@dataclass(frozen=True)
class ContextLink:
    core_evidence_id: str
    direction: str
    distance: int
    crosses_page: bool


@dataclass(frozen=True)
class ContextEvidence:
    evidence: Evidence
    links: Tuple[ContextLink, ...]
    origin: str = "adjacent_context_not_retrieval_hit"


@dataclass(frozen=True)
class ContextResult:
    items: Tuple[ContextEvidence, ...]
    char_count: int
    options: ContextOptions
    omitted: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    scenario_id: str
    purpose: RetrievalPurpose
    knowledge_version: str
    max_results: int
    context_options: Optional[ContextOptions] = None


@dataclass(frozen=True)
class RetrievalHit:
    evidence_id: str
    fragment_id: str
    rank: int
    score: float
    scoring_method: str


@dataclass(frozen=True)
class RetrievalResult:
    evidence: Tuple[Evidence, ...]
    knowledge_version: str
    execution_issues: Tuple[ExecutionIssue, ...] = ()
    hits: Tuple[RetrievalHit, ...] = ()
    context: Optional[ContextResult] = None


class Retriever(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...

    async def validate_result(self, request: RetrievalRequest, result: RetrievalResult) -> None:
        """Check complete output against the requested immutable index snapshot."""
        ...
