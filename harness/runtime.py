"""Minimal dependency-free orchestration with frozen, versioned audit inputs."""
import asyncio
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from agents.contracts import (
    GenerationInput, GenerationOutput, EvidenceVerificationInput,
    EvidenceVerificationOutput, PowerDomainReviewInput, PowerDomainReviewOutput,
    RevisionInput,
)
from core.models import (
    AuditDecision, AuditReport, DecisionKind, ExecutionIssue, ExecutionStatus,
    EvidenceBinding, RunTrace, TaskMode, TraceEvent,
    ClaimExtractionOutput,
)
from core.validation import (
    ContractError, InputError, merge_evidence, require, unique, validate_answer,
    validate_claims, validate_report, validate_request, validate_review,
    validate_revision, validate_types, validate_extraction,
)
from harness.contracts import HarnessResult, RetrievalSettings, ReviewRound
from harness.policy import DeterministicAuditPolicy
from harness.states import RunState, NORMAL_TRANSITIONS, TERMINAL_STATES, INTERRUPT_TARGETS
from harness.retrieval import RetrievalSession, validate_settings
from rag.contracts import RetrievalPurpose
from model_adapter.contracts import ModelBudgetError
from model_adapter.runtime import ModelBudget, model_scope, model_invocation_scope


class RequiredRetrievalFailure(RuntimeError):
    pass


class HarnessObserverError(RuntimeError):
    """Persistence observer failed; stop execution rather than claim durability."""
    pass


class OfflineHarness:
    def __init__(self, generation, verification, domain_review, revision, extractor, policy=None,
                 retriever=None, retrieval_settings=None, unit_tool=None, observer=None):
        self.generation = generation
        self.verification = verification
        self.domain_review = domain_review
        self.revision = revision
        self.extractor = extractor
        self.unit_tool = unit_tool
        self.observer = observer
        self.policy = policy or DeterministicAuditPolicy()
        self.retriever = retriever
        self.retrieval_settings = retrieval_settings or RetrievalSettings()
        validate_settings(self.retrieval_settings)
        if retriever is not None:
            from rag.retriever import BM25Retriever
            if isinstance(retriever, BM25Retriever):
                raise InputError("Use AsyncSQLiteBM25Retriever for Harness; a live SQLite connection is thread-owned")
        self._runs = {}

    async def cancel(self, run_id):
        task = self._runs.get(run_id)
        if task:
            task.cancel()

    async def run(self, request, budget, *, knowledge_version=None, generation_only=False, answer_requirements=(),
                  evidence_only=False, indexed_reference_ids=(), generation_snapshot=None, run_id=None):
        # Invalid user input raises InputError before any agent is executed.
        validate_request(request, budget)
        if generation_snapshot is not None:
            from services.evidence_scope import validate_snapshot
            if request.existing_answer is None:
                raise InputError("Saved generation snapshot requires an existing answer")
            validate_snapshot(generation_snapshot, request.existing_answer)
            known_input = {e.evidence_id: e for e in request.provided_evidence}
            require(all(known_input.get(e.evidence_id) == e for e in generation_snapshot.evidence),
                    "Saved generation snapshot must match supplied original records")
            require(generation_snapshot.knowledge_version == knowledge_version,
                    "Saved generation snapshot knowledge version mismatch")
            if generation_snapshot.snapshot_version=="generation-full-input-v2":
                require(generation_snapshot.question==request.question and generation_snapshot.user_context==request.user_context and generation_snapshot.engineering_context==request.engineering_context,
                    "Full generation input does not match frozen question/context")
        if type(generation_only) is not bool or (generation_only and request.mode != TaskMode.QUESTION_ANSWER):
            raise InputError("generation_only requires question_answer mode")
        if type(evidence_only) is not bool or (evidence_only and (generation_only or request.mode != TaskMode.ASSESS_EXISTING)):
            raise InputError("evidence_only requires assess_existing mode")
        try:
            validate_types(answer_requirements, tuple[str, ...])
            validate_types(indexed_reference_ids, tuple[str, ...])
            require(set(indexed_reference_ids) <= {e.evidence_id for e in request.provided_evidence}, "Unknown indexed reference")
            require(not indexed_reference_ids or self.retriever is not None, "Indexed references require a validating Retriever")
        except ContractError as exc:
            raise InputError(str(exc)) from exc
        if self.retriever is not None and (type(knowledge_version) is not str or not knowledge_version.strip()):
            raise InputError("Enabled retrieval requires an explicit fixed knowledge_version")
        run_id = run_id or uuid4().hex
        require(run_id not in self._runs, "run already active")
        self._runs[run_id] = asyncio.current_task()
        events, issues = [], []
        state = RunState.RECEIVED
        answer, claims = request.existing_answer, ()
        evidence = request.provided_evidence
        bindings = tuple(EvidenceBinding(e.evidence_id, "user_reference") for e in evidence)
        verification = domain = report = None
        generated = extracted = None
        review_rounds, revision_outputs = [], []
        tool_results=[];tool_calls=0
        active_snapshot = generation_snapshot
        rounds, calls = 0, 0
        run_started = perf_counter()
        deadline = run_started + budget.max_duration_seconds
        def reserve_model_call():
            nonlocal calls
            if calls >= budget.max_model_calls:
                raise ModelBudgetError()
            calls += 1
            return calls
        model_budget = ModelBudget(budget.max_model_calls, deadline, reserve_model_call)
        retrieval = None if self.retriever is None else RetrievalSession(
            self.retriever, knowledge_version, self.retrieval_settings, budget, deadline, request.provided_evidence,
            indexed_reference_ids)

        def record(component, status, started, detail="", outputs=(), model_version=None, prompt_version=None, stage_output=None):
            ref = () if answer is None else (f"{answer.answer_id}@{answer.version}",)
            events.append(TraceEvent(
                event_id=uuid4().hex, timestamp_utc=datetime.now(timezone.utc).isoformat(),
                component=component, status=status, input_refs=ref, output_refs=outputs,
                duration_ms=max(0, int((perf_counter() - started) * 1000)),
                answer_version=None if answer is None else answer.version,
                state=state.value, detail=detail,
                knowledge_version=knowledge_version if retrieval else None,
                model_version=model_version, prompt_version=prompt_version,
            ))
            if self.observer is not None:
                try:
                    self.observer({"run_id":run_id,"state":state.value,"event":events[-1],
                        "answer":answer,"claims":claims,"evidence":evidence,"evidence_bindings":bindings,
                        "generation_output":generated,"extraction_output":extracted,
                        "verification_output":verification,"domain_output":domain,"report":report,
                        "review_rounds":tuple(review_rounds),"revision_outputs":tuple(revision_outputs),
                        "tool_results":tuple(tool_results),"model_records":tuple(model_budget.records),
                        "retrieval_records":() if retrieval is None else tuple(retrieval.records),
                        "execution_issues":tuple(issues),"stage_output":stage_output,
                        "budget_usage":{"model_calls":calls,"tool_calls":tool_calls}})
                except Exception as exc:
                    raise HarnessObserverError("Stage persistence failed; run stopped") from exc

        def transition(target):
            nonlocal state
            require(state not in TERMINAL_STATES, "cannot transition from terminal state")
            require(target in NORMAL_TRANSITIONS[state] or target in INTERRUPT_TARGETS, "illegal state transition")
            state = target
            record("state", ExecutionStatus.SUCCEEDED, perf_counter(), target.value)

        async def invoke(component, function, inputs, validator, model_call=False, managed_model=False):
            nonlocal calls
            started = perf_counter()
            invocation_id = uuid4().hex
            invocation_version = None if answer is None else answer.version
            try:
                remaining = deadline - started
                if remaining <= 0:
                    raise TimeoutError("Total run duration exhausted")
                if model_call and not managed_model:
                    if calls >= budget.max_model_calls:
                        raise RuntimeError("Agent call budget exhausted")
                    calls += 1
                with model_scope(model_budget), model_invocation_scope(invocation_id, component, invocation_version):
                    output = await asyncio.wait_for(function(inputs), min(budget.step_timeout_seconds, remaining))
                validator(output)
                if perf_counter() > deadline:
                    raise TimeoutError("Total run duration exhausted while validating output")
                output_issues = getattr(output, "execution_issues", ())
                status = output_issues[0].status if output_issues else ExecutionStatus.SUCCEEDED
                record(component, status, started, "; ".join(i.message for i in output_issues),stage_output=output)
                return output, None
            except HarnessObserverError:
                raise
            except asyncio.CancelledError:
                record(component, ExecutionStatus.CANCELLED, started, "Cancelled")
                raise
            except Exception as exc:
                status = ExecutionStatus.TIMED_OUT if isinstance(exc, TimeoutError) else ExecutionStatus.FAILED
                code = getattr(exc, "code", "OUTPUT_CONTRACT_ERROR" if isinstance(exc, ContractError) else (
                    "TIMEOUT" if status == ExecutionStatus.TIMED_OUT else "EXECUTION_FAILURE"))
                issue = ExecutionIssue(component, status, code, f"{type(exc).__name__}: {exc}")
                record(component, status, started, issue.message)
                return None, issue
            finally:
                if managed_model:
                    import json
                    from dataclasses import asdict
                    for item in model_budget.records:
                        if item.invocation_id != invocation_id:
                            continue
                        record("model_request", item.status, perf_counter() - item.duration_ms / 1000,
                               json.dumps(asdict(item), ensure_ascii=False),
                               outputs=(f"{run_id}:model:{item.call_number}",),
                               model_version=item.requested_model_id, prompt_version=item.prompt_version)

        def make_report(decision):
            result = AuditReport(
                uuid4().hex, request.task_id, answer, claims, evidence,
                () if verification is None else verification.findings,
                () if domain is None else domain.findings, tuple(issues), decision, bindings,
            )
            validate_report(result)
            return result

        async def retrieve_for(purpose):
            nonlocal evidence, bindings
            started = perf_counter()
            try:
                if purpose == RetrievalPurpose.VERIFICATION and self.retrieval_settings.fact_strategy == 'per_claim_v1':
                    from harness.fact_retrieval import retrieve_facts
                    delivery = await retrieve_facts(retrieval, request, answer, claims)
                else:
                    delivery = await retrieval.retrieve(purpose, request, answer, claims)
                evidence = merge_evidence(evidence, delivery.evidence)
                bindings += delivery.bindings
                return delivery
            finally:
                if retrieval.records:
                    import json
                    from dataclasses import asdict
                    last = retrieval.records[-1]
                    record("retrieval_" + purpose.value, last.status, started,
                           json.dumps(asdict(last), ensure_ascii=False),
                           last.core_evidence_ids + last.context_evidence_ids)

        def guard_agent_evidence(output, allowed):
            if retrieval is None:
                return
            known = {e.evidence_id: e for e in allowed}
            for item in getattr(output, "evidence", ()):
                if item.provenance is not None:
                    require(known.get(item.evidence_id) == item,
                            "Agent cannot mint or change index/source provenance")
            merge_evidence(evidence, getattr(output, "evidence", ()))

        def collect_agent_evidence(items):
            nonlocal bindings
            existing = {b.evidence_id for b in bindings}
            bindings += tuple(EvidenceBinding(e.evidence_id, "agent_output_unverified",
                                              answer_version=answer.version)
                              for e in items if e.evidence_id not in existing)
            if retrieval:
                retrieval.known_evidence.update((e.evidence_id, e) for e in items)

        reason = ""
        try:
            transition(RunState.VALIDATED)
            if indexed_reference_ids:
                refs = tuple(e for e in evidence if e.evidence_id in indexed_reference_ids)
                async def validate_saved(items):
                    await self.retriever.validate_evidence(items, knowledge_version)
                _, issue = await invoke("original_index_validation", validate_saved, refs, lambda _: None)
                if issue:
                    issues.append(issue)
                    raise RequiredRetrievalFailure("Saved original evidence failed frozen-index validation")
                bindings = tuple(EvidenceBinding(e.evidence_id,
                    "index_saved_reference" if e.evidence_id in indexed_reference_ids else "user_reference",
                    "original_citation", None if answer is None else answer.version) for e in evidence)
            if request.mode == TaskMode.QUESTION_ANSWER:
                transition(RunState.RETRIEVING)
                record("provided_evidence", ExecutionStatus.SUCCEEDED, perf_counter(),
                       "User references; not index-verified" if retrieval else "Offline evidence only; no RAG call")
                if retrieval:
                    generated_delivery = await retrieve_for(RetrievalPurpose.GENERATION)
                    if generated_delivery.issue:
                        issues.append(generated_delivery.issue)
                        raise RequiredRetrievalFailure("Required generation retrieval did not complete")
                transition(RunState.GENERATING)

                def check_generation(output):
                    validate_types(output, GenerationOutput)
                    validate_answer(output.answer, evidence)
                    if output.evidence_snapshot is not None:
                        from services.evidence_scope import validate_snapshot
                        validate_snapshot(output.evidence_snapshot,output.answer)
                        require(output.evidence_snapshot.evidence==evidence,"Generation snapshot must preserve all supplied evidence")
                        require(output.evidence_snapshot.knowledge_version==(knowledge_version if retrieval else None),"Generation snapshot knowledge version changed")
                    for issue in output.execution_issues:
                        require(issue.status != ExecutionStatus.SUCCEEDED, "execution issue cannot be successful")

                generated, issue = await invoke("generation", self.generation.run,
                                               GenerationInput(request, evidence, bindings,
                                                               knowledge_version if retrieval else None, answer_requirements),
                                               check_generation, True, getattr(self.generation, "uses_model_adapter", False))
                if issue:
                    issues.append(issue)
                    raise RuntimeError(issue.message)
                issues.extend(generated.execution_issues)
                if generated.execution_issues:
                    raise RuntimeError("Generation reported execution failure")
                answer = generated.answer
                active_snapshot = generated.evidence_snapshot
                record("answer_created", ExecutionStatus.SUCCEEDED, perf_counter(), outputs=(f"{answer.answer_id}@{answer.version}",))
                if generation_only:
                    reason = "Draft generated only; no factual or domain audit performed"
                    transition(RunState.GENERATED)
            while not generation_only:
                transition(RunState.EXTRACTING_CLAIMS)
                def check_extraction(output):
                    if isinstance(output, ClaimExtractionOutput):
                        validate_extraction(output, answer)
                    else:
                        validate_claims(output, answer)
                extraction, issue = await invoke("claim_extraction", self.extractor.extract, answer,
                    check_extraction, getattr(self.extractor, "uses_model_adapter", False),
                    getattr(self.extractor, "uses_model_adapter", False))
                if issue:
                    issues.append(issue)
                    raise RuntimeError(issue.message)
                extracted = extraction if isinstance(extraction, ClaimExtractionOutput) else None
                claims = extracted.claims if extracted is not None else extraction
                current_tools=[]
                if self.unit_tool is not None:
                    from tools.contracts import ToolRequest
                    from tools.unit_conversion import requests_for,validate_result
                    for payload in requests_for(claims,version=self.unit_tool.spec.version):
                        if tool_calls>=budget.max_tool_calls:
                            issue=ExecutionIssue('scalar_unit_conversion',ExecutionStatus.FAILED,'TOOL_BUDGET_EXHAUSTED','Required scalar tool budget exhausted')
                            issues.append(issue);record('scalar_unit_conversion',issue.status,perf_counter(),issue.message);break
                        tool_calls+=1
                        result,issue=await invoke('scalar_unit_conversion',self.unit_tool.execute,
                            ToolRequest(uuid4().hex,request.task_id,'scalar_unit_conversion','evidence_verification',payload,min(5.,budget.step_timeout_seconds)),validate_result)
                        if issue:issues.append(issue)
                        else:
                            current_tools.append(result);tool_results.append(result)
                            record('tool_result',result.status,perf_counter(),__import__('json').dumps(__import__('dataclasses').asdict(result)),outputs=(result.result_id,))
                            if result.issue:issues.append(result.issue)
                record("claims_created", ExecutionStatus.SUCCEEDED, perf_counter(), outputs=tuple(c.claim_id for c in claims))
                if extracted is not None:
                    import json
                    from dataclasses import asdict
                    record("claim_coverage", ExecutionStatus.SUCCEEDED, perf_counter(),
                           json.dumps(asdict(extracted), ensure_ascii=False))
                transition(RunState.VERIFYING)
                original_ids = {eid for c in answer.citations for eid in c.evidence_ids}
                original_evidence = tuple(e for e in evidence if e.evidence_id in original_ids)
                # Both agents receive the identical immutable answer and claim tuple.
                v_evidence = d_evidence = evidence
                v_bindings = d_bindings = bindings
                v_retrieval_issue = d_retrieval_issue = None
                if retrieval:
                    # Bounded, sequential retrieval. The agents remain two parallel reviewers.
                    vd = await retrieve_for(RetrievalPurpose.VERIFICATION)
                    if not evidence_only:
                        dd = await retrieve_for(RetrievalPurpose.DOMAIN_REVIEW)
                    user_evidence = tuple(e for e in request.provided_evidence if e.evidence_id not in indexed_reference_ids)
                    v_evidence = merge_evidence(user_evidence, vd.evidence)
                    if not evidence_only:
                        domain_references = (user_evidence if getattr(self.domain_review, "protocol_version", 1) >= 2
                                             else request.provided_evidence)
                        d_evidence = merge_evidence(domain_references, dd.evidence)
                    user_bindings = tuple(b for b in bindings if b.origin == "user_reference")
                    v_bindings = user_bindings + vd.bindings
                    v_retrieval_issue = vd.issue
                    if not evidence_only:
                        d_bindings, d_retrieval_issue = user_bindings + dd.bindings, dd.issue
                current_snapshot = active_snapshot
                if current_snapshot is not None and current_snapshot.answer_version != answer.version:
                    current_snapshot = None
                v_input = EvidenceVerificationInput(request, answer, claims, v_evidence, v_bindings,
                                                    knowledge_version if retrieval else None, original_evidence,
                                                    current_snapshot)
                d_input = PowerDomainReviewInput(request, answer, claims, d_evidence, getattr(self.domain_review,"rule_set_version","offline-rules-v1"),
                                                d_bindings, knowledge_version if retrieval else None)
                from agents.contracts import ReliabilityVerificationInput,ReliabilityDomainInput
                from dataclasses import fields
                if getattr(self.verification,'schema_version',None) in (9,10,11,12,13):
                    v_input=ReliabilityVerificationInput(**{f.name:getattr(v_input,f.name) for f in fields(v_input)},tool_results=tuple(current_tools),delivery_summary=__import__('json').dumps(__import__('dataclasses').asdict(vd.record)) if retrieval else '',fact_retrieval_bindings=vd.record.fact_bindings if retrieval else ())
                if getattr(self.domain_review,'protocol_version',None) in (3,4):
                    d_input=ReliabilityDomainInput(**{f.name:getattr(d_input,f.name) for f in fields(d_input)},tool_results=tuple(current_tools),delivery_summary=__import__('json').dumps(__import__('dataclasses').asdict(dd.record)) if retrieval and not evidence_only else '')

                async def review(component, agent, inputs, allowed, is_verification, retrieval_issue):
                    if is_verification and inputs.generation_snapshot is not None:
                        allowed = merge_evidence(allowed, inputs.generation_snapshot.evidence)
                    if retrieval_issue and not (is_verification and getattr(inputs, 'fact_retrieval_bindings', ())):
                        return None, retrieval_issue
                    def check(output):
                        guard_agent_evidence(output, allowed)
                        if not is_verification and getattr(output,"prompt_version",None) and output.prompt_version.startswith(("power-domain-review-v1","power-domain-review-v2","power-domain-review-v3")):
                            require(output.engineering_context == request.engineering_context,"Domain review changed engineering inputs")
                        validate_review(output, answer, claims, allowed, is_verification)
                    output, issue = await invoke(component, agent.run, inputs, check, True,
                                                getattr(agent, "uses_model_adapter", False))
                    if output is not None and retrieval_issue:
                        from dataclasses import replace
                        output = replace(output, execution_issues=output.execution_issues + (vd.issues or (retrieval_issue,)))
                    return output, issue

                if evidence_only:
                    verification, issue = await review("evidence_verification", self.verification, v_input,
                        merge_evidence(v_evidence, original_evidence), True, v_retrieval_issue)
                    if issue:
                        issues.append(issue)
                        if getattr(self.verification,"schema_version",None) in (7,8):
                            from agents.verification_contract_v7 import execution_incomplete
                            verification = execution_incomplete(v_input,issue)
                        else:
                            verification = EvidenceVerificationOutput(answer.answer_id, answer.version, claims, (), (), (issue,))
                        reason = "Evidence verification execution incomplete; domain review not run"
                        transition(RunState.REVIEW_REQUIRED)
                    else:
                        issues.extend(verification.execution_issues)
                        evidence = merge_evidence(evidence, verification.evidence)
                        collect_agent_evidence(verification.evidence)
                        reason = "Extracted claims evidence-reviewed only; all coverage gaps remain unreviewed; no domain review or audit pass"
                        transition(RunState.REVIEW_REQUIRED if verification.execution_issues else RunState.EVIDENCE_REVIEWED)
                    break

                reviewers = [asyncio.create_task(job) for job in (
                    review("evidence_verification", self.verification, v_input, merge_evidence(v_evidence, original_evidence), True, v_retrieval_issue),
                    review("power_domain_review", self.domain_review, d_input, d_evidence, False, d_retrieval_issue),
                )]
                try:
                    (verification, v_issue), (domain, d_issue) = await asyncio.gather(*reviewers)
                except BaseException:
                    for reviewer in reviewers:
                        reviewer.cancel()
                    await asyncio.gather(*reviewers,return_exceptions=True)
                    raise
                if v_issue:
                    if getattr(self.verification,"schema_version",None) in (7,8):
                        from agents.verification_contract_v7 import execution_incomplete
                        verification = execution_incomplete(v_input,v_issue)
                    else:
                        verification = EvidenceVerificationOutput(answer.answer_id, answer.version, claims, (), (), (v_issue,))
                if d_issue:
                    if getattr(self.domain_review,"rule_set_version",None)=="power-demo-rules-v1":
                        from agents.power_domain_review import execution_incomplete_domain
                        domain = execution_incomplete_domain(d_input,d_issue)
                    else:
                        domain = PowerDomainReviewOutput(answer.answer_id, answer.version, (), (), (d_issue,))
                # Conflicting output IDs invalidate the offending component, not its peer.
                try:
                    evidence = merge_evidence(evidence, verification.evidence)
                    collect_agent_evidence(verification.evidence)
                except ContractError as exc:
                    issue = ExecutionIssue("evidence_verification", ExecutionStatus.FAILED, "OUTPUT_CONTRACT_ERROR", str(exc))
                    verification = EvidenceVerificationOutput(answer.answer_id, answer.version, claims, (), (), (issue,))
                    record("evidence_verification_validation", ExecutionStatus.FAILED, perf_counter(), str(exc))
                try:
                    evidence = merge_evidence(evidence, domain.evidence)
                    unique(verification.findings + domain.findings, "finding_id")
                    collect_agent_evidence(domain.evidence)
                except ContractError as exc:
                    issue = ExecutionIssue("power_domain_review", ExecutionStatus.FAILED, "OUTPUT_CONTRACT_ERROR", str(exc))
                    domain = PowerDomainReviewOutput(answer.answer_id, answer.version, (), (), (issue,))
                    record("power_domain_review_validation", ExecutionStatus.FAILED, perf_counter(), str(exc))
                issues.extend(verification.execution_issues + domain.execution_issues)
                transition(RunState.DECIDING)
                decision = self.policy.decide(verification, domain, budget, rounds)
                real_repair = (getattr(self.policy,"allows_bounded_real_revision",False)
                    and getattr(self.revision,"bounded_real_revision",False) and rounds < 1)
                if decision.kind in (DecisionKind.PASS, DecisionKind.REVISE) and (
                        getattr(self.verification, "uses_model_adapter", False) or getattr(self.extractor, "uses_model_adapter", False)) and not (decision.kind==DecisionKind.REVISE and real_repair):
                    # Model reviews and demo rules are not safety certification.
                    decision = AuditDecision(DecisionKind.REVIEW_REQUIRED,
                        ("Model and rule reviews are limited; no engineering feasibility/safety certification",)
                        + decision.reasons, "evidence-local-gate-v1", decision.unresolved_finding_ids)
                if extracted is not None and (extracted.uncovered_spans or extracted.non_claim_spans):
                    decision = AuditDecision(decision.kind if decision.kind==DecisionKind.REVISE and real_repair else DecisionKind.REVIEW_REQUIRED,
                        ("Some answer text is not claim-reviewed; coverage gaps remain unresolved",)+decision.reasons, "coverage-gate-v1",decision.unresolved_finding_ids)
                if retrieval:
                    if any(r.status != ExecutionStatus.SUCCEEDED for r in retrieval.records):
                        decision = AuditDecision(DecisionKind.REVIEW_REQUIRED,
                            ("Required retrieval did not complete; partial valid evidence retained",),
                            "retrieval-gate-v1", decision.unresolved_finding_ids)
                    elif any(r.outcome == "empty" for r in retrieval.records) and decision.kind == DecisionKind.PASS:
                        decision = AuditDecision(DecisionKind.INSUFFICIENT_EVIDENCE,
                            ("Required retrieval completed with no hits; this is not evidence of a false claim",),
                            "retrieval-gate-v1", decision.unresolved_finding_ids)
                report = make_report(decision)
                review_rounds.append(ReviewRound(answer,extracted,verification,domain,report))
                record("audit_policy", ExecutionStatus.SUCCEEDED, perf_counter(),
                       f"{decision.kind.value}: {'; '.join(decision.reasons)}")
                reason = "; ".join(decision.reasons)
                if decision.kind != DecisionKind.REVISE:
                    transition(RunState.COMPLETED if decision.kind == DecisionKind.PASS else RunState.REVIEW_REQUIRED)
                    break
                if rounds >= budget.max_revision_rounds:
                    raise ContractError("Policy attempted revision beyond limit")
                transition(RunState.REVISING)
                def check_revision(output):
                    guard_agent_evidence(output, evidence)
                    validate_revision(output, answer, evidence, verification.findings + domain.findings)
                    if getattr(output,"evidence_snapshot",None) is not None:
                        from services.evidence_scope import validate_snapshot
                        validate_snapshot(output.evidence_snapshot,output.answer)
                        require(output.evidence_snapshot.evidence==evidence,"Revision snapshot changed allowed evidence")
                revised, issue = await invoke(
                    "revision", self.revision.run,
                    RevisionInput(request, answer, verification, domain, evidence, decision.reasons,
                                  bindings, knowledge_version if retrieval else None),
                    check_revision, True, getattr(self.revision,"uses_model_adapter",False),
                )
                if issue or revised.execution_issues:
                    issues.extend((issue,) if issue else revised.execution_issues)
                    decision = AuditDecision(DecisionKind.REVIEW_REQUIRED, ("Revision execution failed",), "offline-policy-v1",
                                             decision.unresolved_finding_ids)
                    report = make_report(decision)
                    reason = decision.reasons[0]
                    transition(RunState.REVIEW_REQUIRED)
                    break
                answer = revised.answer
                revision_outputs.append(revised)
                active_snapshot = revised.evidence_snapshot
                evidence = merge_evidence(evidence, revised.evidence)
                collect_agent_evidence(revised.evidence)
                record("revision_changes", ExecutionStatus.SUCCEEDED, perf_counter(),
                       "; ".join(change.description for change in revised.changes),
                       outputs=(f"{answer.answer_id}@{answer.version}",))
                rounds += 1
                verification = domain = None
                report = None
        except HarnessObserverError:
            raise
        except RequiredRetrievalFailure as exc:
            reason = str(exc)
            transition(RunState.REVIEW_REQUIRED)
        except asyncio.CancelledError:
            reason = "Run cancelled"
            issues.append(ExecutionIssue("harness", ExecutionStatus.CANCELLED, "CANCELLED", reason))
            transition(RunState.CANCELLED)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            if not issues:
                issues.append(ExecutionIssue("harness", ExecutionStatus.FAILED, "EXECUTION_FAILURE", reason))
            transition(RunState.FAILED)
        finally:
            self._runs.pop(run_id, None)
        record("termination", ExecutionStatus.CANCELLED if state == RunState.CANCELLED else
               ExecutionStatus.FAILED if state == RunState.FAILED else ExecutionStatus.SUCCEEDED,
               perf_counter(), reason)
        result=HarnessResult(run_id, state, RunTrace(run_id, request.task_id, tuple(events)), report, reason,
                             tuple(issues), evidence, bindings, () if retrieval is None else tuple(retrieval.records),
                             max(0, int((perf_counter() - run_started) * 1000)), answer, generated,
                             tuple(model_budget.records), extracted, verification, domain,tuple(review_rounds),tuple(revision_outputs))
        if self.unit_tool is not None:
            from harness.contracts import ToolHarnessResult
            from dataclasses import fields
            result=ToolHarnessResult(**{f.name:getattr(result,f.name) for f in fields(result)},tool_results=tuple(tool_results))
        return result
