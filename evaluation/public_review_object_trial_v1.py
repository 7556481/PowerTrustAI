"""One explicitly authorized three-branch v2 validation; no resume or resubmission.

Execution stays inside OfflineHarness. run_fixed owns batch admission; this
entry archives an execution failure before raising its explicit stop signal.
"""
import argparse
import asyncio
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

from evaluation.batch_control import run_fixed
from evaluation.public_review_validation_materials_v1 import ROOT, sha
from evaluation.public_review_object_materials_v1 import PUBLIC, ORDER, build_inputs, identities
from agents.generation import messages_for
from services.task_premises_v1 import catalog
from core.models import PremiseBoundClaim
from core.validation import require
from model_adapter.contracts import ModelOutputError, ModelSettings

DIRECTORY = ROOT / "data/evaluation_local/public-review-object-v2-live-v1/batch-v1"
RESPONSES = ROOT / "data/retrieval_local/public-review-object-v2-live-v1/batch-v1"
FREEZE = PUBLIC / "execution-freeze-v1.json"
VERSION = "public-review-object-v2-execution-v1"
GENERATION_PROMPT = "evidence-bound-generation-v3-answer-units-product-v1-question-language-v11-length-planning"
EXTRACTION_PROMPT = "public-review-object-boundary-v2-dev-extraction"
FACT_PROMPT = "evidence-verification-v9.22-object-boundary-v2-dev"
DOMAIN_PROMPT = "power-domain-review-v3.5-task-obligations"


def plain(value):
    if is_dataclass(value):
        return {k: plain(v) for k, v in asdict(value).items()}
    if isinstance(value, Enum): return value.value
    if isinstance(value, dict): return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [plain(v) for v in value]
    return value


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    """Exclusive private/public artifact; never replace an existing run record."""
    text = json.dumps(plain(value), ensure_ascii=False, indent=2) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


class BranchExecutionFailed(RuntimeError):
    pass


class PreSendFailure(ModelOutputError):
    code = "FROZEN_PAYLOAD_GATE_FAILED"


class PreSendStorageFailure(ModelOutputError):
    code = "DIAGNOSTIC_STORAGE_FAILED"


def workload(answer, snapshot, extraction, used, limit=40):
    citations = len(answer.citations)
    if extraction is None:
        independent, initial = 1, citations + 3
    else:
        full = bool(snapshot and snapshot.snapshot_version == "generation-full-input-v2"
                    and sum(len(e.text) for e in snapshot.evidence) <= 32000)
        claims = extraction.claims if hasattr(extraction, "claims") else extraction
        independent = int(any(any(full or part.category != "input_evidence_coverage"
            or isinstance(c, PremiseBoundClaim) and c.component_objects[i] == "premise_restatement"
            for i, part in enumerate(c.components)) for c in claims))
        initial = citations + independent + 1
    available = limit - used
    return {"after": "before_extraction" if extraction is None else "extraction", "citations": citations,
            "independent_initial": independent, "independent_provisional": extraction is None,
            "required_initial_remaining": initial, "used": used, "available": available,
            "initial_shortfall": max(0, initial - available), "room_after_initial": max(0, available - initial),
            "correction_potential_remaining": 3 if extraction is None else 2,
            "note": "Actual C and eligible I; no completion guarantee, citation removal or budget increase."}


def assert_no_evaluator_keys(value):
    if type(value) is dict:
        require(not set(value).intersection({"diagnostic_map", "evaluator_rubric", "expected_labels",
                "reference_labels", "quality_checks", "omission_rule", "unresolved_target",
                "diagnostic_reference_clauses", "coverage_components", "answer_boundary", "review_boundary",
                "expected", "reference_units", "sample_role", "evaluator_criteria"}),
                "Evaluator/mapping fields cannot enter audit payload")
        for child in value.values(): assert_no_evaluator_keys(child)
    elif type(value) is list:
        for child in value: assert_no_evaluator_keys(child)


class GuardedAdapter:
    def __init__(self, delegate, case, value, state, directory):
        self.delegate, self.case, self.value = delegate, case, value
        self.state, self.directory = state, directory

    async def complete(self, request):
        try:
            require(not self.state.get("fatal_gate"), "A previous pre-send gate failed")
            require(request.model_id == "deepseek-flash" and request.max_output_tokens == 8000,
                    "Frozen model settings")
            rows = [asdict(m) for m in request.messages]
            generation = request.prompt_version == GENERATION_PROMPT
            task = self.state["request"]
            if generation:
                require(self.case["request_id"] == "OB2-01", "Diagnostic cannot generate")
                expected = [asdict(m) for m in messages_for(self.value, 3, product_guidance=True)]
                require(rows[:len(expected)] == expected, "Exact frozen original generation messages")
                require(sha(expected) == self.case["initial_generation_messages_sha256"], "Prepared message identity")
                require(len(rows) == len(expected) + int(request.correction), "One generation correction")
            else:
                require(request.prompt_version in (EXTRACTION_PROMPT, FACT_PROMPT, DOMAIN_PROMPT), "Frozen B audit prompt")
                require(len(rows) == 2 + int(request.correction), "Audit message shape")
                payload = json.loads(rows[1]["content"])
                assert_no_evaluator_keys(payload)
                if "TRANSPORT_SHARED_VALUES" in payload:
                    from services.review_transport import expand
                    payload = expand(payload)
                    assert_no_evaluator_keys(payload)
                if request.prompt_version in (EXTRACTION_PROMPT, FACT_PROMPT):
                    require(payload["CURRENT_TASK"] == {"task_id": task.task_id, "question": task.question,
                            "user_context": task.user_context}, "Exact current task")
                    require(payload["TASK_PREMISES"] == plain(catalog(task)), "Only declared task premises")
                if request.prompt_version == EXTRACTION_PROMPT:
                    require(set(payload) == {"answer_id", "answer_version", "ANSWER_ANCHORS", "assumptions",
                        "missing_information", "CURRENT_TASK", "TASK_PREMISES"}, "Extraction whitelist")
                    from services.answer_anchors import anchors
                    require(payload["ANSWER_ANCHORS"] == plain(anchors(self.state["answer"])), "All actual answer anchors")
                if "question" in payload:
                    require(payload["question"] == task.question, "Original question retained")
                if "answer" in payload:
                    require(payload["answer"]["text"] == self.state["answer"].text, "Full actual answer retained")
            from model_adapter.runtime import current_budget, current_model_invocation
            budget = current_budget()
            self.state["send_sequence"] += 1
            number = self.state["send_sequence"]
            item = {"sequence": number, "branch": self.case["request_id"], "prompt_version": request.prompt_version,
                    "correction": request.correction, "messages": rows, "messages_sha256": sha(rows),
                    "elapsed_before_send": perf_counter() - self.state["started"],
                    "invocation": current_model_invocation(),
                    "completed_corrections_before_send": [] if budget is None else [
                        {"call_number": r.call_number, "invocation_id": r.invocation_id,
                         "component": r.component, "prompt_version": r.prompt_version}
                        for r in budget.records if r.correction]}
            try:
                write(self.directory / f"before-send-{number:03d}.json", item)
            except Exception:
                self.state["fatal_gate"] = "pre_send_storage_failed"
                raise PreSendStorageFailure({"stage": "pre_send", "field_path": "messages", "constraint": "message_identity_persistence_failed"}) from None
            self.state["sent"].append({k: v for k, v in item.items() if k != "messages"})
        except ModelOutputError:
            raise
        except Exception:
            self.state["fatal_gate"] = "payload_identity_or_whitelist_failed"
            raise PreSendFailure({"stage": "pre_send", "field_path": "messages", "constraint": "frozen_payload_or_whitelist_failed"}) from None
        return await self.delegate.complete(request)


def build_harness(case, value, observer, state, adapters, directory):
    from agents.generation import EvidenceGenerationAgent
    from agents.premise_verification_v2 import PremiseVerificationAgentV2 as PremiseVerificationAgent
    from agents.power_domain_review import ModelPowerDomainReviewAgent
    from agents.revision import ModelRevisionAgent
    from services.premise_claim_extractor_v2 import PremiseClaimExtractorV2 as PremiseClaimExtractor
    from tools.unit_conversion import UnitConversionTool
    from harness.product_policy import ProductAuditPolicy
    from harness.runtime import OfflineHarness
    settings = ModelSettings("deepseek-flash", 90, 8000, 96000, "https://api.deepseek.com", "DEEPSEEK_API_KEY")
    main = GuardedAdapter(adapters[0], case, value, state, directory)
    domain = GuardedAdapter(adapters[1], case, value, state, directory)
    result = OfflineHarness(EvidenceGenerationAgent(main, settings, schema_version=3, diagnostic_dir=directory, product_guidance=True),
        PremiseVerificationAgent(main, settings, diagnostic_dir=directory, correction_accounting="invocation_scoped_v1"),
        ModelPowerDomainReviewAgent(domain, settings, diagnostic_dir=directory, protocol_version=5,
            safety_review=True, task_applicability=True),
        ModelRevisionAgent(main, settings, diagnostic_dir=directory, protocol_version=2, clean_answer_body=True),
        PremiseClaimExtractor(main, settings, diagnostic_dir=directory),
        policy=ProductAuditPolicy(), unit_tool=UnitConversionTool(version="scalar-si-conversion-v2"), observer=observer)
    if case["request_id"] == "OB2-03":
        from evaluation.public_review_object_materials_v1 import FrozenObjectExtractor
        result.extractor = FrozenObjectExtractor()
    return result



def failed(result):
    value = plain(result)
    if value["execution_issues"] or value["state"] in ("failed", "cancelled", "execution_incomplete"):
        return True
    if any((value.get(k) or {}).get("execution_issues") for k in ("verification_output", "domain_output")):
        return True
    report = value.get("report")
    if not report: return True
    return report["decision"].get("execution_integrity") == "incomplete"


async def run_batch(freeze, directory, response_root, adapter_factory, harness_factory=build_harness):
    """Only sequential admission around existing Harness, no second execution engine."""
    from harness.contracts import RunBudget
    values, diagnostic = build_inputs(read(PUBLIC / "inputs-r1.json"))
    expected, _ = identities(values, diagnostic)
    require(freeze["order"] == expected, "Exactly three frozen branches")
    states, outputs = {}, {}

    async def submit(case):
        ident = case["request_id"]
        require(ident not in states, "Never resubmit a branch")
        task = values[case["case_id"]].request
        require(sha(asdict(task)) == case["request_sha256"], "Frozen input identity")
        states[ident] = {"started": perf_counter(), "send_sequence": 0, "sent": [], "events": 0,
                         "times": {}, "workload": [], "latest": None, "request": task}
        if task.existing_answer is not None:
            states[ident]["answer"] = task.existing_answer
            states[ident]["workload"].append(workload(task.existing_answer, None, None, 0))
            if ident == "OB2-03":
                states[ident]["workload"][-1].update(required_initial_remaining=2, correction_potential_remaining=2,
                    note="Injected deterministic extraction: no model extraction/correction. Independent and domain initial only.")
        return ident

    async def collect(ident):
        case = next(c for c in freeze["order"] if c["request_id"] == ident)
        value, state = values[case["case_id"]], states[ident]
        branch = directory / ident
        diagnostic_dir = response_root / ident
        generated = None

        def observer(snapshot):
            nonlocal generated
            state["latest"] = snapshot
            state["events"] += 1
            write(branch / f"event-{state['events']:04d}.json", snapshot)
            event, stage = snapshot["event"], snapshot.get("stage_output")
            if event.component == "generation" and stage is not None:
                generated = stage
                state["answer"] = stage.answer
                state["times"]["generation_output_persisted"] = perf_counter() - state["started"]
                state["workload"].append(workload(stage.answer, stage.evidence_snapshot, None, snapshot["budget_usage"]["model_calls"]))
                print(ident + ": generation persisted", flush=True)
            if event.component == "claim_extraction" and stage is not None:
                state["workload"].append(workload(state["answer"], None if generated is None else generated.evidence_snapshot,
                                                       stage, snapshot["budget_usage"]["model_calls"]))
            if event.component in ("evidence_verification", "power_domain_review"):
                state["times"][event.component + "_persisted"] = perf_counter() - state["started"]

        adapters = []
        try:
            for _ in range(2): adapters.append(adapter_factory())
            harness = harness_factory(case, value, observer, state, adapters, diagnostic_dir)
            budget = RunBudget(max_model_calls=40, max_revision_rounds=0, max_transient_retries=0,
                               max_retrieval_calls=0, max_duration_seconds=800, step_timeout_seconds=110)
            result = await harness.run(state["request"], budget, answer_requirements=value.answer_requirements,
                                       run_id=ident)
            outputs[ident] = plain(result)
            write(branch / "final-result.json", result)
            state["times"]["final_result_persisted"] = perf_counter() - state["started"]
            write(branch / "execution-observations.json", {"times": state["times"], "workload": state["workload"],
                                                          "sent": state["sent"], "fatal_gate": state.get("fatal_gate")})
            print(ident + ": " + result.state.value + ", sent=" + str(len(state["sent"])), flush=True)
            if failed(result): raise BranchExecutionFailed("Final branch execution or required review failed")
            return {"branch_id": ident, "execution_issues": [], "state": result.state.value}
        except BranchExecutionFailed:
            raise
        except BaseException as exc:
            state["entry_failure"] = type(exc).__name__
            # Keep latest partial result separately; never turn storage errors into configuration failures.
            try:
                write(branch / "entry-failure.json", {"exception_type": type(exc).__name__,
                      "latest": state["latest"], "sent": state["sent"], "times": state["times"],
                      "workload": state["workload"], "fatal_gate": state.get("fatal_gate")})
            except Exception:
                state["failure_archive_unconfirmed"] = True
            raise
        finally:
            for adapter in adapters:
                if hasattr(adapter, "close"): adapter.close()

    def persist(ident, kind, payload):
        if kind == "control" and payload.get("exception_type") == "BranchExecutionFailed":
            payload = {**payload, "original_controller_reason": payload["reason"],
                       "reason": "branch_final_execution_failure"}
        try:
            write(directory / ident / ("controller-" + kind + ".json"), payload)
        except Exception:
            states[ident]["entry_failure"] = "ControllerStorageFailure"
            raise

    controller_error = None
    try:
        control = await run_fixed([{"id": c["request_id"], "input": c} for c in freeze["order"]],
                                  submit=submit, collect=collect, persist=persist)
    except BaseException as exc:
        control, controller_error = [], type(exc).__name__
    summary = {"version": VERSION, "controller": control, "controller_error": controller_error, "branches": []}
    for case in freeze["order"]:
        ident = case["request_id"]
        state = states.get(ident)
        summary["branches"].append({"request_id": ident, "case_id": case["case_id"], "mode": case["mode"],
            "status": "unexecuted" if state is None else "execution_failed" if state.get("entry_failure") or ident not in outputs or failed(outputs[ident]) else "complete",
            "reason": "stopped_after_previous_final_execution_or_storage_failure" if state is None else None,
            "result": outputs.get(ident), "times": {} if state is None else state["times"],
            "workload": [] if state is None else state["workload"], "sent": [] if state is None else state["sent"],
            "entry_failure": None if state is None else state.get("entry_failure")})
    write(directory / "summary.json", summary)
    return summary


def prepare_freeze():
    require(not FREEZE.exists(), "Execution freeze already exists; no replacement")
    plan = read(PUBLIC / "freeze-plan-v1.json")
    from evaluation.public_review_object_materials_v1 import check
    check()
    values, diag = build_inputs(read(PUBLIC / "inputs-r1.json"))
    rows, _ = identities(values, diag)
    require(tuple(r["request_id"] for r in rows) == ORDER, "Prepared identity/order")
    require(not DIRECTORY.exists(), "One fixed new batch directory only")
    paths = set()
    for name in ("agents", "core", "harness", "model_adapter", "services", "tools"):
        paths.update(p for p in (ROOT / name).rglob("*.py"))
    paths.update([Path(__file__).resolve(), ROOT / "evaluation/batch_control.py",
                  ROOT / "evaluation/public_review_object_materials_v1.py",
                  ROOT / "evaluation/public_review_validation_materials_v1.py",
                  ROOT / "tests/test_public_review_object_trial_v1.py"])
    paths.update(PUBLIC / n for n in ("inputs-v1.json", "inputs-r1.json", "review-criteria-v1.json", "freeze-plan-v1.json"))
    freeze = {"version": VERSION, "source_base_commit": "c59badb1807777646c5a16da66003ac2675d0bb9",
              "owner_authorized": True, "authorization_scope": "Three branches accepted; necessary DeepSeek fees authorized; only OB2-01 length corrected to220",
              "order": rows, "per_branch_model_calls": 40, "batch_call_cap": None,
              "revision": 0, "transient_retries": 0, "retrieval": 0,
              "request_timeout": 90, "step_timeout": 110, "branch_timeout": 800,
              "model": {"model_id": "deepseek-flash", "max_output_tokens": 8000, "max_response_chars": 96000,
                        "endpoint": "https://api.deepseek.com", "thinking": "disabled", "temperature": "service default", "seed": None},
              "failure_rule": "persist final/partial failure, stop subsequent branches, never resume or resubmit",
              "pipeline": plan["pipeline"],
              "budget_formula": plan["call_plan"],
              "counter_condition": "invocation_scoped_v1 explicitly enabled only for B; no old-accounting live rerun",
              "dynamic_messages": "persist actual scopes and exact messages with hash before each actual send; no predicted audit/correction hashes",
              "bound_files": [{"path": str(p.relative_to(ROOT)).replace('\\', '/'),
                               "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]}
    write(FREEZE, freeze)
    require(not DIRECTORY.exists(), "Fixed batch directory must be new")
    write(DIRECTORY / "freeze.json", freeze)
    print("Execution identity frozen; no attempt marker and no model calls yet")


def preflight():
    freeze = read(FREEZE)
    require(freeze == read(DIRECTORY / "freeze.json"), "Public/private freeze match")
    require(freeze["owner_authorized"] and freeze["per_branch_model_calls"] == 40 and freeze["batch_call_cap"] is None,
            "Authorized branch protection only")
    for item in freeze["bound_files"]:
        require(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"], "Frozen source/material mismatch")
    require(not (DIRECTORY / "attempt.json").exists(), "Attempt exists; no automatic resume or new directory")
    return freeze


async def execute():
    freeze = preflight()
    write(DIRECTORY / "attempt.json", {"version": VERSION, "freeze_sha256": hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
                                       "authorization": "explicit user message; deepseek-flash actual fees accepted"})
    from harness.deepseek_trial import load_project_env
    from model_adapter.deepseek import create_adapter
    load_project_env()  # Only this explicitly authorized real entry loads .env; never display its contents.
    settings = ModelSettings("deepseek-flash", 90, 8000, 96000, "https://api.deepseek.com", "DEEPSEEK_API_KEY")
    return await run_batch(freeze, DIRECTORY, RESPONSES, lambda: create_adapter(settings))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare-freeze", "preflight", "execute"))
    args = parser.parse_args()
    if args.action == "prepare-freeze": prepare_freeze()
    elif args.action == "preflight": preflight(); print("Frozen identity verified; no model calls")
    else:
        result = asyncio.run(execute())
        print(json.dumps({"branches": [{k: r[k] for k in ("request_id", "status")} for r in result["branches"]]}))
