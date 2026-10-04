"""Offline readable reliability report; no model calls or label promotion."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def build():
    first=ROOT/'data/retrieval_local/deepseek/reliability-v1'
    final=ROOT/'data/retrieval_local/deepseek/reliability-v1-patch1'
    batches=[load(p/'live-summary-v1.json') for p in (first,final)]
    repair=load(final.parent/'reliability-v1-repair1/live-summary-v1.json')
    batches.append(repair)
    for r in repair['runs']:
        target=next(x for x in batches[1]['runs'] if x['scenario']==r['scenario']);target.update({k:v for k,v in r.items() if k!='scenario'})
    plan=load(final/'plan-v1.json');audit=load(first/'archive-audit-v3.json')
    records=[r for b in batches for r in b['model_records']]
    lines=['# 审核可靠性修复 v1：离线与真实验证',
        '日期：2026-10-04。以下为程序核对及 AI 辅助语义复核，不是独立专家金标准、语义准确率或工程安全认证。',
        '默认 BM25、Dense、RRF、证据交付、旧项目和历史记录保持不变；不采用 cross_page_next_first。',
        '## 版本与执行边界',
        '主张协议 atomic-claims-v5；事实审核 v9→独立补丁 v9.1；领域审核 v3；生成 v3、修订 v2、确定性政策和演示规则 v1 未调整。',
        '首批 v9 的候选目录校验存在程序错误。该批已结束，所有失败保持失败；补丁采用独立目录与冻结哈希，复用四份已保存生成回答，原构造错误回答不变。不同版本不混作同版本对照。补丁批次在修订前因内存tuple/JSONarray恢复边界退出；独立修订验证从已保存JSON恢复，旧失败状态不改写。',
        '全部阶段按最多一次格式纠正执行。初审优先；修订前预留含格式纠正的完整重审预算8次，余额不足明确不执行。最坏全闭环超过60次，不能保证所有场景都修订。',
        f'本轮实际请求 **{len(records)}/60**；首批 {batches[0]["actual_model_calls"]}，补丁 {batches[1]["actual_model_calls"]}；独立修订 {batches[2]["actual_model_calls"]}。',
        f'实际模型：`{batches[1]["model_id"]}`；知识版本：`{plan["knowledge_version"]}`。',
        '代码/协议配置文件 SHA-256、固定输入与检查点见 plan-v1.json。检查点是开发回归依据，没有交付给模型。',
        '## 原88份归档重放',
        f'原协议结构合法 {audit["counts"].get("valid_structure",0)}；结构失败 {audit["counts"].get("invalid_structure",0)}；无法重放 {audit["counts"].get("not_replayed",0)}。原响应哈希及历史文件哈希核对通过。结构合法不代表判断正确。',
        '|约束类别（单响应首个错误）|数量|','|---|---:|']
    errors=Counter(r.get('diagnostic',{}).get('constraint','unknown') for r in audit['responses'] if r['replay']=='invalid_structure')
    lines.extend(f'|{k}|{n}|' for k,n in errors.items())
    lines.extend(['完整错误与可保留同级项目见 archive-audit-v3.json；不能将首个约束计数当所有语义问题数量。',
        '## 确认问题与修复清单',
        '|问题|程序确定部分|模型判断或未知部分|', '|---|---|---|',
        '|quote/qualifiers 定位失败|选择版本绑定段落锚点；程序回填逐字文本、区间、回答ID/版本；共享锚点明确允许不同原子主张，claim/non_claim不可共用|proposition、semantic_qualifiers 为模型规范化语义；字符覆盖不能证明原子拆分完整|',
        '|输入/转述/否定误报|记录完整前后上下文；有限数量规则要求可确认枚举与角色；不确定记未完成|assertion_role 由模型产生，可能误分；用户提供不等于工程事实真实|',
        '|类别与依据冲突|类型内部严格校验、组件依据约束；单finding隔离保留合法同级结果|类别本身及支持关系仍需语义核对，不强改类别放行|',
        '|单位换算无依据|真实白名单SI工具经Harness执行/计预算/轨迹；结果ID绑定claim，只允许标量同量纲换算|不能支持稳定/可行性；原无功MW警告不自动修正Mvar|',
        '|元数据被称官方正文|交付字段来源=index维护或用户清单/未核实来源；applicability不是PDF句子|文档正文归属仍需原文；来源缺失不编造|',
        '|保存快照但未交付正文|≤32000字符交付完整快照正文；超限交付元数据/哈希并程序标not_assessable；实际检索省略记录交付|片段没发现不代表整个来源或所有资料不存在|',
        '|no_issue/缺前提矛盾|领域v3固定数组，no_issue/not_applicable必须空missing_prerequisites；严格错误路径|工程数据充分性仍由有限规则/模型判断，没有仿真|',
        '|首批候选目录程序错误|模型整片段目录与核心完整候选目录分别保存；长正文回归；ID仍严格按当前用途范围选择|不把补丁结构兼容当作历史状态成功或语义正确|',
        '旧数据类字段形状保持，通过显式 ContextualClaim/CalculationBasis/Reliability输入输出/ToolHarnessResult 扩展；旧协议字段及原合法/失败状态不迁移。',
        '## 补丁六场景执行完整性',
        '|场景|提取|事实核验|领域审核|修订|完整重审|必需阶段|终止/未完成原因|', '|---|---|---|---|---|---|---|---|'])
    from evaluation.archive_replay import restore
    from harness.contracts import HarnessResult,RunBudget
    from harness.policy import LimitedRepairPolicy
    complete_count=0;extract_count=0;fact_count=0;domain_count=0;revision_count=0;rereview_count=0
    def completed(r,key):
        value=(r or {}).get(key)
        return bool(value and not value.get('execution_issues'))
    for row in batches[1]['runs']:
        initial=row.get('initial') or {};ex=completed(initial,'extraction_output');fa=completed(initial,'verification_output');do=completed(initial,'domain_output')
        rev=bool(row.get('revision'));re=row.get('rereview') or {};full=all(completed(re,k) for k in ('extraction_output','verification_output','domain_output'))
        policy=LimitedRepairPolicy().decide(restore(initial,HarnessResult).verification_output,restore(initial,HarnessResult).domain_output,RunBudget(max_revision_rounds=1),0) if fa and do else None
        req=bool(row.get('required_stages_complete')) or bool(ex and fa and do and policy and policy.kind.value!='revise');complete_count+=req;extract_count+=ex;fact_count+=fa;domain_count+=do;revision_count+=rev;rereview_count+=full
        lines.append(f'|{row["scenario"]}|{ex}|{fa}|{do}|{rev if rev else row.get("revision_status","未执行")}|{full}|{req}|{row.get("stop",initial.get("termination_reason",""))}|')
    lines.append(f'补丁提取 {extract_count}/6、初次事实审核 {fact_count}/6、初次领域审核 {domain_count}/6；实际修订 {revision_count}，完整重审 {rereview_count}/{revision_count or 0}；必需阶段完成 {complete_count}/6。失败、预算未执行、业务未解决分开保留。')
    lines.extend(['## 逐阶段、逐发现、原文与工具结果'])
    perf=[]
    for row in batches[1]['runs']:
        lines.extend([f'### {row["scenario"]}',f'输入类型：{row["draft_origin"]}；复用生成：{row.get("generation_reused_without_API",False)}；冻结构造回答原样：{row.get("frozen_answer_unchanged","不适用")}。',
            f'开发检查点：{row["expected_checks_not_passed_to_model"]}', '原冻结/生成回答：','```text',(row.get('answer') or {}).get('text','未取得回答'),'```'])
        for phase in ('initial','rereview'):
            run=row.get(phase)
            if not run:continue
            lines.extend([f'#### {phase}',f'状态：{run["state"]}；终止：{run["termination_reason"]}；耗时：{run["duration_ms"]}ms。'])
            if run.get('execution_issues'):lines.extend(['执行错误：','```json',json.dumps(run['execution_issues'],ensure_ascii=False,indent=2),'```'])
            extraction=run.get('extraction_output') or {};claims={c['claim_id']:c for c in extraction.get('claims',[])}
            lines.append('共享主张（角色为模型判断，不等于现实真实性）：')
            for c in claims.values():lines.append(f'- `{c["claim_id"]}` [{c.get("assertion_role","legacy")}] {c.get("proposition")}; 精确锚点 [{c["start_offset"]},{c["end_offset"]})；规范化限定 {c.get("semantic_qualifiers",[])}')
            lines.append('覆盖/遗漏：`'+json.dumps({k:extraction.get(k) for k in ('uncovered_spans','coverage','execution_issues')},ensure_ascii=False)+'`。共享段落覆盖不证明每个命题已拆分。')
            for key in ('verification_output','domain_output'):
                review=run.get(key) or {};evidence={e['evidence_id']:e for e in review.get('evidence',[])};quotes={c['quote_id']:c for c in review.get('quote_candidates',[])}
                lines.append(f'##### {key} ({review.get("prompt_version","未执行")})')
                if key=='verification_output':lines.append(f'完整输入正文实际交付：{review.get("input_body_delivered",False)}；已保存快照不等于已经检查正文。')
                for finding in review.get('findings',[]):
                    lines.extend([f'- `{finding["finding_id"]}` `{finding.get("status",finding.get("severity"))}`：{finding.get("message",finding.get("rationale",""))}',
                        '```json',json.dumps(finding,ensure_ascii=False,indent=2),'```'])
                    for basis in finding.get('bases',[]):
                        if basis['type']=='text_excerpt':
                            q=quotes.get(basis.get('quote_id'));e=evidence.get(basis.get('evidence_id'))
                            if q and e:lines.extend([f'依据 `{e["evidence_id"]}`；版本 `{e["source_version"]}`；{e["locator"]}；摘录区间 [{q["start_offset"]},{q["end_offset"]})：','```text',q['text'],'```'])
                for citation in review.get('citation_reviews',[]):lines.extend(['原引用检查（仅原绑定Evidence）：','```json',json.dumps(citation,ensure_ascii=False,indent=2),'```'])
                for check in review.get('consistency_checks',[]):lines.append('程序规则：`'+json.dumps(check,ensure_ascii=False)+'`')
            if run.get('tool_results'):lines.extend(['真实工具结果（不是仿真）：','```json',json.dumps(run['tool_results'],ensure_ascii=False,indent=2),'```'])
            lines.append('固定策略/报告：`'+json.dumps(run.get('report'),ensure_ascii=False)+'`')
            rs=run['model_records'];totals={k:sum((r.get('usage') or {}).get(k) or 0 for r in rs) for k in ('input_tokens','output_tokens','total_tokens')}
            perf.append({'scenario':row['scenario'],'phase':phase,'duration_ms':run['duration_ms'],'requests':len(rs),'reported_token_totals':totals,'unknown_usage_requests':sum(r.get('usage') is None for r in rs)})
        revision=row.get('revision')
        if revision:lines.extend(['#### Revision 逐finding处理及新回答','```json',json.dumps({k:revision.get(k) for k in ('answer','finding_actions','changes','unresolved_finding_ids','execution_issues')},ensure_ascii=False,indent=2),'```','修改动作覆盖完整不代表问题解决；必须与后面的独立重审比较。'])
        lines.append('最终政策：`'+json.dumps(row.get('final_policy',row.get('initial_policy')),ensure_ascii=False)+'`')
    lines.extend(['## 调用、token、耗时与费用','|阶段提示词|请求|格式纠正|输入token|输出token|未知用量|服务耗时ms（求和）|','|---|---:|---:|---:|---:|---:|---:|'])
    for prompt in dict.fromkeys(r['prompt_version'] for r in records):
        rs=[r for r in records if r['prompt_version']==prompt]
        lines.append(f'|{prompt}|{len(rs)}|{sum(bool(r["correction"]) for r in rs)}|{sum((r.get("usage") or {}).get("input_tokens") or 0 for r in rs)}|{sum((r.get("usage") or {}).get("output_tokens") or 0 for r in rs)}|{sum(r.get("usage") is None for r in rs)}|{sum(r["duration_ms"] for r in rs)}|')
    cost_low=sum(b['cost_estimate']['usd_lower_known_only'] or 0 for b in batches);cost_high=sum(b['cost_estimate']['usd_upper_known_only'] or 0 for b in batches)
    lines.append(f'三批墙钟耗时 {sum(b["wall_ms"] for b in batches)/1000:.3f}s（不含离线测试/诊断）；已知返回用量估算 USD {cost_low:.9f}–{cost_high:.9f}，价格记录日期2026-10-02，峰/非峰区间，不是账单。2026-10-04价格页核实请求超时，未宣称当日价格已确认。')
    lines.extend(['## 验证与复现', '项目解释器 `D:\\PowerTrustAI\\.venv\\Scripts\\python.exe`；最终371项普通测试通过（47.042s），不联网、不调用付费API。14项新回归覆盖协议边界，不作为语义准确率证明。',
        '```powershell','Set-Location D:\\PowerTrustAI','.\\.venv\\Scripts\\python.exe -m unittest discover -q','.\\.venv\\Scripts\\python.exe -m evaluation.reliability_report','```',
        '真实入口：`python -m evaluation.reliability_trial prepare --output-dir <新的忽略目录>`，随后离线验证写入该版本标记才可 `live`。已有目录拒绝再次启动；不要把复现命令理解为自动授权新增批次。原88归档诊断入口 `python -m evaluation.reliability_archive_audit --output-dir <新目录>`。',
        '实际Agent输入在三个批次 actual-inputs-v1/；响应、所有错误和实际候选/交付payload在 response-diagnostics-v1/。本轮已有请求未逐次单存完整system/user消息，提示词和纠正消息可由冻结代码、payload、错误和响应重建，但不得称为请求时完整消息归档。批次结束后补齐逐请求消息预归档，尚未真实重跑；工具结果与实际轨迹在各场景 initial/rereview JSON。无凭据/请求头。',
        '## 已知限制与后续',
        '模型角色、支持关系及条件完整性仍可能漏检/误报；字面位置和结构正确不是语义支持证明。整段锚点允许多主张共享，有明确覆盖但粒度较粗。',
        '快照超32000字符不交付全部正文，程序不评估整体覆盖；当前摘要保存省略原因，不用后检索补成旧生成完整输入。',
        '白名单单位工具不是工程计算；用户原输入量纲错误可以在修订后继续警告。演示规则不是官方强制要求，无仿真，无工程安全认证。',
        '不同批次和协议结果保留，不能从修复后的少量实例计算总体语义准确率；先针对归档中的真实漏检/误报补离线语义回归，再考虑独立验证。'])
    result={'requests':len(records),'batches':[b['actual_model_calls'] for b in batches],'required_complete':complete_count,'extraction_complete':extract_count,'fact_complete':fact_count,'domain_complete':domain_count,'revisions':revision_count,'rereviews_complete':rereview_count,'performance':perf,'usd_lower':cost_low,'usd_upper':cost_high}
    for name,data in (('reading-report-v2.md','\n\n'.join(lines)),('verification-summary-v2.json',json.dumps(result,ensure_ascii=False,indent=2))):
        with (final/name).open('x',encoding='utf-8') as f:f.write(data)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':build()
