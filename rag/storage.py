"""Transactional, immutable document versions and complete knowledge snapshots."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from core.models import Evidence, EvidenceProvenance
from core.validation import ContractError, InputError
from rag.bm25 import INDEX_CONFIG, tokenize
from rag.markdown import MarkdownFragment, split_markdown


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class SourceMetadata:
    source_uri: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    document_title: str | None = None
    source_type: str = "markdown"
    applicability: tuple[str, ...] = ()


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    document_version: str
    knowledge_version: str
    fragment_count: int
    unchanged: bool


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (document_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS versions (
 document_id TEXT NOT NULL REFERENCES documents, version TEXT NOT NULL,
 file_sha256 TEXT NOT NULL, raw_bytes BLOB NOT NULL, raw_text TEXT NOT NULL,
 metadata TEXT NOT NULL, PRIMARY KEY(document_id, version));
CREATE TABLE IF NOT EXISTS fragments (
 fragment_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, version TEXT NOT NULL,
 ordinal INTEGER NOT NULL, raw_text TEXT NOT NULL, search_text TEXT NOT NULL,
 start_offset INTEGER NOT NULL, end_offset INTEGER NOT NULL,
 start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
    heading_path TEXT NOT NULL, heading_levels TEXT NOT NULL, tokens TEXT NOT NULL,
 FOREIGN KEY(document_id, version) REFERENCES versions(document_id, version));
CREATE TABLE IF NOT EXISTS snapshots (
 knowledge_version TEXT PRIMARY KEY, index_version TEXT NOT NULL, created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snapshot_documents (
 knowledge_version TEXT NOT NULL REFERENCES snapshots, document_id TEXT NOT NULL,
 version TEXT NOT NULL, PRIMARY KEY(knowledge_version, document_id),
 FOREIGN KEY(document_id, version) REFERENCES versions(document_id, version));
"""

# Additive extension: existing Markdown versions, IDs, snapshots and index
# configuration remain unchanged. PDF parser/chunking is bound to its versions.
PDF_SCHEMA = """
CREATE TABLE IF NOT EXISTS pdf_versions (
 document_id TEXT NOT NULL, version TEXT NOT NULL, parser_version TEXT NOT NULL,
 extraction_sha256 TEXT NOT NULL, config TEXT NOT NULL, status TEXT NOT NULL,
 diagnostic TEXT NOT NULL, PRIMARY KEY(document_id,version),
 FOREIGN KEY(document_id,version) REFERENCES versions(document_id,version));
CREATE TABLE IF NOT EXISTS pdf_pages (
 document_id TEXT NOT NULL, version TEXT NOT NULL, file_page INTEGER NOT NULL,
 raw_text TEXT NOT NULL, text_sha256 TEXT NOT NULL, status TEXT NOT NULL,
 warnings TEXT NOT NULL, diagnostic TEXT NOT NULL, printed_page TEXT, section TEXT,
 previous_file_page INTEGER, next_file_page INTEGER,
 PRIMARY KEY(document_id,version,file_page),
 FOREIGN KEY(document_id,version) REFERENCES pdf_versions(document_id,version));
CREATE TABLE IF NOT EXISTS pdf_fragments (
 fragment_id TEXT PRIMARY KEY REFERENCES fragments, file_page INTEGER NOT NULL,
 previous_fragment_id TEXT REFERENCES fragments, next_fragment_id TEXT REFERENCES fragments);
"""

PDF_CHUNK_SCHEMA = """
CREATE TABLE IF NOT EXISTS pdf_derivations (
 document_id TEXT NOT NULL, version TEXT NOT NULL, source_version TEXT NOT NULL,
 split_config TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
 PRIMARY KEY(document_id,version),
 FOREIGN KEY(document_id,version) REFERENCES pdf_versions(document_id,version),
 FOREIGN KEY(document_id,source_version) REFERENCES versions(document_id,version));
CREATE TABLE IF NOT EXISTS pdf_chunk_details (
 fragment_id TEXT PRIMARY KEY REFERENCES pdf_fragments, split_method TEXT NOT NULL,
 warnings TEXT NOT NULL);
"""


class KnowledgeStore:
    def __init__(self, path, *, readonly=False, validated_pdf_cache=False):
        self._path=Path(path).resolve()
        self._readonly=readonly
        self._validated_pdf_cache = {} if readonly and validated_pdf_cache else None
        self.pdf_validation_hits = 0
        self.pdf_validation_misses = 0
        self.connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) if readonly else sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        existing = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not existing and not readonly:
            self.connection.executescript(SCHEMA)
            with self.connection:
                self.connection.execute("INSERT INTO settings VALUES ('schema_version','1')")
                self.connection.execute("INSERT INTO settings VALUES ('index_config',?)", (canonical(INDEX_CONFIG),))
        try:
            settings = dict(self.connection.execute("SELECT name,value FROM settings"))
            if settings.get("schema_version") != "1" or settings.get("index_config") != canonical(INDEX_CONFIG):
                raise ContractError("Unsupported schema/index configuration; do not silently reindex")
        except Exception:
            self.connection.close()
            raise
        if not readonly:
            self.connection.executescript("BEGIN IMMEDIATE;" + PDF_SCHEMA + "COMMIT;")
            with self.connection:
                self.connection.execute("INSERT OR IGNORE INTO settings VALUES ('pdf_schema_version','1')")
        self._has_pdf_tables = self.connection.execute("SELECT 1 FROM sqlite_master WHERE name='pdf_versions'").fetchone() is not None
        extension = self.connection.execute("SELECT value FROM settings WHERE name='pdf_schema_version'").fetchone()
        if self._has_pdf_tables and (not extension or extension[0] != "1"):
            self.close()
            raise ContractError("Unsupported PDF schema extension")
        if not readonly:
            self.connection.executescript("BEGIN IMMEDIATE;" + PDF_CHUNK_SCHEMA + "COMMIT;")
        self._has_pdf_chunks = self.connection.execute("SELECT 1 FROM sqlite_master WHERE name='pdf_derivations'").fetchone() is not None

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def latest(self):
        row = self.connection.execute("SELECT value FROM settings WHERE name='latest'").fetchone()
        return row[0] if row else None

    def _members(self, knowledge_version):
        row = self.connection.execute("SELECT index_version FROM snapshots WHERE knowledge_version=?", (knowledge_version,)).fetchone()
        if not row:
            raise InputError("Unknown knowledge version")
        if row[0] != canonical(INDEX_CONFIG):
            raise ContractError("Snapshot index configuration mismatch")
        members = dict(self.connection.execute("SELECT document_id,version FROM snapshot_documents WHERE knowledge_version=?", (knowledge_version,)))
        expected = "k-" + digest(canonical({"documents": members, "index": INDEX_CONFIG}).encode("utf-8"))
        if knowledge_version != expected:
            raise ContractError("Knowledge snapshot membership/hash mismatch")
        return members

    def ingest(self, path, document_id, metadata=None, *, update=False):
        if not isinstance(document_id, str) or not document_id.strip():
            raise InputError("document_id is required")
        suffix = Path(path).suffix.lower()
        if suffix not in (".md", ".pdf"):
            raise InputError("Only UTF-8 .md and text .pdf files are supported")
        metadata = metadata or SourceMetadata(source_type="pdf" if suffix == ".pdf" else "markdown")
        from core.validation import validate_types
        validate_types(metadata, SourceMetadata)
        if not metadata.source_type.strip():
            raise InputError("source_type is required")
        data = Path(path).read_bytes()
        if suffix == ".pdf":
            from rag.pdf import extract_pdf, extraction_fingerprint, PDFIngestionError
            report = extract_pdf(data)
            if report.status != "ready_for_review":
                raise PDFIngestionError(report)
            fragments = tuple(MarkdownFragment(p.raw_text, " ".join(p.raw_text.casefold().split()), (),
                0, len(p.raw_text), 1, max(1, len(p.raw_text.splitlines())), ())
                for p in report.pages if p.status == "text_pending_review")
            meta = canonical(asdict(metadata))
            version = digest(canonical({"file_sha256": report.file_sha256, "metadata": meta,
                "pdf_extraction_sha256": extraction_fingerprint(report), "parser_version": report.parser_version}).encode("utf-8"))
            return self._commit_version(document_id, data, "", meta, version, fragments, update, report)
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InputError("Markdown must be UTF-8") from exc
        if raw.startswith("\ufeff"):
            raise InputError("UTF-8 BOM is unsupported; remove it explicitly before ingestion")
        fragments = split_markdown(raw)
        if not fragments:
            raise InputError("Markdown contains no content blocks")
        file_hash = digest(data)
        meta = canonical(asdict(metadata))
        version = digest(canonical({"file_sha256": file_hash, "metadata": meta}).encode("utf-8"))
        return self._commit_version(document_id, data, raw, meta, version, fragments, update)

    def _commit_version(self, document_id, data, raw, meta, version, fragments, update, pdf_report=None, derivation=None):
        file_hash = digest(data)
        with self.transaction():
            latest = self.latest()
            members = self._members(latest) if latest else {}
            if document_id in members and members[document_id] != version and not update:
                raise InputError("Document exists with different content/metadata; explicit update required")
            if members.get(document_id) == version:
                return IngestResult(document_id, version, latest, len(fragments), True)
            self.connection.execute("INSERT OR IGNORE INTO documents VALUES (?)", (document_id,))
            exists = self.connection.execute("SELECT 1 FROM versions WHERE document_id=? AND version=?", (document_id, version)).fetchone()
            if not exists:
                self.connection.execute("INSERT INTO versions VALUES (?,?,?,?,?,?)", (document_id, version, file_hash, data, raw, meta))
                if pdf_report is None:
                    self._insert_fragments(document_id, version, fragments)
                else:
                    if derivation is None:
                        self._insert_pdf(document_id, version, pdf_report, fragments)
                    else:
                        self._insert_pdf(document_id, version, pdf_report, fragments, derivation)
            members[document_id] = version
            knowledge = "k-" + digest(canonical({"documents": members, "index": INDEX_CONFIG}).encode("utf-8"))
            self.connection.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?)", (knowledge, canonical(INDEX_CONFIG), datetime.now(timezone.utc).isoformat()))
            self.connection.executemany("INSERT OR IGNORE INTO snapshot_documents VALUES (?,?,?)", [(knowledge, doc, ver) for doc, ver in sorted(members.items())])
            self.connection.execute("INSERT OR REPLACE INTO settings VALUES ('latest',?)", (knowledge,))
            return IngestResult(document_id, version, knowledge, len(fragments), False)

    def _insert_fragments(self, document_id, version, fragments, parser_version=None):
        for ordinal, fragment in enumerate(fragments):
            fid = self._fragment_id(document_id, version, ordinal, parser_version or INDEX_CONFIG["parser"])
            self.connection.execute("INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                fid, document_id, version, ordinal, fragment.raw_text, fragment.search_text,
                fragment.start_offset, fragment.end_offset, fragment.start_line, fragment.end_line,
                canonical(fragment.heading_path), canonical(fragment.heading_levels), canonical(tokenize(fragment.search_text))))

    @staticmethod
    def _fragment_id(document_id, version, ordinal, parser_version):
        return "f-" + digest(canonical([document_id, version, ordinal, parser_version]).encode("utf-8"))

    def _insert_pdf(self, document_id, version, report, fragments, derivation=None):
        from rag.pdf import extraction_fingerprint
        self.connection.execute("INSERT INTO pdf_versions VALUES (?,?,?,?,?,?,?)", (
            document_id, version, report.parser_version, extraction_fingerprint(report),
            canonical(report.config), report.status, report.diagnostic))
        for page in report.pages:
            self.connection.execute("INSERT INTO pdf_pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                document_id, version, page.file_page, page.raw_text, page.text_sha256, page.status,
                canonical(page.warnings), page.diagnostic, page.printed_page, page.section,
                page.previous_file_page, page.next_file_page))
        identity = report.parser_version if derivation is None else report.parser_version + "|" + derivation["config"]["splitter_version"]
        self._insert_fragments(document_id, version, fragments, identity)
        ids = [self._fragment_id(document_id, version, i, identity) for i in range(len(fragments))]
        file_pages = ([p.file_page for p in report.pages if p.status == "text_pending_review"] if derivation is None
                      else [c.file_page for c in derivation["chunks"]])
        for i, file_page in enumerate(file_pages):
            self.connection.execute("INSERT INTO pdf_fragments VALUES (?,?,?,?)", (
                ids[i], file_page, ids[i - 1] if i else None, ids[i + 1] if i + 1 < len(ids) else None))
        if derivation is not None:
            from rag.pdf_chunks import plan_fingerprint
            self.connection.execute("INSERT INTO pdf_derivations VALUES (?,?,?,?,?)", (document_id, version,
                derivation["source_version"], canonical(derivation["config"]), plan_fingerprint(derivation["chunks"])))
            self.connection.executemany("INSERT INTO pdf_chunk_details VALUES (?,?,?)", [
                (fid, chunk.split_method, canonical(chunk.warnings)) for fid, chunk in zip(ids, derivation["chunks"])])

    def derive_pdf(self, document_id, knowledge_version, *, max_chars=1200):
        """Explicitly derive from frozen stored extraction, without pypdf or re-extraction."""
        from rag.pdf import extraction_fingerprint
        from rag.pdf_chunks import split_config, split_pdf_pages, plan_fingerprint
        members = self._members(knowledge_version)
        if document_id not in members:
            raise InputError("Document is not in source snapshot")
        source_version = members[document_id]
        row = self.connection.execute("SELECT * FROM versions WHERE document_id=? AND version=?", (document_id, source_version)).fetchone()
        report = self.pdf_report(document_id, knowledge_version)
        config = split_config(max_chars)
        chunks = split_pdf_pages(report, config)
        if not chunks:
            raise InputError("No derived PDF chunks")
        version = digest(canonical({"file_sha256": row["file_sha256"], "metadata": row["metadata"],
            "pdf_extraction_sha256": extraction_fingerprint(report), "parser_version": report.parser_version,
            "pdf_split_config": config, "pdf_fragment_plan_sha256": plan_fingerprint(chunks)}).encode("utf-8"))
        derivation = {"source_version": source_version, "config": config, "chunks": chunks}
        return self._commit_version(document_id, row["raw_bytes"], "", row["metadata"], version,
                                    tuple(c.fragment for c in chunks), True, report, derivation)

    def _load_derivation(self, document_id, version, report):
        if not self._has_pdf_chunks:
            return None
        row = self.connection.execute("SELECT * FROM pdf_derivations WHERE document_id=? AND version=?", (document_id, version)).fetchone()
        if row is None:
            return None
        from rag.pdf_chunks import split_pdf_pages, plan_fingerprint
        config = json.loads(row["split_config"])
        chunks = split_pdf_pages(report, config)
        if plan_fingerprint(chunks) != row["plan_sha256"]:
            raise ContractError("Derived PDF chunk plan mismatch")
        return config, chunks, row["plan_sha256"]

    def _load_pdf_report(self, document_id, version, file_hash, knowledge_version=None):
        # Connection-local verified document data, not rankings or audit judgments.
        # SQLite data_version invalidates on other connections' committed changes.
        # No cache in writeable stores; retrieval's full replay/evidence checks remain.
        from copy import deepcopy
        stamp = (self.connection.execute('PRAGMA data_version').fetchone()[0], self.connection.total_changes)
        key = (stamp, knowledge_version, document_id, version, file_hash, 'validated-pdf-report-cache-v1')
        if self._validated_pdf_cache is not None and key in self._validated_pdf_cache:
            self.pdf_validation_hits += 1
            return deepcopy(self._validated_pdf_cache[key])
        self.pdf_validation_misses += 1
        from rag.pdf import PDFPage, PDFExtraction, extraction_fingerprint
        head = self.connection.execute("SELECT * FROM pdf_versions WHERE document_id=? AND version=?", (document_id, version)).fetchone()
        if not head:
            raise ContractError("No PDF extraction for this version")
        rows = self.connection.execute("SELECT * FROM pdf_pages WHERE document_id=? AND version=? ORDER BY file_page", (document_id, version)).fetchall()
        pages = tuple(PDFPage(r["file_page"], r["raw_text"], r["text_sha256"], r["status"], tuple(json.loads(r["warnings"])),
            r["diagnostic"], r["printed_page"], r["section"], r["previous_file_page"], r["next_file_page"]) for r in rows)
        for i, page in enumerate(pages, 1):
            if (page.file_page != i or digest(page.raw_text.encode("utf-8")) != page.text_sha256
                    or page.previous_file_page != (i - 1 if i > 1 else None)
                    or page.next_file_page != (i + 1 if i < len(pages) else None)):
                raise ContractError("PDF page text/hash/adjacency mismatch")
        report = PDFExtraction(file_hash, head["parser_version"], json.loads(head["config"]), pages, head["status"], head["diagnostic"])
        if extraction_fingerprint(report) != head["extraction_sha256"] or report.status != "ready_for_review":
            raise ContractError("PDF extraction fingerprint/status mismatch")
        if self._validated_pdf_cache is not None:
            if stamp != (self.connection.execute('PRAGMA data_version').fetchone()[0], self.connection.total_changes):
                raise ContractError('Knowledge changed during PDF validation')
            if len(self._validated_pdf_cache) >= 8:self._validated_pdf_cache.clear()
            self._validated_pdf_cache[key] = deepcopy(report)
        return report

    def pdf_report(self, document_id, knowledge_version):
        members = self._members(knowledge_version)
        if document_id not in members:
            raise InputError("Document is not in snapshot")
        row = self.connection.execute("SELECT * FROM versions WHERE document_id=? AND version=?", (document_id, members[document_id])).fetchone()
        if digest(row["raw_bytes"]) != row["file_sha256"]:
            raise ContractError("Stored PDF file hash mismatch")
        return self._load_pdf_report(document_id, members[document_id], row["file_sha256"], knowledge_version)

    def rows(self, knowledge_version):
        self._members(knowledge_version)
        return self.connection.execute("""SELECT f.*,v.file_sha256,v.metadata FROM fragments f
            JOIN snapshot_documents s ON s.document_id=f.document_id AND s.version=f.version
            JOIN versions v ON v.document_id=f.document_id AND v.version=f.version
            WHERE s.knowledge_version=? ORDER BY f.document_id,f.version,f.ordinal,f.fragment_id""", (knowledge_version,)).fetchall()

    def evidence(self, fragment_id, knowledge_version):
        from rag.corpus_index import seal,corpus_evidence
        corpus=seal(self,knowledge_version)
        if corpus is not None:
            return corpus_evidence(self,fragment_id,knowledge_version,corpus)
        self._members(knowledge_version)
        row = self.connection.execute("""SELECT f.*,v.file_sha256,v.raw_bytes,v.raw_text AS document_text,v.metadata FROM fragments f
            JOIN versions v ON v.document_id=f.document_id AND v.version=f.version
            JOIN snapshot_documents s ON s.document_id=f.document_id AND s.version=f.version
            WHERE f.fragment_id=? AND s.knowledge_version=?""", (fragment_id, knowledge_version)).fetchone()
        if not row:
            raise ContractError("Fragment is not a member of this knowledge snapshot")
        # Reparse from stored bytes, checking hash, character span, lines, headings,
        # raw/search text and tokens rather than trusting the fragment table alone.
        data, raw = row["raw_bytes"], row["document_text"]
        pdf_head = self.connection.execute("SELECT 1 FROM pdf_versions WHERE document_id=? AND version=?", (row["document_id"], row["version"])).fetchone() if self._has_pdf_tables else None
        if pdf_head:
            return self._pdf_evidence(row, knowledge_version)
        if digest(data) != row["file_sha256"] or data.decode("utf-8") != raw:
            raise ContractError("Stored document hash/text mismatch")
        fragments = split_markdown(raw)
        if not 0 <= row["ordinal"] < len(fragments):
            raise ContractError("Invalid fragment ordinal")
        expected = fragments[row["ordinal"]]
        for key in ("raw_text", "search_text", "start_offset", "end_offset", "start_line", "end_line"):
            if row[key] != getattr(expected, key):
                raise ContractError("Fragment provenance mismatch: " + key)
        if (json.loads(row["heading_path"]) != list(expected.heading_path)
                or json.loads(row["heading_levels"]) != list(expected.heading_levels)
                or json.loads(row["tokens"]) != list(tokenize(expected.search_text))):
            raise ContractError("Fragment heading/token mismatch")
        metadata = json.loads(row["metadata"])
        calculated_version = digest(canonical({"file_sha256": row["file_sha256"], "metadata": row["metadata"]}).encode("utf-8"))
        calculated_fid = "f-" + digest(canonical([row["document_id"], row["version"], row["ordinal"], INDEX_CONFIG["parser"]]).encode("utf-8"))
        if row["version"] != calculated_version or fragment_id != calculated_fid:
            raise ContractError("Document version/fragment ID mismatch")
        provenance = EvidenceProvenance(
            row["document_id"], row["version"], row["file_sha256"], fragment_id, knowledge_version,
            expected.start_offset, expected.end_offset, expected.start_line, expected.end_line,
            expected.heading_path, metadata["source_uri"], metadata["publisher"],
            metadata["publication_date"], metadata["document_title"], expected.heading_levels)
        locator = f"chars[{expected.start_offset}:{expected.end_offset});lines[{expected.start_line}:{expected.end_line}]"
        return Evidence("e-" + digest(canonical([knowledge_version, fragment_id]).encode("utf-8")),
                        row["document_id"], row["version"], locator, expected.raw_text,
                        metadata["source_type"], tuple(metadata["applicability"]), provenance)

    def _pdf_evidence(self, row, knowledge_version):
        from rag.pdf import extraction_fingerprint
        if digest(row["raw_bytes"]) != row["file_sha256"] or row["document_text"] != "":
            raise ContractError("Stored PDF original hash/text mismatch")
        report = self._load_pdf_report(row["document_id"], row["version"], row["file_sha256"], knowledge_version)
        text_pages = [p for p in report.pages if p.status == "text_pending_review"]
        derivation = self._load_derivation(row["document_id"], row["version"], report)
        chunks = derivation[1] if derivation else None
        count = len(chunks) if chunks else len(text_pages)
        ordinal = row["ordinal"]
        if not 0 <= ordinal < count:
            raise ContractError("Invalid PDF fragment ordinal")
        page = report.pages[chunks[ordinal].file_page - 1] if chunks else text_pages[ordinal]
        identity = report.parser_version if not chunks else report.parser_version + "|" + derivation[0]["splitter_version"]
        fragment = self.connection.execute("SELECT * FROM pdf_fragments WHERE fragment_id=?", (row["fragment_id"],)).fetchone()
        ids = [self._fragment_id(row["document_id"], row["version"], i, identity) for i in range(count)]
        previous = ids[ordinal - 1] if ordinal else None
        following = ids[ordinal + 1] if ordinal + 1 < len(ids) else None
        if (not fragment or fragment["file_page"] != page.file_page or fragment["previous_fragment_id"] != previous
                or fragment["next_fragment_id"] != following or row["fragment_id"] != ids[ordinal]):
            raise ContractError("PDF fragment ID/page/adjacency mismatch")
        expected = chunks[ordinal].fragment if chunks else MarkdownFragment(page.raw_text,
            " ".join(page.raw_text.casefold().split()), (), 0, len(page.raw_text), 1, max(1, len(page.raw_text.splitlines())), ())
        expected_fields = {"raw_text": expected.raw_text, "search_text": expected.search_text, "start_offset": expected.start_offset,
                           "end_offset": expected.end_offset, "start_line": expected.start_line, "end_line": expected.end_line,
                           "heading_path": "[]", "heading_levels": "[]", "tokens": canonical(tokenize(expected.search_text))}
        if any(row[key] != value for key, value in expected_fields.items()):
            raise ContractError("PDF fragment text/locator/index mismatch")
        extraction_hash = extraction_fingerprint(report)
        payload = {"file_sha256": row["file_sha256"], "metadata": row["metadata"],
                   "pdf_extraction_sha256": extraction_hash, "parser_version": report.parser_version}
        if derivation:
            payload.update(pdf_split_config=derivation[0], pdf_fragment_plan_sha256=derivation[2])
            detail = self.connection.execute("SELECT * FROM pdf_chunk_details WHERE fragment_id=?", (row["fragment_id"],)).fetchone()
            if not detail or detail["split_method"] != chunks[ordinal].split_method or detail["warnings"] != canonical(chunks[ordinal].warnings):
                raise ContractError("PDF split method/warnings mismatch")
        version = digest(canonical(payload).encode("utf-8"))
        if row["version"] != version:
            raise ContractError("PDF document version mismatch")
        meta = json.loads(row["metadata"])
        warnings = page.warnings + (("adjacent_page_context_not_merged",) if previous or following else ())
        provenance = EvidenceProvenance(row["document_id"], row["version"], row["file_sha256"], row["fragment_id"],
            knowledge_version, expected.start_offset, expected.end_offset, expected.start_line, expected.end_line, source_uri=meta["source_uri"], publisher=meta["publisher"],
            publication_date=meta["publication_date"], document_title=meta["document_title"], file_page=page.file_page,
            printed_page=page.printed_page, section=page.section, parser_version=report.parser_version,
            page_text_sha256=page.text_sha256, extraction_sha256=extraction_hash, text_basis="pdf_extracted_page_text",
            previous_fragment_id=previous, next_fragment_id=following, quality_status=page.status, quality_warnings=warnings,
            splitter_version=derivation[0]["splitter_version"] if derivation else None,
            split_method=chunks[ordinal].split_method if chunks else None, split_warnings=chunks[ordinal].warnings if chunks else ())
        locator = f"pdf_extracted_text:file_page={page.file_page};page_chars[{expected.start_offset}:{expected.end_offset});page_lines[{expected.start_line}:{expected.end_line}]"
        return Evidence("e-" + digest(canonical([knowledge_version, row["fragment_id"]]).encode("utf-8")),
            row["document_id"], row["version"], locator, expected.raw_text, meta["source_type"], tuple(meta["applicability"]), provenance)

    def verify_evidence(self, evidence):
        if evidence.provenance is None:
            raise ContractError("Retrieval evidence requires provenance")
        expected = self.evidence(evidence.provenance.fragment_id, evidence.provenance.knowledge_version)
        if evidence != expected:
            raise ContractError("Evidence differs from stored source")
        return expected
