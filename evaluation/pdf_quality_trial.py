"""Fixed-source comparisons for human review, with no automatic quality verdict."""
import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from evaluation.pdf_trial import QUERIES as ORIGINAL_GUIDELINE_QUERIES
from rag.bm25 import INDEX_CONFIG
from rag.contracts import ContextOptions, RetrievalPurpose, RetrievalRequest
from rag.pdf import extraction_fingerprint
from rag.pdf_chunks import split_config
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata


QUERIES = {
    "nerc-reactive-planning-2016": [("original_broad" if q == "voltage stability" else "original_query", q) for q in ORIGINAL_GUIDELINE_QUERIES] + [
        ("natural_question", "What is voltage stability and how is instability assessed?"),
        ("natural_question", "What limits a generator's ability to supply reactive power?"),
        ("natural_question", "Can QV analysis miss voltage stability problems over a wide area?"),
        ("natural_question", "Does a STATCOM's short overload capability count as reactive reserve?"),
        ("natural_question", "How long must maximum reactive output be sustainable?")],
    "nerc-var-001-5": [
        ("precise", "R1 voltage schedule target tolerance band thirty calendar days"),
        ("precise", "R2 sufficient reactive resources normal contingency"),
        ("precise", "R5 generator voltage reactive power schedule transformer notification"),
        ("precise", "WECC variance automatic voltage regulators"),
        ("precise", "version history errata"),
        ("natural_question", "What must a transmission operator do to maintain system voltage?"),
        ("natural_question", "How quickly must a voltage schedule be supplied when requested?"),
        ("natural_question", "Does this standard apply to all generator operators?"),
        ("natural_question", "What should happen when a generator cannot follow its voltage schedule?"),
        ("natural_question", "Which side of a transformer can be used to specify the voltage schedule?")],
    "pnnl-35221": [
        ("precise", "long-term short-term voltage instability reactive reserve"),
        ("precise", "Voltage Instability Predictor VIP Thevenin impedance"),
        ("precise", "reactive power margin topology breaker status FIDVR"),
        ("precise", "model-based measurement-based voltage stability monitoring tools"),
        ("natural_question", "What is voltage instability?"),
        ("natural_question", "How do PMUs help detect a lack of reactive power support?"),
        ("natural_question", "What data are needed to calculate reactive power margin?"),
        ("natural_question", "Can this method distinguish motor stalling from voltage instability?")],
}

VISUAL_FOCUS = {
    "nerc-reactive-planning-2016": {8: "Resource conditions, generator limits and damaged formulas; compare page 9",
        9: "Continuation of generator conditions from page 8", 21: "QV start, footnotes and continuation on page 22",
        22: "QV limitations, negation and continuation onto page 23", 23: "PV scope and control limitations",
        25: "Sustained output, STATCOM overload exclusion, generator limits; schedule continues on page 26",
        27: "Merged table headings and row/column alignment", 34: "Time-dependent limits and table cell association",
        38: "Negation, TO/DP scope and regional attribution", 57: "Errata date/figure reference; do not automatically repair page 11"},
    "nerc-var-001-5": {1: "Applicability and Western Interconnection scope", 2: "R1/R2 versus measures; time limit and conditions",
        3: "R5 nested subrequirements, transformer side, obligations and measures", 6: "Regional variance scope",
        10: "WECC regional-variance control-loop requirements versus measures and scope",
        11: "Violation-severity table alignment and applicability", 12: "Violation-severity table continuation",
        13: "Version-history table, date/version association",
        14: "Version-history continuation", 15: "Technical rationale versus normative requirements"},
    "pnnl-35221": {23: "Long-/short-term instability distinction and report focus", 24: "Tool categories, RPM input data and scope",
        25: "RPM/VIP continuation, explanatory figures and qualifiers", 26: "Dashboards/images not interpreted",
        27: "Case examples and figure attribution"},
}


def _dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="data/retrieval_local/pdf-quality")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--context-chars", type=int, default=2400)
    parser.add_argument("--context-depth", type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "docs/knowledge-sources/manifest.json").read_text(encoding="utf-8"))
    comparisons, checklist, failures, audit = [], [], [], []
    for doc in manifest["documents"]:
        doc_id = doc["document_id"]
        if doc_id not in QUERIES:
            audit.append({"document_id": doc_id, "status": "excluded_not_downloaded", "collection_status": doc["download_status"]})
            continue
        path = root / doc["local_file"]
        try:
            data = path.read_bytes()
            file_hash = hashlib.sha256(data).hexdigest()
            if file_hash != doc["sha256"]:
                raise ValueError("Actual file hash differs from collection manifest")
            audit.append({"document_id": doc_id, "file_sha256": file_hash, "hash_matches_manifest": True})
            metadata = SourceMetadata(doc["download_url"], doc["institution"], doc["publication_date_internal"],
                doc["internal_title"], doc["document_type"], (doc["applicable_region"],))
            with KnowledgeStore(output_dir / (doc_id + ".sqlite3")) as store:
                # Dedicated, single-document corpus. Explicitly select/reuse the
                # fixed baseline on reruns, preserving every historical snapshot.
                baseline = store.ingest(path, doc_id, metadata, update=True)
                old_report = store.pdf_report(doc_id, baseline.knowledge_version)
                derived = store.derive_pdf(doc_id, baseline.knowledge_version, max_chars=args.max_chars)
                new_report = store.pdf_report(doc_id, derived.knowledge_version)
                assert old_report == new_report, "Comparison must reuse byte-identical extraction"
                page_index = {p.file_page: p for p in new_report.pages}
                adjacency = {r["fragment_id"]: r["file_page"] for r in store.connection.execute(
                    "SELECT pf.fragment_id,pf.file_page FROM pdf_fragments pf JOIN fragments f ON f.fragment_id=pf.fragment_id WHERE f.document_id=? AND f.version=?", (doc_id, derived.document_version))}
                rows = store.rows(derived.knowledge_version)
                for row in rows:
                    page = page_index[adjacency[row["fragment_id"]]]
                    assert page.raw_text[row["start_offset"]:row["end_offset"]] == row["raw_text"]
                    assert 0 <= row["start_offset"] < row["end_offset"] <= len(page.raw_text)
                    assert len(row["raw_text"]) <= args.max_chars
                methods = Counter(r[0] for r in store.connection.execute(
                    "SELECT d.split_method FROM pdf_chunk_details d JOIN fragments f ON f.fragment_id=d.fragment_id WHERE f.document_id=? AND f.version=?", (doc_id, derived.document_version)))
                queries = []
                for kind, query in QUERIES[doc_id]:
                    results = {}
                    for strategy, version in (("page_baseline", baseline.knowledge_version), ("paragraph_derived", derived.knowledge_version)):
                        request = RetrievalRequest(query, "fixed_source_pdf_comparison", RetrievalPurpose.VERIFICATION, version, 3,
                            ContextOptions(args.context_chars, 6, args.context_depth) if strategy == "paragraph_derived" else None)
                        result = asyncio.run(BM25Retriever(store).retrieve(request))
                        emitted = list(result.evidence)
                        if result.context:
                            emitted.extend(item.evidence for item in result.context.items)
                        for evidence in emitted:
                            p = evidence.provenance
                            assert page_index[p.file_page].raw_text[p.start_offset:p.end_offset] == evidence.text
                        results[strategy] = asdict(result)
                    queries.append({"query_kind": kind, "query": query, "results": results,
                                    "automated_span_check": "passed", "human_relevance_review": "pending"})
                for page in new_report.pages:
                    page_fragments = [r for r in rows if adjacency[r["fragment_id"]] == page.file_page]
                    checklist.append({"document_id": doc_id, "file_sha256": file_hash,
                        "knowledge_version": derived.knowledge_version, "file_page": page.file_page,
                        "problem_types": list(page.warnings) + sorted({w for r in page_fragments
                            for w in json.loads(store.connection.execute("SELECT warnings FROM pdf_chunk_details WHERE fragment_id=?", (r["fragment_id"],)).fetchone()[0])}),
                        "extracted_text": page.raw_text, "extracted_text_chars": [0, len(page.raw_text)],
                        "visual_check_required": VISUAL_FOCUS.get(doc_id, {}).get(page.file_page,
                            "Reading order, hidden image text, table/formula meaning and extraction completeness"),
                        "visual_status": "pending_human_review", "automated_span_check": "passed",
                        "fragments": [{"fragment_id": r["fragment_id"], "chars": [r["start_offset"], r["end_offset"]],
                            "raw_text": r["raw_text"]} for r in page_fragments]})
                comparisons.append({"document_id": doc_id, "source": doc, "file_sha256": file_hash,
                    "extraction_sha256": extraction_fingerprint(old_report), "baseline": asdict(baseline),
                    "query_set_sha256": hashlib.sha256(json.dumps(QUERIES[doc_id], ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
                    "split_config": split_config(args.max_chars),
                    "derived": asdict(derived), "split_methods": dict(methods), "queries": queries,
                    "quality_statuses": dict(Counter(p.status for p in new_report.pages)),
                    "score_interpretation": "No score-scale comparison across documents or chunking corpora; no quality verdict"})
                print(json.dumps({"document_id": doc_id, "baseline_fragments": baseline.fragment_count,
                    "derived_fragments": derived.fragment_count, "split_methods": dict(methods), "queries": len(queries)}, ensure_ascii=False), flush=True)
        except Exception as exc:
            failure = {"document_id": doc_id, "error": f"{type(exc).__name__}: {exc}"}
            if hasattr(exc, "report"):
                failure["extraction_report"] = asdict(exc.report)
            failures.append(failure)
            print(json.dumps(failure, ensure_ascii=False), flush=True)
    output = {"status": "developer_comparison_for_pending_human_review", "bm25_config": INDEX_CONFIG,
        "chunk_max_chars": args.max_chars, "context_max_chars": args.context_chars, "context_depth": args.context_depth,
        "collection_audit": audit, "documents": comparisons, "failures": failures}
    _dump(output_dir / "comparison.json", output)
    _dump(output_dir / "manual-review.json", {"status": "pending_human_review", "items": checklist})
    lines = ["# Fixed-source PDF comparison: pending human review", "",
             "Scores are not comparable across documents or chunking corpora. No automatic quality verdict.", ""]
    for doc in comparisons:
        lines += ["## " + doc["document_id"], "", "| Query kind / query | Page baseline: file pages / scores | Derived: page:chars / scores | Context pages / omitted |", "| --- | --- | --- | --- |"]
        for item in doc["queries"]:
            old, new = item["results"]["page_baseline"], item["results"]["paragraph_derived"]
            def describe(result, spans=False):
                return "; ".join(f"{e['provenance']['file_page']}" +
                    (f":{e['provenance']['start_offset']}-{e['provenance']['end_offset']}" if spans else "") + f" / {h['score']:.6f}"
                    for e, h in zip(result["evidence"], result["hits"])) or "empty"
            context = new["context"]
            context_text = ",".join(str(c["evidence"]["provenance"]["file_page"]) for c in context["items"]) if context else ""
            lines.append(f"| {item['query_kind']}: {item['query']} | {describe(old)} | {describe(new, True)} | {context_text}; omitted={len(context['omitted']) if context else 0} |")
        lines.append("")
    (output_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "documents": len(comparisons), "review_pages": len(checklist), "failures": len(failures)}), flush=True)
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
