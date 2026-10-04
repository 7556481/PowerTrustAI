"""synthetic_fixture only: program contracts, not real retrieval accuracy."""
import asyncio
from dataclasses import replace
import math
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.validation import ContractError, InputError
from rag.contracts import ContextOptions, RetrievalPurpose, RetrievalRequest
from rag.retriever import BM25Retriever
from rag.semantic import VectorIndex, SemanticRetriever, AsyncSQLiteSemanticRetriever, profile_id, fuse_ranks, packed_vector
from rag.storage import KnowledgeStore, SourceMetadata


class FixtureEncoder:
    def __init__(self, version="synthetic-v1"):
        self.profile = {"model_id": "synthetic_fixture", "revision": version, "dimension": 3,
                        "normalization": "L2", "metric": "cosine-dot"}
        self.fail = False

    def encode(self, texts, kind):
        if self.fail:
            raise RuntimeError("synthetic encoder failure")
        result = []
        for text in texts:
            text = text.casefold()
            v = (1.0 if "voltage" in text or "电压" in text else 0.0,
                 1.0 if "reactive" in text or "无功" in text else 0.0, 0.1)
            norm = math.sqrt(sum(x*x for x in v))
            result.append(tuple(x/norm for x in v))
        return result


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db, self.vec = self.root / "source.db", self.root / "vectors.db"
        self.store = KnowledgeStore(self.db)
        self.path = self.root / "synthetic.md"
        self.path.write_text("# synthetic_fixture\n\nVoltage constraints apply only under stated conditions.\n\nReactive capability depends on operating conditions.\n", encoding="utf-8")
        self.first = self.store.ingest(self.path, "fixture", SourceMetadata(source_type="synthetic_fixture"))
        self.kv = self.first.knowledge_version
        self.encoder = FixtureEncoder()
        self.index = VectorIndex(self.vec)
        self.index.build(self.store, self.kv, self.encoder)

    def tearDown(self):
        self.index.close()
        self.store.close()
        self.tmp.cleanup()

    def req(self, query="电压", kv=None, context=None):
        return RetrievalRequest(query, "synthetic_fixture", RetrievalPurpose.VERIFICATION, kv or self.kv, 3, context)

    def run_query(self, req=None, mode="dense"):
        return asyncio.run(SemanticRetriever(self.store, self.index, self.encoder, mode=mode).retrieve(req or self.req()))

    def test_chinese_query_preserves_english_raw_and_provenance(self):
        result = self.run_query()
        self.assertIn("Voltage", result.evidence[0].text)
        self.assertEqual(self.store.verify_evidence(result.evidence[0]), result.evidence[0])
        self.assertIn("Dense-cosine-v1", result.hits[0].scoring_method)

    def test_bm25_is_original_no_embedding_needed(self):
        self.encoder.fail = True
        request = self.req("voltage")
        self.assertEqual(self.run_query(request, "bm25"), asyncio.run(BM25Retriever(self.store).retrieve(request)))

    def test_hybrid_versioned_relevance_not_support(self):
        result = self.run_query(self.req("reactive"), "hybrid")
        self.assertIn("Reactive", result.evidence[0].text)
        self.assertIn("RRF-v1", result.hits[0].scoring_method)
        self.assertFalse(hasattr(result.hits[0], "supported"))

    def test_old_snapshot_before_topk_and_after_update(self):
        old = self.run_query()
        self.path.write_text("# synthetic_fixture\n\nVoltage new and unrelated changed evidence.\n", encoding="utf-8")
        new = self.store.ingest(self.path, "fixture", SourceMetadata(source_type="synthetic_fixture"), update=True)
        self.index.build(self.store, new.knowledge_version, self.encoder)
        self.assertEqual(old, self.run_query())
        latest = self.run_query(self.req(kv=new.knowledge_version))
        self.assertNotEqual(old.evidence[0].source_version, latest.evidence[0].source_version)
        self.assertTrue(all(e.provenance.knowledge_version == new.knowledge_version for e in latest.evidence))

    def test_missing_snapshot_refused_not_postfiltered(self):
        self.path.write_text("# synthetic_fixture\n\nUpdated voltage\n", encoding="utf-8")
        new = self.store.ingest(self.path, "fixture", SourceMetadata(source_type="synthetic_fixture"), update=True)
        with self.assertRaisesRegex(ContractError, "No complete vector"):
            self.run_query(self.req(kv=new.knowledge_version))

    def test_changed_model_requires_own_index(self):
        encoder = FixtureEncoder("synthetic-v2")
        with self.assertRaises(ContractError):
            asyncio.run(SemanticRetriever(self.store, self.index, encoder).retrieve(self.req()))
        self.index.build(self.store, self.kv, encoder)
        self.assertNotEqual(profile_id(encoder), profile_id(self.encoder))
        self.assertEqual(self.run_query().evidence, asyncio.run(SemanticRetriever(self.store, self.index, encoder).retrieve(self.req())).evidence)

    def test_incomplete_index_rejected(self):
        with self.index.connection:
            self.index.connection.execute("DELETE FROM vectors WHERE fragment_id=(SELECT fragment_id FROM vectors LIMIT 1)")
        with self.assertRaisesRegex(ContractError, "Incomplete"):
            self.run_query()

    def test_vector_corruption_rejected(self):
        with self.index.connection:
            self.index.connection.execute("UPDATE vectors SET vector=zeroblob(length(vector))")
        with self.assertRaisesRegex(ContractError, "integrity"):
            self.run_query()

    def test_source_representation_change_rejected(self):
        with self.store.connection:
            self.store.connection.execute("UPDATE fragments SET search_text='corrupted'")
        with self.assertRaisesRegex(ContractError, "source/split"):
            self.run_query()

    def test_build_idempotent(self):
        self.assertTrue(self.index.build(self.store, self.kv, self.encoder)["unchanged"])

    def test_failed_build_does_not_damage_valid_index(self):
        changed = FixtureEncoder("failure-v2")
        changed.fail = True
        before = self.run_query()
        with self.assertRaises(RuntimeError):
            self.index.build(self.store, self.kv, changed)
        self.assertEqual(before, self.run_query())
        self.assertEqual(self.index.connection.execute("SELECT count(*) FROM manifests").fetchone()[0], 1)

    def test_transaction_failure_rolls_back(self):
        self.index.connection.execute("CREATE TRIGGER fail_new BEFORE INSERT ON vectors BEGIN SELECT RAISE(ABORT,'synthetic transaction failure'); END")
        with self.assertRaises(Exception):
            self.index.build(self.store, self.kv, FixtureEncoder("failure-v2"))
        self.assertEqual(self.index.connection.execute("SELECT count(*) FROM manifests").fetchone()[0], 1)
        self.run_query()

    def test_empty_query_and_lexical_no_hit(self):
        self.assertFalse(self.run_query(self.req(" ")).evidence)
        self.assertFalse(self.run_query(self.req("zzzzunmatched"), "bm25").evidence)

    def test_context_uses_existing_ids_and_backtrace(self):
        result = self.run_query(self.req(context=ContextOptions()))
        self.assertIsNotNone(result.context)
        for item in result.context.items:
            self.store.verify_evidence(item.evidence)
            self.assertEqual(item.origin, "adjacent_context_not_retrieval_hit")

    def test_tampered_result_rejected(self):
        retriever = SemanticRetriever(self.store, self.index, self.encoder)
        result = self.run_query()
        bad = replace(result, evidence=(replace(result.evidence[0], text="tampered"),))
        with self.assertRaises(ContractError):
            asyncio.run(retriever.validate_result(self.req(), bad))

    def test_async_connections_are_worker_owned(self):
        async def run():
            with AsyncSQLiteSemanticRetriever(self.db, self.vec, self.encoder, mode="hybrid") as retriever:
                value = await retriever.retrieve(self.req())
                await retriever.validate_result(self.req(), value)
                await retriever.validate_evidence(value.evidence, self.kv)
                return value
        self.assertTrue(asyncio.run(run()).evidence)

    def test_rrf_uses_ranks_not_incompatible_scores(self):
        scores = fuse_ranks([(0, 1000), (1, .01)], [(1, .99), (0, .8)])
        self.assertAlmostEqual(scores[0], 1/61 + 1/62)
        self.assertEqual(scores[0], scores[1])

    def test_vector_dimension_normalization_nonfinite(self):
        for vector in ((1, 0), (float("nan"), 0, 0), (2, 0, 0)):
            with self.assertRaises(ContractError):
                packed_vector(vector, 3)

    def test_invalid_mode(self):
        with self.assertRaises(InputError):
            SemanticRetriever(self.store, self.index, self.encoder, mode="reranker")

    def test_invalid_request(self):
        with self.assertRaises(InputError):
            self.run_query(replace(self.req(), max_results=0))

    def test_stable_ties(self):
        first = self.run_query(self.req("irrelevant"))
        self.assertEqual(first, self.run_query(self.req("irrelevant")))

    def test_foreign_fragment_in_index_is_not_silently_filtered(self):
        with self.index.connection:
            self.index.connection.execute("INSERT INTO vectors SELECT profile_id,knowledge_version,'foreign',vector,sha256 FROM vectors LIMIT 1")
        with self.assertRaisesRegex(ContractError, "foreign-fragment"):
            self.run_query()

    def test_nonpositive_cosine_is_not_shifted_into_a_hit(self):
        # Opposite normalized vectors remain valid index records, but cannot be
        # returned as positive Harness hits. This is relevance, not contradiction.
        import struct
        from rag.storage import digest
        for row in self.index.connection.execute("SELECT fragment_id,vector FROM vectors").fetchall():
            vec = struct.unpack("<fff", row["vector"])
            blob = struct.pack("<fff", *(-x for x in vec))
            with self.index.connection:
                self.index.connection.execute("UPDATE vectors SET vector=?,sha256=? WHERE fragment_id=?", (blob,digest(blob),row["fragment_id"]))
        self.assertFalse(self.run_query().hits)

    def test_harness_injection_uses_existing_three_purposes(self):
        from agents.fakes import (FakeConfig, FakeGenerationAgent, FakeEvidenceVerificationAgent,
            FakePowerDomainReviewAgent, FakeRevisionAgent, FakeClaimExtractor)
        from core.models import TaskRequest, TaskMode
        from harness.runtime import OfflineHarness
        from harness.contracts import RetrievalSettings, RunBudget
        config = FakeConfig(text="Voltage constraints")
        async def run():
            with AsyncSQLiteSemanticRetriever(self.db, self.vec, self.encoder, mode="hybrid") as retriever:
                harness = OfflineHarness(FakeGenerationAgent(config), FakeEvidenceVerificationAgent(config),
                    FakePowerDomainReviewAgent(config), FakeRevisionAgent(), FakeClaimExtractor(),
                    retriever=retriever, retrieval_settings=RetrievalSettings(max_results=2))
                return await harness.run(TaskRequest("synthetic", TaskMode.QUESTION_ANSWER, "synthetic_fixture", "Voltage constraints"),
                    RunBudget(), knowledge_version=self.kv)
        value = asyncio.run(run())
        self.assertEqual([r.purpose for r in value.retrieval_records], ["generation", "verification", "domain_review"])
        self.assertTrue(all(r.outcome == "hits" for r in value.retrieval_records))
        self.assertTrue(all(r.knowledge_version == self.kv for r in value.retrieval_records))

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "optional PDF dependency absent")
    def test_splitter_change_is_new_index_and_old_snapshot_survives(self):
        from tests.pdf_fixtures import make_pdf
        pdf = self.root / "synthetic.pdf"
        pdf.write_bytes(make_pdf(["Voltage synthetic fixture.\n" * 40]))
        first = self.store.ingest(pdf, "pdf", SourceMetadata(source_type="synthetic_fixture"))
        a = self.store.derive_pdf("pdf", first.knowledge_version, max_chars=200)
        self.index.build(self.store, a.knowledge_version, self.encoder)
        before = self.run_query(self.req(kv=a.knowledge_version))
        b = self.store.derive_pdf("pdf", a.knowledge_version, max_chars=100)
        with self.assertRaises(ContractError):
            self.run_query(self.req(kv=b.knowledge_version))
        self.index.build(self.store, b.knowledge_version, self.encoder)
        self.assertEqual(before, self.run_query(self.req(kv=a.knowledge_version)))


class EncodingWindowTests(unittest.TestCase):
    def setUp(self):
        from rag.embedding import E5ONNXEncoder
        from types import SimpleNamespace
        class Tokenizer:
            def encode(self, text, **kwargs):
                prefix = [10, 11]
                remainder = text.split(":", 1)[1].lstrip()
                return SimpleNamespace(ids=prefix + [100 + i for i in range(len(remainder))])
        self.encoder = E5ONNXEncoder.__new__(E5ONNXEncoder)
        self.encoder.tokenizer = Tokenizer()

    def test_no_tail_truncation_and_bounded_windows(self):
        windows = self.encoder.token_windows("x" * 1200, "passage")
        content = {t for w in windows for t in w[3:-1]}
        self.assertEqual(content, set(range(100, 1300)))
        self.assertTrue(all(len(w) <= 512 for w in windows))
        self.assertEqual(windows[0][-33:-1], windows[1][3:35])

    def test_query_uses_single_window_up_to_limit(self):
        windows = self.encoder.token_windows("x" * 508, "query")
        self.assertEqual(len(windows), 1)
        self.assertEqual(len(windows[0]), 512)
        with self.assertRaises(InputError):
            self.encoder.token_windows("x" * 509, "query")

    def test_blank_and_wrong_kind(self):
        for text, kind in ((" ", "query"), ("hello", "unknown")):
            with self.assertRaises(InputError):
                self.encoder.token_windows(text, kind)

    def test_prefix_boundary_mismatch_refused(self):
        from types import SimpleNamespace
        self.encoder.tokenizer.encode = lambda text, **kw: SimpleNamespace(ids=[1] if text.endswith(":") else [2])
        with self.assertRaises(ContractError):
            self.encoder.token_windows("x", "query")


class RetrievalMetricTests(unittest.TestCase):
    def test_known_labels_metric_math(self):
        from evaluation.semantic_trial import metrics
        labels = {"q1": {"status": "human_confirmed", "exhaustive": True, "relevant_fragment_ids": ["a", "b"]},
                  "q2": {"status": "human_confirmed", "exhaustive": True, "relevant_fragment_ids": ["z"]}}
        result = metrics({"q1": ["x", "a", "b"], "q2": ["x", "z"]}, labels, 2)
        self.assertEqual(result["Hit@k"], 1)
        self.assertEqual(result["Recall@k"], .75)
        self.assertEqual(result["MRR@k"], .5)

    def test_pending_and_partial_labels_not_scored(self):
        from evaluation.semantic_trial import metrics
        for label in ({"status": "pending_human_annotation"}, {"status": "human_confirmed", "exhaustive": False}):
            result = metrics({"q": ["x"]}, {"q": label}, 5)
            self.assertIsNone(result["Hit@k"])
            self.assertEqual(result["scored_queries"], 0)

    def test_no_relevant_queries_separate(self):
        from evaluation.semantic_trial import metrics
        result = metrics({"q": ["x"]}, {"q": {"status": "human_confirmed", "exhaustive": True, "relevant_fragment_ids": []}}, 5)
        self.assertEqual(result["no_relevant_queries"], ["q"])
        self.assertIsNone(result["Recall@k"])

    def test_family_split_no_leakage(self):
        from evaluation.semantic_trial import CANDIDATES, FAMILIES
        self.assertEqual(len(CANDIDATES), 18)
        self.assertEqual(set(c[0] for c in CANDIDATES), set(FAMILIES))
        self.assertEqual(sum(FAMILIES[c[0]] == "development" for c in CANDIDATES), 8)


if __name__ == "__main__":
    unittest.main()
