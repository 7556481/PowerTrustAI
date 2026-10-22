"""Authorized-entry offline gates: never construct a provider or read .env."""
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from agents.fakes import FakeConfig, make_fake_harness
from agents.contracts import GenerationOutput
from core.models import AnswerDraft, CitationBinding, VerificationStatus, ClaimExtractionOutput
from evaluation import generation_mapping_trial_v1 as trial
from evaluation.generation_mapping_comparison_materials_v1 import build_inputs, message_rows, PUBLIC
from model_adapter.contracts import ModelRequest, ModelMessage, ModelResponse
from services.evidence_scope import make_snapshot


def plan():
    return trial.read(PUBLIC / "freeze-plan-v1.json")


class Delegate:
    def __init__(self, answer="{bad"):
        self.calls = 0
        self.answer = answer

    async def complete(self, request):
        self.calls += 1
        return ModelResponse(self.answer)

    def close(self): pass


class Gates(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.net = patch.object(socket.socket, "connect", side_effect=AssertionError("Offline only"))
        self.net.start()
        self.addCleanup(self.net.stop)
        root = Path(__file__).resolve().parents[1] / "data/retrieval_local"
        root.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix="generation-trial-tests-", dir=root)
        self.root = Path(directory.name)
        self.assertTrue(self.root.resolve().is_relative_to(root.resolve()))
        self.addCleanup(directory.cleanup)
        self.values = build_inputs(trial.read(PUBLIC / "tasks-v1.json"))

    def state(self):
        from time import perf_counter
        return {"started": perf_counter(), "send_sequence": 0, "sent": []}

    async def test_exact_generation_and_presend_hash_before_delegate(self):
        case = plan()["order"][0]
        value = self.values[case["task_id"]]
        delegate = Delegate()
        guard = trial.GuardedAdapter(delegate, case, value, self.state(), self.root)
        messages = tuple(ModelMessage(**m) for m in message_rows(value, "original"))
        request = ModelRequest("deepseek-flash", messages, 8000,
                 "evidence-bound-generation-v3-answer-units-product-v1-question-language-v11-length-planning")
        await guard.complete(request)
        saved = trial.read(self.root / "before-send-001.json")
        self.assertEqual(saved["messages_sha256"], case["initial_messages_sha256"])
        self.assertEqual(delegate.calls, 1)

    async def test_identity_mismatch_no_send_no_fallback(self):
        case = plan()["order"][0]
        delegate, state = Delegate(), self.state()
        guard = trial.GuardedAdapter(delegate, case, self.values[case["task_id"]], state, self.root)
        request = ModelRequest("deepseek-flash", (ModelMessage("user", "changed"),), 8000,
                 "evidence-bound-generation-v3-answer-units-product-v1-question-language-v11-length-planning")
        for _ in range(2):
            with self.assertRaises(trial.PreSendFailure): await guard.complete(request)
        self.assertEqual(delegate.calls, 0)
        self.assertTrue(state["fatal_gate"])

    async def test_audit_mapping_or_rubric_keys_rejected_without_keyword_filtering_answer(self):
        for field in ("diagnostic_map", "quality_checks", "expected_labels"):
            with self.subTest(field=field):
                delegate = Delegate()
                guard = trial.GuardedAdapter(delegate, plan()["order"][0], self.values["GEC-01"], self.state(), self.root)
                req = ModelRequest("deepseek-flash", (ModelMessage("system", "frozen"),
                     ModelMessage("user", json.dumps({field: []}))), 8000, "power-domain-review-v3.5-task-obligations")
                with self.assertRaises(trial.PreSendFailure): await guard.complete(req)
                self.assertEqual(delegate.calls, 0)
        trial.assert_no_evaluator_keys({"text": "The actual answer contains the word diagnostic_map."})

    async def test_presend_storage_failure_zero_delegate_calls(self):
        case = plan()["order"][0]
        delegate = Delegate()
        guard = trial.GuardedAdapter(delegate, case, self.values["GEC-01"], self.state(), self.root)
        request = ModelRequest("deepseek-flash", tuple(ModelMessage(**m) for m in message_rows(self.values["GEC-01"], "original")),
                 8000, "evidence-bound-generation-v3-answer-units-product-v1-question-language-v11-length-planning")
        with patch.object(trial, "write", side_effect=OSError("fixture")):
            with self.assertRaises(trial.PreSendStorageFailure): await guard.complete(request)
        self.assertEqual(delegate.calls, 0)

    async def test_real_harness_generation_final_failure_stops_next_branch(self):
        delegates = []
        def factory():
            d = Delegate(); delegates.append(d); return d
        summary = await trial.run_batch(plan(), self.root / "batch", self.root / "responses", factory)
        self.assertEqual([r["status"] for r in summary["branches"]], ["execution_failed"] + ["unexecuted"] * 7)
        self.assertEqual(sum(d.calls for d in delegates), 2)
        self.assertEqual(len(delegates), 2)

    async def test_actual_extraction_and_both_review_messages_pass_gate_before_review_failure(self):
        requests = []
        evidence_id = self.values['GEC-01'].evidence[0].evidence_id

        class Scripted(Delegate):
            async def complete(self, request):
                self.calls += 1
                requests.append(request)
                if request.prompt_version.startswith('evidence-bound-generation'):
                    value = {'answer_units': [{'kind': 'technical', 'text': '教学合成回答。',
                              'evidence_ids': [evidence_id]}], 'assumptions': [],
                              'missing_information': [], 'evidence_sufficient': True}
                elif request.prompt_version.startswith('atomic-claims'):
                    payload = json.loads(request.messages[1].content)
                    value = {'claims': [{'anchor_id': a['anchor_id'], 'proposition': a['text'],
                        'claim_type': 'technical', 'components': [{'category': 'technical_fact',
                        'proposition': a['text'], 'basis_target': 'technical_content',
                        'verification_obligation': 'technical_truth'}], 'assertion_role': 'asserted',
                        'semantic_qualifiers': []} for a in payload['ANSWER_ANCHORS']], 'non_claims': []}
                else:
                    return ModelResponse('{bad')
                return ModelResponse(json.dumps(value, ensure_ascii=False))

        summary = await trial.run_batch(plan(), self.root / 'actual-batch', self.root / 'actual-responses', Scripted)
        branch = summary['branches'][0]
        self.assertEqual(branch['status'], 'execution_failed')
        self.assertEqual(len(branch['workload']), 2)
        self.assertIsNotNone(branch['result']['answer'])
        prompts = {r.prompt_version for r in requests}
        self.assertIn('evidence-verification-v9.20-lossless-transport-json-nesting', prompts)
        self.assertIn('power-domain-review-v3.5-task-obligations', prompts)
        self.assertEqual(len(requests), len(branch['sent']))
        self.assertTrue(all(b['status'] == 'unexecuted' for b in summary['branches'][1:]))
        self.assertTrue((self.root / "actual-batch/GEC-01-original/final-result.json").exists())
        control = trial.read(self.root / "actual-batch/GEC-01-original/controller-control.json")
        self.assertEqual(control["reason"], "branch_final_execution_failure")
        self.assertNotEqual(control["reason"], "frozen_configuration_mismatch")

    async def test_required_audit_failure_retains_answer_and_stops(self):
        def harness_factory(case, value, observer, state, adapters, directory):
            h = make_fake_harness(FakeConfig(verification_error=True))
            h.observer = observer
            return h
        summary = await trial.run_batch(plan(), self.root / "batch", self.root / "responses", Delegate, harness_factory)
        self.assertEqual(summary["branches"][0]["status"], "execution_failed")
        self.assertIsNotNone(summary["branches"][0]["result"]["answer"])
        self.assertEqual(sum(r["status"] == "unexecuted" for r in summary["branches"]), 7)

    async def test_all_eight_semantic_insufficiency_branches_continue_with_40_shared_protection(self):
        budgets = []
        def harness_factory(case, value, observer, state, adapters, directory):
            h = make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)))
            h.observer = observer
            run = h.run
            async def capture(request, budget, **kwargs):
                budgets.append(budget)
                return await run(request, budget, **kwargs)
            h.run = capture
            return h
        summary = await trial.run_batch(plan(), self.root / "batch", self.root / "responses", Delegate, harness_factory)
        self.assertEqual([r["status"] for r in summary["branches"]], ["complete"] * 8)
        self.assertEqual({b.max_model_calls for b in budgets}, {40})
        self.assertEqual({b.max_revision_rounds for b in budgets}, {0})

    async def test_storage_failure_after_valid_result_is_not_reported_complete(self):
        def harness_factory(case, value, observer, state, adapters, directory):
            h = make_fake_harness(); h.observer = observer; return h
        real_write = trial.write
        def fail_final(path, value):
            if Path(path).name == "final-result.json": raise OSError("fixture")
            return real_write(path, value)
        with patch.object(trial, "write", side_effect=fail_final):
            summary = await trial.run_batch(plan(), self.root / "batch", self.root / "responses", Delegate, harness_factory)
        self.assertEqual(summary["branches"][0]["status"], "execution_failed")
        self.assertEqual(summary["branches"][1]["status"], "unexecuted")

    async def test_controller_acceptance_storage_failure_no_harness_calls(self):
        calls = []
        def factory(*args): calls.append(True); raise AssertionError("must not run")
        real_write = trial.write
        def fail_acceptance(path, value):
            if Path(path).name == "controller-accepted.json": raise OSError("fixture")
            return real_write(path, value)
        with patch.object(trial, "write", side_effect=fail_acceptance):
            summary = await trial.run_batch(plan(), self.root / "batch", self.root / "responses", Delegate, factory)
        self.assertFalse(calls)
        self.assertEqual(summary["branches"][0]["status"], "execution_failed")
        self.assertEqual(summary["branches"][1]["status"], "unexecuted")

    async def test_workload_actual_citation_count_not_arbitrary_c_plus_eight_cap(self):
        value = self.values["GEC-01"]
        answer = AnswerDraft("a", 1, "Text.", citations=tuple(CitationBinding(0, 5, (value.evidence[0].evidence_id,)) for _ in range(38)))
        generated = GenerationOutput(answer, evidence_snapshot=make_snapshot(answer, value.evidence, None, request=value.request, prompt_version="fixture"))
        initial = trial.workload(generated, None, 1)
        self.assertEqual(initial["available"], 39)
        self.assertEqual(initial["required_initial_remaining"], 41)
        self.assertEqual(initial["initial_shortfall"], 2)
        extracted = ClaimExtractionOutput("a", 1, (), (), ())
        after = trial.workload(generated, extracted, 2)
        self.assertEqual(after["independent_initial"], 0)
        self.assertEqual(after["required_initial_remaining"], 39)
        self.assertEqual(after["initial_shortfall"], 1)

    async def test_attempt_guard_refuses_resume_and_changed_identity(self):
        from tempfile import TemporaryDirectory
        public = self.root / "freeze.json"
        directory = self.root / "batch"
        value = {"owner_authorized": True, "per_branch_model_calls": 40, "batch_call_cap": None, "bound_files": []}
        trial.write(public, value); trial.write(directory / "freeze.json", value)
        with patch.object(trial, "FREEZE", public), patch.object(trial, "DIRECTORY", directory):
            self.assertEqual(trial.preflight(), value)
            trial.write(directory / "attempt.json", {})
            with self.assertRaises(ValueError): trial.preflight()


if __name__ == "__main__": unittest.main()
