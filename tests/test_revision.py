"""Synthetic mechanics and archived failures, not independent quality acceptance."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import unittest
from agents.contracts import GenerationInput,RevisionInput
from agents.generation import parse_units,parse_answer
from agents.revision import ModelRevisionAgent,parse_revision
from agents.fakes import make_fake_harness,FakeConfig
from core.models import *
from core.validation import ContractError
from harness.contracts import RunBudget
from harness.policy import LimitedRepairPolicy
from model_adapter.contracts import ModelResponse,ModelSettings
from model_adapter.runtime import ModelBudget,model_scope
from services.answer_units import assemble
from services.evidence_scope import validate_snapshot

E=Evidence("e","synthetic","v1","synthetic","Voltage alone is insufficient.","synthetic_fixture")

def units(text="电压正常。\nStill not proof."):
    return {"answer_units":[{"kind":"technical","text":text,"evidence_ids":["e"]},
        {"kind":"technical","text":text,"evidence_ids":["e"]},
        {"kind":"clarification","text":"Which contingency?","evidence_ids":[]}],
        "assumptions":[],"missing_information":["Operating point"],"evidence_sufficient":False}

class UnitTests(unittest.TestCase):
    def test_archived_revision_missing_ids_replay_with_actionable_diagnostics(self):
        from types import SimpleNamespace
        from harness.evidence_review_demo import restore_answer,restore_evidence
        path=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek/revision-constructed-v1.json"
        if not path.exists():self.skipTest("Private development archive unavailable")
        data=json.loads(path.read_text(encoding="utf-8"))
        for run in data["runs"]:
            round=run["result"]["review_rounds"][0]
            findings=[SimpleNamespace(finding_id=f["finding_id"]) for f in round["verification"]["findings"]]
            domain=[SimpleNamespace(finding_id=f["finding_id"]) for f in round["domain_review"]["findings"]]
            inputs=RevisionInput(TaskRequest("t",TaskMode.ASSESS_EXISTING,"s",run["question"]),
                restore_answer(round["answer"]),SimpleNamespace(findings=tuple(findings)),
                SimpleNamespace(findings=tuple(domain)),tuple(restore_evidence(e) for e in run["result"]["evidence"]),())
            for rec in run["result"]["model_records"]:
                if not rec["prompt_version"].startswith("bounded-revision-v1-"):continue
                saved=json.loads(Path(rec["diagnostic_path"]).read_text(encoding="utf-8"))
                with self.assertRaises(ContractError) as ctx:parse_revision(json.loads(saved["response_text"]),inputs)
                self.assertEqual(ctx.exception.diagnostic["constraint"],"every_finding_needs_change_or_explicit_unresolved_record")
                self.assertTrue(ctx.exception.diagnostic["missing_finding_ids"])
                self.assertTrue(any(i.startswith("finding-claim-") for i in ctx.exception.diagnostic["missing_finding_ids"]))
    def test_archived_domain_conflict_still_rejected(self):
        from types import SimpleNamespace
        from agents.contracts import PowerDomainReviewInput
        from agents.power_domain_review import parse_domain,RULE_SET_VERSION
        from harness.evidence_review_demo import restore_answer,restore_evidence
        path=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek/revision-engineering-v1.json"
        if not path.exists():self.skipTest("Private development archive unavailable")
        run=json.loads(path.read_text(encoding="utf-8"))["runs"][0]
        result=run["result"];round=result["review_rounds"][0]
        inputs=PowerDomainReviewInput(TaskRequest("t",TaskMode.ASSESS_EXISTING,"s",run["question"]),
            restore_answer(round["answer"]),tuple(SimpleNamespace(claim_id=c["claim_id"]) for c in round["verification"]["claims"]),
            tuple(restore_evidence(e) for e in result["domain_output"]["evidence"]),RULE_SET_VERSION)
        for rec in result["model_records"]:
            if not rec["prompt_version"].startswith("power-domain-review"):continue
            saved=json.loads(Path(rec["diagnostic_path"]).read_text(encoding="utf-8"))
            with self.assertRaises(ContractError) as ctx:parse_domain(json.loads(saved["response_text"]),inputs)
            self.assertIn("missing_prerequisites_cannot_be_no_issue",str(ctx.exception.diagnostic))
    def test_real_enumeration_miss_is_preserved_with_program_warning(self):
        path=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek/revision-constructed-v1.json"
        if not path.exists():self.skipTest("Private development archive unavailable")
        result=json.loads(path.read_text(encoding="utf-8"))["runs"][1]["result"]
        out=result["verification_output"]
        count_claims={c["claim_id"] for c in out["claims"] if "four equipment ratings" in c["proposition"].lower()}
        self.assertTrue(any(f["claim_id"] in count_claims and f["status"]=="supported" for f in out["findings"]))
        self.assertTrue(any(f["category"].startswith("enumeration:") and f["check_status"]=="warning"
            for f in result["domain_output"]["findings"]))
        self.assertEqual(result["state"],"review_required")
    def test_repeat_newline_unicode_offsets(self):
        value=units();answer=assemble(value,"a",7,(E,))
        self.assertEqual(answer.version,7)
        for c in answer.citations:self.assertEqual(answer.text[c.start_offset:c.end_offset],value["answer_units"][0]["text"])
        self.assertEqual(answer.citations[1].start_offset,len(value["answer_units"][0]["text"])+2)
        self.assertEqual(len(answer.citations),2)
    def test_scope_label_not_exempt_and_model_version_rejected(self):
        value=units("Normal voltage guarantees stability.")
        value["answer_units"][0].update(kind="scope",evidence_ids=[])
        answer=assemble(value,"a",1,(E,))
        self.assertTrue(answer.text.startswith("Normal voltage guarantees stability."))
        self.assertEqual(answer.citations[0].start_offset,len(value["answer_units"][0]["text"])+2)
        inputs=GenerationInput(TaskRequest("t",TaskMode.QUESTION_ANSWER,"s","Question"),(E,))
        value["version"]=1
        with self.assertRaises(ContractError):parse_units(value,inputs)
    def test_archived_rereview_wrong_scope_remains_failure(self):
        from agents.contracts import EvidenceVerificationInput
        from agents.evidence_verification import parse_verification
        from harness.evidence_review_demo import restore_answer,restore_evidence,restore_snapshot
        path=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek/revision-normal-voltage-v2.json"
        if not path.exists():self.skipTest("Private development archive unavailable")
        data=json.loads(path.read_text(encoding="utf-8"));result=data["runs"][0]["result"];round=result["review_rounds"][1]
        answer=restore_answer(round["answer"]);known={e["evidence_id"]:restore_evidence(e) for e in result["evidence"]}
        ids={eid for r in result["retrieval_records"] if r["purpose"]=="verification" and r["answer_version"]==2
            for eid in r["core_evidence_ids"]+r["context_evidence_ids"]}
        claims=tuple(Claim(**dict(c,qualifiers=tuple(c["qualifiers"]),components=tuple(ClaimComponent(**part) for part in c["components"]))) for c in round["verification"]["claims"])
        original={eid for c in answer.citations for eid in c.evidence_ids}
        inputs=EvidenceVerificationInput(TaskRequest("t",TaskMode.ASSESS_EXISTING,"s",data["runs"][0]["question"]),
            answer,claims,tuple(e for eid,e in known.items() if eid in ids),knowledge_version=data["knowledge_version"],
            original_evidence=tuple(known[eid] for eid in original),
            generation_snapshot=restore_snapshot(round["verification"]["generation_snapshot"]))
        failed=[r for r in result["model_records"] if r["prompt_version"].startswith("evidence-verification") and r["output_status"]=="invalid_structure"]
        self.assertEqual(len(failed),2)
        for rec in failed:
            raw=json.loads(Path(rec["diagnostic_path"]).read_text(encoding="utf-8"))["response_text"]
            with self.assertRaises(ContractError) as ctx:parse_verification(json.loads(raw),inputs,schema_version=7)
            self.assertIn("candidate_Evidence_not_allowed_for_this_judgment",str(ctx.exception.diagnostic))
    def test_unknown_id_extra_offsets_all_errors(self):
        value=units();value["answer_units"][0].update(evidence_ids=["unknown"],start_offset=0)
        with self.assertRaises(ContractError) as ctx:assemble(value,"a",1,(E,))
        constraints={e["constraint"] for e in ctx.exception.diagnostic["errors"]}
        self.assertIn("unexpected_fields_not_allowed",constraints)
        self.assertIn("existing_input_evidence_ids_required",constraints)
    def test_uncited_technical_not_auto_supported(self):
        value=units();value["answer_units"][0]["evidence_ids"]=[]
        inputs=GenerationInput(TaskRequest("t",TaskMode.QUESTION_ANSWER,"s","Question"),(E,))
        a,sufficient=parse_units(value,inputs)
        self.assertFalse(sufficient);self.assertEqual(len(a.citations),1)
    def test_legacy_archives_remain_failure(self):
        root=Path(__file__).resolve().parents[1]/"data/retrieval_local/deepseek/response-diagnostics"
        for name in ("response-95fd103f39dc4f1ba2b881e3e55a4905.json","response-dadf62eba698484f8f583f13cdd1611f.json"):
            value=json.loads((root/name).read_text(encoding="utf-8"))
            raw=json.loads(value["response_text"])
            ev=replace(E,evidence_id=raw["citations"][0]["evidence_ids"][0])
            inputs=GenerationInput(TaskRequest("fresh-domain-case-2-1",TaskMode.QUESTION_ANSWER,"s","Question"),(ev,))
            with self.assertRaises(Exception) as ctx:parse_answer(value["response_text"],inputs)
            self.assertEqual(ctx.exception.diagnostic["field_path"],"$.citations[0].quote")
            self.assertNotIn(raw["citations"][0]["quote"],raw["text"])

class RevisionTests(unittest.IsolatedAsyncioTestCase):
    async def prepared(self):
        h=make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)))
        result=await h.run(TaskRequest("t",TaskMode.QUESTION_ANSWER,"s","Question"),RunBudget(max_revision_rounds=0))
        return h,result,RevisionInput(TaskRequest("t",TaskMode.QUESTION_ANSWER,"s","Question"),result.answer,
            result.verification_output,result.domain_output,result.evidence,("Correct errors",))
    def value(self,inputs):
        return {"answer_units":[{"kind":"scope","text":"Cannot conclude stability.","evidence_ids":[]}],
            "assumptions":[],"missing_information":["Study"],"changes":[{"finding_ids":[inputs.verification.findings[0].finding_id],
            "description":"Removed unsupported assurance"}],"unresolved_finding_ids":[f.finding_id for f in inputs.domain_review.findings]}
    async def test_real_interface_bound_version_snapshot_budget(self):
        h,result,inputs=await self.prepared();value=self.value(inputs)
        class Adapter:
            async def complete(self,request):return ModelResponse(json.dumps(value),"synthetic",finish_reason="stop")
        with model_scope(ModelBudget(1)):
            out=await ModelRevisionAgent(Adapter(),ModelSettings("synthetic")).run(inputs)
        self.assertEqual(out.answer.version,2);self.assertEqual(out.answer.answer_id,result.answer.answer_id)
        validate_snapshot(out.evidence_snapshot,out.answer)
        self.assertEqual(out.evidence_snapshot.input_prompt_version,"bounded-revision-v1.1-explicit-finding-catalog")
        self.assertEqual(len(out.model_records),1)
    async def test_unknown_findings_and_missing_accounting_rejected(self):
        _,_,inputs=await self.prepared();value=self.value(inputs);value["changes"][0]["finding_ids"]=["unknown"]
        with self.assertRaises(ContractError):parse_revision(value,inputs)
    async def test_revision_two_invalid_responses_consume_two_calls(self):
        from model_adapter.contracts import ModelOutputError
        _,_,inputs=await self.prepared();value=self.value(inputs)
        value["answer_units"][0]["evidence_ids"]=["unknown"]
        class Adapter:
            requests=[]
            async def complete(self,request):
                self.requests.append(request)
                return ModelResponse(json.dumps(value),"synthetic",finish_reason="stop")
        budget=ModelBudget(2);adapter=Adapter()
        with model_scope(budget):
            with self.assertRaises(ModelOutputError):
                await ModelRevisionAgent(adapter,ModelSettings("synthetic")).run(inputs)
        self.assertEqual(budget.used,2)
        self.assertTrue(adapter.requests[1].correction)
        feedback=json.loads(adapter.requests[1].messages[-1].content)
        self.assertIn("existing_input_evidence_ids_required",str(feedback["validation_errors"]))
    async def test_revision_budget_and_timeout_are_execution_failures(self):
        from model_adapter.contracts import ModelBudgetError,ModelTimeoutError
        _,_,inputs=await self.prepared()
        class Adapter:
            async def complete(self,request):
                await asyncio.sleep(.05)
                return ModelResponse("{}","synthetic",finish_reason="stop")
        with model_scope(ModelBudget(0)):
            with self.assertRaises(ModelBudgetError):await ModelRevisionAgent(Adapter(),ModelSettings("synthetic")).run(inputs)
        with model_scope(ModelBudget(1)):
            with self.assertRaises(ModelTimeoutError):
                await ModelRevisionAgent(Adapter(),ModelSettings("synthetic",timeout_seconds=.001)).run(inputs)
    async def test_full_harness_rereviews_keeps_history_and_single_budget(self):
        h,_,_=await self.prepared()
        h.extractor.versions.clear();h.verification.inputs.clear();h.domain_review.inputs.clear()
        class Adapter:
            async def complete(self,request):
                req=json.loads(request.messages[1].content)
                frozen=json.loads(req["answer_requirements"][-1])
                ids=[f["finding_id"] for output in ("verification","domain_review") for f in frozen[output]["findings"]]
                return ModelResponse(json.dumps({"answer_units":[{"kind":"scope","text":"Limited revised answer.","evidence_ids":[]}],
                    "assumptions":[],"missing_information":["Study"],"changes":[{"finding_ids":ids,"description":"Narrowed conclusion"}],
                    "unresolved_finding_ids":ids}),"synthetic",finish_reason="stop")
        h.revision=ModelRevisionAgent(Adapter(),ModelSettings("synthetic"));h.policy=LimitedRepairPolicy()
        result=await h.run(TaskRequest("t",TaskMode.QUESTION_ANSWER,"s","Question"),RunBudget(max_model_calls=6,max_revision_rounds=1))
        self.assertEqual([r.answer.version for r in result.review_rounds],[1,2])
        self.assertEqual(len(result.revision_outputs),1);self.assertEqual(len(result.model_records),1)
        self.assertEqual(h.extractor.versions,[1,2]);self.assertNotEqual(result.report.decision.kind,DecisionKind.PASS)
        self.assertEqual(h.verification.inputs[1].generation_snapshot.answer_version,2)
        self.assertEqual(result.review_rounds[0].answer.text,"Reactive power affects voltage.")
