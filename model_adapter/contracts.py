from dataclasses import dataclass, field
from typing import Protocol
from core.models import ExecutionStatus
from core.validation import ContractError


class ModelConnectionError(RuntimeError):
    code = "MODEL_CONNECTION_FAILED"
    def __init__(self):
        super().__init__("Model connection failed; provider details withheld")


class ModelTimeoutError(TimeoutError):
    code = "MODEL_TIMEOUT"
    def __init__(self):
        super().__init__("Model request timed out")


class ModelRateLimitError(RuntimeError):
    code = "MODEL_RATE_LIMITED"
    def __init__(self):
        super().__init__("Model service rate limited the request")


class ModelAuthenticationError(ModelConnectionError):
    code = "MODEL_AUTHENTICATION_FAILED"
    def __init__(self):
        RuntimeError.__init__(self, "Model authentication failed; check local credential configuration")


class ModelBalanceError(ModelConnectionError):
    code = "MODEL_INSUFFICIENT_BALANCE"
    def __init__(self):
        RuntimeError.__init__(self, "Model account balance insufficient")


class ModelRequestError(ModelConnectionError):
    code = "MODEL_REQUEST_REJECTED"
    def __init__(self):
        RuntimeError.__init__(self, "Model API rejected request parameters")


class ModelServiceError(ModelConnectionError):
    code = "MODEL_SERVICE_UNAVAILABLE"
    def __init__(self):
        RuntimeError.__init__(self, "Model service unavailable")


class ModelOutputError(ContractError):
    code = "MODEL_OUTPUT_ERROR"
    def __init__(self, diagnostic=None):
        self.diagnostic = diagnostic
        message = "Model output violates structured generation contract"
        if diagnostic:
            message = "{stage}: {field_path}: {constraint}".format(**diagnostic)
        super().__init__(message, diagnostic)


class ModelBudgetError(RuntimeError):
    code = "MODEL_CALL_BUDGET_EXHAUSTED"
    def __init__(self):
        super().__init__("Model request budget exhausted")


@dataclass(frozen=True)
class ModelSettings:
    model_id: str
    timeout_seconds: float = 30.0
    max_output_tokens: int = 1200
    max_response_chars: int = 24000
    endpoint: str | None = field(default=None, repr=False)
    credential_env: str | None = None


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelRequest:
    model_id: str
    messages: tuple[ModelMessage, ...]
    max_output_tokens: int
    prompt_version: str
    correction: bool = False


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_amount: float | None = None
    currency: str | None = None
    cache_hit_tokens: int | None = None
    cache_miss_tokens: int | None = None


@dataclass(frozen=True)
class ModelCostEstimate:
    status: str
    price_date: str
    source_url: str
    usd_lower: float | None = None
    usd_upper: float | None = None
    note: str = "Estimate only, not a provider invoice"


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model_id: str | None = None
    usage: ModelUsage | None = None
    finish_reason: str | None = None
    cost_estimate: ModelCostEstimate | None = None


@dataclass(frozen=True)
class ModelCallRecord:
    call_number: int
    requested_model_id: str
    prompt_version: str
    correction: bool
    status: ExecutionStatus
    duration_ms: int
    returned_model_id: str | None = None
    usage: ModelUsage | None = None
    finish_reason: str | None = None
    error_code: str | None = None
    output_status: str = "not_checked"
    cost_estimate: ModelCostEstimate | None = None
    validation_error: dict | None = None
    diagnostic_path: str | None = None
    response_contract_version: str | None = None
    candidate_catalog_path: str | None = None
    input_snapshot_path: str | None = None
    request_metrics: dict | None = None


class ModelAdapter(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Implement explicit provider transport; never log credentials or raw errors.

        Honor request.max_output_tokens and own transport timeouts. Convert
        connection/429/timeout errors to the typed exceptions in this module.
        No implicit retry. Return only service-reported usage, otherwise None.
        """
        ...
