"""Offline accounting, scoped archive integrity and failure matrix; no API/env."""
import hashlib
import json
from pathlib import Path
from harness.deepseek_trial import PROJECT_ROOT,fee_summary
from evaluation.protocol_failure_matrix import inspect as old_failures

FILES=("stability-minimal-v1.json","stability-minimal-v2.json","stability-minimal-v3-rereview.json")


def inspect():
    root=PROJECT_ROOT/"data/retrieval_local/deepseek";records=[];steps=[];runs=[];failures=[]
    for name in FILES:
        path=root/name;payload=json.loads(path.read_text(encoding="utf-8"))
        for run in payload["runs"]:
            result=run["result"];runs.append({"file":name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "minimal_execution_complete":run.get("minimal_execution_complete",False),"state":result["state"],
                "termination_reason":result["termination_reason"]})
            versions={}
            for event in result["trace"]["events"]:
                if event["component"]=="model_request":
                    record=json.loads(event["detail"]);versions[record["call_number"]]=event["answer_version"]
            for record in result["model_records"]:
                records.append(record)
                archive=json.loads(Path(record["diagnostic_path"]).read_text(encoding="utf-8"))
                assert hashlib.sha256(archive["response_text"].encode()).hexdigest()==archive["response_sha256"]
                phase=record["prompt_version"]
                metrics=record["request_metrics"];purpose=None;version=versions.get(record["call_number"])
                if record["candidate_catalog_path"]:
                    scope=json.loads(Path(record["candidate_catalog_path"]).read_text(encoding="utf-8"))
                    digest=scope.pop("scope_sha256")
                    assert hashlib.sha256(json.dumps(scope,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==digest
                    purpose=scope["purpose"];version=scope["answer_version"]
                    assert metrics["candidate_count"]==len(scope["QUOTE_CANDIDATES"])
                    assert all(q["quote_id"].startswith(scope["scope_id"]+"-") for q in scope["QUOTE_CANDIDATES"])
                steps.append({"file":name,"call":record["call_number"],"stage":phase,"purpose":purpose,"answer_version":version,
                    "correction":record["correction"],"status":record["output_status"],"duration_ms":record["duration_ms"],
                    "input_tokens":None if record["usage"] is None else record["usage"]["input_tokens"],
                    "output_tokens":None if record["usage"] is None else record["usage"]["output_tokens"],**metrics})
                for error in (record.get("validation_error") or {}).get("errors",[]):
                    failures.append({"file":name,"call":record["call_number"],"stage":phase,"correction":record["correction"],
                        "field_path":error["field_path"],"constraint":error["constraint"],
                        "retained_items":(record["validation_error"] or {}).get("retained_items",[])})
    assert len(records)==19
    usage={key:sum((r["usage"] or {}).get(key,0) or 0 for r in records) for key in ("input_tokens","output_tokens","total_tokens")}
    stages=[]
    for stage in dict.fromkeys(s["stage"] for s in steps):
        group=[s for s in steps if s["stage"]==stage]
        stages.append({"stage":stage,"requests":len(group),"input_tokens":sum(s["input_tokens"] or 0 for s in group),
            "output_tokens":sum(s["output_tokens"] or 0 for s in group),"duration_ms_sum":sum(s["duration_ms"] for s in group),
            "candidate_count_delivered":sum(s["candidate_count"] for s in group),"evidence_chars_delivered":sum(s["evidence_chars_delivered"] for s in group),
            "message_chars":sum(s["message_chars"] for s in group)})
    return {"scope":"EXECUTION_STABILITY_DEVELOPMENT_REPORT_NO_ENGINEERING_CERTIFICATION","new_requests":len(records),
        "cap":20,"remaining":1,"usage":usage,"cost":fee_summary(records),"runs":runs,
        "old_responses_inspected":old_failures()["responses_inspected"],"old_failures":old_failures()["failures"],
        "new_failures":failures,"stages":stages,"steps":steps}


def render(data):
    lines=["# 本轮执行稳定性与开销报告","",
        "真实模型、构造错误开发案例、演示规则；不代表独立验收或工程安全认证。",
        f"新增请求 {data['new_requests']}/{data['cap']}，剩余 {data['remaining']}。未启动其他两场景：不足以完成必需阶段。",
        f"Tokens: {json.dumps(data['usage'])}",f"费用估算（非账单）: {json.dumps(data['cost'])}","",
        "最小链路通过来源链接保留首轮双审核和一次 Revision，随后重新提取并完成两类重审；历史失败记录未修改。",
        "执行完成不等于支持关系成立，最终 review_required，包含覆盖缺口、证据不足和未执行工程分析。","",
        "## 分阶段汇总","",
        "| 阶段版本 | 请求 | input | output | 候选累计 | 证据字符交付累计 | 耗时累计 ms |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for s in data["stages"]:
        lines.append(f"| {s['stage']} | {s['requests']} | {s['input_tokens']} | {s['output_tokens']} | {s['candidate_count_delivered']} | {s['evidence_chars_delivered']} | {s['duration_ms_sum']} |")
    lines += ["","累计耗时含并行步骤，不能当作墙钟时长。候选数/字符数按每次实际交付累计，包括格式纠正。","",
        "## 每次请求","",
        "| 文件 | 调用 | 版本 | 目的/阶段 | 纠正 | input/output | 候选 | 证据字符 | ms | 结构 |",
        "|---|---:|---:|---|---|---|---:|---:|---:|---|"]
    for s in data["steps"]:
        lines.append(f"| {s['file']} | {s['call']} | {s['answer_version']} | {s['purpose'] or s['stage']} | {s['correction']} | {s['input_tokens']}/{s['output_tokens']} | {s['candidate_count']} | {s['evidence_chars_delivered']} | {s['duration_ms']} | {s['status']} |")
    lines += ["","## 本轮新增失败矩阵","",
        "| 文件/调用 | 阶段 | 纠正 | 字段 | 约束 | 保留有效项 |","|---|---|---|---|---|---:|"]
    for f in data["new_failures"]:
        lines.append(f"| {f['file']} / {f['call']} | {f['stage']} | {f['correction']} | {f['field_path']} | {f['constraint']} | {len(f['retained_items'])} |")
    lines += ["","历史 25 次响应的完整失败矩阵见 protocol-failure-matrix-v1.md；JSON 含历史和本轮全部字段诊断。","",
        "## 错误与隔离边界","",
        "- 领域 no_issue + 非空缺失前提：协议/提示词矛盾。v2 用状态判别字段，no_issue/not_applicable 禁止该字段；程序绑定空列表。没有删除返回的非法字段。",
        "- 候选越界：原协议混交独立检索与原引用材料。v8 分开请求；别的版本/角色/引用候选从未进入当前可选清单。未知 ID 严格拒绝，别名仅精确映射当前程序目录。",
        "- Revision 漏 ID：分组修改难以证明覆盖。v2 程序给完整清单，模型逐项 modified/retained/unresolved，重复/遗漏/未知均拒绝；覆盖不等于解决。",
        "- 本轮首次 v8 把 region 写入提示词，但核心要求 jurisdiction：确认的提示词不一致，已修复并离线重放；不是放宽核心约束。",
        "- 原引用请求混入独立 finding 的可选字段说明，模型连续返回 dimension_findings：v8.2 分开输出 Schema，错误反馈列出完整白名单。",
        "- 最后重审将 answer_scope 错用 snapshot basis：模型依据选择错误，保留其他 6 项并反馈具体类型要求；一次纠正后完成。历史失败仍为失败。",
        "- 原子边界为完整 finding/check，包含其全部 bases、component_reviews 与本地索引。一个坏 basis 不保留该 finding 的 supported，其他 finding 可以保留。",
        "- 根结构、版本、快照、未知输入绑定是全局边界；根字段错误不接受本次任何项。跨项重复 ID 使对应重复项无效。合并后再次执行完整核心校验；未完成项只有明确的程序执行未完成状态。",
        "- 格式纠正保留先前已校验项及归档来源；任一未完成项产生执行问题，Harness 不允许整体通过。两个审核器仍首次独立，没有共享对方结论。","",
        "## 重复交付与限制","",
        "- 原 v7 同时交付两种作用域，多个候选的 text/context_text 与完整快照又重复原文。旧日志没有完整请求字符计数，不能编造旧实际字符总量。",
        "- 新作用域每条 Evidence 只交付完整片段一次，元数据/定位保留；不改变 BM25、PDF 切分，也不删限定条件。内部 canonical 目录仍保留全部既有候选以严格校验。",
        "- Revision 用带条件和理由的 finding 清单替代包含双方完整 Evidence/候选/请求日志的嵌套输出，允许原文独立交付一次。没有把旧审核事实改成新结论。",
        "- 原引用单独核验增加请求数；两轮审核和两名独立审核者仍需重复读取相关资料，不能为省量共享其语义结论。",
        "- 格式纠正会再次发送原输入及非法响应；message_chars 含全部实际消息，provider token 用量为真实返回，不用字符猜 token。",
        "- 修订从单句扩展到 QV、缺失工程输入等多项主张，导致重审开销上升；这不是无限删资料可以解决的，应继续约束修订只修实际问题。",
        "- QV 方法的广域局限、地域限定、引用是否完整支持和输入声明分类仍需人工复核。流程完成率不能作为审核准确率。",
        "- 19 次请求止步；其他两场景本轮没有真实恢复，启动门已具备，但须另轮预算。"]
    return "\n".join(lines)+"\n"


def main():
    root=PROJECT_ROOT/"data/retrieval_local/deepseek";data=inspect()
    with (root/"stability-summary-v1.json").open("x",encoding="utf-8") as h:json.dump(data,h,ensure_ascii=False,indent=2)
    with (root/"stability-summary-v1.md").open("x",encoding="utf-8") as h:h.write(render(data))
    print(json.dumps({"requests":data["new_requests"],"usage":data["usage"],"cost":data["cost"],"report":str(root/"stability-summary-v1.md")},indent=2))


if __name__=="__main__":main()
