"""Offline development report. No credential loader or API/model client calls."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from core.models import QuoteCandidate
from harness.deepseek_trial import fee_summary
from services.quantity_checks import enumeration_check

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/"data/retrieval_local/deepseek"
FILES=("power-review-fresh-case1-v1.json","power-review-fresh-case1-v2.json","power-review-fresh-case1-domain-retry-v1.json",
       "power-review-fresh-case2-case3-v1.json","power-review-fresh-case3-v2.json","power-review-fresh-case2-v2.json")


def build():
    records=[];attempts=[];sources=[]
    for name in FILES:
        path=LOCAL/name;raw=path.read_bytes();d=json.loads(raw);sources.append({"path":str(path),"sha256":hashlib.sha256(raw).hexdigest()})
        if "runs" not in d:
            records.extend(d["model_records"]);attempts.append({"file":name,"kind":"domain_component_retry","case":1,"calls":d["actual_model_calls"],"execution_issues":d["domain_output"]["execution_issues"]})
        else:
            for run in d["runs"]:
                gen=run["generation"]["result"];review=run.get("review")
                records.extend(gen["model_records"])
                if review:records.extend(review["model_records"])
                attempts.append({"file":name,"case":run["case"],"calls":len(gen["model_records"])+(0 if not review else len(review["model_records"])),
                    "generation_state":gen["state"],"review_state":None if not review else review["state"],
                    "generation_issues":gen["execution_issues"],
                    "verification_issues":None if not review else review["verification_output"]["execution_issues"],
                    "domain_issues":None if not review else review["domain_output"]["execution_issues"]})
    assert len(records)<=20
    usage={k:sum((r.get("usage") or {}).get(k) or 0 for r in records) for k in ("input_tokens","output_tokens","total_tokens","cache_hit_tokens","cache_miss_tokens")}
    unknown_usage=sum(r.get("usage") is None for r in records)
    old=LOCAL/"evidence-review-q3-v6-run1.json";old_raw=old.read_bytes();historic=json.loads(old_raw)["runs"][0]["result"]["verification_output"]
    def catalog(output):
        return {c["quote_id"]:QuoteCandidate(**dict(c,warnings=tuple(c["warnings"]))) for c in output["quote_candidates"]}
    candidates=catalog(historic);claim=historic["claims"][0];finding=historic["findings"][0]
    probe=enumeration_check(claim["proposition"],tuple(candidates[b["quote_id"]] for b in finding["bases"] if b["type"]=="text_excerpt"),claim["claim_id"])
    semantic_miss={"scope":"REAL_ARCHIVED_DEVELOPMENT_MISS_NOT_INDEPENDENT_ACCEPTANCE","source":str(old),"source_sha256":hashlib.sha256(old_raw).hexdigest(),
        "claim":claim,"original_component_statuses":finding["component_reviews"],"current_program_check":asdict(probe),"original_bases":finding["bases"]}
    fresh=json.loads((LOCAL/"power-review-fresh-case3-v2.json").read_text(encoding="utf-8"))["runs"][0]["review"]["verification_output"]
    quotes=catalog(fresh);claims={c["claim_id"]:c for c in fresh["claims"]};recomputed=[]
    for f in fresh["findings"]:
        old_check=next(c for c in fresh["consistency_checks"] if c["claim_id"]==f["claim_id"])
        if old_check["status"]=="warning":
            check=enumeration_check(claims[f["claim_id"]]["proposition"],tuple(quotes[b["quote_id"]] for b in f["bases"] if b["type"]=="text_excerpt"),f["claim_id"])
            recomputed.append({"claim_id":f["claim_id"],"proposition":claims[f["claim_id"]]["proposition"],"original_program_check":old_check,"current_program_check":asdict(check),
                "note":"offline recomputation under v1.1; does not replace original run or certify semantics"})
    assert all(v["current_program_check"]["status"]=="incomplete" for v in recomputed)
    summary={"scope":"LIMITED_POWER_REVIEW_DEVELOPMENT_NO_CERTIFICATION","new_requests":len(records),"cap":20,"remaining_not_used":20-len(records),
        "usage_known_only":usage,"usage_unknown_requests":unknown_usage,"cost_summary":fee_summary(records),
        "execution_rates":{"new_answer_scenarios_completed":"2/3 (66.7%)","paid_generation_attempts_completed":"2/4 (50%); wrong-version 0-call preflight excluded",
            "first_dual_review_executions_completed":"1/2 accepted-answer scenarios (50%)",
            "distinct_scenarios_with_both_reviews_completed_after_component_retry":"2/3 planned (66.7%)",
            "full_input_v2_accepted_real_generations":"0; implemented after earlier evidence-only snapshots, last generation failed",
            "engineering_feasibility_calculations":"0; no simulation"},"attempts":attempts,"sources":sources,
        "archived_q3_real_semantic_miss":semantic_miss,"new_quantity_false_positive_offline_repairs":recomputed,
        "stop_reason":"Fresh case2 citation quote absent from answer repeated after one specific format correction; no further paid calls"}
    lines=["# 最小领域审核：本轮实现、真实验证与限制","",
        "没有整体审核 pass、安全认证、仿真或修订。工程输入均为 synthetic_fixture，官方资料仍为固定 NERC 文档索引。下述完成率是执行完成率，不是语义正确率。",
        "", "## 执行情况", "", "| 记录 | 场景 | 请求 | 结果 |", "| --- | --- | --- | --- |"]
    for a in attempts:
        lines.append(f"| {a['file']} | {a['case']} | {a['calls']} | "+(str(a["execution_issues"]) if a.get("kind") else f"{a['generation_state']} / {a['review_state']}")+" |")
    lines += ["",f"总新增请求 {len(records)}/20；剩余 {20-len(records)} 次未使用，已停止。",
        f"已返回 token 小计：{json.dumps(usage)}。{unknown_usage} 次服务拒绝未返回 token；没有编造为零用量。",
        f"费用估计：{json.dumps(summary['cost_summary'])}。按项目保存的 2026-10-02 价格与服务返回缓存用量估算，不是账单；未知用量请求不包含在小计内。",
        "", "执行完成率：新回答场景 2/3；有模型请求的生成尝试 2/4（排除错误知识版本的零调用预检）；首次双审核 1/2 个有效回答；组件修复后，两类审核均完成的场景为计划中的 2/3。",
        "", "## 确认的失败、漏检和误报", "",
        "1. 旧第 3 题真实语义漏检保留：模型 supported 的技术部分声称 four equipment ratings；原文列三个额定值＋有功输出。当前有限枚举程序返回 4 对 3 警告。父级 not_assessable 不能掩盖子判断漏检。完整原文、Evidence/quote ID 与文件页 8 在下方及旧归档可回查。",
        "2. 新场景 3 的数量程序 v1 误报：把 not to four equipment ratings / phrasing is a paraphrase 当成肯定计数。v1.1 离线修复后返回 incomplete / count_assertion_polarity_or_attribution_unclear，不称回答数量错误。保留原警告与新计算的并列记录；未再付费重跑此场景。",
        "3. 场景 1 领域模型 v1.1 的疑似过度告警：回答明确否定正常电压可证明稳定、列出仍需分析，模型仍因未执行分析、未提供网络前提给 warning。后续 v1.2 提示词限定实际越界断言与操作建议；场景 3 能输出 analysis_scope=no_issue、operating_prerequisites=not_applicable。但场景 1 没有在 v1.2 下重新验证，不能宣布其误报已真实消除。",
        "4. 新场景 3 正文已指出 MW/MVAR 与 230 kV/230 V 不一致；程序结构化输入检查也确实检测到维度/同参考对象数值不一致。这是输入告警，不等于生成回答错误。模型 answer_units=warning 的理由也指输入未澄清，应避免误读为正文单位漏检。",
        "5. 新场景 3 的输入覆盖模型以 Evidence-only 快照不包含 Q/电压输入为由给 insufficient_evidence。工程输入在场景记录中存在，但旧快照只覆盖证据，不覆盖问题/用户上下文。新 full-input-v2 绑定这些字段，旧快照仍不补齐；分类与引用范围仍需要人工复核。",
        "6. 场景 2 原生成器两次失败没有原始输出或具体错误，历史根因无法还原。补归档后，第二次尝试明确是引用资料句而非回答句：两次 $.citations[0].quote 的 exact_source_quote_with_adjacent_context_not_found。纠正仍重复后已停止，未伪造有效回答或接着审核。",
        "7. 场景 1 领域首次服务拒绝，没有服务错误正文。确认提示词漏 JSON 模式声明并按官方文档修复后，一次组件重试成功；这支持修复有效，但不能还原全部服务器拒绝原因。",
        "8. 最初知识版本参数手误，Retriever 拒绝且零请求，记录保留。没有因此猜测索引版本或改数据。",
        "", "## 确定性与来源边界", "",
        "missing_input_snapshot 由程序直接产生；模型只返回剩余组成部分，原引用候选仍限定原 Evidence。外层步骤超时也保留程序前提、领域规则及另一审核结果。没有静默补造模型支持结论。",
        "领域规则为 power-demo-rules-v1，每项保存来源（项目开发规格）、范围、版本、演示标志。文献、工程规则和计算区分；没有计算类型，simulation_not_run 由程序固定，未完成不得放行。",
        "两类审核通过现有 Harness 独立执行，共享冻结回答与主张，不把对方结论传入提示词；两个连接器最多两个请求在途，同步工作线程仍不能被 asyncio 超时强制终止。",
        "", "## 快照与可观测性", "",
        "场景 1 和 3 接受的回答保存了完整 Evidence 集合，且问题/工程上下文另存于场景记录；当时没有 full-input-v2 的统一哈希绑定。不能把这些历史记录补称为 v2。",
        "最后场景 2 使用的新生成逻辑会在成功时保存 full-input-v2（问题、用户上下文、工程数据、回答要求、提示词版本、全部 Evidence 与来源绑定）；但该次生成失败，所以本轮没有已接受的 v2 真实回答。该能力通过离线端到端与篡改测试验证，真实成功样例仍待后续授权运行。",
        "进一步增加请求前输入归档，即使生成结构失败也保留完整私有输入及哈希；该改动在付费运行停止后完成，本轮仅离线验证。模型响应正文、具体错误、版本、目录路径不进入普通日志，密钥和请求头未归档。",
        "", "## 文件职责与运行", "",
        "- agents/verification_contract_v7.py：程序前提、模型剩余任务、失败保留与数量结果。",
        "- services/quantity_checks.py：有限枚举与结构化维度/同参考对象数值检查。",
        "- agents/power_domain_review.py：注册演示规则、独立模型检查、quote_id 绑定与输出校验。",
        "- core/models.py、agents/contracts.py、core/validation.py、core/typed_evidence.py：兼容模型扩展与严格绑定。",
        "- harness/runtime.py、policy.py、contracts.py：复用双审核调度，失败保留/未完成门控，保留 domain_output。",
        "- services/evidence_scope.py、agents/generation.py、services/response_diagnostics.py、structured_model.py、model_adapter/contracts.py/runtime.py：完整输入快照、具体生成诊断、失败输入归档。",
        "- harness/power_review_demo.py：现有生成入口＋Harness 的受限新鲜场景，全部请求共享明确总上限。",
        "- tests/test_power_review.py：开发/模拟及真实归档回归；不是独立验收集。",
        "- evaluation/power_review_offline.py：本报告的纯离线生成器。",
        "", "本轮不再执行付费命令。后续授权运行须新输出路径，参见 D:\\PowerTrustAI\\docs\\power-domain-review.md。",
        "", "## 旧第 3 题漏检及新程序误报修复的可回查记录", "", "~~~json",
        json.dumps(semantic_miss,ensure_ascii=False,indent=2),"~~~","", "~~~json",json.dumps(recomputed,ensure_ascii=False,indent=2),"~~~",
        "", "## 来源哈希", "", "~~~json",json.dumps(sources,ensure_ascii=False,indent=2),"~~~"]
    for source in sources:
        assert hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest()==source["sha256"]
    assert hashlib.sha256(old.read_bytes()).hexdigest()==semantic_miss["source_sha256"]
    return summary,"\n".join(lines)+"\n"


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",required=True);args=p.parse_args();path=Path(args.output).resolve()
    if not path.is_relative_to(ROOT/"data/retrieval_local") or path.suffix!=".json" or path.exists() or path.with_suffix(".md").exists():
        p.error("Require nonexisting private JSON/Markdown outputs")
    data,report=build();path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as h:json.dump(data,h,ensure_ascii=False,indent=2)
    with path.with_suffix(".md").open("x",encoding="utf-8") as h:h.write(report)
    print(json.dumps({"output":str(path),"requests":data["new_requests"],"usage":data["usage_known_only"],"cost":data["cost_summary"]}))


if __name__=="__main__":main()
