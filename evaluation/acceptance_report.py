"""Offline accounting and human-readable acceptance-preparation report."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from evaluation.acceptance_preparation import PRIVATE, KNOWLEDGE, sha, write_new
from evaluation.archive_replay import replay_failed_review
from harness.deepseek_trial import fee_summary


def build():
    files = [PRIVATE / f"acceptance-real-v{i}.json" for i in range(1, 5)]
    payloads = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    records, steps, sources, errors = [], [], [], []
    for path, data in zip(files, payloads):
        assert len(data["model_records"]) == data["actual_model_calls"]
        sources.append({"path": str(path), "sha256": sha(path), "calls": data["actual_model_calls"],
                        "baseline_id": data["baseline_id"]})
        if data.get("prior_source"):
            parent = data["prior_source"]
            assert sha(Path(parent["path"])) == parent["sha256"]
        for stage in data["stages"]:
            if stage["status"] == "not_started_budget":
                continue
            assert stage["actual_requests"] <= stage["worst_requests"]
            result = stage.get("result") or {}
            stage_records = result.get("model_records", stage.get("model_records", []))
            for record in stage_records:
                raw = json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))
                assert hashlib.sha256(raw["response_text"].encode()).hexdigest() == raw["response_sha256"]
                assert raw["prompt_version"] == record["prompt_version"]
                purpose = None
                if record.get("candidate_catalog_path"):
                    catalog = json.loads(Path(record["candidate_catalog_path"]).read_text(encoding="utf-8"))
                    digest = catalog.pop("scope_sha256")
                    assert hashlib.sha256(json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()).hexdigest() == digest
                    purpose = catalog["purpose"]
                    assert catalog["knowledge_version"] == KNOWLEDGE
                    assert all(q["quote_id"].startswith(catalog["scope_id"] + "-") for q in catalog["QUOTE_CANDIDATES"])
                    assert len(catalog["QUOTE_CANDIDATES"]) == record["request_metrics"]["candidate_count"]
                steps.append({"file": path.name, "stage": stage["label"], "purpose": purpose,
                              **{k: record[k] for k in ("prompt_version", "response_contract_version", "returned_model_id",
                                  "correction", "duration_ms", "output_status", "usage", "request_metrics")}})
                if record["validation_error"]:
                    diagnostic = record["validation_error"]
                    for error in diagnostic.get("errors", [diagnostic]):
                        errors.append({"file": path.name, "stage": stage["label"], "correction": record["correction"],
                                       "field_path": error["field_path"], "constraint": error["constraint"],
                                       "retained_items": diagnostic.get("retained_items", [])})
        records.extend(data["model_records"])
    assert len(steps) == len(records) == 38
    latest = payloads[-1]
    snapshots = []
    anchor_checks = 0
    for run in latest["runs"]:
        revision = run["revision"]
        initial = run["initial"]
        assert {a["finding_id"] for a in revision["finding_actions"]} == {
            f["finding_id"] for output in (initial["verification_output"], initial["domain_output"]) for f in output["findings"]}
        snapshot = revision["evidence_snapshot"]
        snapshots.append({"scenario": run["scenario"], "snapshot_id": snapshot["snapshot_id"],
                          "snapshot_version": snapshot["snapshot_version"], "evidence_count": len(snapshot["evidence"]),
                          "evidence_chars": sum(len(e["text"]) for e in snapshot["evidence"]),
                          "knowledge_version": snapshot["knowledge_version"]})
        result = run["rereview"]
        answer, known = result["answer"], {e["evidence_id"]: e for e in result["evidence"]}
        for claim in result["extraction_output"]["claims"]:
            assert answer["text"][claim["start_offset"]:claim["end_offset"]] == claim["text"]
            anchor_checks += 1
        for output in (result["verification_output"], result["domain_output"]):
            for finding in output["findings"] + output.get("citation_reviews", []):
                for basis in finding.get("bases", []):
                    if basis["type"] == "text_excerpt":
                        q = basis["excerpt"]
                        assert known[basis["evidence_id"]]["text"][q["start_offset"]:q["end_offset"]] == q["text"]
                        anchor_checks += 1
        for record in revision["model_records"]:
            archive = json.loads(Path(record["input_snapshot_path"]).read_text(encoding="utf-8"))
            assert archive["evidence"] == snapshot["evidence"]
            assert archive["question"] == snapshot["question"]
            assert archive["engineering_context"] == snapshot["engineering_context"]
    baseline = json.loads((PRIVATE / "acceptance-baseline-v4.json").read_text(encoding="utf-8"))
    root = PRIVATE.parents[2]
    assert all(sha(root / p) == value for p, value in baseline["source_files"].items())
    historical = json.loads((PRIVATE / "acceptance-minimal-offline-v1.json").read_text(encoding="utf-8"))
    assert sha(Path(historical["source"])) == historical["sha256"]
    assert all(sha(Path(r["file"])) == r["sha256"] for r in historical["archives"])
    db = baseline["knowledge_db"]
    with sqlite3.connect(Path(db).as_uri() + "?mode=ro", uri=True) as con:
        index_row = con.execute("SELECT index_version,created_utc FROM snapshots WHERE knowledge_version=?", (KNOWLEDGE,)).fetchone()
        pdf_derivations = con.execute("SELECT document_id,version,source_version,split_config,plan_sha256 FROM pdf_derivations").fetchall()
    stages = []
    for version in dict.fromkeys(s["prompt_version"] for s in steps):
        group = [s for s in steps if s["prompt_version"] == version]
        stages.append({"prompt_version": version, "calls": len(group),
                       "input_tokens": sum((s["usage"] or {}).get("input_tokens") or 0 for s in group),
                       "output_tokens": sum((s["usage"] or {}).get("output_tokens") or 0 for s in group),
                       "candidate_count": sum(s["request_metrics"]["candidate_count"] for s in group),
                       "evidence_chars": sum(s["request_metrics"]["evidence_chars_delivered"] for s in group),
                       "duration_ms_sum": sum(s["duration_ms"] for s in group)})
    return {"scope": "ACCEPTANCE_PREPARATION_NOT_ENGINEERING_CERTIFICATION",
            "sources": sources, "new_requests": len(records), "usage": {
                k: sum((r["usage"] or {}).get(k) or 0 for r in records) for k in ("input_tokens", "output_tokens", "total_tokens")},
            "cost_estimate": fee_summary(records), "output_status_counts": dict(Counter(r["output_status"] for r in records)),
            "model_ids": sorted({r["returned_model_id"] for r in records}), "current_baseline": baseline,
            "knowledge_snapshot_index": {"knowledge_version": KNOWLEDGE, "index_config": json.loads(index_row[0]),
                                        "created_utc": index_row[1], "pdf_derivations": pdf_derivations},
            "narrowing_validation": payloads[0]["narrowing_validation"],
            "snapshots": snapshots, "automatic_literal_anchor_checks": anchor_checks,
            "historical_integrity_checks": True, "stages": stages, "steps": steps, "failures": errors,
            "offline_replays": {"engineering_initial_and_correction": replay_failed_review(files[0]),
                               "quantity_initial_and_correction": replay_failed_review(files[1], "quantity-unit-error")},
            "final_runs": latest["runs"], "tests": {"interpreter": r"D:\PowerTrustAI\.venv\Scripts\python.exe",
                                                     "note": "Final unittest result appended after completion; ordinary tests are offline."}}


def render(data):
    lines = ["# 闭环验收准备统一报告", "",
             "真实 API + 人工构造开发案例；全部结果仍是 review_required，不是独立验收成功或工程安全认证。",
             f"本轮新增 {data['new_requests']} 次：首次 19；用户追加授权后 12 + 2 + 5。",
             f"实际模型：{data['model_ids']}；token={json.dumps(data['usage'], ensure_ascii=False)}。",
             f"费用按归档 2026-10-02 价格估算，不是账单：{json.dumps(data['cost_estimate'], ensure_ascii=False)}", "",
             "## 版本对应与知识", "", f"最终执行基线：{data['current_baseline']['baseline_id']}",
             "没有根目录 Git commit；各基线以逐文件 SHA-256 固定，历史没有完整代码快照的部分明确未知。",
             "输出契约保持 v8.2；v8.2.1 补显式 bases 示例；v8.2.2 补冻结分类与已有 classification_issue 的使用边界。",
             "领域 output-v2、Revision output-v2、power-demo-rules-v1 未扩展。BM25、分词、PDF 切分未修改。",
             f"知识版本：{KNOWLEDGE}；PDF 派生配置及真实索引配置在同名 JSON。",
             "旧最小闭环：stability-minimal-v2 首轮/Revision + stability-minimal-v3-rereview 重审；旧失败仍是失败。",
             "本轮 v1 先真实验证收紧交付，v2 工程重审完成，v4 数量重审完成；对应四个代码基线分别保存。", "",
             "| 文件 | 基线 | 新请求 |", "|---|---|---:|"]
    for source in data["sources"]:
        lines.append(f"| {Path(source['path']).name} | {source['baseline_id']} | {source['calls']} |")
    narrow = data["narrowing_validation"]
    lines += ["", "## 领域交付收紧的实际验证", "",
              f"本轮领域实际收到 {len(narrow['actual_model_catalog_evidence_ids'])} 个候选 Evidence，"
              f"其集合与当前领域检索匹配；排除 {len(narrow['excluded_saved_only_ids'])} 个旧保存集合的额外 ID。",
              "检查依据是实际候选归档及检索轨迹，不是仅检查 Python 参数。不能将候选数变化当检索质量提升。", "",
              "## 原最小闭环离线复核", "",
              "完整逐 finding 对照见 acceptance-minimal-offline-v1.md：原错误断言确实从正文删除。",
              "QV/电压准则只是间接支持，首轮 contradicted 与最终 supported 的语义关系仍需人工复核。",
              "uncovered_spans=[]；coverage-gate 的覆盖缺口由非主张 No. 和澄清问题触发，不能证明技术事实漏审。",
              "单位未评估、未仿真是业务边界，不是执行失败；概念题也强制这些门槛疑似过于保守。",
              "地区/自愿性限定在新回答及部分 finding 中未完整保留；Evidence 元数据存在不等于用户已获告知。", "",
              "## 本轮逐发现修订与重审", ""]
    for run in data["final_runs"]:
        initial, revision, final = run["initial"], run["revision"], run["rereview"]
        lines += [f"### {run['scenario']}", "", "输入明确标记 human_constructed_synthetic_fixture_error。",
                  "原始错误：", "", initial["answer"]["text"], "", "修订正文：", "", revision["answer"]["text"], "",
                  f"有效阶段链完整={run['loop_execution_complete']}；最终={final['state']}。",
                  "单次无失败端到端运行未实现；该链包含保存的有效初始审核、一次 Revision 与新重审。"]
        if run["scenario"] == "quantity-unit-error":
            lines += ["数量场景最终提取来自 acceptance-real-v2 的同一冻结 v2 回答；v3 的两次提取失败不改写为成功。",
                      "在 v4 中仅复用已接受的真实提取输出，并重新执行两类审核；归档链、回答正文、版本、引用与知识均校验。"]
        old_findings = {f["finding_id"]: f for out in (initial["verification_output"], initial["domain_output"]) for f in out["findings"]}
        final_domains = {f["finding_id"]: f for f in final["domain_output"]["findings"]}
        for action in revision["finding_actions"]:
            finding = old_findings[action["finding_id"]]
            after = final_domains.get(action["finding_id"])
            lines += ["", f"- {action['finding_id']}",
                      f"  首轮 {finding.get('status', finding.get('check_status'))}：{finding['rationale']}",
                      f"  Revision {action['action']}：{action['explanation']}",
                      "  重审：" + (f"{after['check_status']}；{after['rationale']}" if after else
                                  "主张 ID 随修订改变，不能按旧 ID 自动宣告解决；以下按新主张核对。")]
        claims = {c["claim_id"]: c for c in final["verification_output"]["claims"]}
        lines += ["", "修订后逐主张（标签是模型判断，不是人工真值）：", ""]
        for f in final["verification_output"]["findings"]:
            lines += [f"- {f['claim_id']}：{claims[f['claim_id']]['proposition']}；{f['status']}；{f['rationale']}"]
            for component in f["component_reviews"]:
                if component["classification_issue"]:
                    lines += [f"  显式分类异议：{json.dumps(component['classification_issue'], ensure_ascii=False)}"]
        lines += ["", "原引用独立检查：", ""]
        for citation in final["verification_output"]["citation_reviews"]:
            lines += [f"- binding {citation['citation_index']}：{citation['status']}；{citation['rationale']}"]
        lines += ["", "最终程序决策：", "", "~~~json", json.dumps(final["report"]["decision"], ensure_ascii=False, indent=2),
                  "~~~", f"最终 execution_issues={json.dumps(final['execution_issues'], ensure_ascii=False)}", "",
                  "未解决业务项包括输入质量/单位、缺证据及未执行仿真；完成审核不等于解决全部业务问题。"]
    lines += ["", "## 确认的真实失败与改动边界", "",
              "- v1 提取非主张与主张重叠、answer_scope 错用 snapshot：一次纠正有效。",
              "- v1 工程混合 finding 初次 supported 无快照 bases；纠正 bases=[] 却索引 [0]。离线重放同路径同约束仍失败；v8.2.1 只补合法示例/错误信息。",
              "- v2 数量混合 finding 把被冻结的 technical_fact 用 snapshot 支持，纠正后仍违规。未删字段或补造依据；v8.2.2 明确现有分类异议边界。",
              "- v3 提取初次 exact_source_quote_with_adjacent_context_not_found，纠正 must_be_literal_substring_of_source_quote。提取仍不稳定，没有通过模糊匹配或放宽限定词规则。",
              "- v4 保留真实有效提取重新审核；初次仍有错误，只允许一次格式纠正，最终结构执行完成。",
              "- 历史所有失败继续保留；有效 atomic finding 被保留，不将被拒绝 finding 伪装为已完成。", "",
              "## 人工重点复核", "",
              "- 工程修订确实删除 safely/guarantee 保证，但两段原引用均不足以支持具体输入缺失及数据清单；可定位引用不等于支持。",
              "- 数量修订不再把有功输出列为第四类额定值，并否定原单位/等值错误；这些字面修改可查，最终输入原始错误仍存在，不能靠重写回答修复用户数据。",
              "- 数量场景技术常识与输入描述混合，上游分类仍有疑点；最终部分 insufficient_evidence 反映当前事实审核依据能力，不代表 SI 规则错误。",
              "- v2 数量原引用 binding 1 被模型标 contradicted，而 v4 标 insufficient_evidence；原文不含完整输入/单位定义，先者疑似误报，待人工核实。",
              "- 首轮型号/额定值数量被判 insufficient_evidence 而非 contradicted；程序枚举捕获 4/3，但不将模型标签当已解决真实漏检。",
              "- 原最小场景的 QV 跨页限定和 North American/voluntary 范围未充分带入正文；需视觉核对。",
              "- 关于未仿真的事实应参考实际运行轨迹，不能仅从快照缺少产物推断。", "",
              "## 分阶段用量与交付开销", "",
              "| 提示词版本 | 请求 | input token | output token | 候选累计 | 证据字符累计 | 耗时累计 ms |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for s in data["stages"]:
        lines.append(f"| {s['prompt_version']} | {s['calls']} | {s['input_tokens']} | {s['output_tokens']} | {s['candidate_count']} | {s['evidence_chars']} | {s['duration_ms_sum']} |")
    lines += ["", "累计耗时包含并发，不能当墙钟时长；字符和候选是每次真实交付量，含格式纠正。",
              "重复开销来自多次格式纠正、混合主张的重复组件以及多次原引用全文交付；本轮未裁剪限定条件或优化 BM25。", "",
              "## 每次请求", "",
              "| 文件/阶段 | 目的 | 纠正 | input/output | 候选 | 证据字符 | ms | 输出结构 |",
              "|---|---|---|---|---:|---:|---:|---|"]
    for s in data["steps"]:
        u, m = s["usage"] or {}, s["request_metrics"]
        lines.append(f"| {s['file']} / {s['stage']} | {s['purpose'] or s['prompt_version']} | {s['correction']} | {u.get('input_tokens')}/{u.get('output_tokens')} | {m['candidate_count']} | {m['evidence_chars_delivered']} | {s['duration_ms']} | {s['output_status']} |")
    lines += ["", "## 统计和验收边界", "",
              "有效阶段链：两个构造场景最终 2/2，有重试与真实已接受提取的明确复用；不是两次无失败独立运行。",
              f"单次模型响应结构统计：{data['output_status_counts']}；不能作为语义准确率。",
              "18 个新验收候选见 docs/acceptance-candidates-v1.md，未真实运行，全部标签待人工核实。",
              "问题族整族隔离开发/验收；执行完成率、语义混淆矩阵及修订新增错误率分开统计。",
              "Embedding、向量索引、混合检索、证据支持微调已列入后续路线，本轮未实现。",
              "普通测试结果与实际解释器见同名 JSON/最终追加段。", "",
              "## 可回查原文", ""]
    seen = set()
    for run in data["final_runs"]:
        result = run["rereview"]
        known = {e["evidence_id"]: e for e in result["evidence"]}
        for output in (result["verification_output"], result["domain_output"]):
            for f in output["findings"] + output.get("citation_reviews", []):
                for b in f.get("bases", []):
                    if b["type"] != "text_excerpt" or b["quote_id"] in seen:
                        continue
                    seen.add(b["quote_id"])
                    e, q = known[b["evidence_id"]], b["excerpt"]
                    p = e["provenance"]
                    lines += [f"Quote {b['quote_id']}；Evidence {e['evidence_id']}；文件页 {p['file_page']}；{e['locator']}",
                              f"原文件 SHA {p['file_sha256']}；片段区间 [{q['start_offset']}:{q['end_offset']})；quality={p['quality_warnings']}",
                              "~~~text", q["text"], "~~~", ""]
    lines += ["原文为保存的 PDF 提取文本，尚需视觉核对；逐字一致不是语义支持证明。"]
    return "\n".join(lines) + "\n"


def main():
    data = build()
    write_new(PRIVATE / "acceptance-summary-v1.json", data)
    write_new(PRIVATE / "acceptance-summary-v1.md", render(data))
    print(json.dumps({"requests": data["new_requests"], "usage": data["usage"],
                      "cost": data["cost_estimate"], "literal_checks": data["automatic_literal_anchor_checks"]}))


if __name__ == "__main__":
    main()
