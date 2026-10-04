"""Bounded acceptance-preparation experiment using existing Harness and Agents.

This is a staged experiment, not a new scheduler or an output contract. Each
stage reserves its known worst-case requests, including one format correction.
"""
import argparse
import asyncio
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
from time import perf_counter

from agents.contracts import RevisionInput
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.power_domain_review import ModelPowerDomainReviewAgent
from agents.revision import ModelRevisionAgent
from core.models import AnswerDraft, TaskRequest, TaskMode, VerificationStatus
from core.validation import validate_revision
from evaluation.acceptance_preparation import PRIVATE, KNOWLEDGE, sha
from harness.contracts import RunBudget
from harness.deepseek_trial import load_project_env, fee_summary
from harness.evidence_review_demo import restore_answer, restore_evidence, restore_snapshot
from harness.policy import LimitedRepairPolicy
from harness.power_review_demo import CASES
from harness.runtime import OfflineHarness
from model_adapter.contracts import ModelSettings
from model_adapter.deepseek import create_adapter
from model_adapter.runtime import ModelBudget, model_scope
from rag.retriever import AsyncSQLiteBM25Retriever
from services.claim_extractor import ModelClaimExtractor
from services.evidence_scope import validate_snapshot


def review_worst_calls(answer):
    # Extraction + independent facts + independent domain, plus one per binding.
    # Every structured request has at most one explicit format correction.
    return 2 * (3 + len(answer.citations))


def reserve(used, cap, worst):
    if worst <= 0 or used < 0 or cap < 0:
        raise ValueError("Invalid budget preflight")
    return used + worst <= cap


def execution_complete(result):
    return (result.extraction_output is not None and result.verification_output is not None
            and result.domain_output is not None and not result.execution_issues
            and not result.verification_output.execution_issues and not result.domain_output.execution_issues
            and len(result.review_rounds) == 1)


async def experiment(args, adapter, domain_adapter, settings, checkpoint):
    baseline = json.loads((PRIVATE / getattr(args, "baseline", "acceptance-baseline-v1.json")).read_text(encoding="utf-8"))
    data = {"scope": "ACCEPTANCE_PREPARATION_REAL_DEVELOPMENT_NOT_INDEPENDENT_ACCEPTANCE",
            "baseline_id": baseline["baseline_id"], "knowledge_version": KNOWLEDGE,
            "max_requests": args.max_requests, "actual_model_calls": 0,
            "stages": [], "runs": [], "cost_summary": {}, "model_records": [],
            "budget_note": "Stage-level worst-case preflight includes one correction per request. Revised citation count is unknown before revision; it is frozen and re-preflighted afterward. An accepted revision is retained if its full rereview cannot fit; never label that loop complete."}
    records = []
    diagnostic_dir = PRIVATE / "response-diagnostics"
    policy = LimitedRepairPolicy()

    def save():
        data["actual_model_calls"] = len(records)
        data["model_records"] = [asdict(r) for r in records]
        data["cost_summary"] = fee_summary(data["model_records"])
        checkpoint(data)

    def preflight(label, worst):
        allowed = reserve(len(records), args.max_requests, worst)
        row = {"label": label, "used_before": len(records), "remaining_before": args.max_requests - len(records),
               "worst_requests": worst, "allowed": allowed, "status": "reserved" if allowed else "not_started_budget"}
        data["stages"].append(row)
        save()
        return row

    async def review(request, answer, evidence=(), snapshot=None, label="review"):
        extractor = ModelClaimExtractor(adapter, settings, diagnostic_dir=diagnostic_dir, typed_components=True)
        extraction_source = None
        if getattr(args, "reuse_frozen_extraction", False):
            from evaluation.archive_replay import find_frozen_extraction, FrozenArchivedExtraction
            extracted, extraction_source = find_frozen_extraction(args.continue_from, answer, KNOWLEDGE)
            extractor = FrozenArchivedExtraction(answer, extracted)
        row = preflight(label, review_worst_calls(answer) - (2 if extraction_source else 0))
        if extraction_source:
            row["retained_extraction_source"] = extraction_source
        if not row["allowed"]:
            return None
        before = len(records)
        with AsyncSQLiteBM25Retriever(args.db) as retriever:
            harness = OfflineHarness(None,
                ModelEvidenceVerificationAgent(adapter, settings, diagnostic_dir=diagnostic_dir, schema_version=8),
                ModelPowerDomainReviewAgent(domain_adapter, settings, diagnostic_dir=diagnostic_dir, protocol_version=2),
                None, extractor,
                policy=policy, retriever=retriever)
            result = await harness.run(replace(request, existing_answer=answer, provided_evidence=evidence),
                RunBudget(max_model_calls=row["worst_requests"], max_revision_rounds=0,
                          max_duration_seconds=500, step_timeout_seconds=110, max_retrieval_chars_total=160000),
                knowledge_version=KNOWLEDGE, indexed_reference_ids=tuple(e.evidence_id for e in evidence),
                generation_snapshot=snapshot)
        records.extend(result.model_records)
        row.update(actual_requests=len(records) - before, status="completed" if execution_complete(result) else "execution_incomplete",
                   state=result.state.value, decision=asdict(result.report.decision) if result.report else None,
                   result=asdict(result))
        assert row["actual_requests"] <= row["worst_requests"]
        save()
        return result

    if getattr(args, "continue_from", None):
        from evaluation.acceptance_continuation import continue_trial
        return await continue_trial(args, adapter, settings, records, data, preflight, review, save)
    # First validate the final narrowing on the same accepted frozen revision.
    source = PRIVATE / "stability-minimal-v2.json"
    historical = json.loads(source.read_text(encoding="utf-8"))["runs"][0]["result"]
    revised = historical["revision_outputs"][0]
    answer, snapshot = restore_answer(revised["answer"]), restore_snapshot(revised["evidence_snapshot"])
    evidence = tuple(restore_evidence(e) for e in historical["evidence"])
    request = TaskRequest("acceptance-narrowing", TaskMode.ASSESS_EXISTING, "voltage_stability_reactive_support",
                          snapshot.question, snapshot.user_context, answer, evidence, snapshot.engineering_context)
    narrowed = await review(request, answer, evidence, snapshot, "narrowed-domain-frozen-v2")
    if narrowed is None:
        data["stop_reason"] = "Budget cannot reserve narrowed-domain validation"
        save()
        return data
    domain_ids = {e.evidence_id for e in narrowed.domain_output.evidence} if narrowed.domain_output else set()
    current_domain_ids = {eid for row in narrowed.retrieval_records if row.purpose == "domain_review"
                          for eid in row.core_evidence_ids + row.context_evidence_ids}
    catalog_ids = set()
    for record in narrowed.model_records:
        if record.prompt_version.startswith("power-domain-review-v2") and record.candidate_catalog_path:
            catalog = json.loads(Path(record.candidate_catalog_path).read_text(encoding="utf-8"))
            catalog_ids.update(q["evidence_id"] for q in catalog["QUOTE_CANDIDATES"])
    data["narrowing_validation"] = {
        "prior_source": {"path": str(source), "sha256": sha(source)},
        "current_domain_evidence_ids": sorted(domain_ids), "current_domain_retrieval_ids": sorted(current_domain_ids),
        "actual_model_catalog_evidence_ids": sorted(catalog_ids),
        "excluded_saved_only_ids": sorted({e.evidence_id for e in evidence} - current_domain_ids),
        "delivery_check": bool(domain_ids) and domain_ids <= current_domain_ids and catalog_ids == domain_ids,
        "all_review_execution_complete": execution_complete(narrowed)}
    save()
    if not data["narrowing_validation"]["delivery_check"] or not execution_complete(narrowed):
        data["stop_reason"] = "Narrowing or required execution incomplete; inspect archives offline before proceeding"
        save()
        return data

    # Both remaining scenarios use explicitly constructed errors, not model
    # generation. No invented original citation or historical input snapshot.
    cases = [
        ("engineering-data", 2, "The plant can safely add 30 MVAr reactive support and guarantee voltage stability."),
        ("quantity-unit-error", 3, "Four equipment ratings limit synchronous generator capability: stator winding rating, field current rating, terminal voltage rating, and active power output. Reactive power Q=30 MW has the correct unit. The same bus values 230 kV and 230 V are identical.")]
    pending = []
    # First retain both initial dual reviews before allocating optional repairs.
    for name, number, text in cases:
        question, context = CASES[number]
        answer = AnswerDraft("acceptance-constructed-" + name, 1, text)
        request = TaskRequest("acceptance-" + name, TaskMode.ASSESS_EXISTING, "voltage_stability_reactive_support",
                              question, "human_constructed synthetic_fixture error; no historical generation snapshot; no simulation executed",
                              answer, (), context)
        run = {"scenario": name, "input_origin": "human_constructed_synthetic_fixture_error",
               "request": asdict(request), "initial": None, "revision": None, "rereview": None,
               "loop_execution_complete": False}
        data["runs"].append(run)
        result = await review(request, answer, label=name + ":initial")
        if result is None:
            run["stop_reason"] = "Initial review not started: insufficient worst-case reserve"
        else:
            run["initial"] = asdict(result)
            pending.append((run, request, result))
        save()

    for run, request, initial in pending:
        if not execution_complete(initial):
            run["stop_reason"] = "Initial execution incomplete; no identical paid retry or revision"
            save()
            continue
        actionable = any(f.status in (VerificationStatus.CONTRADICTED, VerificationStatus.INSUFFICIENT_EVIDENCE)
                         for f in initial.verification_output.findings)
        actionable = actionable or any(f.check_status == "warning" for f in initial.domain_output.findings)
        actionable = actionable or any(c.status == "warning" for c in initial.verification_output.consistency_checks)
        if not actionable:
            run["stop_reason"] = "No actionable finding; no forced revision"
            save()
            continue
        # Revision itself has known bound 2. Before starting, also reserve at
        # least 6 for mandatory non-citation rereview. Citation requests are
        # unknowable until the actual accepted revised output is frozen.
        if not reserve(len(records), args.max_requests, 8):
            run["stop_reason"] = "No reserve for revision plus mandatory rereview; not started"
            save()
            continue
        row = preflight(run["scenario"] + ":revision", 2)
        budget = ModelBudget(limit=2, deadline=perf_counter() + 110)
        agent = ModelRevisionAgent(adapter, settings, diagnostic_dir=diagnostic_dir, protocol_version=2)
        next_decision = policy.decide(initial.verification_output, initial.domain_output,
                                      RunBudget(max_revision_rounds=1), 0)
        inputs = RevisionInput(request, initial.answer, initial.verification_output, initial.domain_output,
                               initial.evidence, next_decision.reasons, initial.evidence_bindings, KNOWLEDGE)
        try:
            with model_scope(budget):
                revision = await agent.run(inputs)
            validate_revision(revision, initial.answer, initial.evidence,
                              initial.verification_output.findings + initial.domain_output.findings)
            validate_snapshot(revision.evidence_snapshot, revision.answer)
            assert revision.evidence_snapshot.evidence == initial.evidence
        except Exception as exc:
            row.update(status="execution_incomplete", error_type=type(exc).__name__)
            run["stop_reason"] = "Revision failed; use archived diagnostics, no identical paid retry"
            revision = None
        else:
            row["status"] = "completed"
            run["revision"] = asdict(revision)
        records.extend(budget.records)
        row["actual_requests"] = len(budget.records)
        row["model_records"] = [asdict(r) for r in budget.records]
        save()
        if revision is None:
            continue
        next_result = await review(request, revision.answer, initial.evidence, revision.evidence_snapshot,
                                   run["scenario"] + ":full-rereview")
        if next_result is None:
            run["stop_reason"] = "Accepted revision retained; actual citation count exceeds remaining full-rereview reserve"
        else:
            run["rereview"] = asdict(next_result)
            run["loop_execution_complete"] = execution_complete(next_result)
            run["stop_reason"] = next_result.termination_reason
        save()
    data["stop_reason"] = "Staged trials ended; see each execution and business outcome separately"
    save()
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicit paid execution; otherwise no credentials/API")
    parser.add_argument("--db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-requests", type=int, default=25)
    parser.add_argument("--baseline", default="acceptance-baseline-v1.json")
    parser.add_argument("--continue-from", help="Private saved stages; each new run uses a new output and explicit budget")
    parser.add_argument("--reuse-frozen-extraction", action="store_true", help="Experiment-only exact archived real extraction; explicitly recorded, no new extraction request")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    cap = 40 if args.continue_from else 25
    if not args.live or not 1 <= args.max_requests <= cap:
        parser.error("Explicit --live and bounded actual request cap required")
    if not output.is_relative_to(PRIVATE) or output.suffix != ".json" or output.exists():
        parser.error("New private JSON output required")
    baseline_path = (PRIVATE / args.baseline).resolve()
    if not baseline_path.is_relative_to(PRIVATE) or not baseline_path.exists():
        parser.error("Save offline baseline first")
    if args.continue_from:
        source = Path(args.continue_from).resolve()
        if not source.is_relative_to(PRIVATE) or not source.exists() or source == output:
            parser.error("Existing private source and a distinct new output required")
    if args.reuse_frozen_extraction and not args.continue_from:
        parser.error("Archived extraction reuse requires explicit private continuation")
    load_project_env()
    model = os.environ.get("DEEPSEEK_MODEL_ID")
    if not model:
        parser.error("Configured model required; credentials are never displayed")
    settings = ModelSettings(model, 90, 8000, 96000, "https://api.deepseek.com", "DEEPSEEK_API_KEY")
    adapter, domain_adapter = create_adapter(settings), create_adapter(settings)
    with output.open("x", encoding="utf-8") as handle:
        handle.write("{}\n")
    def checkpoint(data):
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        data = asyncio.run(experiment(args, adapter, domain_adapter, settings, checkpoint))
    finally:
        adapter.close()
        domain_adapter.close()
    print(json.dumps({"output": str(output), "actual_model_calls": data["actual_model_calls"],
                      "narrowing": data.get("narrowing_validation"),
                      "loops": [(r["scenario"], r["loop_execution_complete"], r.get("stop_reason")) for r in data["runs"]]}))


if __name__ == "__main__":
    main()
