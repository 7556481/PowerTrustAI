"""Per-run retrieval accounting used by the existing Harness, not a scheduler."""
import asyncio
from dataclasses import dataclass, replace
from time import perf_counter
from uuid import uuid4
from rag.timing import bind_request,reset_request

from core.models import EvidenceBinding, ExecutionIssue, ExecutionStatus
from core.validation import ContractError, InputError, merge_evidence, require, validate_types
from harness.contracts import RetrievalRecord, RetrievalSettings, RetrievalRequestOptions
from rag.contracts import ContextOptions, RetrievalRequest, RetrievalResult


QUERY_METHOD = "deterministic-question-shared-claims-scenario-v1"


class ReportedRetrievalFailure(RuntimeError):
    def __init__(self, issue):
        super().__init__(issue.message)
        self.status = issue.status


def query_for(purpose, request, claims):
    if purpose.value == "generation":
        return request.question
    claim_text = "\n".join(c.text for c in claims)
    if purpose.value == "verification":
        return claim_text
    return "\n".join((request.question, claim_text, request.scenario_id,
                      "engineering prerequisites constraints operating limits applicability"))


def validate_settings(settings):
    try:
        validate_types(settings, RetrievalSettings)
        require(settings.max_results > 0, "max_results must be positive")
        require(settings.fact_strategy in ('aggregate', 'per_claim_v1'), 'Unknown fact retrieval strategy')
        options = settings.context_options
        if options:
            require(options.max_chars >= 0 and options.max_fragments >= 0 and 0 <= options.depth <= 4,
                    "invalid retrieval context limits")
            require(options.priority in ("storage_order", "cross_page_next_first"),
                    "invalid retrieval context priority")
    except ContractError as exc:
        raise InputError(str(exc)) from exc


@dataclass(frozen=True)
class Delivery:
    evidence: tuple
    bindings: tuple
    issue: ExecutionIssue | None
    record: RetrievalRecord
    issues: tuple = ()


class RetrievalSession:
    def __init__(self, retriever, knowledge_version, settings, budget, deadline, user_evidence, validated_index_ids=()):
        self.retriever, self.knowledge_version, self.settings = retriever, knowledge_version, settings
        self.budget, self.deadline = budget, deadline
        self.user_ids = {e.evidence_id for e in user_evidence} - set(validated_index_ids)
        self.known_evidence = {e.evidence_id: e for e in user_evidence}
        self.calls = self.chars = 0
        self.records = []
        self.query_cache = {}
        self.fact_delivered = set()

    async def retrieve(self, purpose, request, answer, claims, *, query_override=None, fact_query=False):
        started, rid = perf_counter(), uuid4().hex
        retrieval_request=None
        version = None if answer is None else answer.version
        query = query_for(purpose, request, claims) if query_override is None else query_override
        reused = None
        result, evidence, bindings, omitted = None, (), (), []
        issue, outcome, status, offered, reason = None, "failed", ExecutionStatus.FAILED, 0, ""
        accepted = 0
        omission_reasons = []
        timing_token=bind_request(rid,version,purpose.value)
        try:
            remaining = self.deadline - started
            if remaining <= 0:
                raise TimeoutError("Total run duration exhausted before retrieval")
            if self.chars >= self.budget.max_retrieval_chars_total or self.budget.max_retrieval_chars_per_call == 0:
                outcome = "budget_exhausted"
                raise RuntimeError("Retrieval evidence character budget exhausted")
            context = self.settings.context_options
            if context:
                context = ContextOptions(min(context.max_chars, self.budget.max_retrieval_chars_per_call,
                                             self.budget.max_retrieval_chars_total - self.chars),
                                         context.max_fragments, context.depth, context.allow_cross_page)
                context = ContextOptions(context.max_chars, context.max_fragments, context.depth,
                                         context.allow_cross_page, self.settings.context_options.priority)
            retrieval_request = RetrievalRequest(query, request.scenario_id, purpose, self.knowledge_version,
                                                 self.settings.max_results, context)
            identity=getattr(self.retriever,'cache_identity',('bm25',))
            cache_key = (self.knowledge_version, identity, query, self.settings.max_results, context)
            cached = self.query_cache.get(cache_key) if fact_query else None
            if cached is None:
                if self.calls >= self.budget.max_retrieval_calls:
                    outcome = 'budget_exhausted'
                    raise RuntimeError('Retrieval call budget exhausted')
                self.calls += 1

            async def work():
                output = cached[0] if cached else await self.retriever.retrieve(retrieval_request)
                validate_types(output, RetrievalResult)
                require(output.knowledge_version == self.knowledge_version, "Retrieved snapshot mismatch")
                for reported in output.execution_issues:
                    require(reported.status != ExecutionStatus.SUCCEEDED, "Execution issue cannot be successful")
                if output.execution_issues:
                    raise ReportedRetrievalFailure(output.execution_issues[0])
                core = merge_evidence(output.evidence)
                extra = () if output.context is None else tuple(i.evidence for i in output.context.items)
                merge_evidence(core, extra)
                require(not self.user_ids.intersection(e.evidence_id for e in core + extra),
                        "Index evidence ID collides with user reference; cannot relabel user evidence")
                merge_evidence(tuple(self.known_evidence.values()), core, extra)
                require(tuple(h.evidence_id for h in output.hits) == tuple(e.evidence_id for e in core),
                        "Hit and core evidence IDs mismatch")
                require(tuple(h.rank for h in output.hits) == tuple(range(1, len(core) + 1)), "Invalid hit ranks")
                for e, h in zip(core, output.hits):
                    require(e.provenance is not None and e.provenance.knowledge_version == self.knowledge_version,
                            "Index evidence lacks frozen provenance")
                    require(e.provenance.fragment_id == h.fragment_id and h.score > 0 and bool(h.scoring_method),
                            "Invalid hit metadata")
                # The index adapter replays the fixed deterministic retrieval, including
                # raw text, hashes, spans, hit ranks/scores and mechanical context links.
                await self.retriever.validate_result(retrieval_request, output)
                return output

            result = await asyncio.wait_for(work(), min(self.budget.step_timeout_seconds, remaining))
            if fact_query:
                reused = cached[1] if cached else None
                self.query_cache.setdefault(cache_key, (result, rid))
            extras = () if result.context is None else result.context.items
            offered = sum(len(e.text) for e in result.evidence) + sum(len(i.evidence.text) for i in extras)
            capacity = min(self.budget.max_retrieval_chars_per_call,
                           self.budget.max_retrieval_chars_total - self.chars)
            chosen, core_ids = [], set()
            charged = 0
            for e in result.evidence:
                cost = 0 if fact_query and (version, e.evidence_id) in self.fact_delivered else len(e.text)
                if cost <= capacity:
                    chosen.append(e)
                    core_ids.add(e.evidence_id)
                    capacity -= cost
                    charged += cost
                    bindings += (EvidenceBinding(e.evidence_id, "index_core_hit", purpose.value, version, rid),)
                else:
                    omitted.append(e.evidence_id)
                    omission_reasons.append((e.evidence_id, 'core_fragment_exceeds_delivery_capacity'))
            core_omitted = bool(omitted)
            for item in extras:
                e = item.evidence
                linked = tuple(link.core_evidence_id for link in item.links if link.core_evidence_id in core_ids)
                cost = 0 if fact_query and (version, e.evidence_id) in self.fact_delivered else len(e.text)
                if linked and cost <= capacity:
                    chosen.append(e)
                    capacity -= cost
                    charged += cost
                    bindings += (EvidenceBinding(e.evidence_id, "index_adjacent_context", purpose.value,
                                                 version, rid, linked),)
                else:
                    omitted.append(e.evidence_id)
                    omission_reasons.append((e.evidence_id, 'adjacent_fragment_exceeds_delivery_capacity' if linked else 'linked_core_not_delivered'))
            evidence = tuple(chosen)
            self.known_evidence.update((e.evidence_id, e) for e in evidence)
            accepted = sum(len(e.text) for e in evidence)
            self.chars += charged
            if fact_query:
                self.fact_delivered.update((version,e.evidence_id) for e in evidence)
            if core_omitted:
                outcome = "budget_exhausted"
                raise RuntimeError("Evidence character budget omitted required core hits; partial evidence retained")
            status = ExecutionStatus.SUCCEEDED
            outcome = "hits" if result.evidence else "empty"
            reason = "Validated against frozen index; relevance is not factual support"
        except asyncio.CancelledError:
            status, outcome, reason = ExecutionStatus.CANCELLED, "cancelled", "Retrieval waiter cancelled"
            raise
        except Exception as exc:
            status = getattr(exc, "status", ExecutionStatus.TIMED_OUT if isinstance(exc, TimeoutError) else ExecutionStatus.FAILED)
            if status == ExecutionStatus.TIMED_OUT:
                outcome = "timed_out"
            elif status == ExecutionStatus.CANCELLED:
                outcome = "cancelled"
            code = ("RETRIEVAL_BUDGET_EXHAUSTED" if outcome == "budget_exhausted" else
                    "RETRIEVAL_TIMEOUT" if status == ExecutionStatus.TIMED_OUT else
                    "RETRIEVAL_CANCELLED" if status == ExecutionStatus.CANCELLED else
                    "RETRIEVAL_CONTRACT_ERROR" if isinstance(exc, ContractError) else "RETRIEVAL_FAILURE")
            reason = f"{type(exc).__name__}: {exc}"
            issue = ExecutionIssue("retrieval_" + purpose.value, status, code, reason)
        finally:
            record = RetrievalRecord(rid, purpose.value, query, QUERY_METHOD, version, self.knowledge_version,
                status, outcome, () if result is None else result.hits,
                tuple(b.evidence_id for b in bindings if b.origin == "index_core_hit"),
                tuple(b.evidence_id for b in bindings if b.origin == "index_adjacent_context"),
                tuple(omitted), offered, accepted, self.chars, self.calls,
                max(0, int((perf_counter() - started) * 1000)), reason,
                () if result is None or result.context is None else result.context.omitted,
                None if answer is None else answer.answer_id, reused,
                omission_reasons=tuple(omission_reasons), offered_context_links=() if result is None or result.context is None else
                tuple((item.evidence.evidence_id, tuple(link.core_evidence_id for link in item.links)) for item in result.context.items),
                request_options=None if retrieval_request is None else RetrievalRequestOptions(retrieval_request.scenario_id,retrieval_request.max_results,retrieval_request.context_options,getattr(self.retriever,'execution_profile','baseline_v1')))
            self.records.append(record)
            reset_request(timing_token)
        return Delivery(evidence, bindings, issue, record)
