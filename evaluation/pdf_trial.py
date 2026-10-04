"""Local official-source smoke run, NOT a human-labelled retrieval evaluation."""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from rag.contracts import RetrievalPurpose, RetrievalRequest
from rag.retriever import BM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata


QUERIES = (
    "dynamic reactive reserve STATCOM overload sustained maximum output",
    "QV analysis may not reveal wide-area voltage stability problems",
    "PV analysis active power transfer operating limits",
    "static dynamic reactive resources voltage squared",
    "synchronous generator capability stator field current excitation limiters",
    "NERC standards do not require minimum load power factor",
    "STATCOM SVC errata voltage-current characteristics",
    "voltage stability",
    "synchrophasor",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/retrieval_local/official-pdf.sqlite3")
    parser.add_argument("--output", default="data/retrieval_local/pdf-trial.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "docs/knowledge-sources/manifest.json").read_text(encoding="utf-8"))
    audit = []
    for document in manifest["documents"]:
        path = root / document["local_file"] if document["local_file"] else None
        item = {"document_id": document["document_id"], "collection_status": document["download_status"],
                "local_file_exists": bool(path and path.is_file()), "hash_matches_manifest": None}
        if item["local_file_exists"]:
            item["hash_matches_manifest"] = hashlib.sha256(path.read_bytes()).hexdigest() == document["sha256"]
            if not item["hash_matches_manifest"]:
                raise ValueError("Collection hash mismatch: " + document["document_id"])
        audit.append(item)
    document = next(d for d in manifest["documents"] if d["document_id"] == "nerc-reactive-planning-2016")
    path = root / document["local_file"]
    metadata = SourceMetadata(source_uri=document["download_url"], publisher=document["institution"],
        publication_date=document["publication_date_internal"], document_title=document["internal_title"],
        source_type=document["document_type"], applicability=(document["applicable_region"],))
    db = root / args.db
    db.parent.mkdir(parents=True, exist_ok=True)
    with KnowledgeStore(db) as store:
        ingested = store.ingest(path, document["document_id"], metadata)
        duplicate = store.ingest(path, document["document_id"], metadata)
        report = store.pdf_report(document["document_id"], ingested.knowledge_version)
        results = []
        for query in QUERIES:
            result = asyncio.run(BM25Retriever(store).retrieve(RetrievalRequest(
                query, "voltage_stability_local_smoke", RetrievalPurpose.VERIFICATION, ingested.knowledge_version, 3)))
            for evidence in result.evidence:
                store.verify_evidence(evidence)
                p = evidence.provenance
                assert evidence.text == report.pages[p.file_page - 1].raw_text[p.start_offset:p.end_offset]
            results.append({"query": query, "result": asdict(result), "stored_lookup_valid": True,
                            "content_review": "pending_manual_review_not_fact_support"})
        output = {"status": "developer_smoke_run_not_human_annotated_acceptance", "collection_audit": audit,
                  "ingested": asdict(ingested), "duplicate": asdict(duplicate),
                  "source_errata_from_collection": document["errata"], "extraction": asdict(report), "queries": results}
    target = root / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(target), "ingested": asdict(ingested), "duplicate_unchanged": duplicate.unchanged,
        "queries": [{"query": q["query"], "top": [{"file_page": e["provenance"]["file_page"],
            "fragment_id": h["fragment_id"], "rank": h["rank"], "score": h["score"]}
            for e, h in zip(q["result"]["evidence"], q["result"]["hits"])]} for q in results]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
