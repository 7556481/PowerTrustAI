"""Public Harness lifecycle and the original sequential stage driver."""
import asyncio

from core.validation import InputError
from harness.contracts import RetrievalSettings
from harness.policy import DeterministicAuditPolicy
from harness.retrieval import validate_settings
from harness.execution import RunExecution, RequiredRetrievalFailure, HarnessObserverError


class OfflineHarness:
    def __init__(self, generation, verification, domain_review, revision, extractor, policy=None,
                 retriever=None, retrieval_settings=None, unit_tool=None, observer=None,
                 generation_query_converter=None, generation_corpus_english=False):
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
        execution = RunExecution(
            self, request, budget, knowledge_version=knowledge_version,
            generation_only=generation_only, answer_requirements=answer_requirements,
            evidence_only=evidence_only, indexed_reference_ids=indexed_reference_ids,
            generation_snapshot=generation_snapshot, run_id=run_id,
        )
        return await execution.run()
