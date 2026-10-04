"""Adapter-layer limits and per-run request accounting, independent of prompts."""
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
import os
from time import perf_counter

from core.models import ExecutionStatus
from core.validation import ContractError, InputError, require, validate_types
from model_adapter.contracts import *


_scope = ContextVar("powertrust_model_budget", default=None)
_invocation = ContextVar("powertrust_model_invocation", default=None)


@contextmanager
def model_invocation_scope(invocation_id, component, answer_version):
    """Inherited by wait_for/child tasks; the shared budget remains run-owned."""
    token = _invocation.set((invocation_id, component, answer_version))
    try:
        yield
    finally:
        _invocation.reset(token)


class ModelBudget:
    def __init__(self, limit=2, deadline=None, reserve=None):
        self.limit, self.deadline, self.reserve = limit, deadline, reserve
        self.used = 0
        self.records = []

    def claim(self):
        if self.deadline is not None and perf_counter() >= self.deadline:
            raise ModelTimeoutError()
        if self.used >= self.limit:
            raise ModelBudgetError()
        number = self.reserve() if self.reserve else self.used + 1
        self.used += 1
        return number

    def annotate(self, number, status, diagnostic=None, diagnostic_path=None):
        for i, record in enumerate(self.records):
            if record.call_number == number:
                self.records[i] = replace(record, output_status=status, validation_error=diagnostic,
                                          diagnostic_path=diagnostic_path)


@contextmanager
def model_scope(budget):
    token = _scope.set(budget)
    try:
        yield
    finally:
        _scope.reset(token)


def current_budget():
    return _scope.get()


def credential_from_environment(settings):
    """Only an explicitly configured factory uses this; never enumerate env vars."""
    if not settings.credential_env:
        return None
    value = os.environ.get(settings.credential_env)
    if not value:
        raise InputError("Configured model credential is missing")
    return value


class ModelClient:
    def __init__(self, adapter, settings):
        try:
            validate_types(settings, ModelSettings)
            require(bool(settings.model_id.strip()), "Explicit model_id required")
            require(settings.timeout_seconds > 0 and settings.max_output_tokens > 0
                    and settings.max_response_chars > 0, "Invalid model limits")
        except ContractError as exc:
            raise InputError(str(exc)) from exc
        self.adapter, self.settings = adapter, settings

    async def complete(self, messages, prompt_version, budget, correction=False, *, response_contract_version=None, candidate_catalog_path=None, input_snapshot_path=None):
        owner = _invocation.get() or (None, None, None)
        number = budget.claim()
        started, response = perf_counter(), None
        status, code = ExecutionStatus.SUCCEEDED, None
        try:
            remaining = self.settings.timeout_seconds
            if budget.deadline is not None:
                remaining = min(remaining, budget.deadline - started)
            if remaining <= 0:
                raise ModelTimeoutError()
            request = ModelRequest(self.settings.model_id, messages, self.settings.max_output_tokens,
                                   prompt_version, correction)
            try:
                candidate = await asyncio.wait_for(self.adapter.complete(request), remaining)
            except TimeoutError:
                raise ModelTimeoutError() from None
            except (ModelConnectionError, ModelRateLimitError, ModelOutputError):
                raise
            except asyncio.CancelledError:
                raise
            except Exception:
                # Provider exceptions may embed headers, URLs, credentials or body.
                raise ModelConnectionError() from None
            try:
                validate_types(candidate, ModelResponse)
                if candidate.usage:
                    for value in (candidate.usage.input_tokens, candidate.usage.output_tokens,
                                  candidate.usage.total_tokens, candidate.usage.cost_amount,
                                  candidate.usage.cache_hit_tokens, candidate.usage.cache_miss_tokens):
                        require(value is None or value >= 0, "Invalid service usage")
                response = candidate
                require(len(response.text) <= self.settings.max_response_chars, "Response size exceeded")
                require(response.finish_reason not in ("length", "max_tokens"), "Truncated output")
                require(not response.usage or response.usage.output_tokens is None or
                        response.usage.output_tokens <= self.settings.max_output_tokens, "Output token limit exceeded")
            except ContractError:
                error = ModelOutputError()
                # Private handoff for opt-in diagnostics only; exception text is
                # still generic and never contains model response material.
                error._response_for_diagnostics = response
                raise error from None
            return response, number
        except asyncio.CancelledError:
            status, code = ExecutionStatus.CANCELLED, "MODEL_CANCELLED"
            raise
        except Exception as exc:
            status = ExecutionStatus.TIMED_OUT if isinstance(exc, TimeoutError) else ExecutionStatus.FAILED
            code = getattr(exc, "code", "MODEL_CONNECTION_FAILED")
            exc.model_call_number = number
            raise
        finally:
            from services.request_metrics import measure
            budget.records.append(ModelCallRecord(number, self.settings.model_id, prompt_version, correction,
                status, max(0, int((perf_counter() - started) * 1000)),
                None if response is None else response.model_id,
                None if response is None else response.usage,
                None if response is None else response.finish_reason, code,
                cost_estimate=None if response is None else response.cost_estimate,
                response_contract_version=response_contract_version,candidate_catalog_path=candidate_catalog_path,input_snapshot_path=input_snapshot_path,
                request_metrics=measure(messages),invocation_id=owner[0],component=owner[1],answer_version=owner[2]))
