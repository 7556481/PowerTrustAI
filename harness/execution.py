"""Shared Harness stages, extracted without a graph dependency or new scheduler."""
import asyncio
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4
from dataclasses import replace

from agents.contracts import (
    GenerationInput, GenerationOutput, EvidenceVerificationInput,
    EvidenceVerificationOutput, PowerDomainReviewInput, PowerDomainReviewOutput,
    RevisionInput,
)
from core.models import (
    AuditDecision, AuditReport, DecisionKind, ExecutionIssue, ExecutionStatus,
    EvidenceBinding, RunTrace, TaskMode, TraceEvent, ClaimExtractionOutput,
)
from core.validation import (
    ContractError, InputError, merge_evidence, require, unique, validate_answer,
    validate_claims, validate_report, validate_request, validate_review,
    validate_revision, validate_types, validate_extraction,
)
from harness.contracts import HarnessResult, ReviewRound
from harness.states import RunState, NORMAL_TRANSITIONS, TERMINAL_STATES, INTERRUPT_TARGETS
from harness.retrieval import RetrievalSession
from rag.contracts import RetrievalPurpose
from model_adapter.contracts import ModelBudgetError
from model_adapter.runtime import ModelBudget, model_scope, model_invocation_scope


class RequiredRetrievalFailure(RuntimeError):
    pass

class HarnessObserverError(RuntimeError):
    """Persistence observer failed; stop execution rather than claim durability."""
    pass

class RunExecution:
    """Per-run shared stages; orchestration and resources stay owned by OfflineHarness."""

    def __init__(self, harness, request, budget, *, knowledge_version=None,
                 generation_only=False, answer_requirements=(), evidence_only=False,
                 indexed_reference_ids=(), generation_snapshot=None, run_id=None):
        self.harness = harness
        self.request = request
        self.budget = budget
        self.knowledge_version = knowledge_version
        self.generation_only = generation_only
        self.answer_requirements = answer_requirements
        self.evidence_only = evidence_only
        self.indexed_reference_ids = indexed_reference_ids
        self.generation_snapshot = generation_snapshot
        self.run_id = run_id
        validate_request(self.request, self.budget)
        if self.generation_snapshot is not None:
            from services.evidence_scope import validate_snapshot
            if self.request.existing_answer is None:
                raise InputError('Saved generation snapshot requires an existing answer')
            validate_snapshot(self.generation_snapshot, self.request.existing_answer)
            known_input = {e.evidence_id: e for e in self.request.provided_evidence}
            require(all((known_input.get(e.evidence_id) == e for e in self.generation_snapshot.evidence)), 'Saved generation snapshot must match supplied original records')
            require(self.generation_snapshot.knowledge_version == self.knowledge_version, 'Saved generation snapshot knowledge version mismatch')
            if self.generation_snapshot.snapshot_version == 'generation-full-input-v2':
                require(self.generation_snapshot.question == self.request.question and self.generation_snapshot.user_context == self.request.user_context and (self.generation_snapshot.engineering_context == self.request.engineering_context), 'Full generation input does not match frozen question/context')
        if type(self.generation_only) is not bool or (self.generation_only and self.request.mode != TaskMode.QUESTION_ANSWER):
            raise InputError('generation_only requires question_answer mode')
        if type(self.evidence_only) is not bool or (self.evidence_only and (self.generation_only or self.request.mode != TaskMode.ASSESS_EXISTING)):
            raise InputError('evidence_only requires assess_existing mode')
        try:
            validate_types(self.answer_requirements, tuple[str, ...])
            validate_types(self.indexed_reference_ids, tuple[str, ...])
            require(set(self.indexed_reference_ids) <= {e.evidence_id for e in self.request.provided_evidence}, 'Unknown indexed reference')
            require(not self.indexed_reference_ids or self.harness.retriever is not None, 'Indexed references require a validating Retriever')
        except ContractError as exc:
            raise InputError(str(exc)) from exc
        if self.harness.retriever is not None and (type(self.knowledge_version) is not str or not self.knowledge_version.strip()):
            raise InputError('Enabled retrieval requires an explicit fixed knowledge_version')
        self.run_id = self.run_id or uuid4().hex
        require(self.run_id not in self.harness._runs, 'run already active')
        self.harness._runs[self.run_id] = asyncio.current_task()
        self.events, self.issues = ([], [])
        self.state = RunState.RECEIVED
        self.answer, self.claims = (self.request.existing_answer, ())
        self.evidence = self.request.provided_evidence
        self.bindings = tuple((EvidenceBinding(e.evidence_id, 'user_reference') for e in self.evidence))
        self.verification = self.domain = self.report = None
        self.generated = self.extracted = None
        self.review_rounds, self.revision_outputs = ([], [])
        self.tool_results = []
        self.tool_calls = 0
        self.active_snapshot = self.generation_snapshot
        self.rounds, self.calls = (0, 0)
        self.run_started = perf_counter()
        self.deadline = self.run_started + self.budget.max_duration_seconds
        self.model_budget = ModelBudget(
            self.budget.max_model_calls, self.deadline, self.reserve_model_call)
        self.retrieval = None if self.harness.retriever is None else RetrievalSession(
            self.harness.retriever, self.knowledge_version, self.harness.retrieval_settings,
            self.budget, self.deadline, self.request.provided_evidence, self.indexed_reference_ids)
        self.reason = ''

    def reserve_model_call(self):
        if self.calls >= self.budget.max_model_calls:
            raise ModelBudgetError()
        self.calls += 1
        return self.calls

    def record(self, component, status, started, detail='', outputs=(), model_version=None, prompt_version=None, stage_output=None):
        ref = () if self.answer is None else (f'{self.answer.answer_id}@{self.answer.version}',)
        self.events.append(TraceEvent(event_id=uuid4().hex, timestamp_utc=datetime.now(timezone.utc).isoformat(), component=component, status=status, input_refs=ref, output_refs=outputs, duration_ms=max(0, int((perf_counter() - started) * 1000)), answer_version=None if self.answer is None else self.answer.version, state=self.state.value, detail=detail, knowledge_version=self.knowledge_version if self.retrieval else None, model_version=model_version, prompt_version=prompt_version))
        if self.harness.observer is not None:
            try:
                self.harness.observer({'run_id': self.run_id, 'state': self.state.value, 'event': self.events[-1], 'answer': self.answer, 'claims': self.claims, 'evidence': self.evidence, 'evidence_bindings': self.bindings, 'generation_output': self.generated, 'extraction_output': self.extracted, 'verification_output': self.verification, 'domain_output': self.domain, 'report': self.report, 'review_rounds': tuple(self.review_rounds), 'revision_outputs': tuple(self.revision_outputs), 'tool_results': tuple(self.tool_results), 'model_records': tuple(self.model_budget.records), 'retrieval_records': () if self.retrieval is None else tuple(self.retrieval.records), 'execution_issues': tuple(self.issues), 'stage_output': stage_output, 'budget_usage': {'model_calls': self.calls, 'tool_calls': self.tool_calls}})
            except Exception as exc:
                raise HarnessObserverError('Stage persistence failed; run stopped') from exc

    def transition(self, target):
        require(self.state not in TERMINAL_STATES, 'cannot transition from terminal state')
        require(target in NORMAL_TRANSITIONS[self.state] or target in INTERRUPT_TARGETS, 'illegal state transition')
        self.state = target
        self.record('state', ExecutionStatus.SUCCEEDED, perf_counter(), target.value)

    async def invoke(self, component, function, inputs, validator, model_call=False, managed_model=False):
        started = perf_counter()
        invocation_id = uuid4().hex
        invocation_version = None if self.answer is None else self.answer.version
        try:
            remaining = self.deadline - started
            if remaining <= 0:
                raise TimeoutError('Total run duration exhausted')
            if model_call and (not managed_model):
                if self.calls >= self.budget.max_model_calls:
                    raise RuntimeError('Agent call budget exhausted')
                self.calls += 1
            with model_scope(self.model_budget), model_invocation_scope(invocation_id, component, invocation_version):
                output = await asyncio.wait_for(function(inputs), min(self.budget.step_timeout_seconds, remaining))
            validator(output)
            if perf_counter() > self.deadline:
                raise TimeoutError('Total run duration exhausted while validating output')
            output_issues = getattr(output, 'execution_issues', ())
            status = output_issues[0].status if output_issues else ExecutionStatus.SUCCEEDED
            self.record(component, status, started, '; '.join((i.message for i in output_issues)), stage_output=output)
            return (output, None)
        except HarnessObserverError:
            raise
        except asyncio.CancelledError:
            self.record(component, ExecutionStatus.CANCELLED, started, 'Cancelled')
            raise
        except Exception as exc:
            status = ExecutionStatus.TIMED_OUT if isinstance(exc, TimeoutError) else ExecutionStatus.FAILED
            code = getattr(exc, 'code', 'OUTPUT_CONTRACT_ERROR' if isinstance(exc, ContractError) else 'TIMEOUT' if status == ExecutionStatus.TIMED_OUT else 'EXECUTION_FAILURE')
            issue = ExecutionIssue(component, status, code, f'{type(exc).__name__}: {exc}')
            self.record(component, status, started, issue.message)
            return (None, issue)
        finally:
            if managed_model:
                import json
                from dataclasses import asdict
                for item in self.model_budget.records:
                    if item.invocation_id != invocation_id:
                        continue
                    self.record('model_request', item.status, perf_counter() - item.duration_ms / 1000, json.dumps(asdict(item), ensure_ascii=False), outputs=(f'{self.run_id}:model:{item.call_number}',), model_version=item.requested_model_id, prompt_version=item.prompt_version)

    def make_report(self, decision):
        result = AuditReport(uuid4().hex, self.request.task_id, self.answer, self.claims, self.evidence, () if self.verification is None else self.verification.findings, () if self.domain is None else self.domain.findings, tuple(self.issues), decision, self.bindings)
        from agents.contracts import LiteralVerificationOutput
        if isinstance(self.verification,LiteralVerificationOutput):
            from core.literal_review import LiteralAuditReport
            from dataclasses import fields
            result=LiteralAuditReport(**{f.name:getattr(result,f.name) for f in fields(result)},literal_reviews=self.verification.literal_reviews,literal_defects=self.verification.literal_defects,
                literal_protocol='source_first_audit_v1' if self.harness.audit_strategy=='source_first_audit_v1' else 'literal-review-v1')
        validate_report(result)
        return result

    async def retrieve_for(self, purpose, query_override=None):
        if getattr(self.harness.retriever,'manages_query_conversion',False):
            with model_scope(self.model_budget), model_invocation_scope(uuid4().hex,'retrieval_'+purpose.value,None if self.answer is None else self.answer.version):
                return await self._retrieve_for(purpose,query_override)
        return await self._retrieve_for(purpose,query_override)

    async def _retrieve_for(self, purpose, query_override=None):
        started = perf_counter()
        try:
            if purpose == RetrievalPurpose.VERIFICATION and self.harness.retrieval_settings.fact_strategy == 'per_claim_v1':
                from harness.fact_retrieval import retrieve_facts
                delivery = await retrieve_facts(self.retrieval, self.request, self.answer, self.claims)
            else:
                delivery = await self.retrieval.retrieve(purpose, self.request, self.answer, self.claims, query_override=query_override)
            if getattr(self.harness, 'subject_supplement', False) and query_override is None and (not delivery.issue) and (purpose == RetrievalPurpose.GENERATION or (purpose == RetrievalPurpose.VERIFICATION and self.harness.retrieval_settings.fact_strategy == 'aggregate')):
                from services.audit_subject_query import question_subject, before_review, PRE_REVIEW_VERSION
                subject_query = question_subject(self.request.question) if purpose == RetrievalPurpose.GENERATION else before_review(self.claims)
                if subject_query and subject_query != delivery.record.query:
                    import json
                    from dataclasses import asdict, replace
                    self.record('retrieval_original_' + purpose.value, delivery.record.status, started, json.dumps(asdict(delivery.record), ensure_ascii=False))
                    extra = await self.retrieval.retrieve(purpose, self.request, self.answer, self.claims, query_override=subject_query)
                    self.record('retrieval_subject_' + purpose.value, extra.record.status, started, json.dumps({'version': PRE_REVIEW_VERSION, 'original_retrieval_id': delivery.record.retrieval_id, 'supplement': asdict(extra.record)}, ensure_ascii=False))
                    combined = merge_evidence(delivery.evidence, extra.evidence)
                    summary = replace(delivery.record, query_method=PRE_REVIEW_VERSION, status=extra.record.status if extra.issue else delivery.record.status, outcome='partial' if extra.issue else 'delivered' if combined else 'empty', hits=delivery.record.hits + extra.record.hits, core_evidence_ids=tuple(dict.fromkeys(delivery.record.core_evidence_ids + extra.record.core_evidence_ids)), context_evidence_ids=tuple(dict.fromkeys(delivery.record.context_evidence_ids + extra.record.context_evidence_ids)), accepted_chars=sum((len(e.text) for e in combined)), calls_used=self.retrieval.calls, cumulative_chars=self.retrieval.chars, reason='Original query and literal subject supplement; complete delivered bodies retained')
                    delivery = replace(delivery, evidence=combined, bindings=delivery.bindings + extra.bindings, record=summary, issue=extra.issue, issues=extra.issues)
            self.evidence = merge_evidence(self.evidence, delivery.evidence)
            self.bindings += delivery.bindings
            return delivery
        finally:
            if self.retrieval.records:
                import json
                from dataclasses import asdict
                last = self.retrieval.records[-1]
                self.record('retrieval_' + purpose.value, last.status, started, json.dumps(asdict(last), ensure_ascii=False), last.core_evidence_ids + last.context_evidence_ids)

    def guard_agent_evidence(self, output, allowed):
        if self.retrieval is None:
            return
        known = {e.evidence_id: e for e in allowed}
        for item in getattr(output, 'evidence', ()):
            if item.provenance is not None:
                require(known.get(item.evidence_id) == item, 'Agent cannot mint or change index/source provenance')
        merge_evidence(self.evidence, getattr(output, 'evidence', ()))

    def collect_agent_evidence(self, items):
        existing = {b.evidence_id for b in self.bindings}
        self.bindings += tuple((EvidenceBinding(e.evidence_id, 'agent_output_unverified', answer_version=self.answer.version) for e in items if e.evidence_id not in existing))
        if self.retrieval:
            self.retrieval.known_evidence.update(((e.evidence_id, e) for e in items))

    async def review(self, component, agent, inputs, allowed, is_verification, retrieval_issue):
        if is_verification and inputs.generation_snapshot is not None:
            allowed = merge_evidence(allowed, inputs.generation_snapshot.evidence)
        if retrieval_issue and (not (is_verification and getattr(inputs, 'fact_retrieval_bindings', ()))):
            return (None, retrieval_issue)

        def check(output):
            self.guard_agent_evidence(output, allowed)
            if is_verification and type(output).__name__ == 'PremiseVerificationOutput':
                from services.task_premises_v1 import validate_catalog
                validate_catalog(self.request, output.task_premises)
            if not is_verification and getattr(output, 'prompt_version', None) and output.prompt_version.startswith(('power-domain-review-v1', 'power-domain-review-v2', 'power-domain-review-v3')):
                require(output.engineering_context == self.request.engineering_context, 'Domain review changed engineering inputs')
            validate_review(output, self.answer, self.claims, allowed, is_verification)
        output, issue = await self.invoke(component, agent.run, inputs, check, True, getattr(agent, 'uses_model_adapter', False))
        if output is not None and retrieval_issue:
            from dataclasses import replace
            output = replace(output, execution_issues=output.execution_issues + (self.vd.issues or (retrieval_issue,)))
        return (output, issue)

    async def validate_saved_inputs(self):
        """Validate saved index bindings before running an agent."""
        self.transition(RunState.VALIDATED)
        if self.indexed_reference_ids:
            refs = tuple((e for e in self.evidence if e.evidence_id in self.indexed_reference_ids))

            async def validate_saved(items):
                await self.harness.retriever.validate_evidence(items, self.knowledge_version)
            _, issue = await self.invoke('original_index_validation', validate_saved, refs, lambda _: None)
            if issue:
                self.issues.append(issue)
                raise RequiredRetrievalFailure('Saved original evidence failed frozen-index validation')
            self.bindings = tuple((EvidenceBinding(e.evidence_id, 'index_saved_reference' if e.evidence_id in self.indexed_reference_ids else 'user_reference', 'original_citation', None if self.answer is None else self.answer.version) for e in self.evidence))

    async def generate(self):
        """Retrieve and generate, preserving the original early terminal paths."""
        self.transition(RunState.RETRIEVING)
        self.record('provided_evidence', ExecutionStatus.SUCCEEDED, perf_counter(), 'User references; not index-verified' if self.retrieval else 'Offline evidence only; no RAG call')
        if self.retrieval:
            generated_delivery = await self.retrieve_for(RetrievalPurpose.GENERATION)
            if generated_delivery.issue:
                self.issues.append(generated_delivery.issue)
                raise RequiredRetrievalFailure('Required generation retrieval did not complete')
            from services.generation_query import chinese_query, VERSION as query_version
            if generated_delivery.record.outcome == 'empty' and self.harness.generation_query_converter is not None and self.harness.generation_corpus_english and chinese_query(self.request.question):
                converted, issue = await self.invoke('generation_query_conversion', self.harness.generation_query_converter.run, self.request.question, lambda q: require(type(q) is str and bool(q.strip()), 'Nonempty query required'), True, getattr(self.harness.generation_query_converter, 'uses_model_adapter', False))
                self.record('generation_query_conversion_result', ExecutionStatus.FAILED if issue else ExecutionStatus.SUCCEEDED, perf_counter(), stage_output={'version': query_version, 'original_query': self.request.question, 'converted_query': converted, 'status': 'failed' if issue else 'succeeded', 'corpus_language': 'english', 'first_retrieval_id': generated_delivery.record.retrieval_id})
                if issue:
                    self.issues.append(issue)
                    raise RequiredRetrievalFailure('英文补检查询转换失败；执行未完成，未生成回答')
                generated_delivery = await self.retrieve_for(RetrievalPurpose.GENERATION, converted)
                if generated_delivery.issue:
                    self.issues.append(generated_delivery.issue)
                    raise RequiredRetrievalFailure('英文补检执行失败；未生成回答')
        self.transition(RunState.GENERATING)

        def check_generation(output):
            validate_types(output, GenerationOutput)
            validate_answer(output.answer, self.evidence)
            if output.evidence_snapshot is not None:
                from services.evidence_scope import validate_snapshot
                validate_snapshot(output.evidence_snapshot, output.answer)
                require(output.evidence_snapshot.evidence == self.evidence, 'Generation snapshot must preserve all supplied evidence')
                require(output.evidence_snapshot.knowledge_version == (self.knowledge_version if self.retrieval else None), 'Generation snapshot knowledge version changed')
            for issue in output.execution_issues:
                require(issue.status != ExecutionStatus.SUCCEEDED, 'execution issue cannot be successful')
        self.generated, issue = await self.invoke('generation', self.harness.generation.run, GenerationInput(self.request, self.evidence, self.bindings, self.knowledge_version if self.retrieval else None, self.answer_requirements), check_generation, True, getattr(self.harness.generation, 'uses_model_adapter', False))
        if issue:
            self.issues.append(issue)
            raise RuntimeError(issue.message)
        self.issues.extend(self.generated.execution_issues)
        if self.generated.execution_issues:
            raise RuntimeError('Generation reported execution failure')
        self.answer = self.generated.answer
        self.active_snapshot = self.generated.evidence_snapshot
        self.record('answer_created', ExecutionStatus.SUCCEEDED, perf_counter(), outputs=(f'{self.answer.answer_id}@{self.answer.version}',))
        if not self.generated.substantive_answer:
            from core.models import ProductDecision
            self.reason = '未生成实质回答，主张提取与双审核不适用；' + ('生成阶段认为交付依据不足，未提供有引用的回答' if self.evidence else '当前检索未找到回答所需依据')
            self.decision = ProductDecision(DecisionKind.NEEDS_INFORMATION, (self.reason,), 'product-decision-v1.1', execution_integrity='complete', risk_level='unknown', resolution='unable_to_answer', reason_codes=('NO_SUBSTANTIVE_ANSWER',), classification_basis=('generation-no-answer-v1: generation returned no substantive cited answer',), applicable_checks=tuple(((name, 'not_applicable', '未生成回答，不核验程序拒答模板') for name in ('claim_extraction', 'fact_support', 'domain_review'))))
            self.report = self.make_report(self.decision)
            self.record('review_not_applicable', ExecutionStatus.SUCCEEDED, perf_counter(), self.reason)
            self.transition(RunState.NEEDS_INFORMATION)
            self.generation_only = True
        elif self.generation_only:
            self.reason = 'Draft generated only; no factual or domain audit performed'
            self.transition(RunState.GENERATED)

    async def extract_and_tools(self):
        """Re-extract this answer version and execute bounded scalar checks."""
        self.transition(RunState.EXTRACTING_CLAIMS)

        def check_extraction(output):
            if isinstance(output, ClaimExtractionOutput):
                validate_extraction(output, self.answer)
            else:
                validate_claims(output, self.answer)
        extract = self.harness.extractor.extract
        if hasattr(self.harness.extractor, 'extract_for_task'):
            extract = lambda answer: self.harness.extractor.extract_for_task(answer, self.request)
        extraction, issue = await self.invoke('claim_extraction', extract, self.answer, check_extraction, getattr(self.harness.extractor, 'uses_model_adapter', False), getattr(self.harness.extractor, 'uses_model_adapter', False))
        if issue:
            self.issues.append(issue)
            raise RuntimeError(issue.message)
        self.extracted = extraction if isinstance(extraction, ClaimExtractionOutput) else None
        self.claims = self.extracted.claims if self.extracted is not None else extraction
        self.current_tools = []
        if self.harness.unit_tool is not None:
            from tools.contracts import ToolRequest
            from tools.unit_conversion import requests_for, validate_result
            for payload in requests_for(self.claims, version=self.harness.unit_tool.spec.version):
                if self.tool_calls >= self.budget.max_tool_calls:
                    issue = ExecutionIssue('scalar_unit_conversion', ExecutionStatus.FAILED, 'TOOL_BUDGET_EXHAUSTED', 'Required scalar tool budget exhausted')
                    self.issues.append(issue)
                    self.record('scalar_unit_conversion', issue.status, perf_counter(), issue.message)
                    break
                self.tool_calls += 1
                result, issue = await self.invoke('scalar_unit_conversion', self.harness.unit_tool.execute, ToolRequest(uuid4().hex, self.request.task_id, 'scalar_unit_conversion', 'evidence_verification', payload, min(5.0, self.budget.step_timeout_seconds)), validate_result)
                if issue:
                    self.issues.append(issue)
                else:
                    self.current_tools.append(result)
                    self.tool_results.append(result)
                    self.record('tool_result', result.status, perf_counter(), __import__('json').dumps(__import__('dataclasses').asdict(result)), outputs=(result.result_id,))
                    if result.issue:
                        self.issues.append(result.issue)
        self.record('claims_created', ExecutionStatus.SUCCEEDED, perf_counter(), outputs=tuple((c.claim_id for c in self.claims)))
        if self.extracted is not None:
            import json
            from dataclasses import asdict
            self.record('claim_coverage', ExecutionStatus.SUCCEEDED, perf_counter(), json.dumps(asdict(self.extracted), ensure_ascii=False))

    async def prepare_review(self):
        """Prepare separate purpose-bound inputs with sequential retrieval."""
        self.transition(RunState.VERIFYING)
        original_ids = {eid for c in self.answer.citations for eid in c.evidence_ids}
        self.original_evidence = tuple((e for e in self.evidence if e.evidence_id in original_ids))
        self.v_evidence = self.d_evidence = self.evidence
        self.v_bindings = self.d_bindings = self.bindings
        self.v_retrieval_issue = self.d_retrieval_issue = None
        from harness.source_first_audit_v1 import enabled as source_first_enabled
        if source_first_enabled(self):
            from harness.source_first_audit_v1 import prepare as prepare_source_first
            await prepare_source_first(self)
        elif self.retrieval:
            self.vd = await self.retrieve_for(RetrievalPurpose.VERIFICATION)
            if not self.evidence_only:
                self.dd = await self.retrieve_for(RetrievalPurpose.DOMAIN_REVIEW)
            user_evidence = tuple((e for e in self.request.provided_evidence if e.evidence_id not in self.indexed_reference_ids))
            self.v_evidence = merge_evidence(user_evidence, self.vd.evidence)
            if not self.evidence_only:
                domain_references = user_evidence if getattr(self.harness.domain_review, 'protocol_version', 1) >= 2 else self.request.provided_evidence
                self.d_evidence = merge_evidence(domain_references, self.dd.evidence)
            user_bindings = tuple((b for b in self.bindings if b.origin == 'user_reference'))
            self.v_bindings = user_bindings + self.vd.bindings
            self.v_retrieval_issue = self.vd.issue
            if not self.evidence_only:
                self.d_bindings, self.d_retrieval_issue = (user_bindings + self.dd.bindings, self.dd.issue)
        current_snapshot = self.active_snapshot
        if current_snapshot is not None and current_snapshot.answer_version != self.answer.version:
            current_snapshot = None
        self.v_input = EvidenceVerificationInput(self.request, self.answer, self.claims, self.v_evidence, self.v_bindings, self.knowledge_version if self.retrieval else None, self.original_evidence, current_snapshot)
        self.d_input = PowerDomainReviewInput(self.request, self.answer, self.claims, self.d_evidence, getattr(self.harness.domain_review, 'rule_set_version', 'offline-rules-v1'), self.d_bindings, self.knowledge_version if self.retrieval else None)
        from services.review_inputs import build as build_review_input
        summary = lambda delivery: __import__('json').dumps(__import__('dataclasses').asdict(delivery.record)) if self.retrieval else ''
        self.v_input = build_review_input(self.harness.verification, self.v_input, tool_results=self.current_tools, delivery_summary=summary(self.vd) if self.retrieval else '', fact_retrieval_bindings=self.vd.record.fact_bindings if self.retrieval else ())
        self.d_input = build_review_input(self.harness.domain_review, self.d_input, tool_results=self.current_tools, delivery_summary=summary(self.dd) if self.retrieval and (not self.evidence_only) else '')

    async def review_pair(self):
        """Keep concurrent review ownership, sibling results and cancellation."""
        if self.evidence_only:
            self.verification, issue = await self.review('evidence_verification', self.harness.verification, self.v_input, merge_evidence(self.v_evidence, self.original_evidence), True, self.v_retrieval_issue)
            if issue:
                self.issues.append(issue)
                if getattr(self.harness.verification, 'schema_version', None) in (7, 8):
                    from agents.verification_contract_v7 import execution_incomplete
                    self.verification = execution_incomplete(self.v_input, issue)
                else:
                    self.verification = EvidenceVerificationOutput(self.answer.answer_id, self.answer.version, self.claims, (), (), (issue,))
                self.reason = 'Evidence verification execution incomplete; domain review not run'
                self.transition(RunState.REVIEW_REQUIRED)
            else:
                self.issues.extend(self.verification.execution_issues)
                self.evidence = merge_evidence(self.evidence, self.verification.evidence)
                self.collect_agent_evidence(self.verification.evidence)
                self.reason = 'Extracted claims evidence-reviewed only; all coverage gaps remain unreviewed; no domain review or audit pass'
                self.transition(RunState.REVIEW_REQUIRED if self.verification.execution_issues else RunState.EVIDENCE_REVIEWED)
            return
        # Retrieve sequentially in prepare_review; run the two reviewers against
        # the same immutable answer/claims and retain each completed stage event.
        reviewers = [asyncio.create_task(job) for job in (
            self.review('evidence_verification', self.harness.verification, self.v_input,
                        merge_evidence(self.v_evidence, self.original_evidence),
                        True, self.v_retrieval_issue),
            self.review('power_domain_review', self.harness.domain_review, self.d_input,
                        self.d_evidence, False, self.d_retrieval_issue),
        )]
        try:
            (self.verification, self.v_issue), (self.domain, self.d_issue) = await asyncio.gather(*reviewers)
        except BaseException:
            for reviewer in reviewers:
                reviewer.cancel()
            await asyncio.gather(*reviewers, return_exceptions=True)
            raise
        if self.v_issue:
            if getattr(self.harness.verification, 'schema_version', None) in (7, 8):
                from agents.verification_contract_v7 import execution_incomplete
                self.verification = execution_incomplete(self.v_input, self.v_issue)
            else:
                self.verification = EvidenceVerificationOutput(self.answer.answer_id, self.answer.version, self.claims, (), (), (self.v_issue,))
        if self.d_issue:
            if getattr(self.harness.domain_review, 'rule_set_version', None) == 'power-demo-rules-v1':
                from agents.power_domain_review import execution_incomplete_domain
                self.domain = execution_incomplete_domain(self.d_input, self.d_issue)
            else:
                self.domain = PowerDomainReviewOutput(self.answer.answer_id, self.answer.version, (), (), (self.d_issue,))

    async def merge_and_decide(self):
        """Merge evidence, apply original policy; return whether review ended."""
        from harness.source_first_audit_v1 import enabled as source_first_enabled, supplement
        if source_first_enabled(self):
            await supplement(self)
        if self.retrieval and getattr(self.harness, 'subject_supplement', False) and (not self.v_issue) and (not self.verification.execution_issues):
            from services.audit_subject_query import query as subject_query, VERSION as SUBJECT_QUERY_VERSION
            q = subject_query(self.claims, self.verification.findings)
            if q:
                extra = await self.retrieval.retrieve(RetrievalPurpose.VERIFICATION, self.request, self.answer, self.claims, query_override=q)
                self.record('fact_subject_supplement', extra.record.status, perf_counter(), SUBJECT_QUERY_VERSION + '; ' + q)
                if extra.issue:
                    self.verification = replace(self.verification, execution_issues=self.verification.execution_issues + (extra.issue,))
                elif any((e.evidence_id not in {x.evidence_id for x in self.v_evidence} for e in extra.evidence)):
                    self.v_evidence = merge_evidence(self.v_evidence, extra.evidence)
                    self.v_input = replace(self.v_input, seed_evidence=self.v_evidence, evidence_bindings=self.v_input.evidence_bindings + extra.bindings)
                    second, second_issue = await self.review('evidence_verification', self.harness.verification, self.v_input, merge_evidence(self.v_evidence, self.original_evidence), True, None)
                    if second_issue:
                        self.verification = replace(self.verification, execution_issues=self.verification.execution_issues + (second_issue,))
                    else:
                        self.verification = second
        try:
            self.evidence = merge_evidence(self.evidence, self.verification.evidence)
            self.collect_agent_evidence(self.verification.evidence)
        except ContractError as exc:
            issue = ExecutionIssue('evidence_verification', ExecutionStatus.FAILED, 'OUTPUT_CONTRACT_ERROR', str(exc))
            self.verification = EvidenceVerificationOutput(self.answer.answer_id, self.answer.version, self.claims, (), (), (issue,))
            self.record('evidence_verification_validation', ExecutionStatus.FAILED, perf_counter(), str(exc))
        try:
            self.evidence = merge_evidence(self.evidence, self.domain.evidence)
            unique(self.verification.findings + self.domain.findings, 'finding_id')
            self.collect_agent_evidence(self.domain.evidence)
        except ContractError as exc:
            issue = ExecutionIssue('power_domain_review', ExecutionStatus.FAILED, 'OUTPUT_CONTRACT_ERROR', str(exc))
            self.domain = PowerDomainReviewOutput(self.answer.answer_id, self.answer.version, (), (), (issue,))
            self.record('power_domain_review_validation', ExecutionStatus.FAILED, perf_counter(), str(exc))
        self.issues.extend(self.verification.execution_issues + self.domain.execution_issues)
        self.transition(RunState.DECIDING)
        self.product_policy = getattr(self.harness.policy, 'product_policy', False)
        self.decision = self.harness.policy.decide_context(self.verification, self.domain, self.budget, self.rounds, request=self.request, answer=self.answer, claims=self.claims, extraction=self.extracted, issues=self.issues, retrieval=self.retrieval) if self.product_policy else self.harness.policy.decide(self.verification, self.domain, self.budget, self.rounds)
        if source_first_enabled(self):
            self.decision=replace(self.decision,reasons=self.decision.reasons+('Scope: source fidelity and task completeness; independent external truth and engineering safety not established',),
                classification_basis=('Source-first supplied-evidence judgments; external gap retrieval separately recorded',))
        real_repair = getattr(self.harness.policy, 'allows_bounded_real_revision', False) and getattr(self.harness.revision, 'bounded_real_revision', False) and (self.rounds < 1)
        if not self.product_policy and self.decision.kind in (DecisionKind.PASS, DecisionKind.REVISE) and (getattr(self.harness.verification, 'uses_model_adapter', False) or getattr(self.harness.extractor, 'uses_model_adapter', False)) and (not (self.decision.kind == DecisionKind.REVISE and real_repair)):
            self.decision = AuditDecision(DecisionKind.REVIEW_REQUIRED, ('Model and rule reviews are limited; no engineering feasibility/safety certification',) + self.decision.reasons, 'evidence-local-gate-v1', self.decision.unresolved_finding_ids)
        if not self.product_policy and self.extracted is not None and (self.extracted.uncovered_spans or self.extracted.non_claim_spans):
            self.decision = AuditDecision(self.decision.kind if self.decision.kind == DecisionKind.REVISE and real_repair else DecisionKind.REVIEW_REQUIRED, ('Some answer text is not claim-reviewed; coverage gaps remain unresolved',) + self.decision.reasons, 'coverage-gate-v1', self.decision.unresolved_finding_ids)
        if self.retrieval and (not self.product_policy):
            if any((r.status != ExecutionStatus.SUCCEEDED for r in self.retrieval.records)):
                self.decision = AuditDecision(DecisionKind.REVIEW_REQUIRED, ('Required retrieval did not complete; partial valid evidence retained',), 'retrieval-gate-v1', self.decision.unresolved_finding_ids)
            elif any((r.outcome == 'empty' for r in self.retrieval.records)) and self.decision.kind == DecisionKind.PASS:
                self.decision = AuditDecision(DecisionKind.INSUFFICIENT_EVIDENCE, ('Required retrieval completed with no hits; this is not evidence of a false claim',), 'retrieval-gate-v1', self.decision.unresolved_finding_ids)
        self.report = self.make_report(self.decision)
        self.review_rounds.append(ReviewRound(self.answer, self.extracted, self.verification, self.domain, self.report))
        self.record('audit_policy', ExecutionStatus.SUCCEEDED, perf_counter(), f"{self.decision.kind.value}: {'; '.join(self.decision.reasons)}")
        self.reason = '; '.join(self.decision.reasons)
        if self.decision.kind != DecisionKind.REVISE:
            terminal = {DecisionKind.PASS: RunState.COMPLETED, DecisionKind.REJECT: RunState.REJECTED, DecisionKind.NEEDS_INFORMATION: RunState.NEEDS_INFORMATION, DecisionKind.EXECUTION_INCOMPLETE: RunState.EXECUTION_INCOMPLETE}
            self.transition(terminal.get(self.decision.kind, RunState.REVIEW_REQUIRED))
            return True
        return False

    async def revise(self):
        """Validate a bounded revision; return whether a full re-audit can run."""
        from dataclasses import replace
        if self.rounds >= self.budget.max_revision_rounds:
            raise ContractError('Policy attempted revision beyond limit')
        self.transition(RunState.REVISING)
        revision_input=RevisionInput(self.request,self.answer,self.verification,self.domain,self.evidence,self.decision.reasons,self.bindings,self.knowledge_version if self.retrieval else None)

        def check_revision(output):
            self.guard_agent_evidence(output, self.evidence)
            from agents.contracts import LocalRevisionOutput
            if isinstance(output,LocalRevisionOutput):
                require(output.bound_defects==self.verification.literal_defects,'Local revision changed the source-bound defect catalog')
            validate_revision(output, self.answer, self.evidence, self.verification.findings + self.domain.findings,revision_context=revision_input)
            if getattr(output, 'evidence_snapshot', None) is not None:
                from services.evidence_scope import validate_snapshot
                validate_snapshot(output.evidence_snapshot, output.answer)
                require(output.evidence_snapshot.evidence == self.evidence, 'Revision snapshot changed allowed evidence')
        revised, issue = await self.invoke('revision', self.harness.revision.run, revision_input, check_revision, True, getattr(self.harness.revision, 'uses_model_adapter', False))
        if issue or revised.execution_issues:
            self.issues.extend((issue,) if issue else revised.execution_issues)
            if self.product_policy:
                from dataclasses import replace
                self.decision = replace(self.decision, kind=DecisionKind.EXECUTION_INCOMPLETE, reasons=('Revision execution failed; no completed repair',), execution_integrity='incomplete', risk_level='unknown', reason_codes=('REVISION_EXECUTION_FAILED',))
            else:
                self.decision = AuditDecision(DecisionKind.REVIEW_REQUIRED, ('Revision execution failed',), 'offline-policy-v1', self.decision.unresolved_finding_ids)
            self.report = self.make_report(self.decision)
            self.reason = self.decision.reasons[0]
            self.transition(RunState.EXECUTION_INCOMPLETE if self.product_policy else RunState.REVIEW_REQUIRED)
            return False
        from agents.contracts import LocalRevisionOutput
        if isinstance(revised,LocalRevisionOutput) and not revised.replacements:
            self.rounds += 1
            self.revision_outputs.append(revised)
            self.decision=replace(self.decision,kind=DecisionKind.REVIEW_REQUIRED,reasons=('Local revision retained the original answer; unresolved findings remain, attempt exhausted',),reason_codes=('LOCAL_REVISION_NO_CHANGE',))
            self.report=self.make_report(self.decision)
            self.reason=self.decision.reasons[0]
            self.transition(RunState.REVIEW_REQUIRED)
            return False
        self.answer = revised.answer
        self.revision_outputs.append(revised)
        self.active_snapshot = revised.evidence_snapshot
        self.evidence = merge_evidence(self.evidence, revised.evidence)
        self.collect_agent_evidence(revised.evidence)
        self.record('revision_changes', ExecutionStatus.SUCCEEDED, perf_counter(), '; '.join((change.description for change in revised.changes)), outputs=(f'{self.answer.answer_id}@{self.answer.version}',))
        self.rounds += 1
        self.verification = self.domain = None
        self.report = None
        return True

    async def run_stages(self):
        """Original sequential route, retained as the default implementation."""
        await self.validate_saved_inputs()
        if self.request.mode == TaskMode.QUESTION_ANSWER:
            await self.generate()
        while not self.generation_only:
            await self.extract_and_tools()
            await self.prepare_review()
            await self.review_pair()
            if self.evidence_only:
                break
            if await self.merge_and_decide():
                break
            if not await self.revise():
                break

    async def run(self, *, driver=None):
        """One driver inside the existing exception, registry and result boundary."""
        try:
            if driver is None:
                await self.run_stages()
            else:
                await driver(self)
        except HarnessObserverError:
            raise
        except RequiredRetrievalFailure as exc:
            self.reason = str(exc)
            self.transition(RunState.EXECUTION_INCOMPLETE if any((i.component == 'generation_query_conversion' for i in self.issues)) else RunState.REVIEW_REQUIRED)
        except asyncio.CancelledError:
            self.reason = 'Run cancelled'
            self.issues.append(ExecutionIssue('harness', ExecutionStatus.CANCELLED, 'CANCELLED', self.reason))
            self.transition(RunState.CANCELLED)
        except Exception as exc:
            self.reason = f'{type(exc).__name__}: {exc}'
            if not self.issues:
                self.issues.append(ExecutionIssue('harness', ExecutionStatus.FAILED, 'EXECUTION_FAILURE', self.reason))
            self.transition(RunState.FAILED)
        finally:
            self.harness._runs.pop(self.run_id, None)
        self.record('termination', ExecutionStatus.CANCELLED if self.state == RunState.CANCELLED else ExecutionStatus.FAILED if self.state == RunState.FAILED else ExecutionStatus.SUCCEEDED, perf_counter(), self.reason)
        result = HarnessResult(
            self.run_id, self.state, RunTrace(self.run_id, self.request.task_id, tuple(self.events)),
            self.report, self.reason, tuple(self.issues), self.evidence, self.bindings,
            () if self.retrieval is None else tuple(self.retrieval.records),
            max(0, int((perf_counter() - self.run_started) * 1000)), self.answer, self.generated,
            tuple(self.model_budget.records), self.extracted, self.verification, self.domain,
            tuple(self.review_rounds), tuple(self.revision_outputs),
        )
        if self.harness.unit_tool is not None:
            from harness.contracts import ToolHarnessResult
            from dataclasses import fields
            result = ToolHarnessResult(**{f.name: getattr(result, f.name) for f in fields(result)}, tool_results=tuple(self.tool_results))
        return result
