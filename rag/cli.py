"""Run from project root: python -m rag.cli --help."""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from core.models import Evidence, EvidenceProvenance
from core.validation import ContractError
from rag.contracts import ContextOptions, RetrievalPurpose, RetrievalRequest
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("path")
    ingest.add_argument("--document-id", required=True)
    ingest.add_argument("--update", action="store_true")
    ingest.add_argument("--source-type")
    for name in ("source-uri", "publisher", "publication-date", "document-title"):
        ingest.add_argument("--" + name)
    ingest.add_argument("--applicability", action="append", default=[])
    query = commands.add_parser("query")
    query.add_argument("query")
    query.add_argument("--knowledge-version", required=True)
    query.add_argument("--max-results", type=int, default=5)
    query.add_argument("--scenario-id", default="retrieval_behavior_development")
    query.add_argument("--purpose", choices=[p.value for p in RetrievalPurpose], default="generation")
    query.add_argument("--context-chars", type=int)
    query.add_argument("--context-max-fragments", type=int, default=6)
    query.add_argument("--context-depth", type=int, default=1)
    query.add_argument("--context-same-page", action="store_true")
    lookup = commands.add_parser("lookup")
    lookup.add_argument("fragment_id")
    lookup.add_argument("--knowledge-version", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("evidence_json", help="UTF-8 JSON containing one Evidence object")
    commands.add_parser("latest")
    inspect = commands.add_parser("inspect-pdf")
    inspect.add_argument("path")
    pages = commands.add_parser("pages")
    pages.add_argument("document_id")
    pages.add_argument("--knowledge-version", required=True)
    derive = commands.add_parser("derive-pdf")
    derive.add_argument("document_id")
    derive.add_argument("--knowledge-version", required=True)
    derive.add_argument("--max-chars", type=int, default=1200)
    context = commands.add_parser("context")
    context.add_argument("fragment_ids", nargs="+")
    context.add_argument("--knowledge-version", required=True)
    context.add_argument("--max-chars", type=int, default=2400)
    context.add_argument("--max-fragments", type=int, default=6)
    context.add_argument("--depth", type=int, default=1)
    context.add_argument("--same-page", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "inspect-pdf":
            from rag.pdf import extract_pdf
            report = extract_pdf(Path(args.path).read_bytes())
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
            if report.status != "ready_for_review":
                parser.exit(2)
            return
        with KnowledgeStore(args.db, readonly=args.command not in ("ingest", "derive-pdf")) as store:
            if args.command == "ingest":
                metadata = SourceMetadata(args.source_uri, args.publisher, args.publication_date,
                                          args.document_title, args.source_type or ("pdf" if Path(args.path).suffix.lower() == ".pdf" else "markdown"), tuple(args.applicability))
                result = asdict(store.ingest(args.path, args.document_id, metadata, update=args.update))
            elif args.command == "query":
                options = None if args.context_chars is None else ContextOptions(args.context_chars, args.context_max_fragments, args.context_depth, not args.context_same_page)
                request = RetrievalRequest(args.query, args.scenario_id, RetrievalPurpose(args.purpose), args.knowledge_version, args.max_results, options)
                result = asdict(asyncio.run(BM25Retriever(store).retrieve(request)))
            elif args.command == "lookup":
                result = {"lookup_valid": True, "evidence": asdict(store.evidence(args.fragment_id, args.knowledge_version))}
            elif args.command == "verify":
                with open(args.evidence_json, encoding="utf-8-sig") as handle:
                    value = json.load(handle)
                value["applicability"] = tuple(value.get("applicability", ()))
                if value.get("provenance"):
                    value["provenance"]["heading_path"] = tuple(value["provenance"]["heading_path"])
                    value["provenance"]["heading_levels"] = tuple(value["provenance"].get("heading_levels", ()))
                    value["provenance"]["quality_warnings"] = tuple(value["provenance"].get("quality_warnings", ()))
                    value["provenance"]["split_warnings"] = tuple(value["provenance"].get("split_warnings", ()))
                    value["provenance"] = EvidenceProvenance(**value["provenance"])
                result = {"lookup_valid": True, "evidence": asdict(store.verify_evidence(Evidence(**value)))}
            elif args.command == "pages":
                result = asdict(store.pdf_report(args.document_id, args.knowledge_version))
            elif args.command == "derive-pdf":
                result = asdict(store.derive_pdf(args.document_id, args.knowledge_version, max_chars=args.max_chars))
            elif args.command == "context":
                from rag.context import read_adjacent_context
                cores = tuple(store.evidence(fid, args.knowledge_version) for fid in args.fragment_ids)
                result = asdict(read_adjacent_context(store, cores, args.knowledge_version,
                               ContextOptions(args.max_chars, args.max_fragments, args.depth, not args.same_page)))
            else:
                result = {"knowledge_version": store.latest()}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ContractError, OSError, sqlite3.Error, ValueError, TypeError, KeyError) as exc:
        if hasattr(exc, "report"):
            print(json.dumps({"error": type(exc).__name__, "report": asdict(exc.report)}, ensure_ascii=False, indent=2))
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
