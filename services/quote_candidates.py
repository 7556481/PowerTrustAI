"""Deterministic literal candidates, not a retrieval or factual-support algorithm."""
import hashlib
import json
import re
from core.models import QuoteCandidate
from core.validation import merge_evidence, require

VERSION = "literal-quote-candidates-v1"
WINDOW_CHARS = 1200
CONTEXT_CHARS = 320
MAX_PER_EVIDENCE = 8


def _id(evidence, start, end):
    binding = [VERSION, evidence.evidence_id, evidence.source_version,
               hashlib.sha256(evidence.text.encode("utf-8")).hexdigest(), start, end]
    return "quote-" + hashlib.sha256(json.dumps(binding, separators=(",", ":")).encode()).hexdigest()[:24]


def _word_boundary(text, position, direction):
    while 0 < position < len(text) and text[position-1].isalnum() and text[position].isalnum():
        position += direction
    return position


def build_candidates(evidence):
    result = []
    for e in merge_evidence(evidence):
        text, spans = e.text, [(0, len(e.text), "whole_fragment")]
        # PDF line wraps are not paragraph boundaries. Blank lines only provide
        # heuristic units, with a complete-fragment candidate always retained.
        cursor = 0
        paragraphs = []
        for match in re.finditer(r"(?:\r?\n[ \t]*){2,}", text):
            if text[cursor:match.start()].strip(): paragraphs.append((cursor, match.start()))
            cursor = match.end()
        if text[cursor:].strip(): paragraphs.append((cursor, len(text)))
        for start, end in paragraphs:
            pos = start
            while pos < end:
                stop = min(pos + WINDOW_CHARS, end)
                method = "blank_line_paragraph" if stop == end and pos == start else "bounded_window"
                if stop < end:
                    bounded = _word_boundary(text, stop, -1)
                    # Very long unbroken tokens remain with whole_fragment only.
                    if bounded <= pos: break
                    stop = bounded
                if text[pos:stop].strip() and (pos, stop) != (0, len(text)):
                    spans.append((pos, stop, method))
                pos = stop
        seen = set()
        for start, end, method in spans:
            if (start, end) in seen: continue
            seen.add((start, end))
            if len(seen) > MAX_PER_EVIDENCE: break
            cs = _word_boundary(text, max(0, start-CONTEXT_CHARS), -1)
            ce = _word_boundary(text, min(len(text), end+CONTEXT_CHARS), 1)
            warnings = ("candidate_units_are_heuristic_not_semantic_proof",)
            if method == "bounded_window": warnings += ("length_boundary_may_split_sentence_or_condition",)
            if len(spans) > MAX_PER_EVIDENCE: warnings += ("candidate_limit_applied_whole_fragment_retained",)
            result.append(QuoteCandidate(_id(e,start,end),e.evidence_id,start,end,text[start:end],
                cs,ce,text[cs:ce],VERSION,method,warnings))
    return tuple(result)


def validate_catalog(candidates, evidence):
    known = {e.evidence_id:e for e in merge_evidence(evidence)}
    require(len({c.quote_id for c in candidates}) == len(candidates), "duplicate candidate ID", path="$.quote_candidates")
    require(all(c.evidence_id in known for c in candidates), "candidate references unknown Evidence", path="$.quote_candidates")
    used = {c.evidence_id for c in candidates}
    expected = {c.quote_id:c for c in build_candidates(tuple(e for eid,e in known.items() if eid in used))}
    require({c.quote_id:c for c in candidates} == expected, "candidate catalog differs from frozen source text/configuration", path="$.quote_candidates")
