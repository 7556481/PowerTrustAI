"""Offline baseline and archived-loop review. Never loads credentials or calls APIs."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from agents.domain_contract_v2 import CONTRACT_VERSION as DOMAIN_CONTRACT, PROMPT_VERSION as DOMAIN_PROMPT
from agents.revision_contract_v2 import CONTRACT_VERSION as REVISION_CONTRACT, PROMPT_VERSION as REVISION_PROMPT
from agents.verification_contract_v8 import CONTRACT_VERSION as EVIDENCE_CONTRACT, PROMPT_VERSION as EVIDENCE_PROMPT
from agents.generation import UNIT_PROMPT_VERSION
from agents.power_domain_review import RULES, RULE_SET_VERSION
from harness.deepseek_trial import PROJECT_ROOT
from rag.bm25 import INDEX_CONFIG
from services.claim_extractor import COMPONENT_PROMPT_VERSION

PRIVATE = PROJECT_ROOT / "data/retrieval_local/deepseek"
KNOWLEDGE = "k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def baseline():
    files = {}
    # Explicit project sources only: no .env, .git, virtualenv or historical prototype.
    for directory in ("agents", "core", "harness", "model_adapter", "rag", "services", "tools", "evaluation", "tests", "docs"):
        for path in sorted((PROJECT_ROOT / directory).rglob("*")):
            if path.is_file() and path.suffix in (".py", ".md", ".json"):
                files[path.relative_to(PROJECT_ROOT).as_posix()] = sha(path)
    for name in ("README.md", "requirements.txt", "requirements-pdf.txt", ".gitignore"):
        path = PROJECT_ROOT / name
        if path.exists():
            files[name] = sha(path)
    fingerprint = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    history = []
    for name in ("stability-minimal-v2.json", "stability-minimal-v3-rereview.json"):
        path = PRIVATE / name
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data["runs"][0]["result"]["model_records"]
        history.append({"file": str(path), "sha256": sha(path),
                        "prompts": sorted({r["prompt_version"] for r in records}),
                        "contracts": sorted({r.get("response_contract_version") for r in records if r.get("response_contract_version")}),
                        "model_ids": sorted({r["returned_model_id"] for r in records if r["returned_model_id"]}),
                        "source_revision": "No historical complete code manifest or root Git commit was saved; exact historical code cannot be reconstructed from version labels alone."})
    return {"baseline_id": "acceptance-preparation-v1-" + fingerprint[:16],
            "captured_utc": datetime.now(timezone.utc).isoformat(), "source_fingerprint_sha256": fingerprint,
            "source_files": files, "git_commit": None,
            "git_note": "New project root is not a Git checkout; use reproducible per-file SHA-256 manifest, not an invented commit.",
            "knowledge_version": KNOWLEDGE,
            "knowledge_db": str(PROJECT_ROOT / "data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3"),
            "index_config": INDEX_CONFIG,
            "current": {"generation": UNIT_PROMPT_VERSION, "claim_extraction": COMPONENT_PROMPT_VERSION,
                        "evidence": {"contract": EVIDENCE_CONTRACT, "prompt": EVIDENCE_PROMPT},
                        "domain": {"contract": DOMAIN_CONTRACT, "prompt": DOMAIN_PROMPT,
                                   "delivery": "protocol_v2_current_domain_retrieval_plus_user_references"},
                        "revision": {"contract": REVISION_CONTRACT, "prompt": REVISION_PROMPT},
                        "policy": ["limited-repair-policy-v1", "coverage-gate-v1"],
                        "rules_version": RULE_SET_VERSION, "rules": [asdict(r) for r in RULES]},
            "historical_success": history,
            "mapping_note": "Historical successful chain links v2 first review/revision to v3 rereview. Current baseline additionally narrows domain delivery; prompt labels unchanged, harness/runtime.py hash differentiates it.",
            "future_only": ["Embedding adapters and vector indices", "Hybrid retrieval and separate retrieval-quality evaluation",
                            "Evidence-support judgment fine-tuning with independently human-reviewed training/evaluation sets"]}


def archived_review():
    path = PRIVATE / "stability-minimal-v3-rereview.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    run = data["runs"][0]
    prior = run["prior_source"]
    assert sha(Path(prior["path"])) == prior["sha256"]
    first, revision, result = prior["retained_round"], prior["retained_revision"], run["result"]
    final = result["review_rounds"][0]
    known = {e["evidence_id"]: e for e in result["evidence"]}
    checks = []
    for label, round_ in (("initial", first), ("rereview", final)):
        answer = round_["answer"]
        for claim in round_["verification"]["claims"]:
            assert answer["text"][claim["start_offset"]:claim["end_offset"]] == claim["text"]
            checks.append({"kind": "claim_anchor", "phase": label, "id": claim["claim_id"], "valid": True})
        for out in (round_["verification"], round_["domain_review"]):
            for finding in out["findings"] + out.get("citation_reviews", []):
                for basis in finding.get("bases", []):
                    if basis["type"] == "text_excerpt":
                        excerpt = basis["excerpt"]
                        assert known[basis["evidence_id"]]["text"][excerpt["start_offset"]:excerpt["end_offset"]] == excerpt["text"]
                        checks.append({"kind": "literal_evidence_anchor", "phase": label,
                                       "id": basis["quote_id"], "valid": True})
    actions = {a["finding_id"]: a for a in revision["finding_actions"]}
    all_first = first["verification"]["findings"] + first["domain_review"]["findings"]
    assert set(actions) == {f["finding_id"] for f in all_first}
    old_ids = [f["finding_id"] for f in first["verification"]["findings"]]
    assessments = {
        old_ids[0]: "原错误断言从正文删除，并改为 does not by itself prove；字面修改可确认。QV/电压准则材料只是间接依据，contradicted 和修订后 supported 的语义标签仍需人工核实，不能把相关概念分开讨论等同于严格逻辑反证。",
        "domain-analysis_scope": "删掉保证稳定的断言，v2 明确不作具体电厂结论；从正文可确认范围收缩。新加入电厂缺输入和 QV 解释，超出了最初单一概念问题。",
        "domain-input_units:units-input": "仍 not_assessable。没有结构化数量并不代表模型请求失败；在无数量的概念问题上将它作为必须完成的门槛疑似过于保守，待人工确认。",
        "domain-simulation_boundary": "仍 not_assessable；当前未实现仿真，措辞修改无法完成工程验证。概念解释是否必须因未仿真留作整体未通过，需要后续验收规则决策，本轮不修改。",
        "domain-engineering_inputs": "首轮和重审均 not_applicable；无具体电厂研究输入，未生成工程结论。",
        "domain-answer_units": "首轮 not_applicable，重审 not_applicable；正文没有数字单位，不能外推为完成所有单位审核。",
        "domain-operating_prerequisites": "首轮 not_applicable、重审 no_issue；正文只是请求研究输入，无操作指令。状态变化不是工程可行性证明。"}
    rows = [{"finding_id": f["finding_id"], "first": f, "revision_action": actions[f["finding_id"]],
             "offline_assessment": assessments[f["finding_id"]],
             "final_same_rule": next((g for g in final["domain_review"]["findings"] if g["finding_id"] == f["finding_id"]), None)}
            for f in all_first]
    archived = []
    for source in (PRIVATE / "stability-minimal-v2.json", path):
        payload = json.loads(source.read_text(encoding="utf-8"))
        for record in payload["runs"][0]["result"]["model_records"]:
            raw_path = Path(record["diagnostic_path"])
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            assert hashlib.sha256(raw["response_text"].encode()).hexdigest() == raw["response_sha256"]
            archived.append({"file": str(raw_path), "sha256": sha(raw_path),
                             "prompt_version": record["prompt_version"], "contract": record.get("response_contract_version"),
                             "output_status": record["output_status"], "errors": record["validation_error"]})
    return {"scope": "OFFLINE_REVIEW_NOT_HUMAN_ACCEPTANCE", "source": str(path), "sha256": sha(path),
            "first_answer": first["answer"], "revision": revision, "finding_comparison": rows,
            "final_answer": final["answer"], "final_round": final, "decision": result["report"]["decision"],
            "execution_issues": result["execution_issues"], "automatic_anchor_checks": checks, "archives": archived,
            "evidence": list(known.values()),
            "manual_flags": [
                "uncovered_spans 为空；non_claim_spans 包含 No. 与澄清问题。coverage-gate 把任意 non_claim_spans 也列为覆盖缺口，提示不能证明技术内容实际漏审。",
                "QV 片段从上一页衔接处开始，末尾止于 allowed to respond as；静态无功锁定、动态响应和宽区域限制可能需要相邻页视觉核对。",
                "修订及重审的主要 applicability_conditions 未完整保留首轮 North American/voluntary/region-specific 限定；Evidence 元数据仍保留地区，不代表回答已向读者说明。",
                "Absolute voltage criteria … rather than as a stability assessment 是超出逐字原文的推论，需检查原文其他章节；不因摘录存在而自动判支持。",
                "answer_scope 用回答本身验证声明存在，不能独立证明 cannot be drawn 的工程理由。",
                "完整输入快照可以验证输入集合；无执行产物不独立证明无仿真，须结合实际工作流执行记录/演示规则。历史核验理由过度依赖 absence of artifacts。",
                "新增加 QV 定义和电厂输入声明，增加了主张数量与引用范围；后续需逐主张人工评估是否必要、有支持且保留限定。"]}


def render_review(data):
    lines = ["# 最小闭环逐发现离线复核", "", "历史记录只读；此报告不是人工标签或工程安全认证。",
             "", "## 原错误与修订正文", "", data["first_answer"]["text"], "",
             "修订后：", "", data["final_answer"]["text"], "", "## 每个 finding 的处理", ""]
    for row in data["finding_comparison"]:
        f, action = row["first"], row["revision_action"]
        lines += [f"### {row['finding_id']}", "",
                  f"首轮：{f.get('status', f.get('check_status'))}；{f['rationale']}",
                  f"Revision：{action['action']}；{action['explanation']}",
                  "离线复核：" + row["offline_assessment"], ""]
    lines += ["## 修订后逐主张及支持依据", ""]
    claims = {c["claim_id"]: c for c in data["final_round"]["verification"]["claims"]}
    for f in data["final_round"]["verification"]["findings"]:
        lines += [f"- {f['claim_id']}：{claims[f['claim_id']]['proposition']}",
                  f"  模型标签={f['status']}；依据类型={[b['type'] for b in f['bases']]}；理由={f['rationale']}"]
    lines += ["", "## 最终决策与执行/业务区分", "", json.dumps(data["decision"], ensure_ascii=False, indent=2),
              "", "执行：重审 extraction、independent review、domain review、original-citation review 最终完成；execution_issues=[]。",
              "业务：单位检查未完成、工程仿真未执行仍保留；非主张文本触发保守 coverage-gate。",
              "历史 v2 重审原引用结构失败仍是失败；v3 是新重审，不是改写历史状态。", "",
              "## 条件、推论与疑似误报待人工复核", ""]
    lines += ["- " + flag for flag in data["manual_flags"]]
    lines += ["", "## 可回查原文（PDF 提取文本，不等于视觉原文）", ""]
    used = {b["evidence_id"] for side in ("verification", "domain_review")
            for f in data["final_round"][side]["findings"] for b in f.get("bases", []) if b["type"] == "text_excerpt"}
    for e in data["evidence"]:
        if e["evidence_id"] in used:
            p = e.get("provenance") or {}
            lines += [f"Evidence {e['evidence_id']}；文件页 {p.get('file_page')}；{e['locator']}",
                      f"源文件 SHA={p.get('file_sha256')}；quality={p.get('quality_warnings')}", "~~~text", e["text"], "~~~", ""]
    lines += ["逐字定位检查通过仅证明区间一致，不证明语义支持。完整原文/逐调用归档校验结果在同名 JSON。"]
    return "\n".join(lines) + "\n"


def main():
    base = baseline()
    review = archived_review()
    write_new(PRIVATE / "acceptance-baseline-v1.json", base)
    write_new(PRIVATE / "acceptance-minimal-offline-v1.json", review)
    write_new(PRIVATE / "acceptance-minimal-offline-v1.md", render_review(review))
    print(json.dumps({"baseline_id": base["baseline_id"], "archives_checked": len(review["archives"]),
                      "anchor_checks": len(review["automatic_anchor_checks"]), "finding_actions": len(review["finding_comparison"])}))


if __name__ == "__main__":
    main()
