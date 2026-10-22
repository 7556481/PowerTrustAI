"""Offline material/message identity checks only; no execution or provider entry.

Evaluator rubric is deliberately never read by the model-input builder.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from agents.contracts import GenerationInput
from agents.generation import messages_for
from agents.generation_mapping_v1 import GenerationCatalog, candidate_messages
from core.models import EngineeringContext, Evidence, EvidenceBinding, TaskMode, TaskRequest
from core.validation import require, validate_types


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs/evaluation/generation-mapping-comparison-v1"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def build_inputs(document):
    require(set(document) == {"version", "status", "common_answer_requirements", "tasks"}, "Task document whitelist")
    require(len(document["tasks"]) == 4, "Exactly four fixed task groups")
    result = {}
    for task in document["tasks"]:
        require(set(task) == {"task_id", "category", "question", "requirements", "user_context", "evidence"},
                "Task input whitelist")
        require(task["task_id"] not in result, "Unique task ID")
        requirements = []
        for row in task["requirements"]:
            require(set(row) == {"requirement_id", "description"}, "User requirement whitelist")
            requirements.append(row["description"])
        require(len({r["requirement_id"] for r in task["requirements"]}) == len(task["requirements"]),
                "Unique original requirement IDs")
        evidence = []
        for row in task["evidence"]:
            require(set(row) == {"evidence_id", "source_id", "source_version", "locator", "text",
                                 "source_type", "applicability"}, "Evidence whitelist")
            evidence.append(Evidence(**{**row, "applicability": tuple(row["applicability"])}))
        request = TaskRequest(task["task_id"], TaskMode.QUESTION_ANSWER, "concept_fixed_evidence_v1",
                              task["question"], user_context=task["user_context"],
                              provided_evidence=tuple(evidence), engineering_context=EngineeringContext(goal="conceptual"))
        value = GenerationInput(request, tuple(evidence),
                                tuple(EvidenceBinding(e.evidence_id, "user_reference") for e in evidence),
                                None, tuple(requirements + document["common_answer_requirements"]))
        validate_types(value, GenerationInput)
        result[task["task_id"]] = value
    require(set(result) == {"GEC-01", "GEC-02", "GEC-03", "GEC-04"}, "Frozen task IDs")
    return result


def message_rows(value, variant):
    require(variant in ("original", "candidate"), "Known generation variant")
    messages = (messages_for(value, 3, product_guidance=True) if variant == "original" else
                candidate_messages(value, GenerationCatalog(value, True), product_guidance=True))
    return [asdict(message) for message in messages]


def check():
    document = json.loads((PUBLIC / "tasks-v1.json").read_text(encoding="utf-8-sig"))
    plan = json.loads((PUBLIC / "freeze-plan-v1.json").read_text(encoding="utf-8-sig"))
    inputs = build_inputs(document)
    sources = json.loads((ROOT / "docs/evaluation/baseline-source-review-v1/selected-source-excerpts-v1.json")
                         .read_text(encoding="utf-8-sig"))
    exact_excerpts = {(source["id"], excerpt["complete_selected_text"]): excerpt
                      for source in sources for excerpt in source["excerpts"]}
    for task in document["tasks"]:
        for evidence in task["evidence"]:
            excerpt = exact_excerpts.get((evidence["source_id"], evidence["text"]))
            require(excerpt is not None, "Exact prior selected excerpt; no changed whitespace/context")
            require(hashlib.sha256(evidence["text"].encode("utf-8")).hexdigest() == excerpt["sha256_utf8"],
                    "Prior public excerpt text identity")
    expected_order = [("GEC-01", "original"), ("GEC-01", "candidate"),
                      ("GEC-02", "candidate"), ("GEC-02", "original"),
                      ("GEC-03", "original"), ("GEC-03", "candidate"),
                      ("GEC-04", "candidate"), ("GEC-04", "original")]
    require([(r["task_id"], r["variant"]) for r in plan["order"]] == expected_order, "Interleaved variant order")
    require(len({r["request_id"] for r in plan["order"]}) == 8, "Unique archive request IDs")
    for row in plan["order"]:
        value = inputs[row["task_id"]]
        rows = message_rows(value, row["variant"])
        require(sha(asdict(value)) == row["generation_input_sha256"], "Fixed paired input identity")
        require(sha(rows) == row["initial_messages_sha256"], "Fixed initial message identity")
    for identity in plan["file_identities"]:
        data = (ROOT / identity["path"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == identity["sha256"], "Prepared file identity")
    require(plan["execution_authorized"] is False and plan["ready_to_execute"] is False, "Preparation only")
    require(plan["budget_proposal"]["per_branch_model_calls"] * 8 == plan["budget_proposal"]["batch_upper_bound"],
            "Derived total request cap includes review, not just generation")
    print("4 groups / 8 initial message identities verified; 0 model calls; plan not authorized for execution")


if __name__ == "__main__":
    check()
