"""synthetic_fixture mechanics and private development replay, not semantic acceptance."""
from tests.fixture_paths import synthetic_diagnostics
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from agents.evidence_verification import ModelEvidenceVerificationAgent, parse_verification
from agents.verification_contract_v6 import PROMPT_VERSION, CONTRACT_VERSION, system_prompt
from core.validation import ContractError, validate_review, merge_evidence
from core.models import Evidence, VerificationStatus
from model_adapter.contracts import ModelResponse, ModelOutputError
from model_adapter.runtime import ModelBudget, model_scope
from services.quote_candidates import build_candidates, validate_catalog, MAX_PER_EVIDENCE
from services.validation_diagnostics import ValidationErrors
from tests.test_generation import ScriptAdapter
from tests.test_evidence_verification import SETTINGS
from tests.test_verification_v5 import inputs_for, wire


def body(inputs,eid="independent"):
    candidate=next(c for c in build_candidates(inputs.seed_evidence+inputs.original_evidence) if c.evidence_id==eid)
    return {"type":"text_excerpt","quote_id":candidate.quote_id}


class CandidateTests(unittest.TestCase):
    def test_crlf_unicode_exact_positions_and_context_without_normalization(self):
        text="First sentence.\r\nThis is only a line wrap.\r\n\r\n不能仅凭电压正常证明稳定😀。\r\n"
        evidence=Evidence("fixture-e","fixture","v1","fixture",text,"synthetic_fixture")
        catalog=build_candidates((evidence,))
        self.assertEqual(catalog,build_candidates((evidence,)))
        for c in catalog:
            self.assertEqual(c.text,text[c.start_offset:c.end_offset])
            self.assertEqual(c.context_text,text[c.context_start_offset:c.context_end_offset])
        self.assertEqual(len(catalog),3) # whole + two paragraphs, not every line
        changed=replace(evidence,text=text+'x')
        self.assertNotEqual(catalog[0].quote_id,build_candidates((changed,))[0].quote_id)
        with self.assertRaises(ContractError):validate_catalog((replace(catalog[0],text="normalized"),), (evidence,))

    def test_bounded_candidates_keep_whole_and_mark_uncertain_boundaries(self):
        text=("synthetic_fixture long sentence. "*500)+"This is not proof of stability."
        evidence=Evidence("long","fixture","v1","fixture",text,"synthetic_fixture")
        catalog=build_candidates((evidence,))
        self.assertLessEqual(len(catalog),MAX_PER_EVIDENCE)
        self.assertEqual(catalog[0].text,text)
        self.assertTrue(any("length_boundary_may_split_sentence_or_condition" in c.warnings for c in catalog))
        self.assertTrue(any("candidate_limit_applied_whole_fragment_retained" in c.warnings for c in catalog))


class ProtocolTests(unittest.TestCase):
    def test_invalid_metadata_field_has_actionable_options_without_acceptance(self):
        inputs=inputs_for()
        basis={"type":"metadata_reference","evidence_id":"independent","field_path":"locator"}
        with self.assertRaises(ValidationErrors) as caught:
            parse_verification(wire(inputs,[basis]),inputs,schema_version=6)
        errors=caught.exception.diagnostic["errors"]
        error=next(e for e in errors if e["constraint"]=="actual_nonnull_metadata_field_required")
        self.assertIn("source_id",error["allowed_nonnull_field_paths"])
        self.assertNotIn("locator",error["allowed_nonnull_field_paths"])
        self.assertIn("otherwise_insufficient_evidence_or_not_assessable",error["processing_options"])

    def test_only_id_body_selection_and_program_backfill(self):
        inputs=inputs_for();value=wire(inputs,[body(inputs)])
        out=parse_verification(value,inputs,schema_version=6)
        self.assertEqual(out.findings[0].excerpts[0].text,inputs.seed_evidence[0].text)
        self.assertTrue(out.quote_candidates)
        validate_review(out,inputs.answer,inputs.claims,out.evidence,True)

    def test_unknown_id_and_old_literal_fields_are_rejected_not_repaired(self):
        inputs=inputs_for()
        for basis in ({"type":"text_excerpt","quote_id":"invented"},
            {"type":"text_excerpt","evidence_id":"independent","quote":inputs.seed_evidence[0].text},
            dict(body(inputs),evidence_id="original"),dict(body(inputs),quote="copied text")):
            with self.assertRaises(ValidationErrors):parse_verification(wire(inputs,[basis]),inputs,schema_version=6)

    def test_candidate_for_wrong_evidence_scope_is_rejected(self):
        inputs=inputs_for()
        with self.assertRaises(ValidationErrors):parse_verification(wire(inputs,[body(inputs,"original")]),inputs,schema_version=6)
        value=wire(inputs,[body(inputs)])
        value["citation_reviews"][0].update(status="supported",bases=[body(inputs)])
        with self.assertRaises(ValidationErrors):parse_verification(value,inputs,schema_version=6)
        value["citation_reviews"][0]["bases"]=[body(inputs,"original")]
        self.assertEqual(parse_verification(value,inputs,schema_version=6).citation_reviews[0].status,VerificationStatus.SUPPORTED)

    def test_no_candidate_or_no_relevant_candidate_allows_insufficient_without_selection(self):
        inputs=replace(inputs_for(),seed_evidence=())
        value=wire(inputs,[],statuses=["insufficient_evidence"],indexes=[[]])
        self.assertEqual(parse_verification(value,inputs,schema_version=6).findings[0].status,VerificationStatus.INSUFFICIENT_EVIDENCE)
        inputs=inputs_for();value=wire(inputs,[body(inputs)],statuses=["insufficient_evidence"])
        self.assertEqual(parse_verification(value,inputs,schema_version=6).findings[0].status,VerificationStatus.INSUFFICIENT_EVIDENCE)

    def test_negation_and_causal_antecedent_preserved_without_semantic_auto_pass(self):
        inputs=inputs_for()
        source="synthetic_fixture: generators can supply reactive power.\nThis capability is driven by excitation.\nNormal voltage does not prove stability."
        inputs=replace(inputs,seed_evidence=(replace(inputs.seed_evidence[0],text=source),))
        for modeled_status in ("contradicted","insufficient_evidence","not_assessable"):
            value=wire(inputs,[body(inputs)],statuses=[modeled_status])
            out=parse_verification(value,inputs,schema_version=6)
            self.assertEqual(out.findings[0].status.value,modeled_status)
            self.assertEqual(out.findings[0].excerpts[0].text,source)
        # A deliberately wrong synthetic model judgment can still be structurally
        # valid; locating an excerpt does NOT certify its semantic relation.
        self.assertEqual(parse_verification(wire(inputs,[body(inputs)]),inputs,schema_version=6).findings[0].status,VerificationStatus.SUPPORTED)

    def test_program_catalog_or_quote_binding_tampering_rejected_by_core(self):
        inputs=inputs_for();out=parse_verification(wire(inputs,[body(inputs)]),inputs,schema_version=6)
        first=out.findings[0];changed=replace(first.bases[0],evidence_id="original")
        with self.assertRaises(ContractError):validate_review(replace(out,findings=(replace(first,bases=(changed,)),)),inputs.answer,inputs.claims,out.evidence,True)
        with self.assertRaises(ContractError):validate_review(replace(out,quote_candidates=(replace(out.quote_candidates[0],context_text="invented"),)+out.quote_candidates[1:]),inputs.answer,inputs.claims,out.evidence,True)

    def test_prompt_and_examples_have_only_candidate_body_ids_and_separate_semantics(self):
        prompt=system_prompt("synthetic_fixture semantic rules")
        self.assertNotIn('"quote": "Exact source text."',prompt)
        self.assertIn("NO other fields: no evidence_id, quote",prompt)
        self.assertIn("Candidate presence/overlap is not support",prompt)
        self.assertIn("causal/pronoun antecedents",prompt)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_truncated_response_is_privately_archived_without_retry(self):
        inputs=inputs_for();response=ModelResponse('{"findings":[',finish_reason="length")
        adapter=ScriptAdapter(response);budget=ModelBudget(2)
        local=Path(__file__).resolve().parents[1]/"data/retrieval_local"
        with synthetic_diagnostics() as directory,model_scope(budget):
            with self.assertRaises(ModelOutputError) as caught:
                await ModelEvidenceVerificationAgent(adapter,SETTINGS,schema_version=6,diagnostic_dir=directory).run(inputs)
            self.assertEqual(budget.used,1)
            self.assertNotIn(response.text,str(caught.exception))
            archive=json.loads(Path(budget.records[0].diagnostic_path).read_text(encoding="utf-8"))
            self.assertEqual(archive["response_text"],response.text)
            self.assertEqual(archive["finish_reason"],"length")
            self.assertEqual(budget.records[0].output_status,"invalid_model_response")

    async def test_catalog_saved_before_both_failed_calls_and_no_silent_literal_conversion(self):
        inputs=inputs_for();invalid=wire(inputs) # historic literal quote, invalid in v6
        adapter=ScriptAdapter(ModelResponse(json.dumps(invalid)));budget=ModelBudget(2)
        local=Path(__file__).resolve().parents[1]/"data/retrieval_local"
        with synthetic_diagnostics() as directory,model_scope(budget):
            with self.assertRaises(ModelOutputError):await ModelEvidenceVerificationAgent(adapter,SETTINGS,schema_version=6,diagnostic_dir=directory).run(inputs)
            self.assertEqual(budget.used,2)
            paths={r.candidate_catalog_path for r in budget.records}
            self.assertEqual(len(paths),1)
            saved=json.loads(Path(next(iter(paths))).read_text(encoding="utf-8"))
            self.assertEqual(saved["candidates"][0]["text"],inputs.seed_evidence[0].text)
            request=json.loads(adapter.requests[0].messages[1].content)
            self.assertTrue(request["QUOTE_CANDIDATES"])
            self.assertNotIn("text",request["INDEPENDENT_EVIDENCE"][0])
            self.assertNotEqual(set(request["INDEPENDENT_ALLOWED_QUOTE_IDS"]),set(request["ORIGINAL_CITATION_ALLOWED_QUOTE_IDS"]["0"]))
            error=json.loads(adapter.requests[1].messages[-1].content)["validation_errors"][0]
            self.assertEqual(error["allowed_fields"],["type","quote_id"])
            for rec in budget.records:
                self.assertEqual(rec.response_contract_version,CONTRACT_VERSION)
                archive=json.loads(Path(rec.diagnostic_path).read_text(encoding="utf-8"))
                self.assertEqual(archive["candidate_catalog_path"],rec.candidate_catalog_path)

    async def test_success_and_correction_are_counted_with_v6_versions(self):
        inputs=inputs_for();valid=wire(inputs,[body(inputs)]);adapter=ScriptAdapter(ModelResponse('{}'),ModelResponse(json.dumps(valid)))
        budget=ModelBudget(2)
        with model_scope(budget):out=await ModelEvidenceVerificationAgent(adapter,SETTINGS,schema_version=6).run(inputs)
        self.assertEqual(out.prompt_version,PROMPT_VERSION)
        self.assertEqual(budget.used,2)


class DevelopmentReplayTests(unittest.TestCase):
    def test_real_q3_v5_records_stay_failed_and_cannot_be_auto_migrated(self):
        from harness.evidence_review_demo import restore_answer,restore_evidence
        from agents.contracts import EvidenceVerificationInput
        from core.models import TaskRequest,TaskMode
        from services.claim_extractor import parse_extraction
        root=Path(__file__).resolve().parents[1]
        path=root/"data/retrieval_local/deepseek/evidence-review-q3-q5-v5-2-run3.json"
        if not path.exists():self.skipTest("Private Q3 development record unavailable")
        data=json.loads(path.read_text(encoding="utf-8"));r=data["runs"][0]["result"]
        self.assertEqual(r["state"],"review_required")
        def load(rec):
            archive=json.loads(Path(rec["diagnostic_path"]).read_text(encoding="utf-8"))
            self.assertEqual(hashlib.sha256(archive["response_text"].encode()).hexdigest(),archive["response_sha256"])
            return json.loads(archive["response_text"])
        answer=restore_answer(r["answer"]);claims=parse_extraction(load(r["model_records"][0]),answer,require_components=True).claims
        evidence=tuple(restore_evidence(e) for e in r["evidence"])
        retrieved={eid for rec in r["retrieval_records"] for eid in rec["core_evidence_ids"]+rec["context_evidence_ids"]}
        original={eid for c in answer.citations for eid in c.evidence_ids}
        inputs=EvidenceVerificationInput(TaskRequest("q3-offline",TaskMode.ASSESS_EXISTING,"fixture",data["runs"][0]["question"],existing_answer=answer),answer,claims,
            tuple(e for e in evidence if e.evidence_id in retrieved),original_evidence=tuple(e for e in evidence if e.evidence_id in original))
        for rec,count in zip(r["model_records"][1:],(5,4)):
            wire_value=load(rec)
            with self.assertRaises(ValidationErrors) as caught:parse_verification(wire_value,inputs,schema_version=5)
            self.assertEqual(len(caught.exception.diagnostics),count)
            with self.assertRaises(ValidationErrors):parse_verification(wire_value,inputs,schema_version=6)
        catalog=build_candidates(merge_evidence(inputs.seed_evidence,inputs.original_evidence))
        for candidate in catalog:
            raw=next(e.text for e in evidence if e.evidence_id==candidate.evidence_id)
            self.assertEqual(raw[candidate.start_offset:candidate.end_offset],candidate.text)
