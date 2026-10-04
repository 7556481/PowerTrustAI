"""Manually start paid local evidence review of saved drafts, never regenerate."""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path

from agents.evidence_verification import ModelEvidenceVerificationAgent, PROMPT_VERSION as REVIEW_PROMPT_VERSION, RESPONSE_CONTRACT_VERSION
from core.models import AnswerDraft, CitationBinding, Evidence, EvidenceProvenance, TaskMode, TaskRequest, GenerationEvidenceSnapshot
from services.evidence_scope import citation_coverage
from core.validation import InputError, merge_evidence, validate_answer
from harness.contracts import RetrievalSettings, RunBudget
from harness.deepseek_trial import PROJECT_ROOT, fee_summary, load_project_env, save
from harness.runtime import OfflineHarness
from model_adapter.contracts import ModelSettings
from model_adapter.deepseek import create_adapter
from rag.retriever import AsyncSQLiteBM25Retriever
from services.claim_extractor import ModelClaimExtractor, PROMPT_VERSION as EXTRACTION_PROMPT_VERSION


def restore_answer(value):
    return AnswerDraft(value["answer_id"], value["version"], value["text"],
        tuple(value.get("assumptions", ())), tuple(value.get("missing_information", ())),
        tuple(CitationBinding(c["start_offset"], c["end_offset"], tuple(c["evidence_ids"])) for c in value.get("citations", ())))


def restore_evidence(value):
    value = dict(value)
    value["applicability"] = tuple(value.get("applicability", ()))
    provenance = value.get("provenance")
    if provenance is not None:
        provenance = {k: tuple(v) if type(v) is list else v for k, v in provenance.items()}
        value["provenance"] = EvidenceProvenance(**provenance)
    return Evidence(**value)


def restore_snapshot(value):
    if value is None:
        return None
    from core.models import EngineeringContext,EngineeringQuantity,EvidenceBinding
    context=value.get("engineering_context")
    if context is not None:
        context=EngineeringContext(**dict(context,quantities=tuple(EngineeringQuantity(**q) for q in context["quantities"]),contingencies=tuple(context["contingencies"])))
    return GenerationEvidenceSnapshot(value["answer_id"], value["answer_version"],
        tuple(restore_evidence(e) for e in value["evidence"]), value["snapshot_id"], value.get("knowledge_version"),
        value.get("snapshot_version","generation-evidence-only-v1"),value.get("question"),value.get("user_context"),context,
        tuple(value.get("answer_requirements",())),value.get("input_prompt_version"),tuple(EvidenceBinding(**dict(b,core_evidence_ids=tuple(b.get("core_evidence_ids",())))) for b in value.get("evidence_bindings",())))


def read_saved_trial(path):
    data = Path(path).read_bytes()
    value = json.loads(data.decode("utf-8"))
    if type(value) is not dict or type(value.get("runs")) is not list or len(value["runs"]) != 5:
        raise InputError("Expected five saved generation runs")
    if type(value.get("knowledge_version")) is not str or not value["knowledge_version"]:
        raise InputError("Saved fixed knowledge_version required")
    for run in value["runs"]:
        evidence = tuple(restore_evidence(e) for e in run["result"]["evidence"])
        merge_evidence(evidence)
        validate_answer(restore_answer(run["result"]["answer"]), evidence)
        if any(e.provenance is None for e in evidence):
            raise InputError("This official trial entry requires traceable indexed evidence")
    return value, hashlib.sha256(data).hexdigest()


def validate_selection(questions, input_digest, confirmation_path=None, confirmed=False):
    if len(questions) != len(set(questions)) or not questions or any(i not in range(1, 6) for i in questions):
        raise InputError("Question IDs must be unique and within 1..5")
    if questions == (1,):
        return
    if not confirmed or confirmation_path is None or 1 in questions:
        raise InputError("Run question 1 first; manually inspect it and supply --confirm-first and --first-review")
    first = json.loads(Path(confirmation_path).read_text(encoding="utf-8"))
    if (first.get("input_sha256") != input_digest or first.get("scope") != "REAL_EVIDENCE_REVIEW_ONLY_NO_DOMAIN_PASS"
            or len(first.get("runs", ())) != 1 or first["runs"][0].get("question_number") != 1
            or first["runs"][0]["result"]["state"] != "evidence_reviewed"):
        raise InputError("First review missing, incomplete, or belongs to a different original trial")


async def review_saved(trial, digest, args, adapter, settings, checkpoint=None):
    # Retain explicit v4 programmatic compatibility; the paid CLI selects v6.
    schema_version = getattr(args, "verification_schema", 4)
    if schema_version >= 5:
        from services.claim_extractor import COMPONENT_PROMPT_VERSION as extraction_prompt
    if schema_version == 7:
        from agents.verification_contract_v7 import CONTRACT_VERSION as contract, PROMPT_VERSION as prompt
    elif schema_version == 6:
        from agents.verification_contract_v6 import CONTRACT_VERSION as contract, PROMPT_VERSION as prompt
    elif schema_version == 5:
        from agents.verification_contract_v5 import CONTRACT_VERSION as contract, PROMPT_VERSION as prompt
        from services.claim_extractor import COMPONENT_PROMPT_VERSION as extraction_prompt
    else:
        contract, prompt, extraction_prompt = RESPONSE_CONTRACT_VERSION, REVIEW_PROMPT_VERSION, EXTRACTION_PROMPT_VERSION
    payload = {"scope": "REAL_EVIDENCE_REVIEW_ONLY_NO_DOMAIN_PASS", "human_review": "pending",
        "input_sha256": digest, "knowledge_version": trial["knowledge_version"],
        "verification_contract_version": contract,
        "verification_schema_version": schema_version, "verification_prompt_version": prompt,
        "claim_extraction_prompt_version": extraction_prompt,
        "execution_limits": {"model_calls_per_question": 4, "initial_extraction": 1,
            "extraction_corrections": 1, "initial_verification": 1, "verification_corrections": 1},
        "domain_review": "not_run", "generation": "not_run", "revision": "not_implemented", "runs": []}
    with AsyncSQLiteBM25Retriever(args.db) as retriever:
        diagnostic_dir = getattr(args, "diagnostic_dir", None)
        harness = OfflineHarness(None, ModelEvidenceVerificationAgent(adapter, settings, diagnostic_dir=diagnostic_dir, schema_version=schema_version), None, None,
            ModelClaimExtractor(adapter, settings, diagnostic_dir=diagnostic_dir, typed_components=schema_version >= 5), retriever=retriever, retrieval_settings=RetrievalSettings())
        for index in args.questions:
            saved = trial["runs"][index - 1]
            original = tuple(restore_evidence(e) for e in saved["result"]["evidence"])
            answer = restore_answer(saved["result"]["answer"])
            if sum(len(e.text) for e in original) > 64000:
                raise InputError("Saved original evidence exceeds bounded input size; no truncation allowed")
            request = TaskRequest(f"evidence-review-{index}", TaskMode.ASSESS_EXISTING,
                "voltage_stability_reactive_support", saved["question"], existing_answer=answer, provided_evidence=original)
            result = await harness.run(request, RunBudget(max_model_calls=4, max_revision_rounds=0,
                max_retrieval_calls=1, max_duration_seconds=400, step_timeout_seconds=200),
                knowledge_version=trial["knowledge_version"], evidence_only=True,
                indexed_reference_ids=tuple(e.evidence_id for e in original),
                generation_snapshot=restore_snapshot((saved["result"].get("generation_output") or {}).get("evidence_snapshot")))
            payload["runs"].append({"question_number": index, "question": saved["question"], "result": asdict(result)})
            records = [r for run in payload["runs"] for r in run["result"]["model_records"]]
            payload["actual_model_calls"] = len(records)
            payload["cost_summary"] = fee_summary(records)
            if checkpoint:
                checkpoint(payload)
            # No hidden retries of failed runs; leave partial traces and stop batch.
            if result.state.value != "evidence_reviewed":
                break
    return payload


def render_review(payload):
    """Human-readable per-claim judgments; quote validation is not semantic proof."""
    # Match the saved JSON representation of str-enums, rather than Enum reprs.
    payload = json.loads(json.dumps(payload, ensure_ascii=False))
    lines = ["# Evidence review only: no domain audit pass", "",
             f"Original JSON SHA-256: {payload['input_sha256']}",
             f"Knowledge version: {payload['knowledge_version']}",
             f"Verification contract: {payload.get('verification_contract_version', 'not_recorded')}; "
             f"prompt: {payload.get('verification_prompt_version', 'not_recorded')}",
             "All judgments are model judgments pending human review. No generation/revision/domain review.", ""]
    for run in payload["runs"]:
        result = run["result"]
        lines += [f"## Question {run['question_number']}", "", run["question"], "",
                  f"State: {result['state']}; termination: {result['termination_reason']}", ""]
        answer = result["answer"]
        lines += ["### Frozen original answer", "", answer["text"], ""]
        lines += [f"Original assumptions (not separately claim-reviewed): {answer['assumptions']}",
                  f"Original missing_information (not separately claim-reviewed): {answer['missing_information']}", ""]
        for rec in result["model_records"]:
            lines.append(f"- Call {rec['call_number']}: {rec['prompt_version']}, correction={rec['correction']}, "
                         f"contract={rec.get('response_contract_version', 'not_recorded')}, "
                         f"{rec['duration_ms']} ms, {rec['status']}, usage={json.dumps(rec['usage'])}, "
                         f"returned_model={rec['returned_model_id']}, finish={rec['finish_reason']}, error={rec['error_code']}")
            if rec.get("validation_error"):
                lines.append("  Validation: " + json.dumps(rec["validation_error"], ensure_ascii=False))
            if rec.get("diagnostic_path"):
                lines.append("  Private response diagnostic: " + rec["diagnostic_path"])
            if rec.get("candidate_catalog_path"):
                lines.append("  Frozen program candidate catalog: " + rec["candidate_catalog_path"])
        lines += ["### Execution issues", "", json.dumps(result["execution_issues"], ensure_ascii=False), ""]
        extraction, output = result["extraction_output"], result["verification_output"]
        if extraction:
            lines += ["", "### Unreviewed/classified nonclaim text", ""]
            for group in ("uncovered_spans", "non_claim_spans"):
                for span in extraction[group]:
                    lines += [f"- {group} [{span['start_offset']}:{span['end_offset']}): {span['reason']}",
                              "~~~text", span["text"], "~~~"]
            lines += ["Semantic atomicity/qualification completeness has not been mechanically proven.", ""]
            lines += [f"Coverage warnings: {extraction['warnings']}", ""]
        if not output:
            lines += ["Verification not completed.", ""]
            continue
        known = {e["evidence_id"]: e for e in result["evidence"]}
        claims = {c["claim_id"]: c for c in output["claims"]}
        def add_quotes(quotes):
            for q in quotes:
                e = known[q["evidence_id"]]
                p = e["provenance"]
                location = e["locator"]
                if p:
                    basis = "page_chars" if p["file_page"] is not None else "source_chars"
                    location += f"; excerpt {basis}[{p['start_offset'] + q['start_offset']}:{p['start_offset'] + q['end_offset']})"
                lines.extend([f"Evidence {e['evidence_id']}, file_page={None if p is None else p['file_page']}, "
                              f"{location}; source={e['source_id']}, applicability={e['applicability']}",
                              f"Quality: {None if p is None else p['quality_warnings']}",
                              "~~~text", q["text"], "~~~", ""])
        for f in output["findings"]:
            c = claims[f["claim_id"]]
            lines += [f"### Independent finding {f['claim_id']}: {f['status']}", "",
                      f"Category: {f.get('claim_category', 'unclassified')}; basis: {f.get('assessment_basis', 'legacy_text_evidence')}; scope: {f.get('scope_id')}",
                      f"Atomic proposition: {c['proposition']}",
                      f"Source answer [{c['start_offset']}:{c['end_offset']}):", "~~~text", c["text"], "~~~",
                      f"Qualifiers: {c['qualifiers']}", f"Reason: {f['rationale']}",
                      f"Conditions: {f['applicability_conditions']}",
                      f"Method: {f['check_method']}; required dimensions: {f.get('required_dimensions', [])}",
                      f"Reported dimension observations (not proof of completed checks): {f.get('dimension_findings', [])}",
                      f"Historical checked_dimensions (legacy checklist only): {f['checked_dimensions']}", ""]
            add_quotes(f["excerpts"])
            if f.get("component_reviews"):
                parts = {part["component_id"]: part for part in c["components"]}
                lines += [f"Shared source anchor group: {c.get('anchor_group_id')}", ""]
                for review in f["component_reviews"]:
                    part = parts[review["component_id"]]
                    lines += [f"Component {part['component_id']} ({part['category']}): {part['proposition']}",
                              f"Status: {review['status']}; basis indexes: {review['basis_indexes']}; reason: {review['rationale']}", ""]
                    if review.get("classification_issue"):
                        lines += ["Classification disagreement (frozen category not changed): " + json.dumps(review["classification_issue"], ensure_ascii=False), ""]
                lines += ["Typed bases (program-bound locations/values):", "~~~json", json.dumps(f["bases"], ensure_ascii=False, indent=2), "~~~", ""]
            for ref in f.get("metadata_refs", []):
                e = known[ref["evidence_id"]]
                lines += [f"Metadata {ref['evidence_id']}: {ref['field_path']} = {ref['value_json']}; location={e['locator']}", ""]
        for review in output["citation_reviews"]:
            binding = answer["citations"][review["citation_index"]]
            from types import SimpleNamespace
            replay_claims = tuple(SimpleNamespace(**c) for c in output["claims"])
            replay_findings = tuple(SimpleNamespace(**dict(f, status=SimpleNamespace(value=f["status"]))) for f in output["findings"])
            partial, coverage = citation_coverage(restore_answer(answer), replay_claims, review["citation_index"], replay_findings)
            lines += [f"### Original citation {review['citation_index']}: semantic status={review['status']}", "",
                      "~~~text", answer["text"][binding["start_offset"]:binding["end_offset"]], "~~~",
                      f"Originally bound IDs: {review['evidence_ids']}", f"Warnings: {review['binding_warnings']}",
                      f"Overlapping claim IDs: {review['claim_ids']} (overlap is not proof of full claim support)",
                      f"Partial source-anchor coverage: {list(partial)}; separate coverage issues: {list(coverage)}",
                      "Boundary/coverage issues remain unresolved. Other citations or independent support cannot cure this original citation.",
                      f"Reason: {review['rationale']}", f"Conditions: {review['applicability_conditions']}",
                      f"Method: {review['check_method']}", ""]
            add_quotes(review["excerpts"])
            if review.get("bases"):
                lines += ["Original citation typed bases:", "~~~json", json.dumps(review["bases"], ensure_ascii=False, indent=2), "~~~", ""]
    lines += [f"Actual recorded model calls: {payload.get('actual_model_calls', 0)}",
              f"Saved price estimate (not invoice): {json.dumps(payload.get('cost_summary'))}",
              "Literal excerpt matching and retrievability do not establish semantic support. Human review required."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(PROJECT_ROOT / "data/retrieval_local/deepseek/official-trial.json"))
    parser.add_argument("--db", default=str(PROJECT_ROOT / "data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3"))
    parser.add_argument("--questions", required=True, help="1 first; then 2,3,4,5 after manual inspection")
    parser.add_argument("--confirm-first", action="store_true")
    parser.add_argument("--first-review")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-id")
    parser.add_argument("--max-output-tokens", type=int, default=10000,
                        help="Explicit paid response token cap (1..16000); no extra requests")
    args = parser.parse_args()
    args.verification_schema = 7
    # The manually started paid entry always archives responses locally. Never
    # load their bodies into normal logs or the Markdown report.
    args.diagnostic_dir = PROJECT_ROOT / "data/retrieval_local/deepseek/response-diagnostics"
    output = Path(args.output).resolve()
    if not output.is_relative_to(PROJECT_ROOT / "data/retrieval_local") or output == Path(args.input).resolve() or output.exists():
        parser.error("Use a NEW JSON output under ignored data/retrieval_local, never the original trial")
    if output.suffix != ".json" or output.with_suffix(".md").exists():
        parser.error("Use a new .json output and a nonexisting matching .md report")
    try:
        trial, digest = read_saved_trial(args.input)
        args.questions = tuple(int(v) for v in args.questions.split(","))
        validate_selection(args.questions, digest, args.first_review, args.confirm_first)
    except (InputError, ValueError, OSError, KeyError, TypeError):
        parser.exit(2, "Invalid saved trial, question selection or first-review confirmation; no model requests\n")
    # Only a human invoking this paid CLI loads credentials. Imports/tests do not.
    try:
        load_project_env()
        model_id = args.model_id or os.environ.get("DEEPSEEK_MODEL_ID")
        if not model_id:
            raise InputError("Model configuration missing")
        if not 1 <= args.max_output_tokens <= 16000:
            raise InputError("Invalid explicit output token cap")
        settings = ModelSettings(model_id, 90, args.max_output_tokens, max(96000, args.max_output_tokens * 12), "https://api.deepseek.com", "DEEPSEEK_API_KEY")
        adapter = create_adapter(settings)
    except InputError:
        parser.exit(2, "Model configuration missing/invalid; no secret logged, no model requests\n")
    def checkpoint(payload):
        save(output, payload)
        output.with_suffix(".md").write_text(render_review(payload), encoding="utf-8")
    try:
        payload = asyncio.run(review_saved(trial, digest, args, adapter, settings, checkpoint))
    finally:
        adapter.close()
    if hashlib.sha256(Path(args.input).read_bytes()).hexdigest() != digest:
        parser.exit(1, "Original trial changed externally during review; investigate output provenance\n")
    print(json.dumps({"scope": payload["scope"], "output": str(output),
        "report": str(output.with_suffix(".md")), "actual_model_calls": payload.get("actual_model_calls", 0),
        "states": [r["result"]["state"] for r in payload["runs"]]}, ensure_ascii=False, indent=2))
    if any(r["result"]["state"] != "evidence_reviewed" for r in payload["runs"]):
        parser.exit(1)


if __name__ == "__main__":
    main()
