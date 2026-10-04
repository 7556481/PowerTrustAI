"""Retrieval-only comparison and pending-human annotation preparation.

No model-generated truth labels, generation API, credentials or protocol edits.
"""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import time
import sys

from rag.bm25 import INDEX_CONFIG
from rag.contracts import RetrievalPurpose, RetrievalRequest
from rag.storage import KnowledgeStore, SourceMetadata, canonical, digest
from rag.semantic_cli import write_new

ROOT = Path(__file__).resolve().parents[1]


def peak_memory():
    """Measured Windows process peak RSS, not an estimated model requirement."""
    try:
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("peak", "working", "paged_peak", "paged", "nonpaged_peak", "nonpaged", "pagefile", "pagefile_peak")]
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi")
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return counters.peak
    except (AttributeError, OSError):
        return None
FAMILIES = {
    "tap-documentation": "development",
    "ambient-mode-estimation": "development",
    "conversion-methodology": "frozen_acceptance_candidate",
    "low-damping-validation": "frozen_acceptance_candidate",
    "research-authority-transfer": "frozen_acceptance_candidate",
    "unsupported-device-threshold": "frozen_acceptance_candidate",
}
# Suggested labels are hypotheses to inspect, NEVER scored as human truth.
CANDIDATES = [
    ("tap-documentation", "After consulting the Generator Owner, what documentation is required for necessary step-up transformer tap changes?", "support", "nerc-var-001-5", [4]),
    ("tap-documentation", "Can a Transmission Operator require tap changes without consulting the Generator Owner?", "conflict_check", "nerc-var-001-5", [4]),
    ("tap-documentation", "Is documenting only the required tap position sufficient under R6?", "missing_conditions", "nerc-var-001-5", [4]),
    ("tap-documentation", "Can R6 alone determine the safe tap position of a particular plant without network data?", "insufficient_evidence", "nerc-var-001-5", [4]),
    ("tap-documentation", "Does deleting the consultation condition preserve the requirements of R6?", "revision_condition_loss", "nerc-var-001-5", [4]),
    ("conversion-methodology", "Who supplies voltage conversion methodology and who supplies supporting equipment and operating data in the Western Interconnection?", "support_roles_scope", "nerc-var-001-5", [9,10]),
    ("conversion-methodology", "Does E.A.15 assign the Generator Operator's voltage conversion methodology to the Transmission Operator?", "role_conflict", "nerc-var-001-5", [9,10]),
    ("conversion-methodology", "Does E.A.16 require data within thirty business days even without a request?", "time_unit_trigger_conflict", "nerc-var-001-5", [10]),
    ("conversion-methodology", "Is there a universal numerical voltage conversion factor in the regional variance?", "insufficient_evidence", "nerc-var-001-5", [9,10]),
    ("conversion-methodology", "Can a revision replace thirty calendar days after a request with thirty hours after commissioning?", "revision_new_error", "nerc-var-001-5", [10]),
    ("ambient-mode-estimation", "How long are ambient and ringdown data windows for mode estimation?", "support_quantity", "pnnl-35221", [30,31]),
    ("ambient-mode-estimation", "Does ambient mode estimation always need less data than ringdown analysis?", "comparison_conflict", "pnnl-35221", [31]),
    ("ambient-mode-estimation", "Are all PMU channels equally useful for estimating a mode regardless of observability?", "negation_condition_conflict", "pnnl-35221", [31]),
    ("low-damping-validation", "Does every low damping-ratio estimate prove physical system stress?", "causal_overreach", "pnnl-35221", [31]),
    ("low-damping-validation", "What observations help validate a persistent low damping estimate?", "support_conditions", "pnnl-35221", [31]),
    ("low-damping-validation", "Can a revised explanation rule out algorithm performance as a cause of low damping estimates?", "revision_negation_error", "pnnl-35221", [31]),
    ("research-authority-transfer", "Are PNNL's mode estimation examples legally binding operating requirements for every Chinese grid?", "region_authority_overreach", "pnnl-35221", [1,2,31]),
    ("unsupported-device-threshold", "What mandatory damping alarm threshold and approved mitigation setting should a named Chinese plant use?", "insufficient_input_scope", "pnnl-35221", [30,31]),
]
DEVELOPMENT = [
    ("voltage-stability", "en", "Does normal bus voltage prove that a power system is voltage stable?"),
    ("generator-capability", "en", "What limits a generator's ability to supply reactive power?"),
    ("qv-limitations", "en", "Can QV analysis miss voltage stability problems over a wide area?"),
    ("reactive-reserve", "en", "Does a STATCOM's short overload capability count as reactive reserve?"),
    ("voltage-stability", "zh", "母线电压正常是否足以证明电压稳定？"),
    ("generator-capability", "zh", "发电机提供无功支撑受到哪些运行条件限制？"),
    ("qv-limitations", "zh", "QV分析是否可能遗漏大范围的电压稳定问题？"),
    ("reactive-reserve", "zh", "STATCOM短时过载能力能否计入无功储备？"),
    ("qv-limitations", "acronym", "QV PV analysis limitations"),
    ("reactive-reserve", "acronym", "STATCOM SVC reactive reserve"),
    ("monitoring", "acronym", "PMU VIP RPM FIDVR"),
    ("monitoring", "zh", "PMU怎样监测电压失稳和无功裕度？"),
]


def metrics(rankings, labels, k):
    """Require reviewed, exhaustive fragment-level judgments on this snapshot.

    No-relevant queries are reported separately, not divided by zero. MRR@k
    uses zero when the first relevant item is below k.
    """
    if k < 1:
        raise ValueError("k must be positive")
    eligible, excluded, no_relevant = [], [], []
    for qid, ranking in rankings.items():
        label = labels.get(qid)
        if not label or label.get("status") != "human_confirmed" or not label.get("exhaustive"):
            excluded.append(qid)
            continue
        positive = set(label["relevant_fragment_ids"])
        if not positive:
            no_relevant.append(qid)
            continue
        top = ranking[:k]
        found = positive.intersection(top)
        rr = next((1/rank for rank, fid in enumerate(top, 1) if fid in positive), 0)
        eligible.append((int(bool(found)), len(found)/len(positive), rr))
    if not eligible:
        return {"Hit@k": None, "Recall@k": None, "MRR@k": None, "k": k, "scored_queries": 0,
            "excluded_queries": excluded, "no_relevant_queries": no_relevant,
            "reason": "No exhaustive human-confirmed relevance labels; proposed labels are not truth."}
    return {"Hit@k": sum(x[0] for x in eligible)/len(eligible), "Recall@k": sum(x[1] for x in eligible)/len(eligible),
        "MRR@k": sum(x[2] for x in eligible)/len(eligible), "k": k, "scored_queries": len(eligible),
        "excluded_queries": excluded, "no_relevant_queries": no_relevant}


def prepare(output):
    output.mkdir(parents=True, exist_ok=True)
    target = output / "corpus.sqlite3"
    if target.exists() or (output / "dataset-v1.json").exists():
        raise FileExistsError("Preparation output exists; choose a new directory, never replace a frozen artifact")
    manifest = json.loads((ROOT / "docs/knowledge-sources/manifest.json").read_text(encoding="utf-8"))
    audit = []
    # Backup the baseline into a NEW database, preserving all historical snapshots.
    with KnowledgeStore(ROOT / "data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3", readonly=True) as source:
        import sqlite3
        destination = sqlite3.connect(target)
        source.connection.backup(destination)
        destination.close()
        baseline_members = source._members(source.latest())
    with KnowledgeStore(target) as store:
        for document in manifest["documents"]:
            if not document["local_file"]:
                audit.append({"document_id": document["document_id"], "status": "excluded", "reason": document["download_status"]})
                continue
            path = ROOT / document["local_file"]
            if digest(path.read_bytes()) != document["sha256"]:
                raise ValueError("Official file differs from frozen source manifest")
            doc_id = document["document_id"]
            if doc_id not in baseline_members:
                metadata = SourceMetadata(document["download_url"], document["institution"], document["publication_date_internal"],
                    document["internal_title"], document["document_type"], (document["applicable_region"],))
                result = store.ingest(path, doc_id, metadata)
                store.derive_pdf(doc_id, result.knowledge_version, max_chars=1200)
            # Check new corpus against each existing chunked document version.
            with KnowledgeStore(ROOT / ("data/retrieval_local/pdf-quality/" + doc_id + ".sqlite3"), readonly=True) as old:
                expected = old._members(old.latest())[doc_id]
            actual = store._members(store.latest())[doc_id]
            if actual != expected:
                raise ValueError("New corpus is not using the exact existing document/split version")
            audit.append({"document_id": doc_id, "file_sha256": document["sha256"], "document_version": actual, "existing_version_matches": True})
        kv = store.latest()
        candidates, queries = [], []
        for number, (family, query, suggestion, doc, pages) in enumerate(CANDIDATES, 1):
            qid = f"A{number:02}"
            references = []
            # Whole relevant page fragments, not model-rewritten excerpts. Reviewers
            # narrow these suggested locations and judge relevance independently.
            for row in store.rows(kv):
                if row["document_id"] != doc:
                    continue
                e = store.evidence(row["fragment_id"], kv)
                if e.provenance.file_page in pages:
                    references.append(asdict(e))
            candidates.append({"id": qid, "family": family, "split": FAMILIES[family], "query": query,
                "status": "pending_human_annotation", "suggested_check": suggestion, "human_label": None,
                "suggested_source_pages": pages, "source_references": references,
                "relevant_fragment_ids": None, "exhaustive": False})
            queries.append({"id": qid, "family": family, "split": FAMILIES[family], "language": "en", "query": query})
        for number, (family, language, query) in enumerate(DEVELOPMENT, 1):
            queries.append({"id": f"D{number:02}", "family": family, "split": "development", "language": language, "query": query})
        dataset = {"version": "retrieval-comparison-queries-v1", "knowledge_version": kv, "bm25_config": INDEX_CONFIG,
            "family_assignment": FAMILIES, "annotation_status": "pending_human_annotation", "queries": queries,
            "query_set_sha256": digest(canonical(queries).encode()), "source_audit": audit,
            "independence_warning": "Candidate acceptance families require human leakage/source review; querying them is not quality acceptance. Do not tune on their results."}
        write_new(output / "dataset-v1.json", dataset)
        write_new(output / "annotation-candidates-v1.json", {"knowledge_version": kv, "candidates": candidates})
        lines = ["# 18 个候选：原文与建议检查标签（全部待人工标注）", "",
            "文件页为 1 基；字符区间为该页保存提取文本的 Python [start:end)。下列原文片段未经视觉/语义验收。",
            "建议检查标签不是标准答案，不能据此计算检索指标。标题、条件、地区信息需人工核对。", "",
            "| ID | 问题族 / 分配 | 查询 | 建议检查 / 人工标签 | 来源页 |", "|---|---|---|---|---|"]
        for case in candidates:
            lines.append(f"| {case['id']} | {case['family']} / {case['split']} | {case['query']} | {case['suggested_check']} / 待标注 | {case['suggested_source_pages']} |")
        for case in candidates:
            lines += ["", f"## {case['id']} 原文与定位", ""]
            for e in case["source_references"]:
                p = e["provenance"]
                lines += [f"{e['source_id']}，{e['locator']}；片段 {p['fragment_id']}；Evidence {e['evidence_id']}。", "", "```text", e["text"], "```", ""]
        with (output / "annotation-candidates-v1.md").open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    return dataset


def compare(args):
    if Path(args.output).exists() or Path(args.output).with_suffix(".md").exists():
        raise FileExistsError("Comparison output exists; choose a new name before running")
    from rag.embedding import E5ONNXEncoder
    from rag.semantic import VectorIndex, SemanticRetriever, RRF_VERSION
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if digest(canonical(dataset["queries"]).encode()) != dataset["query_set_sha256"]:
        raise ValueError("Frozen query set hash mismatch")
    encoder = E5ONNXEncoder(args.model_dir)
    results = []
    started = time.perf_counter()
    with KnowledgeStore(args.db, readonly=True) as store, VectorIndex(args.vectors, readonly=True) as index:
        index.load(store, dataset["knowledge_version"], encoder)
        for query in dataset["queries"]:
            record = {**query, "methods": {}}
            request = RetrievalRequest(query["query"], query["id"], RetrievalPurpose.GENERATION, dataset["knowledge_version"], args.k)
            for mode in ("bm25", "dense", "hybrid"):
                phase = time.perf_counter()
                retriever = SemanticRetriever(store, index, encoder, mode=mode)
                value = asyncio.run(retriever.retrieve(request))
                for e in value.evidence:
                    store.verify_evidence(e)
                record["methods"][mode] = {"result": asdict(value), "elapsed_seconds": time.perf_counter() - phase,
                    "evidence_backtrace_valid": True}
            results.append(record)
    labels = {}
    if args.labels:
        label_data = json.loads(Path(args.labels).read_text(encoding="utf-8"))
        if label_data["knowledge_version"] != dataset["knowledge_version"] or label_data["query_set_sha256"] != dataset["query_set_sha256"]:
            raise ValueError("Human labels must bind to exact corpus and frozen queries")
        labels = label_data["labels"]
        with KnowledgeStore(args.db, readonly=True) as store:
            valid_ids = {r["fragment_id"] for r in store.rows(dataset["knowledge_version"])}
            valid_queries = {q["id"] for q in dataset["queries"]}
            if not set(labels) <= valid_queries:
                raise ValueError("Label contains unknown query ID")
            for label in labels.values():
                if not set(label["relevant_fragment_ids"]) <= valid_ids:
                    raise ValueError("Label contains foreign fragment ID")
    report = {"status": "retrieval_comparison_pending_human_review", "dataset": dataset,
        "embedding_profile": encoder.profile, "fusion": RRF_VERSION,
        "elapsed_seconds": time.perf_counter() - started, "results": results,
        "metrics": {}, "peak_working_set_bytes": peak_memory(),
        "metric_scope": "fragment-level, exhaustive human judgments only; no relevance-is-support claim"}
    for mode in ("bm25", "dense", "hybrid"):
        rankings = {r["id"]: [h["fragment_id"] for h in r["methods"][mode]["result"]["hits"]] for r in results}
        report["metrics"][mode] = {split: metrics({qid: ids for qid, ids in rankings.items()
            if next(r for r in results if r["id"] == qid)["split"] == split}, labels, args.k)
            for split in ("development", "frozen_acceptance_candidate")}
    write_new(args.output, report)
    md = ["# BM25 / Dense / RRF：固定语料与查询集对照", "",
        "全部真实资料指标待人工标签；以下变化不代表语义支持、工程安全或质量验收。", "",
        f"知识版本：{dataset['knowledge_version']}；查询集 SHA：{dataset['query_set_sha256']}。", "",
        "| 查询 | BM25 首位 | Dense 首位 | Hybrid 首位 |", "|---|---|---|---|"]
    for r in results:
        columns = []
        for mode in ("bm25", "dense", "hybrid"):
            es = r["methods"][mode]["result"]["evidence"]
            columns.append("空" if not es else f"{es[0]['source_id']} p{es[0]['provenance']['file_page']}")
        md.append(f"| {r['id']} {r['query']} | " + " | ".join(columns) + " |")
    for r in results:
        md += ["", f"## {r['id']}：{r['query']}", "", f"{r['split']} / {r['language']}；人工相关性标签待标注。", ""]
        for mode in ("bm25", "dense", "hybrid"):
            value = r["methods"][mode]["result"]
            md += [f"### {mode}", ""]
            for e, h in zip(value["evidence"], value["hits"]):
                md += [f"rank={h['rank']} score={h['score']:.8f}；{h['scoring_method']}；{e['source_id']}；{e['locator']}。",
                    f"片段 {h['fragment_id']}；Evidence {e['evidence_id']}；适用范围 {e['applicability']}。",
                    f"质量告警：{e['provenance']['quality_warnings']} / {e['provenance']['split_warnings']}。", "", "```text", e["text"], "```", ""]
    with Path(args.output).with_suffix(".md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(md))
    return {"output": args.output, "queries": len(results), "knowledge_version": dataset["knowledge_version"], "metrics": report["metrics"]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--output-dir", default="data/retrieval_local/semantic")
    run = commands.add_parser("compare")
    run.add_argument("--db", required=True)
    run.add_argument("--dataset", required=True)
    run.add_argument("--vectors", required=True)
    run.add_argument("--model-dir", default="data/retrieval_local/semantic/e5-small")
    run.add_argument("--output", required=True)
    run.add_argument("--labels")
    run.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    result = prepare(ROOT / args.output_dir) if args.command == "prepare" else compare(args)
    print(json.dumps(result if args.command == "compare" else {"knowledge_version": result["knowledge_version"], "queries": len(result["queries"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
