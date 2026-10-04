"""Synthetic extraction/temporary PDF behavior tests, no knowledge scoring."""
import asyncio
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.validation import ContractError, InputError
from rag.context import read_adjacent_context
from rag.contracts import ContextOptions, RetrievalPurpose, RetrievalRequest
from rag.pdf import PDF_CONFIG, PARSER_VERSION, PDFExtraction, PDFPage
from rag.pdf_chunks import split_config, split_pdf_pages
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata
from tests.pdf_fixtures import make_pdf


def report(text, warnings=()):
    page = PDFPage(1, text, hashlib.sha256(text.encode()).hexdigest(), "text_pending_review", warnings)
    return PDFExtraction("synthetic_fixture", PARSER_VERSION, PDF_CONFIG, (page,), "ready_for_review")


class PDFSplitterTests(unittest.TestCase):
    def test_layout_newlines_not_paragraphs_exact_crlf_offsets(self):
        raw = "synthetic first sentence\r\nwrapped continuation\r\n  \r\nSecond paragraph\r\ncontinued."
        chunks = split_pdf_pages(report(raw), split_config(200))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].split_method, "blank_line_paragraph")
        self.assertIn("wrapped continuation", chunks[0].fragment.raw_text)
        self.assertEqual("".join(c.fragment.raw_text for c in chunks), raw)
        self.assertEqual((chunks[0].fragment.start_line, chunks[0].fragment.end_line), (1, 3))
        self.assertEqual(chunks[1].fragment.start_line, 4)
        for c in chunks:
            self.assertEqual(raw[c.fragment.start_offset:c.fragment.end_offset], c.fragment.raw_text)

    def test_unreliable_boundaries_and_risky_page_bounded_fallback(self):
        raw = ("synthetic wrapped line\n" * 30) + "not supported unless this condition holds."
        chunks = split_pdf_pages(report(raw), split_config(80))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c.fragment.raw_text) <= 80 and c.split_method == "fallback_bounded_window" for c in chunks))
        self.assertEqual("".join(c.fragment.raw_text for c in chunks), raw)
        risky = split_pdf_pages(report("one paragraph\n\nsecond paragraph", ("possible_columns_or_table",)), split_config(80))
        self.assertEqual(risky[0].split_method, "fallback_bounded_window")
        self.assertIn("layout_or_character_risk_forced_fallback", risky[0].warnings)

    def test_long_paragraph_hard_limit_unicode_and_config_errors(self):
        raw = "电压😀" * 60 + "\n\nsynthetic next paragraph"
        chunks = split_pdf_pages(report(raw), split_config(32))
        self.assertTrue(all(len(c.fragment.raw_text) <= 32 for c in chunks))
        self.assertEqual("".join(c.fragment.raw_text for c in chunks), raw)
        self.assertIn("length_boundary_not_semantic", chunks[0].warnings)
        with self.assertRaises(InputError):
            split_config(0)
        with self.assertRaises(InputError):
            split_pdf_pages(report(raw), {"splitter_version": "unsupported", "max_chars": 32})


@unittest.skipUnless(importlib.util.find_spec("pypdf"), "Optional pypdf is not installed")
class PDFDerivedContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "synthetic.sqlite3"
        self.store = KnowledgeStore(self.db)
        self.path = self.root / "synthetic_fixture.pdf"

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ingest(self, pages):
        self.path.write_bytes(make_pdf(pages))
        return self.store.ingest(self.path, "synthetic_fixture", SourceMetadata(source_type="synthetic_fixture"))

    def query(self, query, version, options=None):
        return asyncio.run(BM25Retriever(self.store).retrieve(
            RetrievalRequest(query, "synthetic_fixture", RetrievalPurpose.VERIFICATION, version, 5, options)))

    def test_new_derived_versions_fixed_pages_and_history_without_dependency(self):
        baseline = self.ingest(["synthetic_fixture alpha " * 30, "synthetic beta continuation"])
        old = self.query("alpha", baseline.knowledge_version)
        derived = self.store.derive_pdf("synthetic_fixture", baseline.knowledge_version, max_chars=96)
        self.assertNotEqual(baseline.document_version, derived.document_version)
        self.assertEqual(self.store.pdf_report("synthetic_fixture", baseline.knowledge_version),
                         self.store.pdf_report("synthetic_fixture", derived.knowledge_version))
        self.assertEqual(old, self.query("alpha", baseline.knowledge_version))
        self.assertTrue(self.store.derive_pdf("synthetic_fixture", baseline.knowledge_version, max_chars=96).unchanged)
        other = self.store.derive_pdf("synthetic_fixture", baseline.knowledge_version, max_chars=128)
        self.assertNotEqual(derived.document_version, other.document_version)
        self.path.unlink()  # Stored original and extraction suffice for history/derivation.
        with patch.dict(sys.modules, {"pypdf": None}):
            self.assertEqual(old, self.query("alpha", baseline.knowledge_version))
            self.assertTrue(self.query("alpha", derived.knowledge_version).evidence)
            self.store.derive_pdf("synthetic_fixture", baseline.knowledge_version, max_chars=160)

    def test_all_derived_spans_lineage_and_split_method_roundtrip(self):
        old = self.ingest(["synthetic first condition not " * 20, "synthetic next condition"])
        new = self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=64)
        pages = self.store.pdf_report("synthetic_fixture", new.knowledge_version).pages
        for row in self.store.rows(new.knowledge_version):
            evidence = self.store.evidence(row["fragment_id"], new.knowledge_version)
            p = evidence.provenance
            self.assertEqual(pages[p.file_page - 1].raw_text[p.start_offset:p.end_offset], evidence.text)
            self.assertLessEqual(len(evidence.text), 64)
            self.assertEqual(p.splitter_version, "pdf-paragraphs-v2")
            self.assertTrue(p.split_method)
            self.assertTrue(self.store.verify_evidence(evidence))
        before = self.query("first", new.knowledge_version).evidence[0]
        with self.assertRaises(ContractError):
            self.store.verify_evidence(replace(before, provenance=replace(before.provenance, split_method="invented")))

    def test_cross_page_context_core_separation_and_same_page_guard(self):
        old = self.ingest(["synthetic previous condition", "synthetic core", "synthetic following condition"])
        new = self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=200)
        plain = self.query("core", new.knowledge_version)
        enriched = self.query("core", new.knowledge_version, ContextOptions(200, 6, 1))
        self.assertEqual(plain.evidence, enriched.evidence)
        self.assertEqual(plain.hits, enriched.hits)
        self.assertEqual([c.evidence.provenance.file_page for c in enriched.context.items], [1, 3])
        self.assertTrue(all(c.origin == "adjacent_context_not_retrieval_hit" and c.links[0].crosses_page for c in enriched.context.items))
        self.assertTrue(all(not hasattr(c, "score") for c in enriched.context.items))
        same_page = self.query("core", new.knowledge_version, ContextOptions(200, 6, 1, False))
        self.assertFalse(same_page.context.items)
        self.assertIsNone(plain.context)

    def test_context_deduplicates_shared_neighbors_and_core_fragments(self):
        old = self.ingest(["synthetic first", "synthetic middle", "synthetic last"])
        new = self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=200)
        first = self.query("first", new.knowledge_version).evidence[0]
        last = self.query("last", new.knowledge_version).evidence[0]
        context = read_adjacent_context(self.store, (first, last, first), new.knowledge_version, ContextOptions(200, 6, 2))
        self.assertEqual(len(context.items), 1)
        self.assertEqual(len(context.items[0].links), 2)
        self.assertEqual(context.items[0].evidence.provenance.file_page, 2)
        self.assertEqual(context.char_count, len(context.items[0].evidence.text))

    def test_same_page_neighbors_and_skip_oversized_candidate(self):
        old = self.ingest(["synthetic before " * 15 + "uniqueanchor " + "synthetic after " * 15])
        new = self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=80)
        result = self.query("uniqueanchor", new.knowledge_version, ContextOptions(160, 6, 1, False))
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(len(result.context.items), 2)
        core = result.evidence[0]
        before, after = [c.evidence for c in result.context.items]
        self.assertEqual(before.provenance.end_offset, core.provenance.start_offset)
        self.assertEqual(after.provenance.start_offset, core.provenance.end_offset)
        self.assertTrue(all(not c.links[0].crosses_page for c in result.context.items))
        # Use another isolated database so latest snapshot does not affect roots.
        with KnowledgeStore(self.root / "other.sqlite3") as other:
            self.path.write_bytes(make_pdf(["long " * 20, "core", "small"]))
            baseline = other.ingest(self.path, "fixture", SourceMetadata(source_type="synthetic_fixture"))
            derived = other.derive_pdf("fixture", baseline.knowledge_version, max_chars=200)
            core = asyncio.run(BM25Retriever(other).retrieve(RetrievalRequest("core", "synthetic_fixture",
                RetrievalPurpose.VERIFICATION, derived.knowledge_version, 1))).evidence[0]
            context = read_adjacent_context(other, (core,), derived.knowledge_version, ContextOptions(10))
            self.assertEqual(len(context.items), 1)
            self.assertEqual(context.items[0].links[0].direction, "next")
            self.assertTrue(context.omitted[0].startswith("character_limit:"))

    def test_budget_limits_do_not_truncate_evidence_and_zero_budget(self):
        old = self.ingest(["synthetic previous", "synthetic core", "synthetic following"])
        new = self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=200)
        core = self.query("core", new.knowledge_version).evidence[0]
        full = read_adjacent_context(self.store, (core,), new.knowledge_version, ContextOptions(200, 6, 1))
        length = len(full.items[0].evidence.text)
        limited = read_adjacent_context(self.store, (core,), new.knowledge_version, ContextOptions(length, 6, 1))
        self.assertEqual(len(limited.items), 1)
        self.assertEqual(limited.items[0].evidence, full.items[0].evidence)
        self.assertTrue(limited.omitted)
        cap = read_adjacent_context(self.store, (core,), new.knowledge_version, ContextOptions(200, 1, 1))
        self.assertEqual(len(cap.items), 1)
        zero = read_adjacent_context(self.store, (core,), new.knowledge_version, ContextOptions(0, 6, 1))
        self.assertFalse(zero.items)
        self.assertTrue(zero.omitted)
        with self.assertRaises(InputError):
            read_adjacent_context(self.store, (core,), new.knowledge_version, ContextOptions(-1))
        with self.assertRaises(ContractError):
            read_adjacent_context(self.store, (core,), old.knowledge_version, ContextOptions())

    def test_derived_failure_rolls_back_and_bad_split_details_rejected(self):
        old = self.ingest(["synthetic alpha " * 40])
        before = self.store.connection.execute("SELECT count(*) FROM versions").fetchone()[0]
        insert = self.store._insert_pdf
        def fail(*args):
            insert(*args)
            raise sqlite3.OperationalError("synthetic derived failure")
        with patch.object(self.store, "_insert_pdf", side_effect=fail):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=64)
        self.assertEqual(self.store.latest(), old.knowledge_version)
        self.assertEqual(before, self.store.connection.execute("SELECT count(*) FROM versions").fetchone()[0])
        new = self.store.derive_pdf("synthetic_fixture", old.knowledge_version, max_chars=64)
        core = self.query("alpha", new.knowledge_version).evidence[0]
        with self.store.connection:
            self.store.connection.execute("UPDATE pdf_chunk_details SET split_method='tampered' WHERE fragment_id=?", (core.provenance.fragment_id,))
        with self.assertRaises(ContractError):
            self.store.verify_evidence(core)

    def test_cli_derive_query_context_verify_and_old_lookup(self):
        old = self.ingest(["synthetic previous", "synthetic core", "synthetic next"])
        def cli(*args):
            process = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "rag.cli", "--db", str(self.db), *args],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)
        new = cli("derive-pdf", "synthetic_fixture", "--knowledge-version", old.knowledge_version, "--max-chars", "200")
        k = new["knowledge_version"]
        result = cli("query", "core", "--knowledge-version", k, "--context-chars", "200")
        self.assertEqual(len(result["context"]["items"]), 2)
        item = result["evidence"][0]
        fid = item["provenance"]["fragment_id"]
        separate = cli("context", fid, "--knowledge-version", k, "--max-chars", "200")
        self.assertEqual(separate, result["context"])
        path = self.root / "evidence.json"
        path.write_text(json.dumps(item), encoding="utf-8")
        self.assertTrue(cli("verify", str(path))["lookup_valid"])
        self.assertTrue(cli("query", "core", "--knowledge-version", old.knowledge_version)["evidence"])


if __name__ == "__main__":
    unittest.main()
