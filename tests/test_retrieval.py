"""Synthetic fixtures test program behavior, not electrical knowledge quality."""
import asyncio
from dataclasses import replace
import hashlib
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

from core.validation import ContractError, InputError, merge_evidence
from rag.bm25 import SCORING_METHOD, score_corpus, tokenize
from rag.contracts import RetrievalPurpose, RetrievalRequest
from rag.markdown import split_markdown
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata


FIXTURE = Path(__file__).parent / "fixtures" / "retrieval_synthetic.md"
META = SourceMetadata(source_type="synthetic_fixture")


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "knowledge.sqlite3"
        self.store = KnowledgeStore(self.db)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def write(self, text, name="synthetic.md"):
        path = self.root / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def query(self, text, version, purpose=RetrievalPurpose.GENERATION, limit=10):
        return asyncio.run(BM25Retriever(self.store).retrieve(
            RetrievalRequest(text, "synthetic_fixture", purpose, version, limit)))

    def test_idempotency_persists_across_reopen(self):
        first = self.store.ingest(FIXTURE, "fixture", META)
        second = self.store.ingest(FIXTURE, "fixture", META)
        self.assertEqual(first.knowledge_version, second.knowledge_version)
        self.assertTrue(second.unchanged)
        self.assertEqual(self.store.connection.execute("SELECT count(*) FROM snapshots").fetchone()[0], 1)
        self.store.close()
        self.store = KnowledgeStore(self.db)
        self.assertTrue(self.store.ingest(FIXTURE, "fixture", META).unchanged)

    def test_explicit_update_old_snapshot_and_revert(self):
        path = self.write("# synthetic_fixture\n\nalpha oldtoken\n")
        old = self.store.ingest(path, "fixture", META)
        before = self.query("oldtoken", old.knowledge_version)
        path.write_bytes(b"# synthetic_fixture\n\nalpha newtoken\n")
        with self.assertRaises(InputError):
            self.store.ingest(path, "fixture", META)
        new = self.store.ingest(path, "fixture", META, update=True)
        self.assertNotEqual(old.document_version, new.document_version)
        self.assertEqual(before, self.query("oldtoken", old.knowledge_version))
        self.assertFalse(self.query("oldtoken", new.knowledge_version).evidence)
        self.assertTrue(self.query("newtoken", new.knowledge_version).evidence)
        self.assertEqual(self.store.latest(), new.knowledge_version)
        path.write_bytes(b"# synthetic_fixture\n\nalpha oldtoken\n")
        reverted = self.store.ingest(path, "fixture", META, update=True)
        self.assertEqual(reverted.knowledge_version, old.knowledge_version)
        self.assertEqual(self.store.connection.execute("SELECT count(*) FROM versions").fetchone()[0], 2)

    def test_metadata_update_requires_explicit_update(self):
        old = self.store.ingest(FIXTURE, "fixture", META)
        modified = replace(META, publisher="Explicit synthetic publisher")
        with self.assertRaises(InputError):
            self.store.ingest(FIXTURE, "fixture", modified)
        new = self.store.ingest(FIXTURE, "fixture", modified, update=True)
        self.assertNotEqual(old.document_version, new.document_version)
        old_e = self.query("STATCOM", old.knowledge_version).evidence[0]
        new_e = self.query("STATCOM", new.knowledge_version).evidence[0]
        self.assertIsNone(old_e.provenance.publisher)
        self.assertEqual(new_e.provenance.publisher, modified.publisher)

    def test_exact_newlines_offsets_hash_and_line_numbers(self):
        raw = "# synthetic_fixture\r\n\r\n## 中文章\n\n无功 支撑 😀\r\nnext line\r\r最后段"
        path = self.write(raw)
        ingested = self.store.ingest(path, "fixture", META)
        items = self.query("支撑", ingested.knowledge_version).evidence
        self.assertEqual(len(items), 1)
        item, = items
        p = item.provenance
        self.assertEqual(item.text, "无功 支撑 😀\r\nnext line\r")
        self.assertEqual((p.start_line, p.end_line), (5, 6))
        self.assertEqual(raw[p.start_offset:p.end_offset], item.text)
        self.assertEqual(p.file_sha256, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(p.heading_path, ("synthetic_fixture", "中文章"))
        self.assertEqual(p.heading_levels, (1, 2))
        self.assertIsNone(p.publisher)
        self.assertIsNone(p.publication_date)
        self.assertIsNone(p.document_title)
        self.assertIsNone(p.source_uri)
        merge_evidence(items)  # Existing contract validation accepts adapted evidence.

    def test_raw_search_separation_headings_fences_and_setext(self):
        raw = "synthetic_fixture\n===\n\n## Voltage Control\n\nMiXeD Case\n\n```md\n# literal\n\nQ = x_1\n```\n"
        blocks = split_markdown(raw)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].raw_text, "MiXeD Case\n")
        self.assertIn("voltage control mixed case", blocks[0].search_text)
        self.assertEqual(blocks[1].heading_path, blocks[0].heading_path)
        self.assertIn("# literal\n\nQ = x_1", blocks[1].raw_text)
        result = self.store.ingest(self.write(raw), "fixture", META)
        evidence = self.query("voltage", result.knowledge_version).evidence
        self.assertTrue(evidence)
        self.assertNotIn("Voltage Control", evidence[0].text)
        self.assertTrue(all(raw[e.provenance.start_offset:e.provenance.end_offset] == e.text for e in evidence))

    def test_english_chinese_acronyms_empty_and_shared_purposes(self):
        result = self.store.ingest(FIXTURE, "fixture", META)
        k = result.knowledge_version
        english = self.query("statcom", k)
        self.assertEqual(len(english.evidence), 1)
        self.assertIn("STATCOM", english.evidence[0].text)
        self.assertTrue(self.query("无功支撑", k).evidence)
        for query in ("zzzzunmatched", "", "!!!"):
            self.assertEqual(self.query(query, k).evidence, ())
            self.assertEqual(self.query(query, k).hits, ())
        for purpose in RetrievalPurpose:
            self.assertEqual(english, self.query("statcom", k, purpose))
        self.assertEqual(english.hits[0].rank, 1)
        self.assertEqual(english.hits[0].scoring_method, SCORING_METHOD)
        self.assertFalse(hasattr(english.evidence[0], "supported"))

    def test_bm25_hand_calculation_rank_and_query_repetition(self):
        corpus = [("alpha", "alpha", "beta"), ("alpha", "beta"), ("gamma",)]
        scores = score_corpus("alpha", corpus)
        idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
        expected = [idf * 5 / (2 + 1.5 * (0.25 + 0.75 * 3 / 2)),
                    idf * 2.5 / (1 + 1.5 * (0.25 + 0.75 * 2 / 2)), 0]
        for got, want in zip(scores, expected):
            self.assertAlmostEqual(got, want, places=14)
        self.assertGreater(scores[0], scores[1])
        self.assertEqual(scores, score_corpus("alpha alpha", corpus))
        self.assertEqual(tokenize("STATCOM Q-V 电压"), ("statcom", "q", "v", "电", "压", "电压"))
        # Separate retrieval sample without headings: same corpus and independent scores.
        k = self.store.ingest(self.write("alpha alpha beta\n\nalpha beta\n\ngamma"), "synthetic_fixture", META).knowledge_version
        hits = self.query("alpha", k).hits
        self.assertEqual(len(hits), 2)
        for hit, want in zip(hits, expected):
            self.assertAlmostEqual(hit.score, want, places=14)

    def test_stable_ties_and_whole_snapshot_statistics(self):
        path = self.write("alpha")
        first = self.store.ingest(path, "z-synthetic_fixture", META)
        second = self.store.ingest(path, "a-synthetic_fixture", META)
        result = self.query("alpha", second.knowledge_version)
        self.assertEqual([e.source_id for e in result.evidence], ["a-synthetic_fixture", "z-synthetic_fixture"])
        self.assertEqual(result.hits[0].score, result.hits[1].score)
        self.assertEqual(result, self.query("alpha", second.knowledge_version))
        self.assertEqual(len(self.query("alpha", first.knowledge_version).evidence), 1)
        self.assertEqual(len(self.query("alpha", second.knowledge_version, limit=1).evidence), 1)

    def test_evidence_roundtrip_and_tampering(self):
        k = self.store.ingest(FIXTURE, "fixture", META).knowledge_version
        item = self.query("STATCOM", k).evidence[0]
        self.assertEqual(self.store.verify_evidence(item), item)
        self.assertEqual(self.store.evidence(item.provenance.fragment_id, k), item)
        for field in ("text", "evidence_id", "source_id", "locator", "source_version"):
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.store.verify_evidence(replace(item, **{field: "tampered"}))
        with self.assertRaises(ContractError):
            self.store.verify_evidence(replace(item, provenance=replace(item.provenance, start_line=999)))
        with self.assertRaises(ContractError):
            self.store.evidence("unknown", k)
        with self.store.connection:
            self.store.connection.execute("UPDATE fragments SET raw_text='tampered' WHERE fragment_id=?", (item.provenance.fragment_id,))
        with self.assertRaises(ContractError):
            self.store.verify_evidence(item)

    def test_cross_snapshot_reference_rejected(self):
        path = self.write("old alpha")
        old = self.store.ingest(path, "fixture", META)
        item = self.query("alpha", old.knowledge_version).evidence[0]
        path.write_bytes(b"new beta")
        new = self.store.ingest(path, "fixture", META, update=True)
        with self.assertRaises(ContractError):
            self.store.evidence(item.provenance.fragment_id, new.knowledge_version)

    def test_failed_ingestion_rolls_back_partial_writes(self):
        old = self.store.ingest(FIXTURE, "fixture", META)
        expected = self.query("STATCOM", old.knowledge_version)
        counts = [self.store.connection.execute("SELECT count(*) FROM " + t).fetchone()[0]
                  for t in ("documents", "versions", "fragments", "snapshots", "snapshot_documents")]
        insert = self.store._insert_fragments
        def fail_after_insert(*args):
            insert(*args)
            raise sqlite3.OperationalError("synthetic transaction failure")
        with patch.object(self.store, "_insert_fragments", side_effect=fail_after_insert):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.ingest(self.write("synthetic newtoken"), "new_fixture", META)
            with self.assertRaises(sqlite3.OperationalError):
                self.store.ingest(self.write("synthetic changed"), "fixture", META, update=True)
        self.assertEqual(self.store.latest(), old.knowledge_version)
        self.assertEqual(expected, self.query("STATCOM", old.knowledge_version))
        self.assertEqual(counts, [self.store.connection.execute("SELECT count(*) FROM " + t).fetchone()[0]
                                 for t in ("documents", "versions", "fragments", "snapshots", "snapshot_documents")])

    def test_invalid_input_and_index_version(self):
        for data in (b"\xff", b"\xef\xbb\xbftext", b"# heading only\n", b"\n\n"):
            path = self.root / "synthetic.md"
            path.write_bytes(data)
            with self.assertRaises(InputError):
                self.store.ingest(path, "fixture", META)
        with self.assertRaises(InputError):
            self.store.ingest(self.write("synthetic", "synthetic.pdf"), "fixture", META)
        with self.assertRaises(InputError):
            self.query("alpha", "missing")
        k = self.store.ingest(FIXTURE, "fixture", META).knowledge_version
        with self.assertRaises(InputError):
            self.query("alpha", k, limit=0)
        with self.store.connection:
            self.store.connection.execute("UPDATE settings SET value='unknown' WHERE name='index_config'")
        with self.assertRaises(ContractError):
            KnowledgeStore(self.db)

    def test_cli_ingest_query_lookup_verify_and_errors(self):
        def cli(*args, success=True):
            process = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "rag.cli", "--db", str(self.db), *args],
                                     cwd=Path(__file__).resolve().parents[1], capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0 if success else 2, process.stderr)
            return json.loads(process.stdout) if success else process
        result = cli("ingest", str(FIXTURE), "--document-id", "fixture", "--source-type", "synthetic_fixture")
        k = result["knowledge_version"]
        queried = cli("query", "STATCOM", "--knowledge-version", k)
        item = queried["evidence"][0]
        fid = item["provenance"]["fragment_id"]
        self.assertEqual(cli("lookup", fid, "--knowledge-version", k)["evidence"], item)
        path = self.root / "evidence.json"
        path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(cli("verify", str(path))["lookup_valid"])
        item["text"] = "tampered"
        path.write_text(json.dumps(item), encoding="utf-8")
        cli("verify", str(path), success=False)
        cli("query", "STATCOM", "--knowledge-version", "missing", success=False)
        self.assertEqual(cli("latest")["knowledge_version"], k)

    def test_snapshot_integrity_and_readonly_missing_database(self):
        missing = self.root / "missing.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            KnowledgeStore(missing, readonly=True)
        self.assertFalse(missing.exists())
        k = self.store.ingest(FIXTURE, "fixture", META).knowledge_version
        with self.store.connection:
            self.store.connection.execute("DELETE FROM snapshot_documents WHERE knowledge_version=?", (k,))
        with self.assertRaises(ContractError):
            self.query("STATCOM", k)


if __name__ == "__main__":
    unittest.main()
