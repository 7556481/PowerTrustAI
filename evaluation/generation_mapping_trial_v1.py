"""One explicitly authorized fixed-evidence comparison; no resume or resubmission.

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
from evaluation.generation_mapping_comparison_materials_v1 import ROOT, PUBLIC, build_inputs, message_rows, sha
from core.validation import require
from model_adapter.contracts import ModelOutputError, ModelSettings

DIRECTORY = ROOT / "data/evaluation_local/generation-mapping-comparison-v1/batch-v1"
RESPONSES = ROOT / "data/retrieval_local/generation-mapping-comparison-v1/batch-v1"
FREEZE = PUBLIC / "execution-freeze-v1.json"
VERSION = "fixed-evidence-generation-comparison-execution-v1"


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


def workload(generation, extraction, used, limit=40):
    citations = len(generation.answer.citations)
    if extraction is None:
        independent = 1  # Conservative until actual extracted eligible components exist.
        initial = citations + independent + 2  # extraction + domain + fact work
    else:
        snapshot = generation.evidence_snapshot
        full = bool(snapshot and snapshot.snapshot_version == "generation-full-input-v2"
                    and sum(len(e.text) for e in snapshot.evidence) <= 32000)
        claims = extraction.claims if hasattr(extraction, "claims") else extraction
        independent = int(any(any(full or p.category != "input_evidence_coverage"
                                  for p in c.components) for c in claims))
        initial = citations + independent + 1  # domain + independent + each citation
    available = limit - used
    return {"after": "generation" if extraction is None else "extraction", "citations": citations,
            "independent_initial": independent, "independent_provisional": extraction is None,
            "required_initial_remaining": initial, "used": used, "available": available,
            "initial_shortfall": max(0, initial - available),
            "room_after_initial": max(0, available - initial),
            "correction_potential_remaining": 3 if extraction is None else 2,
            "note": "Initial work only; format, message capacity, deadlines and concurrent corrections may still fail. No guarantee or budget increase."}


def assert_no_evaluator_keys(value):
    if type(value) is dict:
        require(not set(value).intersection({"diagnostic_map", "evaluator_rubric", "expected_labels",
                "reference_labels", "quality_checks", "omission_rule", "unresolved_target"}),
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
            generation = request.prompt_version in (
                "evidence-bound-generation-v3-answer-units-product-v1-question-language-v11-length-planning",
                "concept-evidence-generation-map-v1-dev-product")
            if generation:
                expected_prompt = ("evidence-bound-generation-v3-answer-units-product-v1-question-language-v11-length-planning"
                                   if self.case["variant"] == "original" else "concept-evidence-generation-map-v1-dev-product")
                require(request.prompt_version == expected_prompt, "Frozen branch prompt identity")
                expected = message_rows(self.value, self.case["variant"])
                require(rows[:len(expected)] == expected, "Exact frozen generation messages")
                require(sha(expected) == self.case["initial_messages_sha256"], "Prepared message identity")
                require(len(rows) == len(expected) + int(request.correction), "One declared generation correction")
            else:
                require(request.prompt_version in (
                    "atomic-claims-v7-obligations-faithful-assertions-v2",
                    "evidence-verification-v9.20-lossless-transport-json-nesting",
                    "power-domain-review-v3.5-task-obligations"), "Frozen original audit prompt")
                require(len(rows) == 2 + int(request.correction), "Original audit message shape")
                payload = json.loads(rows[1]["content"])
                assert_no_evaluator_keys(payload)
                if "TRANSPORT_SHARED_VALUES" in payload:
                    from services.review_transport import expand
                    payload = expand(payload)
                if "question" in payload:
                    require(payload["question"] == self.value.request.question, "Original question retained")
                if "answer" in payload:
                    require(payload["answer"]["text"] == self.state["answer_text"], "Full actual answer retained")
            self.state["send_sequence"] += 1
            number = self.state["send_sequence"]
            item = {"sequence": number, "branch": self.case["request_id"], "prompt_version": request.prompt_version,
                    "correction": request.correction, "messages": rows, "messages_sha256": sha(rows),
                    "elapsed_before_send": perf_counter() - self.state["started"]}
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
    from agents.generation_mapping_v1 import EvidenceMappingGenerationAgent
    from agents.evidence_verification import ModelEvidenceVerificationAgent
    from agents.power_domain_review import ModelPowerDomainReviewAgent
    from agents.revision import ModelRevisionAgent
    from services.claim_extractor import ModelClaimExtractor
    from tools.unit_conversion import UnitConversionTool
    from harness.product_policy import ProductAuditPolicy
    from harness.runtime import OfflineHarness
    settings = ModelSettings("deepseek-flash", 90, 8000, 96000, "https://api.deepseek.com", "DEEPSEEK_API_KEY")
    main = GuardedAdapter(adapters[0], case, value, state, directory)
    domain = GuardedAdapter(adapters[1], case, value, state, directory)
    kwargs = {"diagnostic_dir": directory, "product_guidance": True}
    generator = (EvidenceGenerationAgent(main, settings, schema_version=3, **kwargs) if case["variant"] == "original"
                 else EvidenceMappingGenerationAgent(main, settings, **kwargs))
    return OfflineHarness(generator,
        ModelEvidenceVerificationAgent(main, settings, diagnostic_dir=directory, schema_version=13,
            support_relation_checks=True, support_relation_version=6, review_message_profile="lossless_v1"),
        ModelPowerDomainReviewAgent(domain, settings, diagnostic_dir=directory, protocol_version=5,
            safety_review=True, task_applicability=True),
        ModelRevisionAgent(main, settings, diagnostic_dir=directory, protocol_version=2, clean_answer_body=True),
        ModelClaimExtractor(main, settings, diagnostic_dir=directory, typed_components=True,
            protocol_version=7, daily_guidance=True),
        policy=ProductAuditPolicy(), unit_tool=UnitConversionTool(version="scalar-si-conversion-v2"), observer=observer)


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
    values = build_inputs(read(PUBLIC / "tasks-v1.json"))
    states, outputs = {}, {}

    async def submit(case):
        ident = case["request_id"]
        require(ident not in states, "Never resubmit a branch")
        require(sha(asdict(values[case["task_id"]])) == case["generation_input_sha256"], "Frozen input identity")
        states[ident] = {"started": perf_counter(), "send_sequence": 0, "sent": [], "events": 0,
                         "times": {}, "workload": [], "latest": None}
        return ident

    async def collect(ident):
        case = next(c for c in freeze["order"] if c["request_id"] == ident)
        value, state = values[case["task_id"]], states[ident]
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
                state["answer_text"] = stage.answer.text
                state["times"]["generation_output_persisted"] = perf_counter() - state["started"]
                state["workload"].append(workload(stage, None, snapshot["budget_usage"]["model_calls"]))
                print(ident + ": generation persisted", flush=True)
            if event.component == "claim_extraction" and stage is not None and generated is not None:
                state["workload"].append(workload(generated, stage, snapshot["budget_usage"]["model_calls"]))
            if event.component in ("evidence_verification", "power_domain_review"):
                state["times"][event.component + "_persisted"] = perf_counter() - state["started"]

        adapters = []
        try:
            for _ in range(2): adapters.append(adapter_factory())
            harness = harness_factory(case, value, observer, state, adapters, diagnostic_dir)
            budget = RunBudget(max_model_calls=40, max_revision_rounds=0, max_transient_retries=0,
                               max_retrieval_calls=0, max_duration_seconds=800, step_timeout_seconds=110)
            result = await harness.run(value.request, budget, answer_requirements=value.answer_requirements,
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
        summary["branches"].append({"request_id": ident, "task_id": case["task_id"], "variant": case["variant"],
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
    values = build_inputs(read(PUBLIC / "tasks-v1.json"))
    for case in plan["order"]:
        require(sha(asdict(values[case["task_id"]])) == case["generation_input_sha256"], "Prepared inputs unchanged")
        require(sha(message_rows(values[case["task_id"]], case["variant"])) == case["initial_messages_sha256"], "Prepared messages unchanged")
    paths = set()
    for name in ("agents", "core", "harness", "model_adapter", "services", "tools"):
        paths.update(p for p in (ROOT / name).rglob("*.py"))
    paths.update([Path(__file__).resolve(), ROOT / "evaluation/batch_control.py",
                  ROOT / "evaluation/generation_mapping_comparison_materials_v1.py",
                  ROOT / "tests/test_generation_mapping_trial_v1.py"])
    paths.update(PUBLIC / n for n in ("tasks-v1.json", "rubric-v1.json", "source-lineage-v1.json", "freeze-plan-v1.json"))
    freeze = {"version": VERSION, "source_base_commit": "fccea835b06e8e97c4e4c0a3ecd0630f6da32d9b",
              "owner_authorized": True, "authorization_scope": "8 initial generations and original audit payloads; actual fees accepted by user",
              "order": plan["order"], "per_branch_model_calls": 40, "batch_call_cap": None,
              "revision": 0, "transient_retries": 0, "retrieval": 0,
              "request_timeout": 90, "step_timeout": 110, "branch_timeout": 800,
              "model": {"model_id": "deepseek-flash", "max_output_tokens": 8000, "max_response_chars": 96000,
                        "endpoint": "https://api.deepseek.com", "thinking": "disabled", "temperature": "service default", "seed": None},
              "failure_rule": "persist final/partial failure, stop subsequent branches, never resume or resubmit",
              "old_budget_proposal": "16/128 withdrawn; C+8 conditional upper bound only, not an admission cap or guarantee",
              "budget_formula": "initial total G+E+I+C+1; G,E each 1..2, I actual eligible independent request 0..1, C original citation bindings, domain 1..2, fact-stage correction <=1; conditional complete-path upper C+7+I, C+8 if I=1",
              "correction_caveat": "Original fact code detects any concurrent correction in shared budget slice; domain correction can suppress later fact correction. Preserve original behavior, report actual stage records.",
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
