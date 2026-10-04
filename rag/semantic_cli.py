"""Optional local retrieval commands; never load .env or invoke generation APIs."""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import time
import sys

from rag.contracts import ContextOptions, RetrievalRequest, RetrievalPurpose
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default="data/retrieval_local/semantic/e5-small")
    parser.add_argument("--db")
    parser.add_argument("--vectors", default="data/retrieval_local/semantic/vectors.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("download-model")
    build = commands.add_parser("build")
    build.add_argument("--knowledge-version", required=True)
    query = commands.add_parser("query")
    query.add_argument("query")
    query.add_argument("--knowledge-version", required=True)
    query.add_argument("--mode", choices=("bm25", "dense", "hybrid"), default="hybrid")
    query.add_argument("--max-results", type=int, default=5)
    query.add_argument("--context-chars", type=int)
    query.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.command == "download-model":
            from rag.embedding import download_model
            print(json.dumps(download_model(args.model_dir), indent=2))
            return
        if not args.db:
            parser.error("--db required for build/query")
        started = time.perf_counter()
        with KnowledgeStore(args.db, readonly=True) as store:
            if args.command == "query" and args.mode == "bm25":
                encoder = index = None
                retriever = BM25Retriever(store)
            else:
                from rag.embedding import E5ONNXEncoder
                from rag.semantic import VectorIndex, SemanticRetriever
                encoder = E5ONNXEncoder(args.model_dir)
                index = VectorIndex(args.vectors, readonly=args.command != "build")
                retriever = SemanticRetriever(store, index, encoder, mode=getattr(args, "mode", "dense"))
            try:
                if args.command == "build":
                    result = index.build(store, args.knowledge_version, encoder)
                else:
                    request = RetrievalRequest(args.query, "local-semantic-demo", RetrievalPurpose.GENERATION,
                        args.knowledge_version, args.max_results,
                        None if args.context_chars is None else ContextOptions(max_chars=args.context_chars))
                    value = asyncio.run(retriever.retrieve(request))
                    asyncio.run(retriever.validate_result(request, value))
                    for e in value.evidence:
                        store.verify_evidence(e)
                    if value.context:
                        for item in value.context.items:
                            store.verify_evidence(item.evidence)
                    result = {"mode": args.mode, "query": args.query, "result": asdict(value),
                        "evidence_backtrace_valid": True, "meaning": "relevance_only_not_fact_support",
                        "embedding_profile": encoder.profile if encoder else None}
                result["elapsed_seconds_including_load_and_validation"] = time.perf_counter() - started
                if getattr(args, "output", None):
                    write_new(args.output, result)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            finally:
                if index:
                    index.close()
    except Exception as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
