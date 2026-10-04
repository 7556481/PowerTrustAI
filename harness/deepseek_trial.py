"""One short official connection test, then at most five unaudited drafts."""
import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import re

from core.validation import InputError
from model_adapter.contracts import ModelMessage, ModelSettings
from model_adapter.deepseek import create_adapter, PRICE_DATE, PRICE_SOURCE
from model_adapter.runtime import ModelClient, ModelBudget
from harness.generation_demo import generate


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_project_env(path=None, environ=None):
    """Load literal KEY=VALUE pairs; no interpolation, execution or overwrite."""
    path = PROJECT_ROOT / ".env" if path is None else Path(path)
    environ = os.environ if environ is None else environ
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return
    except (OSError, UnicodeError):
        raise InputError("Cannot read project .env as UTF-8") from None
    pairs = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or "\x00" in value:
            raise InputError(f"Invalid project .env entry at line {number}")
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise InputError(f"Invalid project .env quoting at line {number}")
            value = value[1:-1]
        pairs.append((key, value))
    # Validate the whole file before changing the environment. Existing even-empty
    # values and the first duplicate in the file take precedence.
    for key, value in pairs:
        environ.setdefault(key, value)


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fee_summary(records):
    available = [r["cost_estimate"] for r in records if r.get("cost_estimate")
                 and r["cost_estimate"]["usd_lower"] is not None]
    return {"price_date": PRICE_DATE, "source": PRICE_SOURCE, "currency": "USD",
            "known_estimate_requests": len(available), "total_request_records": len(records),
            "usd_lower_known_only": sum(e["usd_lower"] for e in available) if available else None,
            "usd_upper_known_only": sum(e["usd_upper"] for e in available) if available else None,
            "complete_estimate": bool(records) and len(available) == len(records),
            "note": "Peak/off-peak range; incomplete estimates exclude unknown charges. Not a bill."}


async def run_trial(args, adapter, settings, checkpoint=None):
    payload = {"scope": "REAL DEEPSEEK GENERATION ONLY; NO AUDIT PASS", "price_date": PRICE_DATE,
               "model_requested": settings.model_id, "knowledge_version": args.knowledge_version,
               "connection": {"status": "not_started"}, "runs": [], "real_generation_completed": False}
    client, budget = ModelClient(adapter, settings), ModelBudget(limit=1)
    try:
        response, number = await client.complete((ModelMessage("system", "Return JSON only: {\"ok\":true}."),
            ModelMessage("user", "Connection test: return the JSON object only.")), "deepseek-connection-v1", budget)
        if json.loads(response.text) != {"ok": True}:
            raise ValueError()
        budget.annotate(number, "valid_connection_json")
        payload["connection"] = {"status": "succeeded", "records": [asdict(r) for r in budget.records]}
    except Exception as exc:
        payload["connection"] = {"status": "failed", "code": getattr(exc, "code", "MODEL_OUTPUT_ERROR"),
                                 "records": [asdict(r) for r in budget.records]}
        payload["cost_summary"] = fee_summary(payload["connection"]["records"])
        if checkpoint:
            checkpoint(payload)
        return payload
    if checkpoint:
        checkpoint(payload)
    if not args.connection_only:
        # Separate output cap for drafts; same adapter, same no-retry transport.
        from dataclasses import replace
        draft_settings = replace(settings, max_output_tokens=args.draft_max_tokens,
                                 max_response_chars=24000)
        def update(completed):
            payload["runs"] = completed[:]
            if checkpoint:
                checkpoint(payload)
        generated = await generate(args, adapter, draft_settings, on_result=update, stop_on_service_failure=True)
        payload["runs"] = generated["runs"]
        payload["real_generation_completed"] = len(payload["runs"]) == 5 and all(
            item["result"]["state"] == "generated" for item in payload["runs"])
    records = payload["connection"]["records"] + [r for item in payload["runs"] for r in item["result"]["model_records"]]
    payload["cost_summary"] = fee_summary(records)
    payload["initial_generations"] = sum(1 for r in records if not r["correction"] and r["prompt_version"] != "deepseek-connection-v1")
    payload["format_corrections"] = sum(1 for r in records if r["correction"])
    if checkpoint:
        checkpoint(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        load_project_env()
    except InputError as exc:
        parser.error(str(exc))
    parser.add_argument("--db")
    parser.add_argument("--knowledge-version")
    parser.add_argument("--model-id", default=os.environ.get("DEEPSEEK_MODEL_ID"))
    parser.add_argument("--endpoint", default="https://api.deepseek.com")
    parser.add_argument("--connection-only", action="store_true")
    parser.add_argument("--model-timeout", type=float, default=45)
    parser.add_argument("--draft-max-tokens", type=int, default=1800)
    parser.add_argument("--output", default="data/retrieval_local/deepseek/official-trial.json")
    args = parser.parse_args()
    output = Path(args.output)
    if not output.resolve().is_relative_to(Path("data/retrieval_local").resolve()):
        parser.error("Private trial output must remain under data/retrieval_local")
    if not args.model_id:
        parser.error("Explicit --model-id or DEEPSEEK_MODEL_ID required")
    if not args.connection_only and (not args.db or not args.knowledge_version):
        parser.error("Five questions require --db and fixed --knowledge-version")
    # Explicit bounded experiment, never user-configurable expansion of batch size.
    args.official_five, args.question, args.simulate_fixture = True, None, False
    args.max_calls, args.duration, args.step_timeout = 2, 180, 110
    args.requirement = ["Preserve qualifications and clearly state evidence coverage limits. Draft only; no audit pass."]
    args.generation_contract_version = 3
    settings = ModelSettings(args.model_id, args.model_timeout, 48, 1024, args.endpoint, "DEEPSEEK_API_KEY")
    try:
        ModelClient(None, settings)
        if args.draft_max_tokens <= 0:
            raise InputError("Invalid output limit")
        from dataclasses import replace
        adapter = create_adapter(replace(settings, max_output_tokens=args.draft_max_tokens, max_response_chars=24000))
    except InputError:
        save(output, {"scope": "NOT RUN", "status": "configuration_missing_or_invalid",
                      "real_generation_completed": False, "remote_requests": 0,
                      "message": "Configure official endpoint, model ID and DEEPSEEK_API_KEY locally; no secret logged"})
        parser.exit(2, "DeepSeek configuration missing/invalid; no remote requests made\n")
    try:
        result = asyncio.run(run_trial(args, adapter, settings, lambda payload: save(output, payload)))
    finally:
        adapter.close()
    print(json.dumps({"output": str(output.resolve()), "connection": result["connection"]["status"],
        "states": [r["result"]["state"] for r in result["runs"]],
        "cost_summary": result.get("cost_summary"), "scope": result["scope"]}, ensure_ascii=False, indent=2))
    if result["connection"]["status"] != "succeeded" or (not args.connection_only and
            any(r["result"]["state"] != "generated" for r in result["runs"])):
        parser.exit(1)


if __name__ == "__main__":
    main()
