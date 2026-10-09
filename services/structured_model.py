"""One initial structured request, at most one explicit budgeted correction."""
import json
from core.validation import ContractError
from model_adapter.contracts import ModelMessage, ModelOutputError
from model_adapter.runtime import ModelBudget, current_budget
from services.validation_diagnostics import StructuredValidationError


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise StructuredValidationError("json_parse", "$", "duplicate_object_keys_not_allowed")
        value[key] = item
    return value


def strict_json(text):
    return json.loads(text, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          StructuredValidationError("json_parse", "$", "nonfinite_numbers_not_allowed")))


async def structured_request(client, messages, prompt_version, parser, *, diagnostics=None, response_contract_version=None, candidate_catalog_path=None, input_snapshot_path=None,max_corrections=1,max_message_chars=None,correction_context=None):
    budget = current_budget() or ModelBudget(limit=2)
    request_numbers = []
    partial=None
    if max_corrections not in (0,1):raise ValueError("At most one format correction allowed")
    for correction in ((False,True) if max_corrections else (False,)):
        if max_message_chars is not None:
            from services.citation_workload import messages_size, ReviewCapacityError
            if messages_size(messages) > max_message_chars:
                error = ReviewCapacityError('Complete review/correction message exceeds configured capacity')
                if partial is not None:error.partial_output=partial
                raise error
        request_messages_path=None if diagnostics is None else diagnostics.save_messages(messages,prompt_version,correction)
        try:
            response, number = await client.complete(messages, prompt_version, budget, correction,
                                                    response_contract_version=response_contract_version,
                                                    candidate_catalog_path=candidate_catalog_path,input_snapshot_path=input_snapshot_path)
            request_numbers.append(number)
        except Exception as exc:
            if partial is not None:exc.partial_output=partial
            response = getattr(exc, "_response_for_diagnostics", None)
            if diagnostics is not None and response is not None:
                record = next(r for r in budget.records if r.call_number == exc.model_call_number)
                diagnostic = {"stage":"model_response", "field_path":"$.finish_reason",
                    "constraint":"complete_bounded_response_required", "finish_reason":response.finish_reason}
                path = diagnostics.save(response, record, diagnostic,request_messages_path=request_messages_path)
                budget.annotate(record.call_number, "invalid_model_response", diagnostic, path)
            raise
        try:
            result = parser(strict_json(response.text))
        except (ContractError, ValueError, TypeError, KeyError, RecursionError) as exc:
            partial=getattr(exc,"partial_output",partial)
            if getattr(exc, "diagnostic", None):
                diagnostic = exc.diagnostic
            elif isinstance(exc, json.JSONDecodeError):
                from services.json_nesting import diagnostic as nesting_diagnostic
                diagnostic = {"stage": "json_parse", "field_path": "$",
                              "constraint": "valid_json_required", "line": exc.lineno, "column": exc.colno,
                              **nesting_diagnostic(response.text)}
            else:
                # Other parsers may raise arbitrary exception text containing input.
                diagnostic = {"stage": "contract_validation", "field_path": "$",
                              "constraint": "structured_contract_violation"}
            budget.annotate(number, "invalid_structure", diagnostic)
            if diagnostics is not None:
                record = next(r for r in budget.records if r.call_number == number)
                path = diagnostics.save(response, record, diagnostic,request_messages_path=request_messages_path)
                budget.annotate(number, "invalid_structure", diagnostic, path)
            if correction or not max_corrections:
                error=ModelOutputError(diagnostic)
                if partial is not None:error.partial_output=partial
                raise error from None
            messages += (ModelMessage("user", json.dumps({"section": "FORMAT_CORRECTION_DATA_UNTRUSTED",
                "invalid_output": response.text,
                "validation_error": diagnostic,
                "validation_errors": diagnostic.get("errors", [diagnostic]),
                  **({"program_scope_guidance":correction_context(response.text,diagnostic)} if correction_context is not None else {}),
                "instruction": "Return valid JSON matching the original schema. For ID-only source evidence, select existing allowed candidate IDs; never copy text or change bindings. Otherwise follow the declared original field rules."},
                ensure_ascii=False)),)
        else:
            budget.annotate(number, "valid_structure")
            if diagnostics is not None:
                record = next(r for r in budget.records if r.call_number == number)
                path = diagnostics.save(response, record, None,request_messages_path=request_messages_path)
                budget.annotate(number, "valid_structure", diagnostic_path=path)
            return result, tuple(r for r in budget.records if r.call_number in request_numbers)
    raise ModelOutputError()
