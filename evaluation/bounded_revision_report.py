"""Offline artifact integrity/counting; no env load, model calls or semantic scores."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from agents.contracts import GenerationInput
from agents.generation import parse_units
from core.models import TaskMode,TaskRequest
from harness.deepseek_trial import PROJECT_ROOT,fee_summary
from harness.evidence_review_demo import restore_answer,restore_evidence,restore_snapshot
from services.answer_units import assemble
from services.evidence_scope import validate_snapshot

FILES=("revision-engineering-v1.json","revision-constructed-v1.json","revision-normal-voltage-v2.json")


def inspect():
    root=PROJECT_ROOT/"data/retrieval_local/deepseek"
    records=[];cases=[];hashes={};valid_requests=invalid_requests=0;checks=[]
    for name in FILES:
        path=root/name;hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        data=json.loads(path.read_text(encoding="utf-8"))
        for run in data["runs"]:
            gen=run.get("generation");result=run.get("result")
            groups=[] if not gen else [gen["model_records"]]
            if result is not None and result != gen:groups.append(result["model_records"])
            for group in groups:
                for record in group:
                    records.append(record)
                    valid_requests+=record["output_status"]=="valid_structure"
                    invalid_requests+=record["output_status"]=="invalid_structure"
                    if record["diagnostic_path"]:
                        saved=json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))
                        assert hashlib.sha256(saved["response_text"].encode()).hexdigest()==saved["response_sha256"]
                    if record.get("input_snapshot_path"):
                        before=json.loads(Path(record["input_snapshot_path"]).read_text(encoding="utf-8"))
                        digest=before.pop("input_sha256")
                        assert hashlib.sha256(json.dumps(before,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==digest
            if gen and gen["generation_output"]:
                output=gen["generation_output"];snap=restore_snapshot(output["evidence_snapshot"])
                answer=restore_answer(gen["answer"]);validate_snapshot(snap,answer)
                record=next(r for r in gen["model_records"] if r["output_status"]=="valid_structure")
                before=json.loads(Path(record["input_snapshot_path"]).read_text(encoding="utf-8"))
                # JSON round-trip normalizes dataclass tuples to arrays.
                assert before["evidence"]==json.loads(json.dumps([asdict(e) for e in snap.evidence]))
                request=TaskRequest("revision-engineering-1",TaskMode.QUESTION_ANSWER,"voltage_stability_reactive_support",
                    snap.question,snap.user_context,engineering_context=snap.engineering_context)
                inputs=GenerationInput(request,snap.evidence,snap.evidence_bindings,snap.knowledge_version,snap.answer_requirements)
                raw=json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))["response_text"]
                replayed,_=parse_units(json.loads(raw),inputs)
                assert replayed==answer
                checks.append({"scenario":run["scenario"],"kind":"full_generation_snapshot_and_answer_units_replay",
                    "evidence_count":len(snap.evidence),"citations":len(answer.citations),"snapshot":snap.snapshot_id})
            if result:
                for revision in result.get("revision_outputs",[]):
                    answer=restore_answer(revision["answer"]);snap=restore_snapshot(revision["evidence_snapshot"]);validate_snapshot(snap,answer)
                    record=next(r for r in revision["model_records"] if r["output_status"]=="valid_structure")
                    before=json.loads(Path(record["input_snapshot_path"]).read_text(encoding="utf-8"))
                    assert before["requested_answer_version"]==answer.version
                    assert before["evidence"]==json.loads(json.dumps([asdict(e) for e in snap.evidence]))
                    raw=json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))["response_text"]
                    replayed=assemble(json.loads(raw),answer.answer_id,answer.version,snap.evidence,stage="revision")
                    assert replayed==answer
                    checks.append({"scenario":run["scenario"],"kind":"full_revision_snapshot_and_answer_units_replay",
                        "evidence_count":len(snap.evidence),"citations":len(answer.citations),"snapshot":snap.snapshot_id})
                for round in result.get("review_rounds",[]):
                    assert round["verification"]["answer_version"]==round["answer"]["version"]==round["domain_review"]["answer_version"]
                    known={e["evidence_id"]:e for e in result["evidence"]}
                    for out in (round["verification"],round["domain_review"]):
                        for c in out["quote_candidates"]:
                            assert known[c["evidence_id"]]["text"][c["start_offset"]:c["end_offset"]]==c["text"]
                cases.append({"file":name,"scenario":run["scenario"],"state":result["state"],
                    "versions":[r["answer"]["version"] for r in result.get("review_rounds",[])],
                    "revisions":len(result.get("revision_outputs",[])),
                    "round_execution":[{"version":r["answer"]["version"],"verification_complete":not r["verification"]["execution_issues"],
                        "domain_complete":not r["domain_review"]["execution_issues"]} for r in result.get("review_rounds",[])],
                    "termination_reason":result["termination_reason"]})
    assert len(records)==25
    return {"scope":"OFFLINE_INTEGRITY_AND_DEVELOPMENT_OBSERVATIONS_NO_AUDIT_PASS","actual_requests":len(records),
        "valid_response_structures":valid_requests,"invalid_response_structures":invalid_requests,
        "usage":{"input_tokens":sum(r["usage"]["input_tokens"] for r in records),
            "output_tokens":sum(r["usage"]["output_tokens"] for r in records),
            "total_tokens":sum(r["usage"]["total_tokens"] for r in records)},
        "cost":fee_summary(records),"source_sha256":hashes,"cases":cases,"integrity_checks":checks}


def main():
    output=PROJECT_ROOT/"data/retrieval_local/deepseek/revision-summary-v1.json"
    result=inspect()
    with output.open("x",encoding="utf-8") as h:json.dump(result,h,ensure_ascii=False,indent=2)
    print(json.dumps({"output":str(output),"requests":result["actual_requests"],"usage":result["usage"],"cost":result["cost"]},indent=2))


if __name__=="__main__":main()
