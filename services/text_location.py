"""Literal Python character positioning; no fuzzy repair or normalization."""
import re
from core.validation import require


def sentence_spans(text):
    # Conservative deterministic sentence/paragraph units, not a linguistic parser.
    spans, start = [], 0
    pattern = r'[。！？][\"\u201d\u2019\']*|[.!?][\"\u201d\u2019\']*(?=\s|$)|\n\s*\n'
    for match in re.finditer(pattern, text):
        end = match.end()
        while start < end and text[start].isspace():
            start += 1
        trimmed = end
        while trimmed > start and text[trimmed - 1].isspace():
            trimmed -= 1
        if start < trimmed:
            spans.append((start, trimmed))
        start = end
    while start < len(text) and text[start].isspace():
        start += 1
    end = len(text.rstrip())
    if start < end:
        spans.append((start, end))
    return tuple(spans)


def boundary_warnings(text, start, end):
    spans = sentence_spans(text)
    warnings = []
    if start not in {s for s, _ in spans} or end not in {e for _, e in spans}:
        warnings.append("citation_not_aligned_to_complete_sentence_or_paragraph")
    for position in (start, end):
        if 0 < position < len(text) and all(c.isascii() and (c.isalnum() or c == "_")
                                          for c in text[position - 1:position + 1]):
            warnings.append("citation_boundary_inside_word")
    return tuple(dict.fromkeys(warnings))


def resolve_span(text, quote, prefix="", suffix="", *, sentence=False):
    require(type(text) is str and type(quote) is str and bool(quote.strip()), "Invalid exact quote")
    require(type(prefix) is str and type(suffix) is str, "Invalid disambiguation context")
    matches, offset = [], 0
    while True:
        start = text.find(quote, offset)
        if start < 0:
            break
        end = start + len(quote)
        if text[:start].endswith(prefix) and text[end:].startswith(suffix):
            matches.append((start, end))
        offset = start + 1
    require(len(matches) == 1, "Exact quote missing or ambiguous; provide unique literal prefix/suffix")
    start, end = matches[0]
    warnings = boundary_warnings(text, start, end)
    require("citation_boundary_inside_word" not in warnings, "Quote boundary inside word")
    require(not sentence or not warnings, "Quote must cover complete sentence/paragraph units")
    return start, end


def locate_descriptor(text, value, *, sentence=False):
    require(type(value) is dict and {"quote"} <= set(value) <= {"quote", "prefix", "suffix"}, "Invalid quote descriptor")
    return resolve_span(text, value["quote"], value.get("prefix", ""), value.get("suffix", ""), sentence=sentence)
