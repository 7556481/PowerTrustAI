"""Bounded fresh generation + independent reviews; no domain safety certification."""
import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
from types import SimpleNamespace
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.power_domain_review import ModelPowerDomainReviewAgent
from core.models import TaskRequest,TaskMode,EngineeringContext,EngineeringQuantity
from core.validation import InputError
from harness.runtime import OfflineHarness
from harness.contracts import RunBudget,RetrievalSettings
from harness.generation_demo import generate
from harness.evidence_review_demo import restore_answer,restore_evidence,restore_snapshot
from harness.deepseek_trial import PROJECT_ROOT,load_project_env,fee_summary
from model_adapter.contracts import ModelSettings
from model_adapter.deepseek import create_adapter
from rag.retriever import AsyncSQLiteBM25Retriever
from services.claim_extractor import ModelClaimExtractor

CASES={
  1:("Is normal bus voltage sufficient to prove voltage stability? Explain what the evidence establishes and what analysis is still needed.",EngineeringContext()),
  2:("Can this particular plant safely add 30 MVAr reactive support and guarantee voltage stability? No network model, operating point, equipment limits or contingency study has been supplied. State what can and cannot be concluded.",EngineeringContext(goal="plant_assessment",quantities=(EngineeringQuantity("Q-proposal","reactive_power",30.,"MVAr","demo-plant"),))),
  3:("Review this synthetic proposed statement, not an established fact: 'Four equipment ratings limit synchronous generator capability: stator winding rating, field current rating, terminal voltage rating, and active power output.' Also review the supplied reactive-power quantity Q=30 MW and two voltage values for the same bus, 230 kV and 230 V. Identify count or unit inconsistencies without pretending to run a study.",EngineeringContext(quantities=(EngineeringQuantity("Q-error","reactive_power",30.,"MW","demo-plant"),EngineeringQuantity("V-1","voltage",230.,"kV","demo-bus"),EngineeringQuantity("V-2","voltage",230.,"V","demo-bus"))))
}


def render(payload):
    payload=json.loads(json.dumps(payload,ensure_ascii=False))
    lines=["# Fresh generation + independent limited reviews","",
        "Real model calls, official retrieved text; scenario engineering data are synthetic_fixture, not real plant inputs.",
        "No simulation, revision, overall audit pass or safety certification. Model findings require human review.",
        f"Knowledge version: {payload['knowledge_version']}",f"New requests: {payload['actual_model_calls']}/{payload['max_requests']}",
        f"Cost estimate (saved price, not invoice): {json.dumps(payload['cost_summary'])}",
        f"Stop reason: {payload.get('stop_reason')}", ""]
    for run in payload["runs"]:
        lines += [f"## Case {run['case']}", "",run["question"],"",f"Engineering context (unverified synthetic data): {json.dumps(run['engineering_context'])}",""]
        gen=run["generation"]["result"];answer=gen.get("answer")
        if answer:lines += ["### New frozen answer","",answer["text"],"",f"Assumptions: {answer['assumptions']}",f"Missing information: {answer['missing_information']}",""]
        snapshot=(gen.get("generation_output") or {}).get("evidence_snapshot")
        lines += [f"Generation state: {gen['state']}; snapshot: {None if snapshot is None else snapshot['snapshot_id']}; input evidence count: {0 if snapshot is None else len(snapshot['evidence'])}",""]
        review=run.get("review")
        if not review:continue
        lines += [f"Aggregate state: {review['state']}; {review['termination_reason']}",""]
        out=review.get("verification_output")
        if out:
            lines += ["### Evidence verification",f"Execution issues: {json.dumps(out['execution_issues'])}",""]
            for f in out["findings"]:
                claim=next(c for c in out["claims"] if c["claim_id"]==f["claim_id"])
                lines += [f"- {claim['claim_id']}: {claim['proposition']}; model/aggregate status={f['status']}; {f['rationale']}"]
                for part in f["component_reviews"]:lines += [f"  Component {part['component_id']}: {part['status']}, origin={part['origin']}, reason={part['reason_code']}; {part['rationale']}"]
            for c in out["consistency_checks"]:lines += [f"Quantity check: {json.dumps(c,ensure_ascii=False)}"]
            for c in out["citation_reviews"]:lines += [f"Original citation {c['citation_index']}: {c['status']}; warnings={c['binding_warnings']}; coverage={c['coverage_issues']}; {c['rationale']}"]
        domain=review.get("domain_output")
        if domain:
            lines += ["","### Independent Power Domain Review",f"Execution issues: {json.dumps(domain['execution_issues'])}",""]
            for rule in domain["rules"]:lines += [f"Rule {rule['rule_id']} @ {rule['version']}; DEMO={rule['demonstration_only']}; source={rule['source']}; scope={rule['applicable_scope']}"]
            for f in domain["findings"]:
                lines += ["",f"- {f['category']}: {f['check_status']}; origin={f['origin']}; basis={f['basis_kind']}; {f['rationale']}",f"  Missing prerequisites: {f['missing_prerequisites']}"]
        known={e["evidence_id"]:e for e in review["evidence"]};seen=set()
        for output in (out,domain):
            if not output:continue
            for f in output["findings"]+output.get("citation_reviews",[]):
                for b in f.get("bases",[]):
                    if b["type"]!="text_excerpt" or b["quote_id"] in seen:continue
                    seen.add(b["quote_id"]);e=known[b["evidence_id"]];p=e["provenance"];q=b["excerpt"]
                    lines += ["",f"Quote {b['quote_id']}; Evidence {e['evidence_id']}; file page={None if p is None else p['file_page']}; locator={e['locator']}",
                        f"Fragment chars [{q['start_offset']}:{q['end_offset']}); raw extraction basis, not visual PDF original.",
                        f"Source: {None if p is None else p['source_uri']}; quality={None if p is None else p['quality_warnings']}","~~~text",q["text"],"~~~"]
        records=gen["model_records"]+review["model_records"]
        lines += ["","### Requests and trace",""]
        for r in records:
            lines += [f"- {r['prompt_version']}; correction={r['correction']}; {r['duration_ms']} ms; finish={r['finish_reason']}; structure={r.get('output_status')}; usage={json.dumps(r['usage'])}; returned model={r['returned_model_id']}"]
            if r.get("validation_error"):lines += ["~~~json",json.dumps(r["validation_error"],ensure_ascii=False,indent=2),"~~~"]
            if r.get("diagnostic_path"):lines += ["Private response: "+r["diagnostic_path"]]
            if r.get("candidate_catalog_path"):lines += ["Private candidates: "+r["candidate_catalog_path"]]
            if r.get("input_snapshot_path"):lines += ["Private full generation input: "+r["input_snapshot_path"]]
        for e in review["trace"]["events"]:lines += [f"Trace {e['component']}: {e['status']}; answer version={e['answer_version']}; {e['duration_ms']} ms"]
    return "\n".join(lines)+"\n"


def repeated_contract_failure(records):
    previous={}
    for r in records:
        d=r.get("validation_error")
        if not d:continue
        keys={(e["stage"],e["constraint"]) for e in d.get("errors",[d])}
        if r["correction"] and keys & previous.get(r["prompt_version"],set()):return True
        previous[r["prompt_version"]]=keys
    return False


async def run_demo(args,adapter,settings,checkpoint=None,*,domain_adapter=None):
    payload={"scope":"LIMITED_REAL_REVIEWS_NO_ENGINEERING_CERTIFICATION","knowledge_version":args.knowledge_version,
        "max_requests":args.max_requests,"actual_model_calls":0,"runs":[],"stop_reason":None,"cost_summary":{}}
    records=[]
    def update():
        payload["actual_model_calls"]=len(records);payload["cost_summary"]=fee_summary(records)
        if checkpoint:checkpoint(payload)
    for case in args.cases:
        remaining=args.max_requests-len(records)
        if remaining<4:payload["stop_reason"]="Insufficient remaining budget for generation + extraction + two independent initial reviews";break
        question,context=CASES[case]
        generation_args=SimpleNamespace(db=args.db,knowledge_version=args.knowledge_version,official_five=False,question=question,
            max_calls=min(2,remaining),duration=240,step_timeout=110,simulate_fixture=False,
            task_id_prefix="fresh-domain-case-"+str(case),
            diagnostic_dir=args.diagnostic_dir,
            user_context="synthetic_fixture engineering inputs; no actual analysis or simulation has run.",
            engineering_context=context,requirement=["Keep the answer within 180 words. Preserve qualifications, cite exact answer sentences and state missing information. Draft only."])
        generated=await generate(generation_args,adapter,settings)
        gen=generated["runs"][0];records.extend(gen["result"]["model_records"])
        run={"case":case,"question":question,"engineering_context":asdict(context),"generation":gen,"review":None}
        payload["runs"].append(run);update()
        if gen["result"]["state"]!="generated":payload["stop_reason"]="Generation incomplete; reviews not run";break
        snapshot=restore_snapshot(gen["result"]["generation_output"]["evidence_snapshot"])
        answer=restore_answer(gen["result"]["answer"]);evidence=tuple(restore_evidence(e) for e in gen["result"]["evidence"])
        request=TaskRequest("power-review-"+str(case),TaskMode.ASSESS_EXISTING,"voltage_stability_reactive_support",question,
            generation_args.user_context,answer,evidence,context)
        left=args.max_requests-len(records)
        if left<3:payload["stop_reason"]="Insufficient budget for three initial review-stage calls";break
        # Same existing Harness, not another scheduler. Reserve no more than 5 for reviews.
        with AsyncSQLiteBM25Retriever(args.db) as retriever:
            harness=OfflineHarness(None,ModelEvidenceVerificationAgent(adapter,settings,diagnostic_dir=args.diagnostic_dir,schema_version=7),
                ModelPowerDomainReviewAgent(domain_adapter or adapter,settings,diagnostic_dir=args.diagnostic_dir),None,
                ModelClaimExtractor(adapter,settings,diagnostic_dir=args.diagnostic_dir,typed_components=True),
                retriever=retriever,retrieval_settings=RetrievalSettings())
            result=await harness.run(request,RunBudget(max_model_calls=min(5,left),max_revision_rounds=0,max_duration_seconds=300,step_timeout_seconds=110),
                knowledge_version=args.knowledge_version,indexed_reference_ids=tuple(e.evidence_id for e in evidence),generation_snapshot=snapshot)
        run["review"]=asdict(result);records.extend(run["review"]["model_records"]);update()
        if repeated_contract_failure(run["review"]["model_records"]):
            payload["stop_reason"]="Same contract error repeated after one format correction; stop paid batch";break
        if any(r["error_code"] in ("MODEL_AUTHENTICATION_FAILED","MODEL_INSUFFICIENT_BALANCE","MODEL_RATE_LIMITED","MODEL_CONNECTION_FAILED","MODEL_TIMEOUT") for r in run["review"]["model_records"]):
            payload["stop_reason"]="Service execution failure; stop paid batch";break
    if payload["stop_reason"] is None:payload["stop_reason"]="Selected fresh scenarios completed; no engineering certification"
    update();return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",required=True);parser.add_argument("--knowledge-version",required=True)
    parser.add_argument("--cases",default="1",help="Explicit subset of new scenarios: 1,2,3")
    parser.add_argument("--max-requests",type=int,default=20);parser.add_argument("--output",required=True)
    parser.add_argument("--model-id");parser.add_argument("--max-output-tokens",type=int,default=8000)
    args=parser.parse_args();output=Path(args.output).resolve()
    if not output.is_relative_to(PROJECT_ROOT/"data/retrieval_local") or output.suffix!=".json" or output.exists() or output.with_suffix(".md").exists():
        parser.error("Require new private .json and .md paths; do not overwrite")
    try:
        args.cases=tuple(int(c) for c in args.cases.split(","))
        if not args.cases or len(set(args.cases))!=len(args.cases) or not set(args.cases)<=set(CASES) or not 1<=args.max_requests<=20 or not 1<=args.max_output_tokens<=16000:raise ValueError()
        load_project_env() # Program-only authentication; no env contents logged.
        model_id=args.model_id or os.environ.get("DEEPSEEK_MODEL_ID")
        if not model_id:raise InputError("Missing configured model")
        settings=ModelSettings(model_id,90,args.max_output_tokens,max(96000,args.max_output_tokens*12),"https://api.deepseek.com","DEEPSEEK_API_KEY")
        adapter=create_adapter(settings)
        domain_adapter=create_adapter(settings)
    except (InputError,ValueError):
        parser.exit(2,"Invalid selection or model configuration; no requests or credentials logged\n")
    args.diagnostic_dir=PROJECT_ROOT/"data/retrieval_local/deepseek/response-diagnostics"
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as h:h.write("{}\n")
    def checkpoint(data):
        output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        output.with_suffix(".md").write_text(render(data),encoding="utf-8")
    try:payload=asyncio.run(run_demo(args,adapter,settings,checkpoint,domain_adapter=domain_adapter))
    finally:
        adapter.close()
        domain_adapter.close()
    print(json.dumps({"output":str(output),"scope":payload["scope"],"actual_model_calls":payload["actual_model_calls"],
        "stop_reason":payload["stop_reason"],"cases":[{"case":r["case"],"generation_state":r["generation"]["result"]["state"],
        "review_state":None if not r["review"] else r["review"]["state"]} for r in payload["runs"]]},ensure_ascii=False,indent=2))


if __name__=="__main__":main()
