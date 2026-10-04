"""Versioned page-local slicing of stored extraction, not visual PDF paragraphs."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re

from core.validation import InputError
from rag.markdown import MarkdownFragment


SPLITTER_VERSION = "pdf-paragraphs-v2"
RISK_FLAGS = {"possible_columns_or_table", "suspected_reading_order", "suspected_character_mapping"}


@dataclass(frozen=True)
class PDFChunk:
    file_page: int
    fragment: MarkdownFragment
    split_method: str
    warnings: tuple[str, ...]


def split_config(max_chars=1200):
    if type(max_chars) is not int or max_chars < 32:
        raise InputError("PDF chunk max_chars must be an integer >= 32")
    return {"splitter_version": SPLITTER_VERSION, "max_chars": max_chars,
            "boundaries": "blank-line-runs-only", "fallback": "bounded-whitespace-windows",
            "risk_flags": sorted(RISK_FLAGS), "cross_page_merge": False}


def _paragraph_ranges(text):
    # A single layout newline is never a paragraph boundary. CRLF is one newline.
    lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n|$)", text)
    if lines and lines[-1] == "":
        lines.pop()
    cuts, offset, start, content = [], 0, 0, False
    for i, line in enumerate(lines):
        content = content or bool(line.strip())
        offset += len(line)
        if (not line.strip() and content and i + 1 < len(lines)
                and lines[i + 1].strip()):
            cuts.append((start, offset))
            start, content = offset, False
    if start < len(text):
        cuts.append((start, len(text)))
    return cuts


def _windows(text, start, end, limit):
    while start < end:
        stop = min(start + limit, end)
        if stop < end:
            # Prefer an existing whitespace boundary near the limit. Never insert
            # characters or erase hyphenation; hard-cut long unbroken runs.
            candidates = [start + m.end() for m in re.finditer(r"\s+", text[start:stop])
                          if m.end() >= limit * 0.6]
            if candidates:
                stop = candidates[-1]
            if text[stop - 1:stop + 1] == "\r\n":
                stop -= 1
        yield start, stop
        start = stop


def split_pdf_pages(report, config):
    if config != split_config(config.get("max_chars")):
        raise InputError("Unknown or incompatible PDF splitter configuration")
    chunks = []
    for page in report.pages:
        if page.status != "text_pending_review":
            continue
        ranges = _paragraph_ranges(page.raw_text)
        risky = bool(RISK_FLAGS.intersection(page.warnings))
        reliable = len(ranges) > 1 and not risky
        if not reliable:
            ranges = [(0, len(page.raw_text))]
        for begin, end in ranges:
            bounded = end - begin > config["max_chars"]
            method = ("blank_line_paragraph" if reliable and not bounded else
                      "paragraph_bounded_window" if reliable else "fallback_bounded_window")
            warnings = ["paragraph_boundaries_pending_manual_review"]
            if not reliable:
                warnings.append("unreliable_page_boundaries")
            if risky:
                warnings.append("layout_or_character_risk_forced_fallback")
            if bounded:
                warnings.append("length_boundary_not_semantic")
            for start, stop in _windows(page.raw_text, begin, end, config["max_chars"]):
                raw = page.raw_text[start:stop]
                if not raw.strip():
                    # Whitespace-only tails stay in the stored page, not in the index.
                    continue
                line_ends = [m.end() for m in re.finditer(r"\r\n|\r|\n", page.raw_text)]
                start_line = 1 + sum(position <= start for position in line_ends)
                end_line = 1 + sum(position <= stop - 1 for position in line_ends)
                fragment = MarkdownFragment(raw, " ".join(raw.casefold().split()), (), start, stop,
                                            max(1, start_line), max(1, end_line), ())
                chunks.append(PDFChunk(page.file_page, fragment, method, tuple(warnings)))
    return tuple(chunks)


def plan_fingerprint(chunks):
    return hashlib.sha256(json.dumps([asdict(c) for c in chunks], ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
