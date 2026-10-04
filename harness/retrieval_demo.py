"""Official local index + simulated four-agent integration, no real knowledge audit."""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from agents.fakes import (FakeConfig, FakeGenerationAgent, FakeEvidenceVerificationAgent,
                         FakePowerDomainReviewAgent, FakeRevisionAgent, FakeClaimExtractor)
from core.models import AnswerDraft, TaskMode, TaskRequest, VerificationStatus
from core.validation import InputError
from harness.contracts import RetrievalSettings, RunBudget
from harness.runtime import OfflineHarness
from rag.contracts import ContextOptions
from rag.retriever import AsyncSQLiteBM25Retriever


async def run_demo(args):
    query = args.question
    config = FakeConfig(text="SIMULATED ANSWER: " + query, reference_input_evidence=True,
        verification_statuses=(VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED)
        if args.revise_once else (VerificationStatus.SUPPORTED,))
    mode = TaskMode(args.mode)
    request = TaskRequest("official-retrieval-simulated-agents", mode, "voltage_stability_reactive_support", query,
        existing_answer=AnswerDraft("simulated-existing", 1, config.text) if mode == TaskMode.ASSESS_EXISTING else None)
    budget = RunBudget(max_retrieval_calls=args.max_calls, max_retrieval_chars_per_call=args.per_call_chars,
        max_retrieval_chars_total=args.total_chars, step_timeout_seconds=args.step_timeout,
        max_duration_seconds=args.duration)
    with AsyncSQLiteBM25Retriever(args.db) as retriever:
        harness = OfflineHarness(FakeGenerationAgent(config), FakeEvidenceVerificationAgent(config),
            FakePowerDomainReviewAgent(config), FakeRevisionAgent(), FakeClaimExtractor(), retriever=retriever,
            retrieval_settings=RetrievalSettings(args.max_results, ContextOptions(args.context_chars, 6, 2)))
        result = await harness.run(request, budget, knowledge_version=args.knowledge_version)
        # Retain exact agent inputs to demonstrate purpose-specific evidence delivery.
        payload = {"scope": "REAL LOCAL RETRIEVAL + SIMULATED GENERATION AND REVIEW",
            "business_conclusion": "INTEGRATION TEST ONLY; NOT A REAL ANSWER OR AUDIT",
            "fixed_knowledge_version": args.knowledge_version,
            "budget": asdict(budget),
            "result": asdict(result),
            "agent_inputs": {"generation": [asdict(i) for i in harness.generation.inputs],
                             "verification": [asdict(i) for i in harness.verification.inputs],
                             "domain_review": [asdict(i) for i in harness.domain_review.inputs]}}
    return payload


def audit_sources(evidence):
    manifest_path = Path("docs/knowledge-sources/manifest.json")
    if not manifest_path.is_file():
        return {"status": "manifest_missing", "documents": []}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {d["document_id"]: d for d in manifest["documents"]}
    ids = sorted({e["provenance"]["document_id"] for e in evidence if e["provenance"]})
    audit = []
    for doc_id in ids:
        doc = records.get(doc_id)
        if doc is None:
            audit.append({"document_id": doc_id, "status": "not_in_official_manifest"})
            continue
        path = Path(doc.get("local_file") or "__unavailable__")
        sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        hashes = {e["provenance"]["file_sha256"] for e in evidence
                  if e["provenance"] and e["provenance"]["document_id"] == doc_id}
        matched = sha is not None and sha == doc.get("sha256") and hashes == {sha}
        audit.append({"document_id": doc_id, "status": "local_file_manifest_index_hash_match" if matched else "source_mismatch_or_missing",
                      "file_sha256": sha, "download_status": doc.get("download_status"),
                      "download_url": doc.get("download_url"), "local_file": doc.get("local_file")})
    return {"status": "local_metadata_check_not_fact_verification", "documents": audit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--knowledge-version", required=True)
    parser.add_argument("--question", default="Does a STATCOM's short overload capability count as reactive reserve?")
    parser.add_argument("--mode", choices=[m.value for m in TaskMode], default="question_answer")
    parser.add_argument("--revise-once", action="store_true")
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--context-chars", type=int, default=2400)
    parser.add_argument("--max-calls", type=int, default=12)
    parser.add_argument("--per-call-chars", type=int, default=16000)
    parser.add_argument("--total-chars", type=int, default=64000)
    parser.add_argument("--step-timeout", type=float, default=10)
    parser.add_argument("--duration", type=float, default=180)
    parser.add_argument("--output", help="UTF-8 JSON trace; official text must remain in ignored local directory")
    args = parser.parse_args()
    if args.output and not Path(args.output).resolve().is_relative_to(Path("data/retrieval_local").resolve()):
        parser.error("Official text output must stay under ignored data/retrieval_local")
    try:
        payload = asyncio.run(run_demo(args))
    except InputError as exc:
        parser.exit(2, f"InputError: {exc}\n")
    # Local file auditing is after the asynchronous run, not in its event loop.
    payload["source_audit"] = audit_sources(payload["result"]["evidence"])
    if args.output:
        output = Path(args.output)
        allowed = Path("data/retrieval_local").resolve()
        if not output.resolve().is_relative_to(allowed):
            parser.error("Official text output must stay under ignored data/retrieval_local")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {"output": str(output.resolve()), "scope": payload["scope"],
                   "business_conclusion": payload["business_conclusion"], "source_audit": payload["source_audit"],
                   "state": payload["result"]["state"],
                   "decision": None if payload["result"]["report"] is None else payload["result"]["report"]["decision"]["kind"],
                   "retrieval_records": payload["result"]["retrieval_records"]}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
