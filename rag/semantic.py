"""Snapshot-scoped exact vectors and rank fusion; Evidence stays in KnowledgeStore."""
import json
import math
from pathlib import Path
import sqlite3
import struct

from core.validation import ContractError, InputError, require, validate_types
from rag.bm25 import score_corpus
from rag.contracts import RetrievalHit, RetrievalRequest, RetrievalResult
from rag.retriever import BM25Retriever, AsyncSQLiteBM25Retriever
from rag.storage import canonical, digest

RRF_VERSION = "RRF-v1(k=60,equal-weights,candidate-depth=50,dense-positive-only)"


def profile_id(encoder):
    return "embedding-" + digest(canonical(encoder.profile).encode())


def source_fingerprint(rows):
    return digest(canonical([(r["fragment_id"], r["document_id"], r["version"], r["file_sha256"],
        digest(r["raw_text"].encode()), digest(r["search_text"].encode())) for r in rows]).encode())


def packed_vector(vector, dimension):
    if len(vector) != dimension or any(not math.isfinite(x) for x in vector):
        raise ContractError("Vector dimension/non-finite value mismatch")
    if not math.isclose(sum(x * x for x in vector), 1, abs_tol=1e-5):
        raise ContractError("Vector must be L2 normalized")
    return struct.pack("<" + "f" * dimension, *vector)


class VectorIndex:
    """Derived SQLite: no source text, Evidence, or publication metadata.

    Build complete snapshots atomically; model/profile mismatch never falls back.
    Connections are owned by the constructing thread, like KnowledgeStore.
    """
    def __init__(self, path, *, readonly=False):
        self.connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) if readonly else sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        if not readonly:
            self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS vector_settings (version TEXT NOT NULL);
            INSERT INTO vector_settings SELECT 'exact-vector-v1' WHERE NOT EXISTS (SELECT 1 FROM vector_settings);
            CREATE TABLE IF NOT EXISTS manifests (
                profile_id TEXT NOT NULL, knowledge_version TEXT NOT NULL, profile TEXT NOT NULL,
                source_fingerprint TEXT NOT NULL, source_versions TEXT NOT NULL, count INTEGER NOT NULL,
                PRIMARY KEY(profile_id,knowledge_version));
            CREATE TABLE IF NOT EXISTS vectors (
                profile_id TEXT NOT NULL, knowledge_version TEXT NOT NULL, fragment_id TEXT NOT NULL,
                vector BLOB NOT NULL, sha256 TEXT NOT NULL,
                PRIMARY KEY(profile_id,knowledge_version,fragment_id),
                FOREIGN KEY(profile_id,knowledge_version) REFERENCES manifests);
            """)
        if [r[0] for r in self.connection.execute("SELECT version FROM vector_settings")] != ["exact-vector-v1"]:
            self.close()
            raise ContractError("Unsupported vector index schema")

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def build(self, store, knowledge_version, encoder):
        rows = store.rows(knowledge_version)
        if not rows:
            raise InputError("Cannot index empty knowledge snapshot")
        pid = profile_id(encoder)
        existing = self.connection.execute("SELECT 1 FROM manifests WHERE profile_id=? AND knowledge_version=?", (pid, knowledge_version)).fetchone()
        if existing:
            self.load(store, knowledge_version, encoder)
            return {"unchanged": True, **self.manifest(pid, knowledge_version)}
        # Validate source spans/versions using the existing Evidence adapter.
        versions = {}
        for row in rows:
            evidence = store.evidence(row["fragment_id"], knowledge_version)
            p = evidence.provenance
            versions[p.document_id] = {"document_version": p.document_version, "file_sha256": p.file_sha256,
                "splitter_version": p.splitter_version, "parser_version": p.parser_version,
                "markdown_parser": "markdown-blocks-v1" if p.file_page is None else None}
        # Encode outside the write transaction; errors publish nothing.
        prepared = []
        for start in range(0, len(rows), 16):
            batch = rows[start:start + 16]
            output = encoder.encode([r["search_text"] for r in batch], "passage")
            if len(output) != len(batch):
                raise ContractError("Encoder batch cardinality mismatch")
            for row, vector in zip(batch, output):
                blob = packed_vector(vector, encoder.profile["dimension"])
                prepared.append((pid, knowledge_version, row["fragment_id"], blob, digest(blob)))
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("INSERT INTO manifests VALUES (?,?,?,?,?,?)", (
                pid, knowledge_version, canonical(encoder.profile), source_fingerprint(rows), canonical(versions), len(rows)))
            self.connection.executemany("INSERT INTO vectors VALUES (?,?,?,?,?)", prepared)
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise
        return {"unchanged": False, **self.manifest(pid, knowledge_version)}

    def manifest(self, pid, knowledge_version):
        row = self.connection.execute("SELECT * FROM manifests WHERE profile_id=? AND knowledge_version=?", (pid, knowledge_version)).fetchone()
        if row is None:
            raise ContractError("No complete vector index for requested model/profile and knowledge snapshot")
        result = dict(row)
        result["profile"] = json.loads(result["profile"])
        result["source_versions"] = json.loads(result["source_versions"])
        return result

    def load(self, store, knowledge_version, encoder):
        pid = profile_id(encoder)
        manifest = self.manifest(pid, knowledge_version)
        rows = store.rows(knowledge_version)
        require(manifest["profile"] == encoder.profile, "Vector profile mismatch")
        require(manifest["source_fingerprint"] == source_fingerprint(rows), "Vector source/split version mismatch")
        actual_sources = {}
        for row in rows:
            if row["document_id"] not in actual_sources:
                p = store.evidence(row["fragment_id"], knowledge_version).provenance
                actual_sources[p.document_id] = {"document_version": p.document_version, "file_sha256": p.file_sha256,
                    "splitter_version": p.splitter_version, "parser_version": p.parser_version,
                    "markdown_parser": "markdown-blocks-v1" if p.file_page is None else None}
        require(manifest["source_versions"] == actual_sources, "Vector source-version manifest mismatch")
        # Restrict by fixed snapshot and model BEFORE similarity/ranking.
        indexed = {r["fragment_id"]: r for r in self.connection.execute(
            "SELECT fragment_id,vector,sha256 FROM vectors WHERE profile_id=? AND knowledge_version=?", (pid, knowledge_version))}
        require(set(indexed) == {r["fragment_id"] for r in rows} and len(indexed) == manifest["count"],
                "Incomplete or foreign-fragment vector index; refusing partial search")
        dimension = encoder.profile["dimension"]
        vectors = []
        for row in rows:
            saved = indexed[row["fragment_id"]]
            blob = saved["vector"]
            require(len(blob) == dimension * 4 and digest(blob) == saved["sha256"], "Vector integrity mismatch")
            vector = struct.unpack("<" + "f" * dimension, blob)
            packed_vector(vector, dimension)
            vectors.append(vector)
        return rows, vectors


def fuse_ranks(bm25, dense, *, constant=60):
    scores = {}
    for ranking in (bm25, dense):
        for rank, (index, _) in enumerate(ranking, 1):
            scores[index] = scores.get(index, 0.0) + 1.0 / (constant + rank)
    return scores


class SemanticRetriever(BM25Retriever):
    def __init__(self, store, vector_index, encoder, *, mode="dense"):
        super().__init__(store)
        if mode not in ("bm25", "dense", "hybrid"):
            raise InputError("Mode must be bm25, dense or hybrid")
        self.vector_index, self.encoder, self.mode = vector_index, encoder, mode

    def _retrieve(self, request):
        if self.mode == "bm25":
            return super()._retrieve(request)
        validate_types(request, RetrievalRequest)
        if not request.knowledge_version.strip() or not request.scenario_id.strip() or request.max_results < 1:
            raise InputError("Fixed snapshot, scenario and positive max_results required")
        rows, vectors = self.vector_index.load(self.store, request.knowledge_version, self.encoder)
        if not request.query.strip():
            return RetrievalResult((), request.knowledge_version)
        query = self.encoder.encode([request.query], "query")
        require(len(query) == 1, "Query encoder cardinality mismatch")
        packed_vector(query[0], self.encoder.profile["dimension"])
        # Exact flat search is adequate for this corpus; no optional NumPy needed in tests.
        dense_scores = [sum(x * y for x, y in zip(query[0], vector)) for vector in vectors]
        tie = lambda i: (rows[i]["document_id"], rows[i]["version"], rows[i]["ordinal"], rows[i]["fragment_id"])
        # Existing Harness contract requires positive hit scores. Preserve actual
        # cosine, do not shift or fabricate a positive confidence/support score.
        dense = sorted(((i, score) for i, score in enumerate(dense_scores) if score > 0),
                       key=lambda pair: (-pair[1], tie(pair[0])))
        method = "Dense-cosine-v1(positive-only);" + profile_id(self.encoder)
        if self.mode == "hybrid":
            bm = score_corpus(request.query, [tuple(json.loads(row["tokens"])) for row in rows])
            lexical = sorted(((i, score) for i, score in enumerate(bm) if score > 0), key=lambda pair: (-pair[1], tie(pair[0])))
            scores = fuse_ranks(lexical[:50], dense[:50])
            dense = sorted(scores.items(), key=lambda pair: (-pair[1], tie(pair[0])))
            method = RRF_VERSION + ";" + profile_id(self.encoder)
        evidence, hits = [], []
        for rank, (i, score) in enumerate(dense[:request.max_results], 1):
            e = self.store.evidence(rows[i]["fragment_id"], request.knowledge_version)
            evidence.append(e)
            hits.append(RetrievalHit(e.evidence_id, rows[i]["fragment_id"], rank, float(score), method))
        context = None
        if request.context_options is not None:
            from rag.context import read_adjacent_context
            context = read_adjacent_context(self.store, tuple(evidence), request.knowledge_version, request.context_options)
        return RetrievalResult(tuple(evidence), request.knowledge_version, hits=tuple(hits), context=context)


class AsyncSQLiteSemanticRetriever(AsyncSQLiteBM25Retriever):
    """Reuse bounded single-worker scheduling; read connections belong to that worker.

    Cancelling await does not terminate ONNX/SQLite work. A busy worker refuses
    another request, as the original BM25 adapter does. Encoder used serially.
    """
    def __init__(self, path, vectors_path, encoder, *, mode="dense"):
        super().__init__(path)
        self.vectors_path, self.encoder, self.mode = vectors_path, MeteredEncoder(encoder), mode
        self.cache_identity=(mode,profile_id(encoder))
        self.validation_replays=0

    @property
    def query_encodings(self):return self.encoder.query_encodings

    def _work(self, request, result, validate):
        if validate == "saved_evidence" or self.mode == "bm25":
            return super()._work(request, result, validate)
        from rag.storage import KnowledgeStore
        with KnowledgeStore(self.path, readonly=True) as store, VectorIndex(self.vectors_path, readonly=True) as index:
            retriever = SemanticRetriever(store, index, self.encoder, mode=self.mode)
            if validate:
                self.validation_replays+=1
                retriever._validate_result(request, result)
                return None
            return retriever._retrieve(request)

class MeteredEncoder:
    """Count actual encoding attempts, including validation replay; no caching."""
    def __init__(self,encoder):
        self.encoder=encoder;self.profile=encoder.profile;self.query_encodings=0;self.encoding_seconds=0
    def encode(self,texts,kind):
        from time import perf_counter
        started=perf_counter()
        if kind=='query':self.query_encodings+=len(texts)
        try:return self.encoder.encode(texts,kind)
        finally:self.encoding_seconds+=perf_counter()-started
    def close(self):
        if hasattr(self.encoder,'close'):self.encoder.close()
