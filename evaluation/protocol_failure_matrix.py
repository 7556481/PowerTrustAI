"""Inspect every archived response offline; historical statuses are immutable."""
import hashlib
import json
from pathlib import Path
from harness.deepseek_trial import PROJECT_ROOT
from evaluation.bounded_revision_report import FILES


def inspect():
    root=PROJECT_ROOT/"data/retrieval_local/deepseek";rows=[];audited=[]
    for name in FILES:
        data=json.loads((root/name).read_text(encoding="utf-8"))
        for run in data["runs"]:
            records=(run.get("generation") or {}).get("model_records",[])+run["result"]["model_records"]
            for record in records:
                saved=json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))
                assert hashlib.sha256(saved["response_text"].encode()).hexdigest()==saved["response_sha256"]
                body=json.loads(saved["response_text"])
                assert saved["prompt_version"]==record["prompt_version"]
                audited.append({"file":name,"scenario":run["scenario"],"call":record["call_number"],
                    "prompt":record["prompt_version"],"output_status":record["output_status"],"response_sha256":saved["response_sha256"]})
                diagnostic=record.get("validation_error")
                if not diagnostic:continue
                subsequent=[r for r in records if r["prompt_version"]==record["prompt_version"] and r["correction"]]
                correction_effective=any(r["output_status"]=="valid_structure" for r in subsequent)
                for error in diagnostic.get("errors",[diagnostic]):
                    constraint=error["constraint"]
                    classification=("protocol_and_prompt" if constraint in ("missing_prerequisites_cannot_be_no_issue","every_finding_needs_change_or_explicit_unresolved_record")
                        else "candidate_scope_protocol_and_model_selection" if "quote" in error["field_path"] or "candidate" in constraint
                        else "model_contract_output")
                    rows.append({"file":name,"scenario":run["scenario"],"stage":record["prompt_version"],"call":record["call_number"],
                        "correction":record["correction"],"field_path":error["field_path"],"constraint":constraint,
                        "correction_effective":correction_effective,"classification":classification,
                        "parser_assessment":"Constraint correctly rejected; no confirmed parser bug or permission to weaken it."})
    assert len(audited)==25
    return {"scope":"OFFLINE_ARCHIVE_REVIEW_NO_API","responses_inspected":25,"failures":rows,"responses":audited}


def main():
    root=PROJECT_ROOT/"data/retrieval_local/deepseek"
    data=inspect()
    with (root/"protocol-failure-matrix-v1.json").open("x",encoding="utf-8") as h:json.dump(data,h,ensure_ascii=False,indent=2)
    lines=["# Offline failure matrix","All 25 archived responses inspected; history unchanged.","",
        "| Scenario | Stage | Call/correction | Field | Constraint | Correction effective | Category |",
        "|---|---|---|---|---|---|---|"]
    for r in data["failures"]:lines.append(f"| {r['scenario']} | {r['stage']} | {r['call']}/{r['correction']} | {r['field_path']} | {r['constraint']} | {r['correction_effective']} | {r['classification']} |")
    with (root/"protocol-failure-matrix-v1.md").open("x",encoding="utf-8") as h:h.write("\n".join(lines)+"\n")
    print(json.dumps({"responses_inspected":25,"violation_rows":len(data["failures"]),"new_calls":0}))


if __name__=="__main__":main()
