"""Run deterministic offline scenarios: python -m harness.demo."""
import asyncio
import json

from agents.fakes import FakeConfig, make_fake_harness
from core.models import AnswerDraft, TaskMode, TaskRequest, VerificationStatus
from harness.contracts import RunBudget


async def main():
    scenarios = (
        ("question_answer_pass", TaskMode.QUESTION_ANSWER, FakeConfig(), RunBudget()),
        ("existing_answer_pass", TaskMode.ASSESS_EXISTING, FakeConfig(), RunBudget()),
        ("revision_pass", TaskMode.QUESTION_ANSWER,
         FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED)), RunBudget()),
        ("insufficient_evidence", TaskMode.QUESTION_ANSWER,
         FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)), RunBudget()),
        ("review_timeout", TaskMode.QUESTION_ANSWER,
         FakeConfig(verification_delay=0.05), RunBudget(step_timeout_seconds=0.01)),
        ("revision_limit", TaskMode.QUESTION_ANSWER,
         FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,)), RunBudget(max_revision_rounds=1)),
        ("invalid_id", TaskMode.QUESTION_ANSWER, FakeConfig(bad_evidence_id=True), RunBudget()),
    )
    for name, mode, config, budget in scenarios:
        request = TaskRequest(name, mode, "voltage_stability_interpretation", "Explain voltage stability",
                              existing_answer=AnswerDraft("existing", 1, config.text)
                              if mode == TaskMode.ASSESS_EXISTING else None)
        result = await make_fake_harness(config).run(request, budget)
        print(json.dumps({
            "scenario": name, "state": result.state.value,
            "decision": None if result.report is None else result.report.decision.kind.value,
            "answer_version": None if result.report is None else result.report.answer.version,
            "issues": [issue.code for issue in result.execution_issues],
            "termination_reason": result.termination_reason,
            "steps": [{"component": e.component, "state": e.state, "answer_version": e.answer_version,
                       "status": e.status.value, "duration_ms": e.duration_ms} for e in result.trace.events],
        }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
