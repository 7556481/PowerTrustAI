"""Literal answer units; offsets are computed, never requested from a model."""
from core.models import AnswerDraft, CitationBinding
from core.validation import validate_answer
from services.validation_diagnostics import ErrorCollector

UNIT_INSTRUCTIONS = """Return answer_units, a nonempty JSON array. Each unit has EXACT
keys kind, text, evidence_ids. kind is technical, clarification, or scope.
text is your final answer sentence/paragraph, NOT a copied citation descriptor.
evidence_ids is an array of existing input Evidence IDs; [] is allowed for
clarifying questions, scope statements and explicitly unsupported conclusions.
An uncited technical statement is NOT verified. Unit kind is descriptive, not an
exemption from claim extraction or review. Preserve text including newlines.
Do not return answer_id, version, body text, quotes, offsets, or citation objects.
The program joins units with two newline characters and binds each cited unit.
Example: [{"kind":"scope","text":"A plant-specific conclusion cannot be drawn.",
"evidence_ids":[]},{"kind":"clarification","text":"What operating point was studied?",
"evidence_ids":[]}]. Evidence IDs in examples are not supplied IDs."""


def assemble(value, answer_id, version, evidence, *, stage="generation"):
    errors = ErrorCollector(stage)
    errors.fields(value, {"answer_units", "assumptions", "missing_information"}, {"evidence_sufficient", "changes", "unresolved_finding_ids"}, "$")
    units = value.get("answer_units", []) if type(value) is dict else []
    errors.check(type(units) is list and bool(units), "$.answer_units", "nonempty_unit_array_required")
    known = {e.evidence_id for e in evidence}
    for key in ("assumptions", "missing_information"):
        items = value.get(key) if type(value) is dict else None
        errors.check(type(items) is list and all(type(i) is str and i.strip() for i in items), "$."+key, "nonempty_string_array_required")
    if type(units) is list:
        for i, unit in enumerate(units):
            path = f"$.answer_units[{i}]"
            if not errors.fields(unit, {"kind", "text", "evidence_ids"}, set(), path):
                continue
            errors.check(unit["kind"] in ("technical", "clarification", "scope"), path+".kind", "known_unit_kind_required")
            errors.check(type(unit["text"]) is str and bool(unit["text"].strip()), path+".text", "nonempty_literal_text_required")
            ids = unit["evidence_ids"]
            if errors.check(type(ids) is list and all(type(e) is str for e in ids), path+".evidence_ids", "string_array_required"):
                errors.check(set(ids) <= known, path+".evidence_ids", "existing_input_evidence_ids_required")
                errors.check(len(ids) == len(set(ids)), path+".evidence_ids", "duplicate_ids_not_allowed")
    errors.finish()
    parts, bindings, offset = [], [], 0
    for unit in units:
        if parts:
            offset += 2
        text = unit["text"]
        if unit["evidence_ids"]:
            bindings.append(CitationBinding(offset, offset+len(text), tuple(unit["evidence_ids"])))
        parts.append(text)
        offset += len(text)
    answer = AnswerDraft(answer_id, version, "\n\n".join(parts),
        tuple(value["assumptions"]), tuple(value["missing_information"]), tuple(bindings))
    validate_answer(answer, evidence)
    return answer
