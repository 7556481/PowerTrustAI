"""Explicit candidate records. No projection to legacy component support/fidelity."""
from dataclasses import dataclass
from core.models import EvidenceExcerpt, AuditReport


@dataclass(frozen=True)
class LiteralDefect:
    finding_id: str
    anchor_id: str
    original_text: str
    start_offset: int
    end_offset: int
    difference: str
    correction_boundary: str
    sources: tuple[EvidenceExcerpt, ...]


@dataclass(frozen=True)
class LiteralUnitReview:
    anchor_id: str
    text: str
    start_offset: int
    end_offset: int
    status: str
    reason: str
    source_reliability: str
    sources: tuple[EvidenceExcerpt, ...]


@dataclass(frozen=True)
class LiteralAuditReport(AuditReport):
    literal_protocol: str = 'literal-review-v1'
    literal_reviews: tuple[LiteralUnitReview, ...] = ()
    literal_defects: tuple[LiteralDefect, ...] = ()
