"""Retriever contract adapter; no factual verification is performed."""
import json
from contextvars import copy_context
from rag.timing import span,timed

from core.validation import InputError, require, validate_types
from rag.bm25 import SCORING_METHOD, score_corpus
from rag.contracts import RetrievalHit, RetrievalRequest, RetrievalResult


class BM25Retriever:
    def __init__(self, store):
        self.store = store

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        return self._retrieve(request)

    async def validate_result(self, request, result):
        self._validate_result(request, result)

    def _validate_result(self, request, result):
        validate_types(result, RetrievalResult)
        require(result == self._retrieve(request), "Retrieved evidence/hits/context differ from fixed index")

    def _retrieve(self, request):
        validate_types(request, RetrievalRequest)
        if not request.knowledge_version.strip() or not request.scenario_id.strip() or request.max_results < 1:
            raise InputError("Fixed knowledge_version, scenario_id and positive max_results required")
        rows = self.store.rows(request.knowledge_version)
        scores = score_corpus(request.query, [tuple(json.loads(row["tokens"])) for row in rows])
        # Stable tie-break independent of insertion time and SQL row order.
        ranked = sorted(((row, score) for row, score in zip(rows, scores) if score > 0),
                        key=lambda pair: (-pair[1], pair[0]["document_id"], pair[0]["version"], pair[0]["ordinal"], pair[0]["fragment_id"]))[:request.max_results]
        evidence, hits = [], []
        for rank, (row, score) in enumerate(ranked, 1):
            item = self.store.evidence(row["fragment_id"], request.knowledge_version)
            evidence.append(item)
            hits.append(RetrievalHit(item.evidence_id, row["fragment_id"], rank, score, SCORING_METHOD))
        context = None
        if request.context_options is not None:
            from rag.context import read_adjacent_context
            context = read_adjacent_context(self.store, tuple(evidence), request.knowledge_version, request.context_options)
        return RetrievalResult(tuple(evidence), request.knowledge_version, hits=tuple(hits), context=context)


class AsyncSQLiteBM25Retriever:
    """One worker, thread-owned read-only connections, no unbounded job queue.

    Async cancellation stops awaiting, not the running Python/SQLite worker.
    A timed-out job remains busy until the actual worker completes.
    """
    def __init__(self, path,*,execution_profile='baseline_v1'):
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        self.path = str(Path(path).resolve())
        if execution_profile not in ('baseline_v1','topic_v3_rank_v1','topic_v4_subject_v1','topic_v5_grammar_v1'):raise ValueError('Unknown retrieval execution profile')
        self.execution_profile=execution_profile
        from rag.chinese_terms import TOPIC_VERSION
        from rag.rank_cache import RankCache
        self.query_version=None if execution_profile=='baseline_v1' else ('topic-subject-grammar-bm25-v2' if execution_profile=='topic_v5_grammar_v1' else 'topic-subject-and-bm25-v1' if execution_profile=='topic_v4_subject_v1' else TOPIC_VERSION)
        self.rank_cache=None if execution_profile=='baseline_v1' else RankCache()
        self.cache_identity=('bm25',execution_profile)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="powertrust-retrieval")
        self._active = None
        self._closed = False
        # One worker-local certificate for the immediately preceding corpus
        # query. This is not a model judgment or a cross-answer query cache.
        self._corpus_certificate = None

    @timed('retriever_worker')
    def _work(self, request, result, validate):
        from rag.storage import KnowledgeStore
        with KnowledgeStore(self.path, readonly=True, validated_pdf_cache=True) as store:
            if validate == "saved_evidence":
                for evidence in result:
                    require(evidence.provenance is not None and evidence.provenance.knowledge_version == request,
                            "Saved evidence snapshot mismatch")
                    require(store.verify_evidence(evidence) == evidence, "Saved evidence differs from fixed index")
                return None
            from rag.corpus_index import seal,CorpusRetriever
            retriever = CorpusRetriever(store,query_version=self.query_version,rank_cache=self.rank_cache) if seal(store,request.knowledge_version) is not None else BM25Retriever(store)
            if validate:
                with span('result_validation') as measured:
                    measured['certificate_hit']=False
                    measured['_fts_mode']=isinstance(retriever,CorpusRetriever)
                    measured['ranking_replay_attempted']=False
                    if isinstance(retriever, CorpusRetriever) and self._corpus_certificate is not None:
                        previous_request, previous_result, previous_profile = self._corpus_certificate
                        if request == previous_request and previous_profile==self.execution_profile:
                            measured['certificate_hit']=True
                            validate_types(result, RetrievalResult)
                            require(result == previous_result, "Retrieved evidence/hits/context differ from certified query")
                            # seal above rechecks the immutable file stamp/identity;
                            # every delivered body still receives strict hit replay.
                            bodies = result.evidence + (() if result.context is None else tuple(x.evidence for x in result.context.items))
                            for evidence in bodies:
                                require(store.verify_evidence(evidence) == evidence, "Certified evidence differs from fixed index")
                            return None
                    measured['ranking_replay_attempted']=True
                    retriever._validate_result(request, result)
                    return None
            self._corpus_certificate = None
            retrieved = retriever._retrieve(request)
            if isinstance(retriever, CorpusRetriever):
                self._corpus_certificate = (request, retrieved,self.execution_profile)
            return retrieved

    @timed('retriever_wait')
    async def _submit(self, request, result=None, validate=False):
        import asyncio
        if self._closed:
            raise RuntimeError("Retriever is closed")
        if self._active is not None and not self._active.done():
            raise RuntimeError("Retriever worker busy; cancelled/timed-out work may still be running")
        context=copy_context()
        self._active = self._executor.submit(context.run,self._work, request, result, validate)
        future = asyncio.wrap_future(self._active)
        # Consume exceptions even if the waiter is cancelled while the worker runs.
        future.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        return await asyncio.shield(future)

    async def retrieve(self, request):
        return await self._submit(request)

    async def validate_result(self, request, result):
        await self._submit(request, result, True)

    async def validate_evidence(self, evidence, knowledge_version):
        """Replay saved citations on the same thread-owned frozen index, no search."""
        await self._submit(knowledge_version, evidence, "saved_evidence")

    def close(self):
        self._closed = True
        self._corpus_certificate = None
        if self.rank_cache is not None:self.rank_cache.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
