"""Retrieve and generate a draft only; no verification, revision or overall pass."""
import argparse
import asyncio
from dataclasses import asdict
import importlib
import json
from pathlib import Path

from agents.generation import EvidenceGenerationAgent
from core.models import TaskMode, TaskRequest
from core.validation import InputError
from harness.contracts import RunBudget, RetrievalSettings
from harness.runtime import OfflineHarness
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from rag.retriever import AsyncSQLiteBM25Retriever


OFFICIAL_QUESTIONS = (
    "How is dynamic reactive reserve defined, and does short STATCOM overload capability count?",
    "What limitations does QV analysis have for identifying wide-area voltage stability problems?",
    "What limits a synchronous generator's reactive power capability?",
    "Is normal bus voltage sufficient to prove voltage stability? Explain what the evidence actually establishes.",
    "What are the current Chinese provincial mandatory voltage stability limits for a specific plant?",
)


def citation_map(result):
    known = {e.evidence_id: e for e in result.evidence}
    if result.answer is None:
        return []
    return [{"answer_chars": [c.start_offset, c.end_offset],
             "answer_text": result.answer.text[c.start_offset:c.end_offset],
             "references": [asdict(known[eid]) for eid in c.evidence_ids]}
            for c in result.answer.citations]


async def generate(args, adapter, settings, *, on_result=None, stop_on_service_failure=False):
    questions = OFFICIAL_QUESTIONS if args.official_five else (args.question,)
    outputs = []
    with AsyncSQLiteBM25Retriever(args.db) as retriever:
        harness = OfflineHarness(EvidenceGenerationAgent(adapter, settings,diagnostic_dir=getattr(args,"diagnostic_dir",None),schema_version=getattr(args,"generation_contract_version",2)), None, None, None, None,
                                  retriever=retriever, retrieval_settings=RetrievalSettings())
        for i, question in enumerate(questions, 1):
            request = TaskRequest(f"{getattr(args,'task_id_prefix','generation')}-{i}", TaskMode.QUESTION_ANSWER,
                                  "voltage_stability_reactive_support", question,
                                  user_context=getattr(args,"user_context",""),
                                  engineering_context=getattr(args,"engineering_context",None))
            result = await harness.run(request, RunBudget(max_model_calls=args.max_calls,
                max_duration_seconds=args.duration, step_timeout_seconds=args.step_timeout),
                knowledge_version=args.knowledge_version, generation_only=True,
                answer_requirements=tuple(args.requirement))
            outputs.append({"question": question, "scope": "SIMULATED_MODEL_INTEGRATION_ONLY" if args.simulate_fixture
                            else "CONFIGURED_MODEL_GENERATION_ONLY_UNAUDITED",
                "human_review": "pending", "result": asdict(result), "citation_map": citation_map(result)})
            if on_result:
                on_result(outputs)
            if stop_on_service_failure and any(issue.code in (
                    "MODEL_AUTHENTICATION_FAILED", "MODEL_INSUFFICIENT_BALANCE", "MODEL_RATE_LIMITED",
                    "MODEL_CONNECTION_FAILED", "MODEL_SERVICE_UNAVAILABLE", "MODEL_TIMEOUT", "TIMEOUT")
                    for issue in result.execution_issues):
                break
    return {"scope": "DRAFTS ONLY; NO FACTUAL OR DOMAIN AUDIT", "real_trial": not args.simulate_fixture,
            "usage_note": "null usage/cost means unknown, never an estimate", "runs": outputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--knowledge-version", required=True)
    parser.add_argument("--question")
    parser.add_argument("--official-five", action="store_true")
    parser.add_argument("--requirement", action="append", default=[])
    parser.add_argument("--adapter-factory", help="Explicit import path module:factory(settings), no default provider")
    parser.add_argument("--simulate-fixture", action="store_true", help="Explicit simulation, not a real trial")
    parser.add_argument("--model-id")
    parser.add_argument("--endpoint", help="Only if required by the explicitly selected provider factory")
    parser.add_argument("--credential-env", help="Name only; value read privately by provider factory")
    parser.add_argument("--model-timeout", type=float, default=30)
    parser.add_argument("--max-output-tokens", type=int, default=1200)
    parser.add_argument("--max-response-chars", type=int, default=24000)
    parser.add_argument("--max-calls", type=int, default=2)
    parser.add_argument("--generation-contract-version", type=int, choices=(2,3), default=3)
    parser.add_argument("--duration", type=float, default=180)
    parser.add_argument("--step-timeout", type=float, default=70)
    parser.add_argument("--output", help="UTF-8 JSON under ignored data/retrieval_local")
    args = parser.parse_args()
    if args.official_five == bool(args.question):
        parser.error("Specify exactly one of --question or --official-five")
    if args.output and not Path(args.output).resolve().is_relative_to(Path("data/retrieval_local").resolve()):
        parser.error("Evidence/answer output must remain in ignored data/retrieval_local")
    if args.simulate_fixture:
        if args.adapter_factory or args.model_id or args.endpoint or args.credential_env:
            parser.error("Simulation cannot be combined with real provider configuration")
        from model_adapter.fixtures import FixtureAdapter
        adapter = FixtureAdapter()
        model_id = "synthetic_fixture"
    else:
        if not args.adapter_factory or not args.model_id:
            parser.error("No generation service configured: require explicit --adapter-factory and --model-id; real trial not completed")
        model_id = args.model_id
        adapter = None
    settings = ModelSettings(model_id, args.model_timeout, args.max_output_tokens,
                             args.max_response_chars, args.endpoint, args.credential_env)
    try:
        ModelClient(adapter, settings)  # Validate config before importing provider code.
        if adapter is None:
            try:
                module, name = args.adapter_factory.split(":", 1)
                adapter = getattr(importlib.import_module(module), name)(settings)
            except InputError:
                parser.exit(2, "Model credential/configuration missing or invalid; details withheld\n")
            except Exception:
                parser.exit(2, "Configured adapter factory failed; provider details withheld\n")
        payload = asyncio.run(generate(args, adapter, settings))
    except InputError:
        parser.exit(2, "Invalid generation input/settings; details withheld\n")
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(path.resolve()), "scope": payload["scope"],
            "real_trial": payload["real_trial"], "drafts": [{"question": r["question"],
            "state": r["result"]["state"], "answer": r["result"]["answer"],
            "model_records": r["result"]["model_records"],
            "sources": [{"evidence_id": e["evidence_id"], "source_type": e["source_type"],
                "applicability": e["applicability"], "locator": e["locator"],
                "file_page": None if e["provenance"] is None else e["provenance"]["file_page"],
                "quality_warnings": [] if e["provenance"] is None else
                    list(e["provenance"]["quality_warnings"]) + list(e["provenance"]["split_warnings"])}
                for e in r["result"]["evidence"]]} for r in payload["runs"]]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
