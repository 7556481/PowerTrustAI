"""Real SQLite/BM25 integration with synthetic_fixture knowledge and fake agents."""
import asyncio
from dataclasses import replace
import importlib.util
from pathlib import Path
import tempfile
import threading
import time
import unittest

from agents.fakes import (FakeConfig, FakeGenerationAgent, FakeEvidenceVerificationAgent,
                         FakePowerDomainReviewAgent, FakeRevisionAgent, FakeClaimExtractor)
from core.models import (AnswerDraft, DecisionKind, Evidence, TaskMode, TaskRequest, VerificationStatus)
from core.validation import InputError
from harness.contracts import RetrievalSettings, RunBudget
from harness.runtime import OfflineHarness
from harness.states import RunState
from rag.contracts import ContextOptions, RetrievalPurpose, RetrievalRequest
from rag.retriever import AsyncSQLiteBM25Retriever, BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata


RAW = ("# synthetic_fixture\n\nVoltage stability reactive power support constraints operating limits.\n\n"
       "STATCOM dynamic reactive reserve excludes short overload output.\n\n"
       "Generator capability has current and excitation constraints.\n")


class HookRetriever:
    def __init__(self, actual, hook=None):
        self.actual, self.hook = actual, hook
        self.requests = []

    async def retrieve(self, request):
        self.requests.append(request)
        if self.hook:
            alternate = await self.hook(request)
            if alternate is not None:
                return alternate
        return await self.actual.retrieve(request)

    async def validate_result(self, request, result):
        await self.actual.validate_result(request, result)


class HarnessRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.md = self.path / "synthetic_fixture.md"
        self.md.write_text(RAW, encoding="utf-8")
        self.db = self.path / "knowledge.sqlite3"
        with KnowledgeStore(self.db) as store:
            self.original = store.ingest(self.md, "synthetic", SourceMetadata(source_type="synthetic_fixture"))
        self.actual = AsyncSQLiteBM25Retriever(self.db)
        self.addCleanup(self.actual.close)
        self.retriever = HookRetriever(self.actual)

    def request(self, *, existing=False, text="Voltage stability reactive power support"):
        return TaskRequest("integration", TaskMode.ASSESS_EXISTING if existing else TaskMode.QUESTION_ANSWER,
                           "synthetic_voltage_stability", text,
                           existing_answer=AnswerDraft("existing", 1, text) if existing else None)

    def harness(self, config=None, settings=None, retriever=None):
        config = config or FakeConfig(text="Voltage stability reactive power support")
        return OfflineHarness(FakeGenerationAgent(config), FakeEvidenceVerificationAgent(config),
                              FakePowerDomainReviewAgent(config), FakeRevisionAgent(), FakeClaimExtractor(),
                              retriever=self.retriever if retriever is None else retriever,
                              retrieval_settings=settings or RetrievalSettings(max_results=2))

    async def run_harness(self, harness=None, request=None, budget=None):
        return await (harness or self.harness()).run(request or self.request(), budget or RunBudget(),
                                                    knowledge_version=self.original.knowledge_version)

    async def test_three_purposes_frozen_inputs_and_full_trace(self):
        harness = self.harness()
        user = Evidence("user-1", "user-not-official", "unknown", "provided text",
                        "A user supplied reference", "user_reference")
        result = await self.run_harness(harness, replace(self.request(), provided_evidence=(user,)))
        self.assertEqual(result.state, RunState.COMPLETED)
        self.assertEqual([r.purpose for r in result.retrieval_records],
                         ["generation", "verification", "domain_review"])
        self.assertTrue(all(r.outcome == "hits" for r in result.retrieval_records))
        v, d = harness.verification.inputs[0], harness.domain_review.inputs[0]
        self.assertIs(v.answer, d.answer)
        self.assertIs(v.claims, d.claims)
        self.assertEqual(v.knowledge_version, self.original.knowledge_version)
        self.assertEqual(result.retrieval_records[1].query, v.claims[0].text)
        self.assertIn(self.request().scenario_id, result.retrieval_records[2].query)
        self.assertEqual({b.purpose for b in v.evidence_bindings if b.origin == "index_core_hit"}, {"verification"})
        self.assertEqual({b.purpose for b in d.evidence_bindings if b.origin == "index_core_hit"}, {"domain_review"})
        self.assertTrue(all(b.origin == "user_reference" for b in result.evidence_bindings if b.evidence_id == "user-1"))
        self.assertTrue(any(b.origin == "agent_output_unverified" for b in result.evidence_bindings))
        self.assertEqual(result.report.evidence_bindings, result.evidence_bindings)
        self.assertTrue(harness.generation.inputs[0].evidence_bindings)
        self.assertEqual(harness.generation.inputs[0].knowledge_version, self.original.knowledge_version)
        self.assertEqual(sum(r.accepted_chars for r in result.retrieval_records),
                         result.retrieval_records[-1].cumulative_chars)
        for r in result.retrieval_records:
            self.assertGreaterEqual(r.duration_ms, 0)
            self.assertEqual(r.knowledge_version, self.original.knowledge_version)
            self.assertTrue(r.query_method)
            self.assertTrue(all(h.scoring_method and h.score > 0 for h in r.hits))
        self.assertEqual(len([e for e in result.trace.events if e.component.startswith("retrieval_")]), 3)

    async def test_assessment_only_two_review_retrievals(self):
        result = await self.run_harness(request=self.request(existing=True))
        self.assertEqual(result.report.decision.kind, DecisionKind.PASS)
        self.assertEqual([r.purpose for r in result.retrieval_records], ["verification", "domain_review"])

    async def test_simulated_reviewer_references_delivered_index_evidence_without_scoring_inference(self):
        config = FakeConfig(text="Voltage stability reactive power support", reference_input_evidence=True)
        result = await self.run_harness(self.harness(config))
        known = {e.evidence_id for e in result.evidence if e.provenance}
        self.assertTrue(all(set(f.evidence_ids) <= known for f in result.report.verification_findings))
        self.assertTrue(all("not a factual support check" in f.rationale for f in result.report.verification_findings))
        contradicted = replace(config, verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,))
        other = await self.run_harness(self.harness(contradicted))
        self.assertEqual(other.report.decision.kind, DecisionKind.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.retrieval_records[1].hits, other.retrieval_records[1].hits)

    async def test_no_retriever_backward_compatible(self):
        from agents.fakes import make_fake_harness
        result = await make_fake_harness().run(self.request(), RunBudget(max_retrieval_calls=0,
            max_retrieval_chars_per_call=0, max_retrieval_chars_total=0))
        self.assertEqual(result.report.decision.kind, DecisionKind.PASS)
        self.assertFalse(result.retrieval_records)

    async def test_configuration_errors_before_calls_and_sync_connection_rejected(self):
        harness = self.harness()
        for version in (None, "", " ", 1):
            with self.assertRaises(InputError):
                await harness.run(self.request(), RunBudget(), knowledge_version=version)
        for budget in (RunBudget(max_retrieval_chars_per_call=-1), RunBudget(max_retrieval_chars_total=True)):
            with self.assertRaises(InputError):
                await harness.run(self.request(), budget, knowledge_version=self.original.knowledge_version)
        with self.assertRaises(InputError):
            self.harness(settings=RetrievalSettings(max_results=0))
        with KnowledgeStore(self.db, readonly=True) as store:
            with self.assertRaises(InputError):
                self.harness(retriever=BM25Retriever(store))
        self.assertFalse(self.retriever.requests)

    async def test_empty_is_insufficient_not_contradicted_or_execution_failure(self):
        harness = self.harness(FakeConfig(text="zqxunknownword"))
        result = await self.run_harness(harness, self.request(text="zqxunknownword"))
        self.assertEqual(result.retrieval_records[0].outcome, "empty")
        self.assertEqual(result.retrieval_records[1].outcome, "empty")
        self.assertEqual(result.report.decision.kind, DecisionKind.INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.execution_issues)
        self.assertTrue(all(f.status != VerificationStatus.CONTRADICTED for f in result.report.verification_findings))

    async def test_retrieval_failure_preserves_successful_peer_and_evidence(self):
        async def hook(request):
            if request.purpose == RetrievalPurpose.VERIFICATION:
                raise RuntimeError("synthetic_fixture retrieval failure")
        self.retriever.hook = hook
        harness = self.harness()
        result = await self.run_harness(harness)
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertEqual(result.report.verification_findings, ())
        self.assertEqual(len(result.report.domain_findings), 1)
        self.assertFalse(harness.verification.inputs)
        self.assertTrue(result.evidence)
        self.assertEqual(result.retrieval_records[1].outcome, "failed")
        self.assertEqual(result.retrieval_records[2].outcome, "hits")

    async def test_generation_retrieval_failure_has_partial_trace_not_fake_answer(self):
        async def hook(request):
            raise RuntimeError("Unavailable index")
        self.retriever.hook = hook
        result = await self.run_harness()
        self.assertEqual(result.state, RunState.REVIEW_REQUIRED)
        self.assertIsNone(result.report)
        self.assertEqual(len(result.retrieval_records), 1)
        self.assertFalse(any(e.component == "generation" for e in result.trace.events))

    async def test_reported_retrieval_issue_keeps_timeout_and_failure_distinct(self):
        from core.models import ExecutionIssue, ExecutionStatus
        from rag.contracts import RetrievalResult
        for status, expected in ((ExecutionStatus.TIMED_OUT, "timed_out"), (ExecutionStatus.FAILED, "failed")):
            async def hook(request):
                if request.purpose == RetrievalPurpose.VERIFICATION:
                    return RetrievalResult((), request.knowledge_version,
                        (ExecutionIssue("index", status, "synthetic_reported_issue", "fixture failure"),))
            self.retriever.hook = hook
            result = await self.run_harness()
            self.assertEqual(result.retrieval_records[1].outcome, expected)
            self.assertTrue(result.report.domain_findings)
            self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)

    async def test_retrieval_timeout_and_total_deadline_are_not_empty(self):
        async def hook(request):
            if request.purpose == RetrievalPurpose.VERIFICATION:
                await asyncio.sleep(0.4)
        self.retriever.hook = hook
        result = await self.run_harness(budget=RunBudget(step_timeout_seconds=0.15))
        self.assertEqual(result.retrieval_records[1].outcome, "timed_out")
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertEqual(len(result.report.domain_findings), 1)
        result = await self.run_harness(budget=RunBudget(step_timeout_seconds=0.5, max_duration_seconds=0.2))
        self.assertEqual(result.retrieval_records[1].outcome, "timed_out")
        self.assertEqual(result.retrieval_records[2].outcome, "timed_out")
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)

    async def test_call_budget_preserves_already_completed_review(self):
        result = await self.run_harness(budget=RunBudget(max_retrieval_calls=2))
        self.assertEqual([r.outcome for r in result.retrieval_records], ["hits", "hits", "budget_exhausted"])
        self.assertEqual(result.retrieval_records[-1].calls_used, 2)
        self.assertTrue(result.report.verification_findings)
        self.assertEqual(result.report.domain_findings, ())
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertTrue(result.report.evidence)

    async def test_single_and_total_character_budget_no_silent_text_truncation(self):
        result = await self.run_harness(budget=RunBudget(max_retrieval_chars_per_call=1))
        self.assertEqual(result.retrieval_records[0].outcome, "budget_exhausted")
        self.assertTrue(result.retrieval_records[0].omitted_evidence_ids)
        self.assertFalse(result.evidence)
        baseline = await self.run_harness()
        allowance = baseline.retrieval_records[0].accepted_chars
        result = await self.run_harness(budget=RunBudget(max_retrieval_chars_total=allowance))
        self.assertEqual(result.retrieval_records[0].outcome, "hits")
        self.assertEqual(result.retrieval_records[1].outcome, "budget_exhausted")
        self.assertEqual(result.retrieval_records[-1].cumulative_chars, allowance)
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        with KnowledgeStore(self.db, readonly=True) as store:
            for evidence in result.evidence:
                if evidence.provenance:
                    self.assertEqual(store.verify_evidence(evidence), evidence)

    async def test_partial_core_omission_retains_valid_full_evidence(self):
        result = await self.run_harness()
        record = result.retrieval_records[0]
        by_id = {e.evidence_id: e for e in result.evidence}
        first_length = len(by_id[record.core_evidence_ids[0]].text)
        partial = await self.run_harness(budget=RunBudget(max_retrieval_chars_per_call=first_length))
        self.assertEqual(partial.retrieval_records[0].outcome, "budget_exhausted")
        self.assertTrue(partial.retrieval_records[0].core_evidence_ids)
        self.assertTrue(partial.evidence)
        self.assertEqual(partial.evidence[0], by_id[record.core_evidence_ids[0]])

    async def test_tampered_evidence_rank_score_and_snapshot_are_rejected(self):
        for kind in ("text", "score", "version", "locator"):
            async def hook(request):
                if request.purpose != RetrievalPurpose.VERIFICATION:
                    return None
                result = await self.actual.retrieve(request)
                if kind == "score":
                    return replace(result, hits=(replace(result.hits[0], score=result.hits[0].score + 1),) + result.hits[1:])
                if kind == "version":
                    return replace(result, knowledge_version="not-this-snapshot")
                first = replace(result.evidence[0], **({"text": "fabricated"} if kind == "text" else {"locator": "wrong-page"}))
                return replace(result, evidence=(first,) + result.evidence[1:])
            self.retriever.hook = hook
            result = await self.run_harness()
            self.assertEqual(result.retrieval_records[1].outcome, "failed", kind)
            self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED, kind)
            self.assertTrue(result.report.domain_findings)
            self.assertNotIn("fabricated", [e.text for e in result.evidence])

    async def test_user_index_id_collision_cannot_be_relabelled(self):
        query = RetrievalRequest(self.request().question, self.request().scenario_id, RetrievalPurpose.GENERATION,
                                 self.original.knowledge_version, 2)
        found = await self.actual.retrieve(query)
        result = await self.run_harness(request=replace(self.request(), provided_evidence=(found.evidence[0],)))
        self.assertEqual(result.retrieval_records[0].outcome, "failed")
        self.assertTrue(all(b.origin == "user_reference" for b in result.evidence_bindings))

    async def test_domain_v2_excludes_saved_index_references_from_current_purpose(self):
        old_query = RetrievalRequest("STATCOM", "synthetic_voltage_stability", RetrievalPurpose.GENERATION,
                                     self.original.knowledge_version, 1)
        old = (await self.actual.retrieve(old_query)).evidence[0]
        user = Evidence("user-note", "user", "v1", "note", "User supplied operating premise.", "user_reference")
        config = FakeConfig(reference_input_evidence=True)
        domain = FakePowerDomainReviewAgent(config)
        domain.protocol_version = 2
        harness = OfflineHarness(FakeGenerationAgent(config), FakeEvidenceVerificationAgent(config), domain,
                                 FakeRevisionAgent(), FakeClaimExtractor(), retriever=self.actual,
                                 retrieval_settings=RetrievalSettings(max_results=1))
        request = replace(self.request(existing=True, text="Voltage stability"), provided_evidence=(old, user))
        result = await harness.run(request, RunBudget(), knowledge_version=self.original.knowledge_version,
                                   indexed_reference_ids=(old.evidence_id,))
        self.assertTrue(domain.inputs)
        ids = {e.evidence_id for e in domain.inputs[0].evidence}
        self.assertNotIn(old.evidence_id, ids)
        self.assertIn(user.evidence_id, ids)
        self.assertTrue(result.report.domain_findings)

    async def test_unknown_snapshot_and_stored_source_tamper_fail_closed(self):
        result = await self.harness().run(self.request(), RunBudget(), knowledge_version="missing")
        self.assertEqual(result.state, RunState.REVIEW_REQUIRED)
        self.assertEqual(result.retrieval_records[0].outcome, "failed")
        with KnowledgeStore(self.db) as store:
            with store.connection:
                store.connection.execute("UPDATE fragments SET raw_text='tampered'")
        result = await self.run_harness()
        self.assertEqual(result.state, RunState.REVIEW_REQUIRED)
        self.assertFalse(result.evidence)

    async def test_update_during_run_and_revision_keep_fixed_snapshot(self):
        updated = []
        def update():
            self.md.write_text(RAW + "\nNEWLY_UPDATED official-looking text must not enter frozen run.\n", encoding="utf-8")
            with KnowledgeStore(self.db) as store:
                return store.ingest(self.md, "synthetic", SourceMetadata(source_type="synthetic_fixture"), update=True)
        async def hook(request):
            if request.purpose == RetrievalPurpose.VERIFICATION and not updated:
                updated.append(await asyncio.to_thread(update))
        self.retriever.hook = hook
        harness = self.harness(FakeConfig(text="Voltage stability reactive power support",
            verification_statuses=(VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED)))
        result = await self.run_harness(harness)
        self.assertEqual(result.report.answer.version, 2)
        self.assertEqual(harness.extractor.versions, [1, 2])
        self.assertEqual([r.answer_version for r in result.retrieval_records], [None, 1, 1, 2, 2])
        self.assertNotEqual(result.retrieval_records[1].query, result.retrieval_records[3].query)
        self.assertTrue(all(r.knowledge_version == self.original.knowledge_version for r in self.retriever.requests))
        self.assertNotEqual(updated[0].knowledge_version, self.original.knowledge_version)
        self.assertTrue(all(e.source_version == self.original.document_version for e in result.evidence if e.provenance))
        self.assertFalse(any("NEWLY_UPDATED" in e.text for e in result.evidence))
        self.assertEqual(result.report.decision.kind, DecisionKind.PASS)

    async def test_agent_cannot_change_index_text_or_provenance(self):
        harness = self.harness()
        original_run = harness.verification.run
        async def altered(inputs):
            output = await original_run(inputs)
            forged = replace(inputs.seed_evidence[0], text="Agent changed raw evidence")
            return replace(output, evidence=(forged,))
        harness.verification.run = altered
        result = await self.run_harness(harness)
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)
        self.assertTrue(result.report.domain_findings)
        self.assertFalse(any(e.text == "Agent changed raw evidence" for e in result.evidence))

    async def test_thread_ownership_event_loop_responsiveness_and_timeout_not_worker_kill(self):
        started, finished = threading.Event(), threading.Event()
        threads = []
        class SlowRetriever(AsyncSQLiteBM25Retriever):
            def _work(inner, request, result, validate):
                if not validate:
                    threads.append(threading.get_ident())
                    started.set()
                    time.sleep(0.2)
                try:
                    return super()._work(request, result, validate)
                finally:
                    if not validate:
                        finished.set()
        with SlowRetriever(self.db) as slow:
            running = asyncio.create_task(self.run_harness(self.harness(retriever=slow),
                budget=RunBudget(step_timeout_seconds=0.05)))
            ticks = 0
            while not running.done():
                await asyncio.sleep(0.003)
                ticks += 1
            result = await running
            self.assertTrue(started.is_set())
            self.assertFalse(finished.is_set())
            self.assertGreater(ticks, 2)
            self.assertNotEqual(threads[0], threading.get_ident())
            self.assertEqual(result.retrieval_records[0].outcome, "timed_out")
            query = RetrievalRequest("voltage", "synthetic", RetrievalPurpose.GENERATION,
                                     self.original.knowledge_version, 1)
            with self.assertRaisesRegex(RuntimeError, "worker busy"):
                await slow.retrieve(query)
            self.assertTrue(await asyncio.to_thread(finished.wait, 1))
            self.assertTrue((await slow.retrieve(query)).evidence)

    async def test_validation_time_is_part_of_step_timeout(self):
        # Isolate the intentionally slow validation stage from disk/thread startup
        # jitter. First retrieve and validate actual SQLite/BM25 results under the
        # normal budget; replay those exact requests/results in the 50ms test.
        prepared = {}
        async def capture(request):
            output = await self.actual.retrieve(request)
            prepared[request.purpose] = (request, output)
            return output
        self.retriever.hook = capture
        warm = await self.run_harness()
        self.assertEqual(warm.report.decision.kind, DecisionKind.PASS)
        async def replay(request):
            saved_request, result = prepared[request.purpose]
            self.assertEqual(request, saved_request)
            return result
        self.retriever.hook = replay
        async def slow_validation(request, result):
            if request.purpose == RetrievalPurpose.VERIFICATION:
                await asyncio.sleep(0.2)
            self.assertEqual(result, prepared[request.purpose][1])
        self.retriever.validate_result = slow_validation
        result = await self.run_harness(budget=RunBudget(step_timeout_seconds=0.05))
        self.assertEqual(result.retrieval_records[1].outcome, "timed_out")
        self.assertFalse(result.retrieval_records[1].core_evidence_ids)
        self.assertTrue(result.report.domain_findings)
        self.assertEqual(result.report.decision.kind, DecisionKind.REVIEW_REQUIRED)

    async def test_cancelled_retrieval_retains_completed_generation_evidence(self):
        waiting = asyncio.Event()
        async def hook(request):
            if request.purpose == RetrievalPurpose.VERIFICATION:
                waiting.set()
                await asyncio.sleep(10)
        self.retriever.hook = hook
        harness = self.harness()
        task = asyncio.create_task(self.run_harness(harness))
        await asyncio.wait_for(waiting.wait(), 1)
        run_id = next(iter(harness._runs))
        await harness.cancel(run_id)
        result = await task
        self.assertEqual(result.state, RunState.CANCELLED)
        self.assertEqual([r.outcome for r in result.retrieval_records], ["hits", "cancelled"])
        self.assertTrue(result.evidence)
        self.assertFalse(any(r.outcome == "empty" for r in result.retrieval_records))

    async def test_demo_cli_marks_simulation_and_serializes_complete_run(self):
        import json
        import subprocess
        import sys
        completed = await asyncio.to_thread(subprocess.run, [sys.executable, "-X", "utf8", "-m",
            "harness.retrieval_demo", "--db", str(self.db), "--knowledge-version", self.original.knowledge_version,
            "--revise-once"], capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertIn("SIMULATED", output["scope"])
        self.assertIn("INTEGRATION TEST ONLY", output["business_conclusion"])
        self.assertEqual(output["result"]["report"]["answer"]["version"], 2)
        self.assertEqual(len(output["result"]["retrieval_records"]), 5)
        self.assertTrue(output["result"]["trace"]["events"])
        self.assertEqual(output["source_audit"]["documents"][0]["status"], "not_in_official_manifest")

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "optional PDF fixture dependency unavailable")
    async def test_pdf_core_context_budget_and_quality_metadata(self):
        from tests.pdf_fixtures import make_pdf
        pdf = self.path / "synthetic_fixture.pdf"
        pdf.write_bytes(make_pdf(["Voltage stability important definition.\n" + "wrapped condition " * 5,
                                  "Adjacent synthetic_fixture context without matching terms."]))
        db = self.path / "pdf.sqlite3"
        with KnowledgeStore(db) as store:
            initial = store.ingest(pdf, "synthetic_pdf", SourceMetadata(source_type="synthetic_fixture",
                applicability=("synthetic only",)))
            derived = store.derive_pdf("synthetic_pdf", initial.knowledge_version, max_chars=80)
        with AsyncSQLiteBM25Retriever(db) as actual:
            config = FakeConfig(text="Voltage stability")
            harness = self.harness(config, RetrievalSettings(1, ContextOptions(400, 6, 2)), actual)
            result = await harness.run(self.request(text="Voltage stability"), RunBudget(),
                                       knowledge_version=derived.knowledge_version)
            self.assertEqual(result.report.decision.kind, DecisionKind.PASS)
            self.assertTrue(any(r.context_evidence_ids for r in result.retrieval_records))
            self.assertTrue(any(b.origin == "index_adjacent_context" and b.core_evidence_ids for b in result.evidence_bindings))
            for e in result.evidence:
                if e.provenance:
                    self.assertEqual(e.provenance.quality_status, "text_pending_review")
                    self.assertEqual(e.applicability, ("synthetic only",))
            core_id = result.retrieval_records[0].core_evidence_ids[0]
            size = len(next(e for e in result.evidence if e.evidence_id == core_id).text)
            limited = await harness.run(self.request(text="Voltage stability"),
                RunBudget(max_retrieval_chars_per_call=size), knowledge_version=derived.knowledge_version)
            self.assertEqual(limited.report.decision.kind, DecisionKind.PASS)
            self.assertTrue(all(not r.context_evidence_ids for r in limited.retrieval_records))
            self.assertTrue(all(r.accepted_chars <= size for r in limited.retrieval_records))
            self.assertTrue(any(r.omitted_evidence_ids or r.context_omissions for r in limited.retrieval_records))
