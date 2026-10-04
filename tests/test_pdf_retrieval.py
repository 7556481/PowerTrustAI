"""Controlled PDF behavior tests, not a human annotated acceptance set."""
import asyncio
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.validation import ContractError, InputError, merge_evidence
from rag.contracts import RetrievalPurpose, RetrievalRequest
from rag.pdf import (PDFDependencyError, PDFIngestionError, PARSER_VERSION,
                     extract_pdf)
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata
from tests.pdf_fixtures import make_pdf


META = SourceMetadata(source_type="synthetic_fixture")


@unittest.skipUnless(importlib.util.find_spec("pypdf"), "Optional pypdf is not installed")
class PDFTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = KnowledgeStore(self.root / "test.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def write(self, pages):
        path = self.root / "synthetic_fixture.pdf"
        path.write_bytes(make_pdf(pages))
        return path

    def query(self, query, version):
        return asyncio.run(BM25Retriever(self.store).retrieve(
            RetrievalRequest(query, "synthetic_fixture", RetrievalPurpose.VERIFICATION, version, 10)))

    def test_page_local_text_offsets_unknown_metadata_and_adjacency(self):
        path = self.write(["synthetic_fixture\nDo not treat alpha as supported unless condition holds.", None,
                           "synthetic_fixture\nContinuation beta remains separate."])
        result = self.store.ingest(path, "synthetic_fixture", META)
        report = self.store.pdf_report("synthetic_fixture", result.knowledge_version)
        self.assertEqual([p.file_page for p in report.pages], [1, 2, 3])
        self.assertEqual(report.pages[1].status, "blank_candidate")
        first = self.query("alpha", result.knowledge_version).evidence[0]
        last = self.query("beta", result.knowledge_version).evidence[0]
        self.assertEqual(first.text, report.pages[0].raw_text)
        self.assertIn("not", first.text)
        self.assertIn("unless condition", first.text)
        p = first.provenance
        self.assertEqual((p.file_page, p.start_offset, p.end_offset), (1, 0, len(first.text)))
        self.assertEqual(p.text_basis, "pdf_extracted_page_text")
        self.assertEqual(p.parser_version, PARSER_VERSION)
        self.assertEqual(p.next_fragment_id, last.provenance.fragment_id)
        self.assertEqual(last.provenance.previous_fragment_id, p.fragment_id)
        self.assertEqual(report.pages[0].next_file_page, 2)  # Physical blank page not silently merged.
        self.assertEqual(last.provenance.file_page, 3)
        for field in ("printed_page", "section", "publisher", "publication_date", "document_title", "source_uri"):
            self.assertIsNone(getattr(p, field))
        self.assertEqual(p.quality_status, "text_pending_review")
        self.assertTrue(self.store.verify_evidence(first))
        merge_evidence((first, last))

    def test_idempotency_explicit_update_and_historical_lookup(self):
        path = self.write(["synthetic_fixture oldtoken"])
        old = self.store.ingest(path, "fixture", META)
        evidence = self.query("oldtoken", old.knowledge_version).evidence[0]
        self.assertTrue(self.store.ingest(path, "fixture", META).unchanged)
        self.assertEqual(old.knowledge_version, self.store.latest())
        path.write_bytes(make_pdf(["synthetic_fixture newtoken"]))
        with self.assertRaises(InputError):
            self.store.ingest(path, "fixture", META)
        new = self.store.ingest(path, "fixture", META, update=True)
        self.assertNotEqual(old.document_version, new.document_version)
        self.assertEqual(self.store.verify_evidence(evidence), evidence)
        self.assertFalse(self.query("oldtoken", new.knowledge_version).evidence)
        self.assertTrue(self.query("newtoken", new.knowledge_version).evidence)
        self.store.close()
        self.store = KnowledgeStore(self.root / "test.sqlite3", readonly=True)
        self.assertEqual(self.store.verify_evidence(evidence), evidence)

    def test_scan_blank_ambiguous_mixed_and_encrypted(self):
        for pages, status in ((["image"], "unsupported_nontext_pages"), ([None], "no_extractable_text"),
                              (["vector"], "unsupported_nontext_pages"), (["synthetic text", "image"], "unsupported_nontext_pages")):
            path = self.write(pages)
            report = extract_pdf(path.read_bytes())
            self.assertEqual(report.status, status)
            with self.assertRaises(PDFIngestionError):
                self.store.ingest(path, "fixture", META)
            self.assertIsNone(self.store.latest())
            self.assertEqual(self.store.connection.execute("SELECT count(*) FROM versions").fetchone()[0], 0)
        self.assertEqual(extract_pdf(make_pdf(["image"])).pages[0].status, "scan_candidate_unsupported")
        self.assertEqual(extract_pdf(make_pdf([None])).pages[0].status, "blank_candidate")
        self.assertEqual(extract_pdf(make_pdf(["vector"])).pages[0].status, "no_text_pending_review")
        self.assertEqual(extract_pdf(make_pdf(["text"], encrypted=True)).status, "encrypted_unsupported")

    def test_corrupt_pdf_and_page_failure_keep_valid_snapshot(self):
        path = self.write(["synthetic_fixture alpha", "synthetic_fixture beta"])
        old = self.store.ingest(path, "fixture", META)
        expected = self.query("alpha", old.knowledge_version)
        from rag.pdf import _extract_page
        def fail_second(page, number):
            if number == 2:
                raise ValueError("synthetic extraction failure")
            return _extract_page(page, number)
        with patch("rag.pdf._extract_page", side_effect=fail_second):
            report = extract_pdf(path.read_bytes())
            self.assertEqual(report.status, "parse_failed")
            self.assertEqual(report.pages[1].diagnostic, "ValueError: synthetic extraction failure")
            with self.assertRaises(PDFIngestionError):
                self.store.ingest(path, "fixture", META, update=True)
        path.write_bytes(b"%PDF-1.7\ntruncated synthetic fixture")
        with self.assertRaises(PDFIngestionError):
            self.store.ingest(path, "fixture", META, update=True)
        self.assertEqual(self.store.latest(), old.knowledge_version)
        self.assertEqual(self.query("alpha", old.knowledge_version), expected)

    def test_pdf_transaction_partial_write_rolls_back(self):
        old = self.store.ingest(self.write(["synthetic oldtoken"]), "fixture", META)
        tables = ("versions", "fragments", "pdf_versions", "pdf_pages", "pdf_fragments", "snapshots")
        before = [self.store.connection.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in tables]
        insert = self.store._insert_pdf
        def failed(*args):
            insert(*args)
            raise sqlite3.OperationalError("synthetic late failure")
        with patch.object(self.store, "_insert_pdf", side_effect=failed):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.ingest(self.write(["synthetic newtoken"]), "fixture", META, update=True)
        self.assertEqual(self.store.latest(), old.knowledge_version)
        self.assertEqual(before, [self.store.connection.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in tables])

    def test_suspected_columns_and_reading_order_are_not_certified(self):
        runs = [(50, 700, "synthetic left one"), (50, 620, "left two"), (50, 500, "left three"),
                (350, 700, "right one"), (350, 620, "right two"), (350, 500, "right three"),
                (50, 700, "returned left top")]
        page = extract_pdf(make_pdf([runs])).pages[0]
        self.assertIn("possible_columns_or_table", page.warnings)
        self.assertIn("suspected_reading_order", page.warnings)
        self.assertEqual(page.status, "text_pending_review")

    def test_page_fragment_and_evidence_tampering_rejected(self):
        k = self.store.ingest(self.write(["synthetic alpha", "synthetic beta"]), "fixture", META).knowledge_version
        evidence = self.query("alpha", k).evidence[0]
        for name, value in (("file_page", 99), ("page_text_sha256", "wrong"), ("parser_version", "wrong"),
                            ("text_basis", "visual_original"), ("next_fragment_id", None)):
            with self.subTest(name=name), self.assertRaises(ContractError):
                self.store.verify_evidence(replace(evidence, provenance=replace(evidence.provenance, **{name: value})))
        with self.store.connection:
            self.store.connection.execute("UPDATE pdf_pages SET raw_text='tampered' WHERE file_page=1")
        with self.assertRaises(ContractError):
            self.store.verify_evidence(evidence)

    def test_shared_markdown_pdf_snapshot_and_old_database_extension(self):
        path = self.root / "synthetic.md"
        path.write_text("# synthetic_fixture\n\nalpha markdown", encoding="utf-8")
        old = self.store.ingest(path, "md", META)
        expected = self.query("alpha", old.knowledge_version)
        # Simulate the actual prior Markdown-only schema; no old data is changed.
        self.store.connection.executescript("DROP TABLE pdf_fragments; DROP TABLE pdf_pages; DROP TABLE pdf_versions; DELETE FROM settings WHERE name='pdf_schema_version';")
        self.store.close()
        self.store = KnowledgeStore(self.root / "test.sqlite3", readonly=True)
        self.assertEqual(expected, self.query("alpha", old.knowledge_version))
        self.store.close()
        self.store = KnowledgeStore(self.root / "test.sqlite3")
        new = self.store.ingest(self.write(["synthetic alpha PDF"]), "pdf", META)
        self.assertEqual(expected, self.query("alpha", old.knowledge_version))
        self.assertEqual({e.source_id for e in self.query("alpha", new.knowledge_version).evidence}, {"md", "pdf"})

    def test_dependency_absent_offline_and_stored_lookup_work(self):
        path = self.write(["synthetic_fixture alpha"])
        result = self.store.ingest(path, "fixture", META)
        evidence = self.query("alpha", result.knowledge_version).evidence[0]
        from rag import pdf
        with patch.dict(sys.modules, {"pypdf": None}):
            with self.assertRaises(PDFDependencyError):
                pdf.extract_pdf(path.read_bytes())
            self.assertEqual(self.store.verify_evidence(evidence), evidence)
        process = subprocess.run([sys.executable, "-X", "utf8", "-B", "-S", "-m", "harness.demo"],
                                 cwd=Path(__file__).resolve().parents[1], capture_output=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(process.stdout.splitlines()), 7)

    def test_cli_pdf_roundtrip_and_failed_inspection_diagnostics(self):
        path = self.write(["synthetic_fixture alpha"])
        def cli(*args, code=0):
            process = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "rag.cli", "--db", str(self.root / "test.sqlite3"), *args],
                                     cwd=Path(__file__).resolve().parents[1], capture_output=True, encoding="utf-8")
            self.assertEqual(process.returncode, code, process.stderr)
            return json.loads(process.stdout)
        self.assertEqual(cli("inspect-pdf", str(path))["status"], "ready_for_review")
        k = cli("ingest", str(path), "--document-id", "fixture", "--source-type", "synthetic_fixture")["knowledge_version"]
        item = cli("query", "alpha", "--knowledge-version", k)["evidence"][0]
        self.assertEqual(cli("pages", "fixture", "--knowledge-version", k)["pages"][0]["file_page"], 1)
        evidence_path = self.root / "evidence.json"
        evidence_path.write_text(json.dumps(item), encoding="utf-8")
        self.assertTrue(cli("verify", str(evidence_path))["lookup_valid"])
        path.write_bytes(make_pdf(["image"]))
        failure = cli("ingest", str(path), "--document-id", "fixture", "--update", code=2)
        self.assertEqual(failure["report"]["status"], "unsupported_nontext_pages")


if __name__ == "__main__":
    unittest.main()
