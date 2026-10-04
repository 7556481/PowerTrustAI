"""Optional, conservative PDF text extraction. No OCR or semantic layout repair."""
from dataclasses import asdict, dataclass, replace
from io import BytesIO
import hashlib
import json
import re

from core.validation import ContractError, InputError


PYPDF_VERSION = "6.10.0"
PARSER_VERSION = "pypdf-6.10.0/plain-pages-v1"
PDF_CONFIG = {"parser_version": PARSER_VERSION, "library_version": PYPDF_VERSION,
              "extraction_mode": "plain", "strict": True,
              "chunking": "one-fragment-per-text-page-v1", "ocr": False}


@dataclass(frozen=True)
class PDFPage:
    file_page: int
    raw_text: str
    text_sha256: str
    status: str
    warnings: tuple[str, ...]
    diagnostic: str = ""
    printed_page: str | None = None
    section: str | None = None
    previous_file_page: int | None = None
    next_file_page: int | None = None


@dataclass(frozen=True)
class PDFExtraction:
    file_sha256: str
    parser_version: str
    config: dict
    pages: tuple[PDFPage, ...]
    status: str
    diagnostic: str = ""


class PDFDependencyError(ContractError):
    pass


class PDFIngestionError(InputError):
    def __init__(self, report):
        self.report = report
        super().__init__(report.status + ": " + report.diagnostic)


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def extraction_fingerprint(report):
    return _hash(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8"))


def _reader(data):
    # Import only when extracting a PDF, never on Harness/Markdown import.
    try:
        import pypdf
    except ImportError as exc:
        raise PDFDependencyError("PDF ingestion requires requirements-pdf.txt; offline modes remain available") from exc
    if pypdf.__version__ != PYPDF_VERSION:
        raise PDFDependencyError(f"Expected pypdf {PYPDF_VERSION}; found {pypdf.__version__}")
    return pypdf.PdfReader(BytesIO(data), strict=True)


def _extract_page(page, number):
    runs, paints = [], []
    images = False
    def before(operator, operands, cm, tm):
        nonlocal images
        if operator in (b"Do", b"INLINE IMAGE", b"BI", b"sh", b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*", b"Tj", b"TJ", b"'", b'"'):
            paints.append(operator)
        if operator in (b"INLINE IMAGE", b"BI"):
            images = True
        if operator == b"Do" and operands:
            resources = page.get("/Resources", {})
            resources = resources.get_object() if hasattr(resources, "get_object") else resources
            obj = resources.get("/XObject", {}).get(operands[0])
            if obj is not None and obj.get_object().get("/Subtype") == "/Image":
                images = True

    def text_visitor(text, cm, tm, font, size):
        if text.strip():
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            runs.append((x, y, text))

    text = page.extract_text(extraction_mode="plain", visitor_operand_before=before,
                             visitor_text=text_visitor) or ""
    warnings = ["extracted_text_not_visual_original", "layout_pending_manual_review",
                "formula_table_structure_not_interpreted"]
    if text.strip():
        status = "text_pending_review"
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        left = [y for x, y, _ in runs if x < width * 0.48]
        right = [y for x, y, _ in runs if x >= width * 0.48]
        if len(left) >= 3 and len(right) >= 3 and min(max(left), max(right)) - max(min(left), min(right)) > 40:
            warnings.append("possible_columns_or_table")
        jumps = sum(b[1] - a[1] > height * 0.12 for a, b in zip(runs, runs[1:]))
        if jumps >= 2:
            warnings.append("suspected_reading_order")
        if "\ufffd" in text or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
            warnings.append("suspected_character_mapping")
        if images:
            warnings.append("images_not_interpreted")
    elif images:
        status = "scan_candidate_unsupported"
        warnings.append("image_without_extractable_text_not_proven_scan")
    elif not paints and not page.get("/Annots"):
        status = "blank_candidate"
        warnings.append("no_observed_paint_or_text_requires_visual_confirmation")
    else:
        status = "no_text_pending_review"
        warnings.append("visible_content_or_annotation_without_extractable_text")
    return PDFPage(number, text, _hash(text.encode("utf-8")), status, tuple(warnings))


def extract_pdf(data: bytes) -> PDFExtraction:
    file_hash = _hash(data)
    try:
        if not data.startswith(b"%PDF-"):
            raise ValueError("Missing PDF header")
        reader = _reader(data)
        if reader.is_encrypted:
            return PDFExtraction(file_hash, PARSER_VERSION, PDF_CONFIG, (), "encrypted_unsupported",
                                 "Encrypted PDFs are not decrypted by this ingestion pipeline")
        count = len(reader.pages)
        if count == 0:
            raise ValueError("PDF has no pages")
    except PDFDependencyError:
        raise
    except Exception as exc:
        return PDFExtraction(file_hash, PARSER_VERSION, PDF_CONFIG, (), "parse_failed", f"{type(exc).__name__}: {exc}")
    pages = []
    for i in range(count):
        try:
            pages.append(_extract_page(reader.pages[i], i + 1))
        except Exception as exc:
            pages.append(PDFPage(i + 1, "", _hash(b""), "parse_failed", ("page_extraction_failed",),
                                 f"{type(exc).__name__}: {exc}"))
    pages = [replace(p, previous_file_page=p.file_page - 1 if p.file_page > 1 else None,
                     next_file_page=p.file_page + 1 if p.file_page < count else None) for p in pages]
    statuses = {p.status for p in pages}
    if "parse_failed" in statuses:
        status, diagnostic = "parse_failed", "At least one page failed; ingestion is atomic and will be rejected"
    elif "scan_candidate_unsupported" in statuses or "no_text_pending_review" in statuses:
        status, diagnostic = "unsupported_nontext_pages", "Nontext content requires OCR or manual review; whole-document ingestion rejected"
    elif "text_pending_review" not in statuses:
        status, diagnostic = "no_extractable_text", "No searchable text; blank candidates require visual confirmation"
    else:
        status, diagnostic = "ready_for_review", "Text was extracted; visual reading order and completeness are not certified"
    return PDFExtraction(file_hash, PARSER_VERSION, PDF_CONFIG, tuple(pages), status, diagnostic)
