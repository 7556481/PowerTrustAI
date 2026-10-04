"""Synthetic protocol/isolation regressions; private archives remain historical."""
import asyncio
from dataclasses import asdict,replace
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from agents.domain_contract_v2 import parse as domain_parse,mark as domain_mark
from agents.power_domain_review import MODEL_KEYS,ModelPowerDomainReviewAgent
from agents.revision_contract_v2 import parse as revision_parse,catalog as revision_catalog
from agents.contracts import RevisionInput
from agents.verification_contract_v8 import baseline,translate,mark
from agents.verification_contract_v7 import parse_v7
from agents.evidence_verification import ModelEvidenceVerificationAgent
from core.models import *
from core.validation import ContractError,validate_review
from services.scoped_candidates import CandidateScope
from services.review_isolation import WireIsolation,PartialReviewError
from services.request_metrics import measure
from model_adapter.runtime import ModelBudget,model_scope
from model_adapter.contracts import ModelMessage,ModelResponse,ModelSettings,ModelConnectionError
from tests.test_power_review import domain_input
from tests.test_verification_v5 import inputs_for
from tests.test_generation import ScriptAdapter

def wire_domain():
    return {"checks":[{"check_id":k,"status":"no_issue","claim_ids":[],"quote_ids":[],
        "basis_kind":"engineering_rule","rationale":"synthetic bounded check"} for k in MODEL_KEYS]}


class ScopeTests(unittest.TestCase):
    def test_citation_schema_has_no_independent_optional_observations(self):
        from agents.verification_contract_v8 import system_for
        citation=system_for("original_citation");independent=system_for("independent")
        self.assertNotIn("optional dimension_findings",citation)
        self.assertIn("No optional fields",citation)
        self.assertIn("optional dimension_findings",independent)
    def test_real_citation_extra_field_is_rejected_with_allowed_fields(self):
        from harness.evidence_review_demo import restore_answer,restore_evidence,restore_snapshot
        from agents.contracts import EvidenceVerificationInput
        from services.quote_candidates import build_candidates
        root=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek"
        path=root/"stability-minimal-v2.json"
        if not path.exists():self.skipTest("Private archive unavailable")
        result=json.loads(path.read_text(encoding="utf-8"))["runs"][0]["result"]
        out=result["verification_output"];answer=restore_answer(result["answer"])
        claims=tuple(Claim(**dict(c,qualifiers=tuple(c["qualifiers"]),components=tuple(ClaimComponent(**p) for p in c["components"]))) for c in out["claims"])
        known={e["evidence_id"]:restore_evidence(e) for e in result["evidence"]}
        ids={eid for r in result["retrieval_records"] if r["purpose"]=="verification" and r["answer_version"]==2
            for eid in r["core_evidence_ids"]+r["context_evidence_ids"]}
        original={eid for c in answer.citations for eid in c.evidence_ids}
        inputs=EvidenceVerificationInput(TaskRequest("offline",TaskMode.ASSESS_EXISTING,"fixture","Question"),answer,claims,
            tuple(e for eid,e in known.items() if eid in ids),original_evidence=tuple(known[eid] for eid in original),
            generation_snapshot=restore_snapshot(out["generation_snapshot"]))
        recs=[r for r in result["model_records"] if r["prompt_version"].startswith("evidence-verification") and r["call_number"] in (9,10)]
        source=json.loads(Path(recs[0]["candidate_catalog_path"]).read_text(encoding="utf-8"))
        scope=CandidateScope(answer,None,"original_citation",tuple(known[eid] for eid in original))
        candidates={(q.evidence_id,q.start_offset,q.end_offset):q for q in build_candidates(tuple(known[eid] for eid in original))}
        scope.scope_id=source["scope_id"];scope.by_wire={q["quote_id"]:candidates[(q["evidence_id"],q["start_offset"],q["end_offset"])] for q in source["QUOTE_CANDIDATES"]}
        base=baseline(inputs)
        def strict(v):
            expanded=json.loads(json.dumps(base));expanded["citation_reviews"][0]=translate(v,scope)["citation_reviews"][0]
            return parse_v7(expanded,inputs)
        for rec in recs:
            raw=json.loads(Path(rec["diagnostic_path"]).read_text(encoding="utf-8"))["response_text"]
            isolation=WireIsolation({"citation_reviews":[base["citation_reviews"][0]]},strict,{"citation_reviews":"citation_index"},mark)
            with self.assertRaises(PartialReviewError) as ctx:isolation.parse(json.loads(raw))
            errors=ctx.exception.diagnostic["errors"]
            error=next(e for e in errors if e["constraint"]=="unexpected_fields_not_allowed")
            self.assertEqual(set(error["allowed_fields"]),{"citation_index","status","rationale","applicability_conditions","bases"})
    def test_all_historical_responses_inspected_and_new_real_dimension_failure_replayed(self):
        from evaluation.protocol_failure_matrix import inspect
        self.assertEqual(inspect()["responses_inspected"],25)
        from harness.evidence_review_demo import restore_answer,restore_evidence
        from agents.contracts import EvidenceVerificationInput
        from services.quote_candidates import build_candidates
        root=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek"
        path=root/"stability-minimal-v1.json"
        if not path.exists():self.skipTest("Private new development archive unavailable")
        result=json.loads(path.read_text(encoding="utf-8"))["runs"][0]["result"]
        saved=result["review_rounds"][0]["verification"]
        answer=restore_answer(result["answer"])
        claims=tuple(Claim(**dict(c,qualifiers=tuple(c["qualifiers"]),components=tuple(ClaimComponent(**p) for p in c["components"]))) for c in saved["claims"])
        evidence=tuple(restore_evidence(e) for e in saved["evidence"])
        inputs=EvidenceVerificationInput(TaskRequest("offline",TaskMode.ASSESS_EXISTING,"fixture","Question"),answer,claims,evidence)
        records=[r for r in result["model_records"] if r["prompt_version"].startswith("evidence-verification")]
        candidates={ (c.evidence_id,c.start_offset,c.end_offset):c for c in build_candidates(evidence)}
        scope=CandidateScope(answer,None,"independent",evidence)
        source=json.loads(Path(records[0]["candidate_catalog_path"]).read_text(encoding="utf-8"))
        scope.scope_id=source["scope_id"];scope.by_wire={}
        for q in source["QUOTE_CANDIDATES"]:
            actual=candidates[(q["evidence_id"],q["start_offset"],q["end_offset"])]
            self.assertEqual(actual.text,q["text"])
            scope.by_wire[q["quote_id"]]=actual
        base=baseline(inputs)
        def strict(v):return parse_v7({**translate(v,scope),"citation_reviews":[]},inputs)
        for record in records:
            raw=json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))["response_text"]
            isolation=WireIsolation({"findings":base["findings"]},strict,{"findings":"claim_id"},mark)
            with self.assertRaises(PartialReviewError) as ctx:isolation.parse(json.loads(raw))
            errors=ctx.exception.diagnostic["errors"]
            expected="known_dimension_required" if record["correction"] else "unexpected_fields_not_allowed"
            self.assertTrue(any(e["constraint"]==expected for e in errors))
        from agents.evidence_verification import DIMENSIONS
        from agents.verification_contract_v8 import SYSTEM
        self.assertIn("jurisdiction",SYSTEM);self.assertEqual(DIMENSIONS[-1],"jurisdiction")
    def test_namespace_answer_version_purpose_and_no_foreign_body(self):
        i=inputs_for();a=CandidateScope(i.answer,"kv","independent",i.seed_evidence)
        b=CandidateScope(replace(i.answer,version=2),"kv","independent",i.seed_evidence)
        c=CandidateScope(i.answer,"kv","citation",i.seed_evidence,check_id=0)
        self.assertTrue(set(a.by_wire).isdisjoint(b.by_wire))
        self.assertTrue(set(a.by_wire).isdisjoint(c.by_wire))
        with self.assertRaises(ContractError):a.resolve(next(iter(b.by_wire)),"$.quote_id")
        self.assertNotIn("candidate_ids",a.payload())
        self.assertEqual(len(a.candidates),len(i.seed_evidence))
        for candidate in a.candidates:self.assertEqual(candidate.text,next(e.text for e in i.seed_evidence if e.evidence_id==candidate.evidence_id))
    def test_scope_unknown_and_old_canonical_id_strictly_rejected(self):
        i=inputs_for();s=CandidateScope(i.answer,"kv","independent",i.seed_evidence)
        for value in ("unknown",s.candidates[0].quote_id):
            with self.assertRaises(ContractError):s.resolve(value,"$.quote_id")
    def test_domain_discriminant_no_issue_cannot_carry_missing(self):
        i=domain_input();s=CandidateScope(i.answer,None,"domain_review",i.evidence)
        v=wire_domain();v["checks"][1]["missing_prerequisites"]=["Study"]
        with self.assertRaises(ContractError):domain_parse(v,i,s)
        output=domain_parse(wire_domain(),i,s)
        self.assertEqual(next(f for f in output.findings if f.category=="analysis_scope").missing_prerequisites,())
    def test_domain_bad_check_retains_peers_and_retry_first_valid(self):
        i=domain_input();s=CandidateScope(i.answer,None,"domain_review",i.evidence)
        fallback={"checks":[{**c,"status":"not_assessable","missing_prerequisites":["incomplete"]} for c in wire_domain()["checks"]]}
        isolation=WireIsolation(fallback,lambda v:domain_parse(v,i,s),{"checks":"check_id"},domain_mark)
        v=wire_domain();v["checks"][1]["missing_prerequisites"]=["invalid"]
        with self.assertRaises(PartialReviewError) as ctx:isolation.parse(v)
        out=ctx.exception.partial_output
        self.assertTrue(out.execution_issues)
        self.assertEqual(next(f for f in out.findings if f.category=="answer_units").check_status,"no_issue")
        self.assertEqual(next(f for f in out.findings if f.category=="analysis_scope").origin,"execution_incomplete")
        v=wire_domain();v["checks"][0]["quote_ids"]=["unknown"]
        with self.assertRaises(PartialReviewError) as ctx:isolation.parse(v)
        self.assertEqual(next(f for f in ctx.exception.partial_output.findings if f.category=="answer_units").check_status,"no_issue")
    def test_independent_invalid_basis_atomicity(self):
        i=inputs_for();c=i.claims[0];c2=replace(c,claim_id=c.claim_id+"-2",components=tuple(replace(p,component_id=p.component_id+"-2") for p in c.components))
        i=replace(i,claims=(c,c2));s=CandidateScope(i.answer,None,"independent",i.seed_evidence)
        base=baseline(i);fallback={"findings":base["findings"]}
        def strict(v):return parse_v7({**translate(v,s),"citation_reviews":base["citation_reviews"]},i)
        isolation=WireIsolation(fallback,strict,{"findings":"claim_id"},mark)
        v=json.loads(json.dumps(fallback));v["findings"][1]["bases"]=[{"type":"text_excerpt","quote_id":"wrong"}]
        with self.assertRaises(PartialReviewError) as ctx:isolation.parse(v)
        out=ctx.exception.partial_output
        self.assertEqual(out.findings[0].component_reviews[0].origin,"model_judgment")
        self.assertEqual(out.findings[1].component_reviews[0].origin,"execution_incomplete")
        validate_review(out,i.answer,i.claims,out.evidence,True)
    def test_metric_counts_duplicate_delivery_not_tokens(self):
        m=ModelMessage("user",json.dumps({"QUOTE_CANDIDATES":[{"evidence_id":"e","text":"abc"}],
            "evidence":[{"evidence_id":"e","text":"abc"}]}))
        value=measure((m,))
        self.assertEqual(value["candidate_count"],1);self.assertEqual(value["evidence_chars_delivered"],6)
        self.assertEqual(value["evidence_chars_unique"],3)


class LiveAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_domain_partial_survives_correction_connection_failure(self):
        value=wire_domain();value["checks"][1]["missing_prerequisites"]=["invalid"]
        adapter=ScriptAdapter(ModelResponse(json.dumps(value),finish_reason="stop"),ModelConnectionError())
        with model_scope(ModelBudget(2)):
            result=await ModelPowerDomainReviewAgent(adapter,ModelSettings("synthetic"),protocol_version=2).run(domain_input())
        self.assertTrue(result.execution_issues)
        self.assertEqual(next(f for f in result.findings if f.category=="answer_units").check_status,"no_issue")
    async def test_v8_separates_independent_and_original_request_candidates(self):
        i=inputs_for()
        class Adapter:
            requests=[]
            async def complete(self,request):
                self.requests.append(request);payload=json.loads(request.messages[1].content)
                if payload["purpose"]=="independent":
                    value={"findings":baseline(i)["findings"]}
                else:
                    value={"citation_reviews":[baseline(i)["citation_reviews"][payload["check_id"]]]}
                return ModelResponse(json.dumps(value),"synthetic",finish_reason="stop")
        adapter=Adapter()
        with model_scope(ModelBudget(4)):
            result=await ModelEvidenceVerificationAgent(adapter,ModelSettings("synthetic"),schema_version=8).run(i)
        self.assertFalse(result.execution_issues)
        payloads=[json.loads(r.messages[1].content) for r in adapter.requests]
        self.assertEqual(len(payloads),1+len(i.answer.citations))
        self.assertNotIn("original_citation",payloads[0])
        self.assertNotIn("claims",payloads[1])
        self.assertTrue(set(q["quote_id"] for q in payloads[0]["QUOTE_CANDIDATES"]).isdisjoint(
            q["quote_id"] for q in payloads[1]["QUOTE_CANDIDATES"]))


class RevisionProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def fixture(self):
        from tests.test_revision import RevisionTests
        _,_,inputs=await RevisionTests().prepared()
        return inputs
    async def test_actions_cover_all_findings_unknown_duplicate_and_missing(self):
        i=await self.fixture();rows=revision_catalog(i)
        value={"answer_units":[{"kind":"scope","text":"Limited corrected answer.","evidence_ids":[]}],
            "assumptions":[],"missing_information":["Study"],"finding_actions":[
                {"finding_id":row["finding_id"],"action":"modified" if j==0 else "retained","explanation":"Synthetic proposed edit"}
                for j,row in enumerate(rows)]}
        out=revision_parse(value,i);self.assertEqual(len(out.finding_actions),len(rows))
        self.assertTrue(out.unresolved_finding_ids)
        for bad in ("missing","duplicate","unknown"):
            v=json.loads(json.dumps(value))
            if bad=="missing":v["finding_actions"].pop()
            elif bad=="duplicate":v["finding_actions"].append(v["finding_actions"][0])
            else:v["finding_actions"][0]["finding_id"]="unknown"
            with self.assertRaises(ContractError):revision_parse(v,i)
