import asyncio
from dataclasses import FrozenInstanceError, replace
import unittest

from agents.fakes import FakeConfig, FakeClaimExtractor, make_fake_harness
from agents.contracts import RevisionOutput
from core.models import *
from core.validation import InputError
from harness.contracts import RunBudget
from harness.states import RunState


def request(mode=TaskMode.QUESTION_ANSWER):
    return TaskRequest("test", mode, "voltage_stability_interpretation",
                       "Explain voltage stability" if mode == TaskMode.QUESTION_ANSWER else "",
                       existing_answer=AnswerDraft("existing", 1, "Reactive power affects voltage.")
                       if mode == TaskMode.ASSESS_EXISTING else None)


class HarnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_pass_both_modes(self):
        for mode in TaskMode:
            with self.subTest(mode=mode):
                harness = make_fake_harness()
                result = await harness.run(request(mode), RunBudget())
                self.assertEqual(result.state, RunState.COMPLETED)
                self.assertEqual(result.report.decision.kind, DecisionKind.PASS)
                self.assertFalse(result.execution_issues)
                v, d = harness.verification.inputs[0], harness.domain_review.inputs[0]
                self.assertIs(v.answer, d.answer)
                self.assertIs(v.claims, d.claims)
                with self.assertRaises(FrozenInstanceError):
                    v.answer.version = 9
                self.assertEqual(result.trace.events[-1].detail, result.termination_reason)
                self.assertTrue(all(e.duration_ms >= 0 for e in result.trace.events))
                self.assertIn(1, [e.answer_version for e in result.trace.events])

    async def test_one_revision_then_pass(self):
        harness = make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,
                                                                     VerificationStatus.SUPPORTED)))
        result = await harness.run(request(), RunBudget())
        self.assertEqual(result.state, RunState.COMPLETED)
        self.assertEqual(result.report.answer.version, 2)
        self.assertEqual(harness.extractor.versions, [1, 2])
        self.assertEqual(len(harness.domain_review.inputs), 2)
        self.assertNotEqual(harness.verification.inputs[0].claims[0].claim_id,
                            harness.verification.inputs[1].claims[0].claim_id)
        self.assertTrue(any("revise:" in e.detail for e in result.trace.events))

    async def test_insufficient_evidence(self):
        harness = make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)))
        result = await harness.run(request(), RunBudget())
        self.assertEqual(result.state, RunState.REVIEW_REQUIRED)
        self.assertEqual(result.report.decision.kind, DecisionKind.INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.execution_issues)
        self.assertEqual(harness.extractor.versions, [1])

    async def test_timeout_preserves_other_result(self):
        harness = make_fake_harness(FakeConfig(verification_delay=0.05))
        result = await harness.run(request(), RunBudget(step_timeout_seconds=0.01))
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertEqual(len(result.report.domain_findings), 1)
        self.assertEqual(result.report.verification_findings, ())
        self.assertEqual(result.execution_issues[0].status, ExecutionStatus.TIMED_OUT)
        self.assertTrue(any(e.component == "evidence_verification" and e.status == ExecutionStatus.TIMED_OUT
                            for e in result.trace.events))

    async def test_domain_failure_preserves_verification(self):
        harness = make_fake_harness(FakeConfig(domain_error=True))
        result = await harness.run(request(), RunBudget())
        self.assertEqual(len(result.report.verification_findings), 1)
        self.assertEqual(result.report.domain_findings, ())
        self.assertEqual(result.execution_issues[0].code, "EXECUTION_FAILURE")

    async def test_revision_limit(self):
        harness = make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)))
        result = await harness.run(request(), RunBudget(max_revision_rounds=1))
        self.assertEqual(result.report.answer.version, 2)
        self.assertEqual(harness.extractor.versions, [1, 2])
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertIn("Revision limit", result.termination_reason)

    async def test_invalid_agent_id_references(self):
        for config in (FakeConfig(bad_evidence_id=True), FakeConfig(bad_claim_id=True)):
            result = await make_fake_harness(config).run(request(), RunBudget())
            self.assertEqual(result.execution_issues[0].code, "OUTPUT_CONTRACT_ERROR")
            self.assertEqual(result.report.verification_findings, ())
            self.assertEqual(len(result.report.domain_findings), 1)

    async def test_input_errors_before_execution(self):
        base = request()
        invalid = [replace(base, question=" "), replace(base, mode="question_answer"),
                   replace(base, provided_evidence=[]), replace(base, scenario_id=""),
                   replace(request(TaskMode.ASSESS_EXISTING), existing_answer=None),
                   replace(request(TaskMode.ASSESS_EXISTING), existing_answer=AnswerDraft("a", 0, "text")),
                   replace(request(TaskMode.ASSESS_EXISTING), existing_answer=AnswerDraft(
                       "a", 1, "text", citations=(CitationBinding(0, 4, ("missing",)),)))]
        for item in invalid:
            harness = make_fake_harness()
            with self.assertRaises(InputError):
                await harness.run(item, RunBudget())
            self.assertEqual(harness.verification.inputs, [])
        for budget in (RunBudget(max_revision_rounds=-1), RunBudget(step_timeout_seconds=0),
                       RunBudget(max_duration_seconds=float("nan")), RunBudget(max_model_calls=True)):
            with self.assertRaises(InputError):
                await make_fake_harness().run(base, budget)

    async def test_bad_extraction_is_execution_failure(self):
        harness = make_fake_harness()
        harness.extractor = FakeClaimExtractor(bad_span=True)
        result = await harness.run(request(), RunBudget())
        self.assertEqual(result.state, RunState.FAILED)
        self.assertIsNone(result.report)
        self.assertEqual(result.execution_issues[0].code, "OUTPUT_CONTRACT_ERROR")

    async def test_high_safety_needs_human(self):
        result = await make_fake_harness(FakeConfig(domain_severities=(Severity.HIGH,))).run(request(), RunBudget())
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertFalse(result.execution_issues)

    async def test_call_budget_and_total_timeout(self):
        result = await make_fake_harness().run(request(), RunBudget(max_model_calls=2))
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        result = await make_fake_harness(FakeConfig(verification_delay=0.1)).run(
            request(), RunBudget(max_duration_seconds=0.02, step_timeout_seconds=1))
        self.assertEqual(result.execution_issues[0].status, ExecutionStatus.TIMED_OUT)

    async def test_invalid_revision_keeps_last_audit(self):
        class BadRevision:
            async def run(self, inputs):
                return RevisionOutput(AnswerDraft("wrong-id", 2, "Replacement"), (), (), ())
        harness = make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)))
        harness.revision = BadRevision()
        result = await harness.run(request(), RunBudget())
        self.assertEqual(result.report.answer.version, 1)
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)

    async def test_cancellation(self):
        harness = make_fake_harness(FakeConfig(verification_delay=1))
        task = asyncio.create_task(harness.run(request(), RunBudget()))
        await asyncio.sleep(0.01)
        await harness.cancel(next(iter(harness._runs)))
        result = await task
        self.assertEqual(result.state, RunState.CANCELLED)
        self.assertEqual(harness._runs, {})

    async def test_stale_version_and_unsupported_ids(self):
        for mutation in ("version", "no_evidence", "duplicate_finding"):
            harness = make_fake_harness()
            original = harness.verification

            class InvalidVerifier:
                async def run(self, inputs):
                    output = await original.run(inputs)
                    if mutation == "version":
                        return replace(output, answer_version=99)
                    if mutation == "no_evidence":
                        return replace(output, findings=(replace(output.findings[0], evidence_ids=()),))
                    return replace(output, findings=output.findings + output.findings)

            harness.verification = InvalidVerifier()
            result = await harness.run(request(), RunBudget())
            self.assertEqual(result.execution_issues[0].code, "OUTPUT_CONTRACT_ERROR")
            self.assertEqual(len(result.report.domain_findings), 1)

    async def test_generation_failure(self):
        class BrokenGenerator:
            async def run(self, inputs):
                raise RuntimeError("offline generation failed")
        harness = make_fake_harness()
        harness.generation = BrokenGenerator()
        result = await harness.run(request(), RunBudget())
        self.assertEqual(result.state, RunState.FAILED)
        self.assertEqual(result.execution_issues[0].component, "generation")
        self.assertIsNone(result.report)

    async def test_conflicting_evidence_and_unknown_revision_reference(self):
        from agents.fakes import fake_evidence
        from agents.contracts import RevisionChange
        harness = make_fake_harness()
        item = replace(request(), provided_evidence=(replace(fake_evidence(), text="Different source text"),))
        result = await harness.run(item, RunBudget())
        self.assertEqual(result.execution_issues[0].code, "OUTPUT_CONTRACT_ERROR")
        self.assertEqual(len(result.report.domain_findings), 1)

        class BadReferences:
            async def run(self, inputs):
                return RevisionOutput(replace(inputs.answer, version=2),
                                      (RevisionChange(("unknown-finding",), "change"),), (), ())
        harness = make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)))
        harness.revision = BadReferences()
        result = await harness.run(request(), RunBudget())
        self.assertEqual(result.execution_issues[0].code, "OUTPUT_CONTRACT_ERROR")
        self.assertEqual(result.report.answer.version, 1)


if __name__ == "__main__":
    unittest.main()
