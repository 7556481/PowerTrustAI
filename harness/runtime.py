"""Public Harness lifecycle and the original sequential stage driver."""

from core.validation import InputError
from harness.contracts import RetrievalSettings
from harness.policy import DeterministicAuditPolicy
from harness.retrieval import validate_settings
from harness.execution import RunExecution, RequiredRetrievalFailure, HarnessObserverError


class OfflineHarness:
    def __init__(self, generation, verification, domain_review, revision, extractor, policy=None,
                 retriever=None, retrieval_settings=None, unit_tool=None, observer=None,
                 generation_query_converter=None, generation_corpus_english=False, *,
                 execution_path="sequential", audit_strategy="baseline"):
        if audit_strategy not in ('baseline', 'source_first_audit_v1'):
            raise InputError('Unknown audit strategy')
        if audit_strategy != 'baseline' and not getattr(verification,'source_first_review',False):
            raise InputError('Source-first strategy requires explicit paired reviewer')
        self.audit_strategy = audit_strategy
        if execution_path not in ("sequential", "langgraph_v1"):
            raise InputError("Unknown Harness execution path")
        self.execution_path = execution_path
        self.generation = generation
        self.verification = verification
        self.domain_review = domain_review
        self.revision = revision
        self.extractor = extractor
        self.unit_tool = unit_tool
        self.observer = observer
        self.generation_query_converter = generation_query_converter
        self.generation_corpus_english = generation_corpus_english
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
        if self.execution_path not in ("sequential", "langgraph_v1"):
            raise InputError("Unknown Harness execution path")
        driver = None
        if self.execution_path == "langgraph_v1":
            # Optional dependencies are never imported by the default path.
            try:
                from harness.graph_runtime_v1 import run_graph, validate_versions
            except ImportError as exc:
                raise InputError("Optional LangGraph dependencies unavailable; install requirements-langgraph.lock.txt") from exc
            validate_versions()
            driver = run_graph
        execution = RunExecution(
            self, request, budget, knowledge_version=knowledge_version,
            generation_only=generation_only, answer_requirements=answer_requirements,
            evidence_only=evidence_only, indexed_reference_ids=indexed_reference_ids,
            generation_snapshot=generation_snapshot, run_id=run_id,
        )
        return await execution.run(driver=driver)
