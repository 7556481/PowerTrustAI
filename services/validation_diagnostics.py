"""Safe structured-output errors: static constraints, never echo model values."""
from core.validation import ContractError


class StructuredValidationError(ContractError):
    def __init__(self, stage, path, constraint):
        self.diagnostic = {"stage": stage, "field_path": path, "constraint": constraint}
        super().__init__(f"{stage}: {path}: {constraint}", self.diagnostic)


class ValidationErrors(ContractError):
    def __init__(self, errors):
        self.diagnostics = tuple(errors)
        self.diagnostic = dict(errors[0], errors=list(errors))
        first = errors[0]
        super().__init__(f"{first['stage']}: {first['field_path']}: {first['constraint']} ({len(errors)} detected errors)", self.diagnostic)


class ErrorCollector:
    def __init__(self, stage="evidence_verification"):
        self.stage, self.errors = stage, []

    def check(self, condition, path, constraint):
        if not condition:
            self.errors.append({"stage": self.stage, "field_path": path, "constraint": constraint})
        return bool(condition)

    def capture(self, fn):
        try:
            return fn()
        except ContractError as exc:
            diagnostic = getattr(exc, "diagnostic", None)
            if not diagnostic:
                raise  # Never convert an unknown programming failure into a fake validation fact.
            self.errors.extend(diagnostic.get("errors", [diagnostic]))
            return None

    def fields(self, value, required, optional, path):
        if not self.check(type(value) is dict, path, "expected_object"):
            return False
        for name in sorted(required):
            self.check(name in value, f"{path}.{name}", "required_field_missing")
        if not self.check(set(value) <= required | optional, path, "unexpected_fields_not_allowed"):
            self.errors[-1].update(allowed_fields=sorted(required|optional),required_fields=sorted(required),
                processing_options=["return_only_declared_fields","do_not_echo_program_binding_or_other_check_fields"])
        return required <= set(value)

    def finish(self):
        if self.errors:
            raise ValidationErrors(self.errors)


def check(condition, path, constraint, stage="claim_extraction"):
    if not condition:
        raise StructuredValidationError(stage, path, constraint)


def object_fields(value, required, optional, path, stage="claim_extraction"):
    check(type(value) is dict, path, "expected_object", stage)
    for name in sorted(required):
        check(name in value, f"{path}.{name}", "required_field_missing", stage)
    check(set(value) <= required | optional, path, "unexpected_fields_not_allowed", stage)


def source_span(text, item, path, *, stage="claim_extraction", sentence=True):
    from services.text_location import boundary_warnings, resolve_span
    for name in ("quote", "prefix", "suffix"):
        if name in item:
            check(type(item[name]) is str, f"{path}.{name}", "expected_string", stage)
    check(bool(item["quote"].strip()), f"{path}.quote", "nonempty_exact_source_quote_required", stage)
    quote, prefix, suffix = item["quote"], item.get("prefix", ""), item.get("suffix", "")
    matches, offset = [], 0
    while True:
        start = text.find(quote, offset)
        if start < 0:
            break
        end = start + len(quote)
        if text[:start].endswith(prefix) and text[end:].startswith(suffix):
            matches.append((start, end))
        offset = start + 1
    check(bool(matches), f"{path}.quote", "exact_source_quote_with_adjacent_context_not_found", stage)
    check(len(matches) == 1, f"{path}.quote", "ambiguous_quote_requires_literal_prefix_or_suffix", stage)
    start, end = matches[0]
    warnings = boundary_warnings(text, start, end)
    check("citation_boundary_inside_word" not in warnings, f"{path}.quote", "boundary_inside_word", stage)
    check(not sentence or not warnings, f"{path}.quote", "complete_sentence_or_paragraph_boundaries_required", stage)
    # Keep the shared locator as the final authority; no fuzzy fallback.
    return resolve_span(text, quote, prefix, suffix, sentence=sentence)
