"""Offline archive replay. No credentials, model client, retrieval or API execution."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from agents.contracts import EvidenceVerificationInput
from agents.evidence_verification import parse_verification
from core.models import TaskRequest, TaskMode
from core.validation import require
from harness.evidence_review_demo import restore_answer, restore_evidence, restore_snapshot, render_review
from services.claim_extractor import parse_extraction
from services.structured_model import strict_json
from services.response_diagnostics import LOCAL_ROOT


def load_archive(record):
    path = Path(record["diagnostic_path"]).resolve()
    require(path.is_relative_to(LOCAL_ROOT.resolve()) and path.suffix == ".json", "Invalid private archive path")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value["prompt_version"] == record["prompt_version"], "Archive prompt binding mismatch")
    require(value["call_number"] == record["call_number"] and value["correction"] == record["correction"], "Archive call binding mismatch")
    require(hashlib.sha256(value["response_text"].encode("utf-8")).hexdigest() == value["response_sha256"], "Archive response hash mismatch")
    return value


def replay(path):
    data = Path(path).read_bytes()
    payload = json.loads(data)
    result, run = payload["runs"][0]["result"], payload["runs"][0]
    answer = restore_answer(result["answer"])
    records = result["model_records"]
    extraction_records = [r for r in records if r["prompt_version"].startswith("atomic-claims-")]
    extraction_record = next((r for r in reversed(extraction_records) if r.get("output_status") == "valid_structure"), extraction_records[0])
    extraction = parse_extraction(strict_json(load_archive(extraction_record)["response_text"]), answer,
                                 require_components=extraction_record["prompt_version"] == "atomic-claims-v4-explicit-components")
    projected = json.loads(json.dumps(asdict(extraction)))
    # Historic wire records predate these optional fields. Only omit empty defaults;
    # never hide newly inferred semantic components or nonempty binding information.
    for actual, saved in zip(projected["claims"], result["extraction_output"]["claims"]):
        for name, default in (("components", []), ("anchor_group_id", None)):
            if name not in saved:
                require(actual[name] == default, "New semantic fields cannot be erased in historic replay")
                del actual[name]
    require(projected == result["extraction_output"], "Extracted claim replay mismatch")
    evidence = tuple(restore_evidence(e) for e in result["evidence"])
    known = {e.evidence_id: e for e in evidence}
    retrieved = {eid for r in result["retrieval_records"] for eid in r["core_evidence_ids"] + r["context_evidence_ids"]}
    original_ids = {eid for c in answer.citations for eid in c.evidence_ids}
    inputs = EvidenceVerificationInput(TaskRequest("offline-replay", TaskMode.ASSESS_EXISTING, "voltage", run["question"], existing_answer=answer),
        answer, extraction.claims, tuple(e for e in evidence if e.evidence_id in retrieved),
        knowledge_version=payload["knowledge_version"], original_evidence=tuple(known[eid] for eid in sorted(original_ids)),
        generation_snapshot=restore_snapshot((result.get("verification_output") or {}).get("generation_snapshot")))
    review_records = [r for r in records if r["prompt_version"].startswith("evidence-verification-")]
    verification_record = next((r for r in reversed(review_records) if r.get("output_status") == "valid_structure"), review_records[0])
    archive = load_archive(verification_record)
    version = 7 if archive["prompt_version"].startswith("evidence-verification-v7") else (6 if archive["prompt_version"].startswith("evidence-verification-v6") else (5 if archive["prompt_version"].startswith("evidence-verification-v5") else (4 if "v4-" in archive["prompt_version"] else (2 if "v2-" in archive["prompt_version"] else 3))))
    if archive["prompt_version"]=="evidence-verification-v7-program-preconditions":
        from agents.verification_contract_v7 import parse_v7
        output=parse_v7(strict_json(archive["response_text"]),inputs,legacy=True)
    else:
        output = parse_verification(strict_json(archive["response_text"]), inputs, schema_version=version)
    # Compare historical semantic values; new diagnostics do not replace judgments.
    require(len(output.findings) == len(result["verification_output"]["findings"]), "Finding replay coverage mismatch")
    for actual, saved in zip(output.findings, result["verification_output"]["findings"]):
        require(actual.status.value == saved["status"] and json.loads(json.dumps(asdict(actual)))["excerpts"] == saved["excerpts"], "Finding replay mismatch")
    for actual, saved in zip(output.citation_reviews, result["verification_output"]["citation_reviews"]):
        require(actual.status.value == saved["status"] and list(actual.evidence_ids) == saved["evidence_ids"]
                and json.loads(json.dumps(asdict(actual)))["excerpts"] == saved["excerpts"], "Original citation replay mismatch")
    return payload, inputs, output, hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    destination = Path(args.output).resolve()
    require(destination.is_relative_to(LOCAL_ROOT.resolve()) and not destination.exists(), "Use a NEW report inside ignored data/retrieval_local")
    payload, inputs, output, digest = replay(args.input)
    report = ["# Offline review of archived model judgments", "",
              "No new model calls; semantic findings remain historical model judgments pending human review.",
              f"Input SHA-256: {digest}",
              "Complete generation input snapshot: " + ("saved" if inputs.generation_snapshot else "NOT VERIFIED; saved evidence candidates do not certify exact generation input completeness, so coverage assertions are not assessable under v3"), "",
              "Historical category labels are not semantic validation. Metadata/scope/advice require reclassification and the appropriate basis; no automatic replacement of historical judgments.", ""]
    report.append(render_review(payload))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(report))
    print(json.dumps({"report": str(destination), "claims_replayed": len(output.claims),
                      "citation_reviews_replayed": len(output.citation_reviews), "new_model_calls": 0,
                      "input_sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
