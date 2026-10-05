"""Official DeepSeek chat connector. Standard library, one POST, zero retries."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import socket
import ssl
from urllib.parse import urlsplit

from core.validation import InputError, ContractError, require, validate_types
from model_adapter.contracts import (ModelSettings, ModelRequest, ModelResponse, ModelUsage,
    ModelCostEstimate, ModelAuthenticationError, ModelBalanceError, ModelConnectionError,
    ModelRateLimitError, ModelRequestError, ModelServiceError, ModelTimeoutError, ModelOutputError)
from model_adapter.runtime import credential_from_environment


PRICE_DATE = "2026-10-02"
PRICE_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing/"
# USD per million tokens, cache-hit / cache-miss / output, peak. Off-peak is half.
# Provider connector metadata only; model IDs never hard-coded in generation logic.
PEAK_PRICES = {"deepseek-flash": (0.006, 0.30, 1.20), "deepseek-v4-pro": (0.044, 1.32, 3.96)}


def estimate_cost(model_id, usage):
    rates = PEAK_PRICES.get(model_id)
    if rates is None or usage is None:
        return ModelCostEstimate("unavailable", PRICE_DATE, PRICE_SOURCE,
                                 note="Unknown official model price or service usage; no estimate")
    hit, miss, output = usage.cache_hit_tokens, usage.cache_miss_tokens, usage.output_tokens
    if (None in (hit, miss, output) or usage.input_tokens is None or hit + miss != usage.input_tokens):
        return ModelCostEstimate("unavailable", PRICE_DATE, PRICE_SOURCE,
                                 note="Missing/inconsistent cache usage; cannot accurately estimate")
    peak = (hit * rates[0] + miss * rates[1] + output * rates[2]) / 1_000_000
    return ModelCostEstimate("off_peak_to_peak_range", PRICE_DATE, PRICE_SOURCE, peak / 2, peak,
        "USD range from verified off-peak/peak rates; completion billing tier unverified, not an invoice")


def _usage(value):
    if value is None:
        return None
    require(type(value) is dict, "Invalid usage")
    result = ModelUsage(value.get("prompt_tokens"), value.get("completion_tokens"), value.get("total_tokens"),
        cache_hit_tokens=value.get("prompt_cache_hit_tokens"), cache_miss_tokens=value.get("prompt_cache_miss_tokens"))
    validate_types(result, ModelUsage)
    for number in (result.input_tokens, result.output_tokens, result.total_tokens,
                   result.cache_hit_tokens, result.cache_miss_tokens):
        require(number is None or number >= 0, "Invalid usage count")
    return result


def parse_response(status, body, requested_model):
    # Never decode/forward server error bodies, which may echo sensitive headers.
    if status in (401, 403):
        raise ModelAuthenticationError()
    if status == 402:
        raise ModelBalanceError()
    if status == 429:
        raise ModelRateLimitError()
    if status >= 500:
        raise ModelServiceError()
    if status != 200:
        raise ModelRequestError()
    try:
        data = json.loads(body)
        require(type(data) is dict and type(data.get("choices")) is list and len(data["choices"]) == 1,
                "Invalid envelope")
        choice = data["choices"][0]
        require(type(choice) is dict and type(choice.get("message")) is dict, "Invalid choice")
        text = choice["message"].get("content")
        require(text is None or type(text) is str, "Invalid content")
        require(not choice["message"].get("tool_calls"), "Unexpected tool call")
        usage = _usage(data.get("usage"))
        result = ModelResponse(text or "", data.get("model"), usage, choice.get("finish_reason"),
                               estimate_cost(requested_model, usage))
        validate_types(result, ModelResponse)
        return result
    except (ContractError, ValueError, TypeError, KeyError, RecursionError):
        raise ModelOutputError() from None


class DeepSeekAdapter:
    def __init__(self, settings, *, exchange=None):
        validate_types(settings, ModelSettings)
        base = settings.endpoint or "https://api.deepseek.com"
        url = urlsplit(base)
        if (url.scheme != "https" or url.netloc != "api.deepseek.com" or url.path.rstrip("/") not in ("", "/v1")
                or url.query or url.fragment or url.username or url.password):
            raise InputError("Official connector accepts only https://api.deepseek.com[/v1]; third-party service requires explicit configuration")
        if settings.credential_env not in (None, "DEEPSEEK_API_KEY"):
            raise InputError("Official connector reads DEEPSEEK_API_KEY only")
        self.settings = settings
        self._path = url.path.rstrip("/") + "/chat/completions"
        self._exchange = exchange or self._http
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="deepseek-http")
        self._active, self._closed = None, False

    def __repr__(self):
        return "DeepSeekAdapter(official, credentials=private-environment, retries=0)"

    def _http(self, body, timeout, byte_limit):
        # Read only the one named credential, locally. No SDK/proxy/redirect/retry.
        from dataclasses import replace
        key = credential_from_environment(replace(self.settings, credential_env="DEEPSEEK_API_KEY"))
        connection = http.client.HTTPSConnection("api.deepseek.com", timeout=timeout,
                                                 context=ssl.create_default_context())
        stage = 'connect_tls'
        try:
            connection.connect()
            stage = 'send_request'
            connection.request("POST", self._path, body=body,
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "application/json"})
            stage = 'receive_response'
            response = connection.getresponse()
            stage = 'read_response'
            data = response.read(byte_limit + 1) if response.status == 200 else b""
            if len(data) > byte_limit:
                raise ModelOutputError()
            return response.status, data
        except (TimeoutError, socket.timeout):
            raise ModelTimeoutError() from None
        except (OSError, http.client.HTTPException) as exc:
            # Never retain exception text, headers, request body or credentials.
            raise ModelConnectionError({'version':'official-network-diagnostic-v1',
                'stage':stage,'exception_type':type(exc).__name__,
                'errno':getattr(exc,'errno',None),'winerror':getattr(exc,'winerror',None)}) from None
        finally:
            connection.close()

    def _work(self, body, model_id):
        try:
            status, raw = self._exchange(body, self.settings.timeout_seconds,
                                         self.settings.max_response_chars * 4 + 32768)
            return parse_response(status, raw, model_id)
        except TimeoutError:
            raise ModelTimeoutError() from None
        except (OSError, http.client.HTTPException):
            raise ModelConnectionError() from None

    async def complete(self, request):
        validate_types(request, ModelRequest)
        if self._closed or (self._active is not None and not self._active.done()):
            raise ModelConnectionError()
        payload = {"model": request.model_id, "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                   "max_tokens": request.max_output_tokens, "stream": False,
                   "response_format": {"type": "json_object"}, "thinking": {"type": "disabled"}}
        # This is the sole POST for this complete call; no fallback model or retry.
        self._active = self._executor.submit(self._work, json.dumps(payload, ensure_ascii=False).encode("utf-8"), request.model_id)
        future = asyncio.wrap_future(self._active)
        future.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        return await asyncio.shield(future)

    def close(self):
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)


def create_adapter(settings):
    # Validate destination before accessing credentials. No request at construction.
    adapter = DeepSeekAdapter(settings)
    try:
        from dataclasses import replace
        credential_from_environment(replace(settings, credential_env="DEEPSEEK_API_KEY"))
    except InputError:
        adapter.close()
        raise
    return adapter
