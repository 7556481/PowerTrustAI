"""Resume experiment stages using saved inputs; no new Agent or scheduler."""
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from agents.contracts import RevisionInput
from agents.revision import ModelRevisionAgent
from core.models import TaskRequest
from core.validation import validate_revision, validate_review
from evaluation.acceptance_preparation import PRIVATE, KNOWLEDGE, sha
from evaluation.archive_replay import restore
from harness.contracts import HarnessResult, RunBudget
from harness.evidence_review_demo import restore_answer, restore_snapshot
from harness.policy import LimitedRepairPolicy
from model_adapter.runtime import ModelBudget, model_scope
from services.evidence_scope import validate_snapshot


async def continue_trial(args, adapter, settings, records, data, preflight, review, save):
    # Never count retained historical calls as new paid requests.
    source = Path(args.continue_from)
    old = json.loads(source.read_text(encoding="utf-8"))
    if old["knowledge_version"] != KNOWLEDGE or not old["narrowing_validation"]["delivery_check"]:
        raise ValueError("Validated narrowing and identical knowledge snapshot required")
    data["prior_source"] = {"path": str(source.resolve()), "sha256": sha(source),
                            "actual_prior_requests_not_new": old["actual_model_calls"]}
    data["narrowing_validation"] = {**old["narrowing_validation"], "retained_from_prior_source": True}
    for previous in old["runs"]:
        if previous.get("loop_execution_complete"):
            data["runs"].append({**previous, "complete_loop_retained_from_prior_source": True})
            save()
            continue
        request = restore(previous["request"], TaskRequest)
        initial = restore(previous["initial"], HarnessResult)
        validate_review(initial.verification_output, initial.answer, initial.extraction_output.claims,
                        initial.verification_output.evidence, True)
        validate_review(initial.domain_output, initial.answer, initial.extraction_output.claims,
                        initial.domain_output.evidence, False)
        run = {"scenario": previous["scenario"], "input_origin": previous["input_origin"],
               "request": previous["request"], "initial": previous["initial"],
               "initial_retained_from_prior_source": True, "revision": None, "rereview": None,
               "loop_execution_complete": False}
        data["runs"].append(run)
        if previous["revision"]:
            answer = restore_answer(previous["revision"]["answer"])
            snapshot = restore_snapshot(previous["revision"]["evidence_snapshot"])
            run["revision"] = previous["revision"]
            run["revision_retained_from_prior_source"] = True
            validate_snapshot(snapshot, answer)
        else:
            # Explicit preflight covers Revision plus mandatory non-citation review.
            # Review repeats exact preflight once actual citation count is known.
            if args.max_requests - len(records) < 8:
                run["stop_reason"] = "No reserve for revision and mandatory rereview"
                save()
                continue
            row = preflight(run["scenario"] + ":revision", 2)
            budget = ModelBudget(limit=2, deadline=perf_counter() + 110)
            agent = ModelRevisionAgent(adapter, settings, diagnostic_dir=PRIVATE / "response-diagnostics", protocol_version=2)
            decision = LimitedRepairPolicy().decide(initial.verification_output, initial.domain_output,
                                                    RunBudget(max_revision_rounds=1), 0)
            inputs = RevisionInput(request, initial.answer, initial.verification_output, initial.domain_output,
                                   initial.evidence, decision.reasons, initial.evidence_bindings, KNOWLEDGE)
            try:
                with model_scope(budget):
                    revision = await agent.run(inputs)
                validate_revision(revision, initial.answer, initial.evidence,
                                  initial.verification_output.findings + initial.domain_output.findings)
                validate_snapshot(revision.evidence_snapshot, revision.answer)
                assert revision.evidence_snapshot.evidence == initial.evidence
            except Exception as exc:
                row.update(status="execution_incomplete", error_type=type(exc).__name__)
                run["stop_reason"] = "Revision failed after bounded correction; no identical retry"
                revision = None
            else:
                row["status"] = "completed"
                run["revision"] = asdict(revision)
            records.extend(budget.records)
            row.update(actual_requests=len(budget.records), model_records=[asdict(r) for r in budget.records])
            save()
            if revision is None:
                continue
            answer, snapshot = revision.answer, revision.evidence_snapshot
        result = await review(request, answer, initial.evidence, snapshot, run["scenario"] + ":full-rereview")
        if result is None:
            run["stop_reason"] = "Frozen revised output retained; full rereview cannot fit its actual worst-case count"
        else:
            from evaluation.acceptance_trial import execution_complete
            run["rereview"] = asdict(result)
            run["loop_execution_complete"] = execution_complete(result)
            run["stop_reason"] = result.termination_reason
        save()
    data["stop_reason"] = "Continuation complete; retained historical failures unchanged"
    save()
    return data
