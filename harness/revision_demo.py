"""Real generation and one bounded repair; synthetic bad drafts are explicit."""
import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
from types import SimpleNamespace
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.power_domain_review import ModelPowerDomainReviewAgent
from agents.revision import ModelRevisionAgent
from core.models import AnswerDraft,CitationBinding,TaskRequest,TaskMode
from harness.contracts import RunBudget,RetrievalSettings
from harness.deepseek_trial import PROJECT_ROOT,load_project_env,fee_summary
from harness.evidence_review_demo import restore_answer,restore_evidence,restore_snapshot
from harness.generation_demo import generate
from harness.policy import LimitedRepairPolicy
from harness.power_review_demo import CASES,repeated_contract_failure
from harness.runtime import OfflineHarness
from model_adapter.contracts import ModelSettings
from model_adapter.deepseek import create_adapter
from rag.retriever import AsyncSQLiteBM25Retriever
from services.claim_extractor import ModelClaimExtractor


def render(data):
    lines=["# Bounded real revision development trial","",
        "Synthetic constructed errors are development cases, not natural generation failures or an acceptance set.",
        "Demo domain rules; no simulation, no overall audit pass, no engineering safety certification.",
        f"New requests {data['actual_model_calls']}/{data['max_requests']}",
        f"Knowledge version: {data['knowledge_version']}",f"Cost (estimate, not invoice): {json.dumps(data['cost_summary'])}",""]
    for run in data["runs"]:
        lines += [f"## {run['scenario']}",run["input_origin"],run["question"],""]
        result=run.get("result")
        if not result:continue
        lines += [f"State: {result['state']}; {result['termination_reason']}",""]
        for round in result.get("review_rounds",[]):
            answer=round["answer"];lines += [f"### Frozen answer v{answer['version']}",answer["text"],
                f"Assumptions: {answer['assumptions']}",f"Missing: {answer['missing_information']}",""]
            known={e["evidence_id"]:e for e in result["evidence"]}
            for cite in answer["citations"]:
                lines += [f"Citation [{cite['start_offset']}:{cite['end_offset']}): "+answer["text"][cite["start_offset"]:cite["end_offset"]]]
                for eid in cite["evidence_ids"]:
                    e=known[eid];p=e["provenance"]
                    lines += [f"Evidence {eid}; file page={None if p is None else p['file_page']}; {e['locator']}",
                        f"Quality: {None if p is None else p['quality_warnings']}","~~~text",e["text"],"~~~"]
            for name in ("verification","domain_review"):
                out=round[name];lines += [f"### {name}",""]
                for f in out["findings"]:
                    lines += [f"- {f['finding_id']}; {f.get('status',f.get('check_status'))}: {f['rationale']}"]
                    for b in f.get("bases",[]):
                        lines += [f"  Basis: {json.dumps(b,ensure_ascii=False)}"]
                if out.get("consistency_checks"):lines += [json.dumps(out["consistency_checks"],ensure_ascii=False,indent=2)]
            extraction=round.get("extraction")
            if extraction:lines += [f"Uncovered spans: {extraction['uncovered_spans']}; non-claim spans: {extraction['non_claim_spans']}"]
        for revision in result.get("revision_outputs",[]):
            lines += ["### Proposed revision changes",json.dumps(revision["changes"],ensure_ascii=False,indent=2),
                "Explicit unresolved: "+json.dumps(revision["unresolved_finding_ids"]),"These declarations do not resolve historical findings."]
        for record in result["model_records"]:
            lines += [f"Request {record['call_number']} {record['prompt_version']}; correction={record['correction']}; {record['duration_ms']} ms; finish={record['finish_reason']}; usage={json.dumps(record['usage'])}",
                f"Response: {record['diagnostic_path']}; input: {record.get('input_snapshot_path')}; errors: {json.dumps(record['validation_error'])}"]
        lines += ["### Trace"]
        for e in result["trace"]["events"]:lines += [f"{e['component']}: {e['status']}; v{e['answer_version']}; {e['duration_ms']} ms"]
    return "\n".join(lines)+"\n"


async def run_demo(args,adapter,domain_adapter,settings,checkpoint):
    data={"scope":"BOUNDED_REAL_REVISION_NO_DOMAIN_PASS","knowledge_version":args.knowledge_version,
        "max_requests":args.max_requests,"actual_model_calls":0,"runs":[],"cost_summary":{}}
    records=[]
    if getattr(args,"review_saved_revision",None):
        import hashlib
        source=Path(args.review_saved_revision)
        prior=json.loads(source.read_text(encoding="utf-8"));run=prior["runs"][0];old=run["result"]
        revision=old["revision_outputs"][0]
        snapshot=restore_snapshot(revision["evidence_snapshot"]);answer=restore_answer(revision["answer"])
        evidence=tuple(restore_evidence(e) for e in old["evidence"])
        request=TaskRequest("stability-saved-revision-review",TaskMode.ASSESS_EXISTING,"voltage_stability_reactive_support",
            snapshot.question,snapshot.user_context,answer,evidence,snapshot.engineering_context)
        with AsyncSQLiteBM25Retriever(args.db) as retriever:
            harness=OfflineHarness(None,ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=args.diagnostic_dir,schema_version=8),
                ModelPowerDomainReviewAgent(domain_adapter,settings,diagnostic_dir=args.diagnostic_dir,protocol_version=2),
                None,ModelClaimExtractor(adapter,settings,diagnostic_dir=args.diagnostic_dir,typed_components=True),
                policy=LimitedRepairPolicy(),retriever=retriever)
            result=await harness.run(request,RunBudget(max_model_calls=args.max_requests,max_revision_rounds=0,
                max_duration_seconds=500,step_timeout_seconds=110,max_retrieval_chars_total=160000),
                knowledge_version=args.knowledge_version,indexed_reference_ids=tuple(e.evidence_id for e in evidence),
                generation_snapshot=snapshot)
        complete=(len(result.review_rounds)==1 and not result.execution_issues and not result.verification_output.execution_issues
            and not result.domain_output.execution_issues and len(old["revision_outputs"])==1
            and not old["review_rounds"][0]["verification"]["execution_issues"] and not old["review_rounds"][0]["domain_review"]["execution_issues"]
            and result.answer==answer)
        data["runs"]=[{"scenario":"normal-voltage-error","question":snapshot.question,"input_origin":"human_constructed_synthetic_fixture_error",
            "generation":None,"result":asdict(result),"minimal_execution_complete":complete,
            "prior_source":{"path":str(source.resolve()),"sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                "retained_round":old["review_rounds"][0],"retained_revision":revision},
            "note":"Continuation re-extracts and independently re-reviews saved v2; no generation/revision rerun; historical failed re-review unchanged"}]
        records=list(asdict(result)["model_records"]);data["actual_model_calls"]=len(records)
        data["cost_summary"]=fee_summary(records);checkpoint(data);return data
    for scenario in args.scenarios:
        left=args.max_requests-len(records)
        if left<3:break
        case=2 if scenario=="engineering-data" else 1 if scenario=="normal-voltage-error" else 3
        question,context=CASES[case]
        stable=getattr(args,"stable_protocols",False)
        if stable and case==1:question="Does normal bus voltage prove voltage stability?"
        run={"scenario":scenario,"question":question,
            "input_origin":"real_generated_draft" if case==2 else "human_constructed_synthetic_fixture_error",
            "generation":None,"result":None}
        data["runs"].append(run)
        snapshot=None; indexed=()
        if case==2:
            generation_args=SimpleNamespace(db=args.db,knowledge_version=args.knowledge_version,official_five=False,question=question,
                max_calls=min(2,left),duration=240,step_timeout=110,simulate_fixture=False,task_id_prefix="revision-engineering",
                diagnostic_dir=args.diagnostic_dir,user_context="synthetic_fixture; no actual engineering study has run.",
                engineering_context=context,requirement=["Keep within 160 words; answer units, traceable citations, specific missing inputs."],
                generation_contract_version=3)
            generated=await generate(generation_args,adapter,settings)
            gen=generated["runs"][0]["result"];run["generation"]=gen;records.extend(gen["model_records"])
            data["actual_model_calls"]=len(records);data["cost_summary"]=fee_summary(records);checkpoint(data)
            if gen["state"]!="generated":
                run["result"]=gen
                continue
            answer=restore_answer(gen["answer"]);evidence=tuple(restore_evidence(e) for e in gen["evidence"])
            snapshot=restore_snapshot(gen["generation_output"]["evidence_snapshot"])
            indexed=tuple(e.evidence_id for e in evidence)
            user_context=generation_args.user_context
        else:
            # Actual indexed records are used, not fabricated supporting text.
            historical=PROJECT_ROOT/"data/retrieval_local/deepseek"/("power-review-fresh-case1-v2.json" if case==1 else "power-review-fresh-case3-v2.json")
            saved=json.loads(historical.read_text(encoding="utf-8"))["runs"][0]["generation"]["result"]
            evidence=tuple(restore_evidence(e) for e in saved["evidence"])
            target=next((e for e in evidence if ("voltage" if case==1 else "rating") in e.text.lower()),evidence[0])
            text=("Normal bus voltage proves that the system is voltage stable; no further stability analysis is needed."
                if case==1 else "Four equipment ratings limit synchronous generator capability: stator winding rating, field current rating, terminal voltage rating, and active power output. Reactive power Q=30 MW has the correct unit. The same bus values 230 kV and 230 V are identical.")
            answer=AnswerDraft("constructed-"+scenario,1,text,citations=(CitationBinding(0,len(text),(target.evidence_id,)),))
            indexed=tuple(e.evidence_id for e in evidence)
            user_context="human_constructed synthetic_fixture erroneous answer; not naturally generated. No generation input snapshot exists and no simulation ran."
            if stable and case==1:
                # Minimal error without invented original citations or unrelated facts.
                answer=AnswerDraft("constructed-minimal-voltage",1,"Normal bus voltage proves voltage stability.")
                evidence=();indexed=()
        request=TaskRequest("revision-"+scenario,TaskMode.ASSESS_EXISTING,"voltage_stability_reactive_support",question,
            user_context,answer,evidence,context)
        left=args.max_requests-len(records)
        if left<3:run["stop_reason"]="Insufficient remaining budget for two independent reviews";break
        with AsyncSQLiteBM25Retriever(args.db) as retriever:
            harness=OfflineHarness(None,
                ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=args.diagnostic_dir,schema_version=8 if stable else 7),
                ModelPowerDomainReviewAgent(domain_adapter,settings,diagnostic_dir=args.diagnostic_dir,protocol_version=2 if stable else 1),
                ModelRevisionAgent(adapter,settings,diagnostic_dir=args.diagnostic_dir,protocol_version=2 if stable else 1),
                ModelClaimExtractor(adapter,settings,diagnostic_dir=args.diagnostic_dir,typed_components=True),
                policy=LimitedRepairPolicy(),retriever=retriever,retrieval_settings=RetrievalSettings())
            result=await harness.run(request,RunBudget(max_model_calls=left,max_revision_rounds=1,
                max_duration_seconds=800,step_timeout_seconds=110,max_retrieval_chars_total=160000),
                knowledge_version=args.knowledge_version,indexed_reference_ids=indexed,generation_snapshot=snapshot)
        run["result"]=asdict(result);records.extend(run["result"]["model_records"])
        run["stop_reason"]="Contract failed after one correction; scenario stopped" if repeated_contract_failure(run["result"]["model_records"]) else result.termination_reason
        data["actual_model_calls"]=len(records);data["cost_summary"]=fee_summary(records);checkpoint(data)
        if stable and case==1:
            run["minimal_execution_complete"]=(len(result.revision_outputs)==1 and len(result.review_rounds)==2
                and all(not r.verification.execution_issues and not r.domain_review.execution_issues for r in result.review_rounds)
                and not result.execution_issues)
            if not run["minimal_execution_complete"]:
                run["stop_reason"]="Minimal required loop incomplete; other scenarios gated";checkpoint(data);break
    data["actual_model_calls"]=len(records);data["cost_summary"]=fee_summary(records)
    checkpoint(data);return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",required=True);parser.add_argument("--knowledge-version",required=True)
    parser.add_argument("--output",required=True);parser.add_argument("--max-requests",type=int,default=25)
    parser.add_argument("--scenarios",default="engineering-data,normal-voltage-error,quantity-unit-error")
    parser.add_argument("--stable-protocols",action="store_true")
    parser.add_argument("--first-success",help="Saved successful minimal execution gate; does not mean audit pass")
    parser.add_argument("--review-saved-revision",help="Re-extract and independently review a saved revision; no generation/revision rerun")
    args=parser.parse_args();args.scenarios=tuple(args.scenarios.split(","))
    output=Path(args.output).resolve()
    if not 1<=args.max_requests<=25 or len(set(args.scenarios))!=len(args.scenarios) or not set(args.scenarios)<={"engineering-data","normal-voltage-error","quantity-unit-error"}:
        parser.error("Explicit scenarios and budget 1..25 required")
    if args.stable_protocols:
        if args.max_requests>20:parser.error("Stable protocol round cap is 20 requests")
        if args.scenarios[0]!="normal-voltage-error" and not args.review_saved_revision:
            if not args.first_success:parser.error("Run minimal loop first or supply --first-success")
            saved=json.loads(Path(args.first_success).read_text(encoding="utf-8"))
            if not any(r.get("minimal_execution_complete") for r in saved["runs"]):parser.error("Minimal execution gate not satisfied")
    if args.review_saved_revision:
        source=Path(args.review_saved_revision).resolve()
        if not args.stable_protocols or not source.is_relative_to(PROJECT_ROOT/"data/retrieval_local"):parser.error("Private source and stable protocols required")
        saved=json.loads(source.read_text(encoding="utf-8"))
        if saved["knowledge_version"]!=args.knowledge_version or len(saved["runs"][0]["result"]["revision_outputs"])!=1:
            parser.error("Frozen revision and knowledge version required")
    if not output.is_relative_to(PROJECT_ROOT/"data/retrieval_local") or output.suffix!=".json" or output.exists() or output.with_suffix(".md").exists():
        parser.error("New ignored JSON and Markdown paths required")
    load_project_env()
    model=os.environ.get("DEEPSEEK_MODEL_ID")
    if not model:parser.error("Missing configured model; no credentials printed")
    settings=ModelSettings(model,90,8000,96000,"https://api.deepseek.com","DEEPSEEK_API_KEY")
    adapter=create_adapter(settings);domain_adapter=create_adapter(settings)
    args.diagnostic_dir=PROJECT_ROOT/"data/retrieval_local/deepseek/response-diagnostics"
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as h:h.write("{}\n")
    def checkpoint(data):
        output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        output.with_suffix(".md").write_text(render(data),encoding="utf-8")
    try:data=asyncio.run(run_demo(args,adapter,domain_adapter,settings,checkpoint))
    finally:adapter.close();domain_adapter.close()
    print(json.dumps({"output":str(output),"actual_model_calls":data["actual_model_calls"],
        "scope":data["scope"],"states":[(r["scenario"],(r.get("result") or {}).get("state")) for r in data["runs"]]},indent=2))


if __name__=="__main__":main()
