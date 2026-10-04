"""Configurable, deterministic offline doubles. No external dependencies."""
import asyncio
from dataclasses import dataclass

from agents.contracts import *
from core.models import *


@dataclass(frozen=True)
class FakeConfig:
    text: str = "Reactive power affects voltage."
    verification_statuses: tuple[VerificationStatus, ...] = (VerificationStatus.SUPPORTED,)
    domain_severities: tuple[Severity, ...] = (Severity.NONE,)
    verification_delay: float = 0.0
    domain_delay: float = 0.0
    verification_error: bool = False
    domain_error: bool = False
    bad_evidence_id: bool = False
    bad_claim_id: bool = False
    reference_input_evidence: bool = False


def fake_evidence():
    return Evidence("offline-e1", "fixture", "v1", "paragraph 1",
                    "Reactive power affects voltage.", "synthetic_fixture")


class FakeGenerationAgent:
    def __init__(self, config=FakeConfig()):
        self.config = config
        self.inputs = []

    async def run(self, inputs):
        self.inputs.append(inputs)
        return GenerationOutput(AnswerDraft(f"{inputs.request.task_id}-answer", 1, self.config.text))


class FakeClaimExtractor:
    def __init__(self, bad_span=False):
        self.bad_span = bad_span
        self.versions = []

    async def extract(self, answer):
        self.versions.append(answer.version)
        return (Claim(f"{answer.answer_id}-v{answer.version}-c1", answer.answer_id, answer.version,
                      answer.text, 0, len(answer.text) + int(self.bad_span), "technical"),)


class FakeEvidenceVerificationAgent:
    def __init__(self, config=FakeConfig()):
        self.config = config
        self.inputs = []

    async def run(self, inputs):
        self.inputs.append(inputs)
        await asyncio.sleep(self.config.verification_delay)
        if self.config.verification_error:
            raise RuntimeError("Configured verification failure")
        index = min(len(self.inputs) - 1, len(self.config.verification_statuses) - 1)
        status = self.config.verification_statuses[index]
        evidence = fake_evidence()
        if self.config.reference_input_evidence:
            core_ids = {b.evidence_id for b in inputs.evidence_bindings if b.origin == "index_core_hit"}
            evidence = next((e for e in inputs.seed_evidence if e.evidence_id in core_ids),
                            next(iter(inputs.seed_evidence), None))
            if evidence is None and status == VerificationStatus.SUPPORTED:
                status = VerificationStatus.INSUFFICIENT_EVIDENCE
        findings = tuple(VerificationFinding(
            f"verify-v{inputs.answer.version}-{claim.claim_id}",
            "unknown-claim" if self.config.bad_claim_id else claim.claim_id,
            status, ("unknown-evidence",) if self.config.bad_evidence_id else
            (() if evidence is None else (evidence.evidence_id,)),
            ("Configured simulated verification; input citation is not a factual support check"
             if self.config.reference_input_evidence else "Configured offline verification"), "fake-v1",
        ) for claim in inputs.claims)
        return EvidenceVerificationOutput(inputs.answer.answer_id, inputs.answer.version,
                                          inputs.claims, findings, () if evidence is None else (evidence,))


class FakePowerDomainReviewAgent:
    def __init__(self, config=FakeConfig()):
        self.config = config
        self.inputs = []

    async def run(self, inputs):
        self.inputs.append(inputs)
        await asyncio.sleep(self.config.domain_delay)
        if self.config.domain_error:
            raise RuntimeError("Configured domain failure")
        index = min(len(self.inputs) - 1, len(self.config.domain_severities) - 1)
        finding = DomainFinding(f"domain-v{inputs.answer.version}", inputs.answer.answer_id,
                                inputs.answer.version, tuple(c.claim_id for c in inputs.claims),
                                self.config.domain_severities[index], "offline_check", "Configured domain review")
        return PowerDomainReviewOutput(inputs.answer.answer_id, inputs.answer.version, (finding,), ())


class FakeRevisionAgent:
    async def run(self, inputs):
        findings = inputs.verification.findings + inputs.domain_review.findings
        return RevisionOutput(
            AnswerDraft(inputs.answer.answer_id, inputs.answer.version + 1,
                        inputs.answer.text + " Conditions require verification."),
            (RevisionChange(tuple(f.finding_id for f in findings), "Applied configured revision"),), (), (),
        )


def make_fake_harness(config=FakeConfig()):
    from harness.runtime import OfflineHarness
    return OfflineHarness(FakeGenerationAgent(config), FakeEvidenceVerificationAgent(config),
                          FakePowerDomainReviewAgent(config), FakeRevisionAgent(), FakeClaimExtractor())
