"""Final offline ledger across immutable reliability versions; no API calls."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from evaluation.reliability_trial import ROOT,load,save_new,digest
from evaluation.archive_replay import restore
from harness.contracts import HarnessResult,RunBudget
from harness.policy import LimitedRepairPolicy

NAMES=('reliability-v1','reliability-v1-patch1','reliability-v1-repair1','reliability-v1-followup1','reliability-v1-followup2')

def done(run,key):
    output=(run or {}).get(key)
    return bool(output and not output.get('execution_issues'))

def build():
    base=ROOT/'data/retrieval_local/deepseek';out=base/NAMES[-1]
    batches=[load(base/name/'live-summary-v1.json') for name in NAMES]
    final=batches[-1];plan=load(out/'plan-v1.json');audit=load(base/NAMES[0]/'archive-audit-v3.json')
    ledger=[];tokens=Counter();unknown=Counter();failures=[];input_metrics=[];archived_messages=0
    for name,b in zip(NAMES,batches):
        for record in b['model_records']:
            raw=load(record['diagnostic_path']);assert hashlib.sha256(raw['response_text'].encode()).hexdigest()==raw['response_sha256']
            message=raw.get('request_messages_path')
            if message:
                payload=load(message);assert all(set(m)=={'role','content'} for m in payload['messages']);archived_messages+=1
            usage=record.get('usage') or {}
            for key in ('input_tokens','output_tokens','total_tokens','cache_hit_tokens','cache_miss_tokens'):
                if usage.get(key) is None:unknown[key]+=1
                else:tokens[key]+=usage[key]
            associations=[]
            for row in b['runs']:
                for phase in ('generation','initial','revision','rereview'):
                    obj=row.get(phase) or {}
                    if any(r.get('diagnostic_path')==record['diagnostic_path'] for r in obj.get('model_records',[])):
                        associations.append({'scenario':row['scenario'],'phase':phase})
            item={'batch':name,'association':associations,'record':record,'request_metrics':raw.get('request_metrics'),
                'request_messages_path':message,'response_sha256_verified':True}
            ledger.append(item);input_metrics.append({k:item[k] for k in ('batch','association','request_metrics','request_messages_path')})
            if record.get('validation_error'):failures.append(item)
    assert all(digest(p)==h for p,h in audit['source_sha256'].items())
    assert all(digest(p)==h for p,h in plan['protected_sha256'].items())
    assert all(digest(p)==h for p,h in plan['source_sha256'].items())
    counters=Counter();details=[];phases=[]
    for row in final['runs']:
        initial=row.get('initial') or {};flags={k:done(initial,k) for k in ('extraction_output','verification_output','domain_output')}
        for k,value in flags.items():counters[k]+=value
        revision=bool(row.get('revision'));counters['revision']+=revision
        rereview=row.get('rereview') or {};full=bool(rereview) and all(done(rereview,k) for k in flags);counters['rereview_complete']+=full
        if all(flags.values()):
            obj=restore(initial,HarnessResult);policy=LimitedRepairPolicy().decide(obj.verification_output,obj.domain_output,RunBudget(max_revision_rounds=1),0)
            required_complete=bool(full if policy.kind.value=='revise' else True)
        else:policy=None;required_complete=False
        counters['required_stages_complete']+=required_complete
        details.append({'scenario':row['scenario'],'initial_flags':flags,'revision':revision,'rereview_complete':full,'required_stages_complete':required_complete,
            'stop':row.get('stop'),'initial_policy':None if policy is None else asdict(policy),'final_policy':row.get('final_policy'),
            'final_issues':rereview.get('execution_issues',initial.get('execution_issues',[]))})
        for phase in ('initial','rereview'):
            run=row.get(phase)
            if not run:continue
            extraction=run.get('extraction_output') or {};v=run.get('verification_output') or {};d=run.get('domain_output') or {}
            phases.append({'scenario':row['scenario'],'phase':phase,'execution_issues':run['execution_issues'],'duration_ms':run['duration_ms'],
                'claims':extraction.get('claims',[]),'uncovered_spans':extraction.get('uncovered_spans',[]),'non_claim_spans':extraction.get('non_claim_spans',[]),
                'verification_findings':v.get('findings',[]),'original_citation_reviews':v.get('citation_reviews',[]),'verification_rules':v.get('consistency_checks',[]),
                'domain_findings':d.get('findings',[]),'domain_rules':d.get('consistency_checks',[]),'tools':run.get('tool_results',[]),
                'generation_body_delivered':v.get('input_body_delivered',False),'retrieval_records':run['retrieval_records'],
                'answer':run['answer'],'report':run['report'],'model_records':run['model_records']})
    low=sum(b['cost_estimate']['usd_lower_known_only'] or 0 for b in batches);high=sum(b['cost_estimate']['usd_upper_known_only'] or 0 for b in batches)
    result={'scope':'DEVELOPMENT RELIABILITY VALIDATION; NO SAFETY CERTIFICATION NO OVERALL PASS',
        'historical88':audit['counts'],'batches':[{'name':n,'calls':b['actual_model_calls'],'wall_ms':b['wall_ms']} for n,b in zip(NAMES,batches)],
        'actual_paid_requests':len(ledger),'reported_usage_totals':dict(tokens),'unknown_usage_requests_per_field':dict(unknown),
        'structural_status_counts':dict(Counter(x['record']['output_status'] for x in ledger)),'request_messages_saved':archived_messages,
        'price_verified_date':'2026-10-04','price_source':'https://api-docs.deepseek.com/quick_start/pricing/?tab=case-studies',
        'usd_estimate_range':[low,high],'not_bill':True,'final_execution_counts':dict(counters),'scenarios':details,
        'historical_files_unchanged':True,'protected_index_config_labels_unchanged':True,'final_code_matches_frozen_plan':True}
    save_new(out/'final-summary-v1.json',result);save_new(out/'all-request-ledger-v1.json',ledger)
    save_new(out/'all-failure-matrix-v1.json',failures);save_new(out/'all-stage-findings-v1.json',phases)
    lines=['# 审核可靠性修复 v1：最终真实验证',
        '2026-10-04。AI辅助离线复核与程序记录，不是独立专家金标准。引用可回查、结构合法和模型同意都不证明语义正确，无工程仿真或安全认证。',
        '## 版本与不可混淆的结果',
        '原88份：67结构合法、21失败，全部原协议重放、没有迁移失败为成功。',
        '第一轮v9长正文候选目录程序缺陷28请求；v9.1六题初审23请求与独立修订5请求；追加授权后v6提取/单范围审核接线失败13请求；最终接线修复独立批次如下。不同版本分别保留，不合并成同版本质量对照。',
        f'累计 **{len(ledger)}** 次付费请求，模型 `{final["model_id"]}`。最初60次限制在用户追加授权后解除；最终固定批次上限160、最坏154，每阶段最多一次纠正，没有无限重试。',
        f'最终知识 `{final["knowledge_version"]}`；默认BM25/Dense/RRF/切分/交付未改，不采用 cross_page_next_first。',
        '最终协议：atomic-claims-v6（程序锚点＋模型声明组件依据目标）；evidence-verification-output-v9.2（schema10，逐请求单命名空间）；领域v3、生成v3、修订v2、演示规则v1、SI工具v1。',
        '源码、提示词及规则/config哈希见 plan-v1.json；旧协议显式保留，旧数据类字段形状由扩展类保持。四份生成回答原样复用、构造错误原样冻结，不将后来的检索补成旧生成输入。',
        '## 最终执行完整性',
        '|场景|提取|初次事实核验|初次领域审核|一次修订|完整重审|必需阶段完成|未完成原因|','|---|---|---|---|---|---|---|---|']
    for r in details:lines.append(f'|{r["scenario"]}|{r["initial_flags"]["extraction_output"]}|{r["initial_flags"]["verification_output"]}|{r["initial_flags"]["domain_output"]}|{r["revision"]}|{r["rereview_complete"]}|{r["required_stages_complete"]}|{r["stop"] or json.dumps(r["final_issues"],ensure_ascii=False)}|')
    lines.append(f'最终提取{counters["extraction_output"]}/6，事实初审{counters["verification_output"]}/6，领域初审{counters["domain_output"]}/6；修订{counters["revision"]}，完整重审{counters["rereview_complete"]}/{counters["revision"]}；必需阶段完成{counters["required_stages_complete"]}/6。这里是执行结构完成，not_assessable、缺证据和缺工程前提仍属于未解决业务检查。')
    lines.extend(['## 六场景：逐主张、规则、修订与重审'])
    for row in final['runs']:
        lines.extend([f'### {row["scenario"]}',f'开发检查点（没有交付给模型）：{row["expected_checks_not_passed_to_model"]}',
            '原回答：','```text',row['answer']['text'],'```'])
        for phase in ('initial','rereview'):
            run=row.get(phase)
            if not run:continue
            lines.extend([f'#### {phase}',f'状态 `{run["state"]}`；终止 `{run["termination_reason"]}`；{run["duration_ms"]}ms。'])
            ex=run.get('extraction_output') or {};v=run.get('verification_output') or {};d=run.get('domain_output') or {};claims={c['claim_id']:c for c in ex.get('claims',[])}
            lines.append(f'主张{len(claims)}；未覆盖区间 {json.dumps(ex.get("uncovered_spans",[]),ensure_ascii=False)}。字符覆盖不能证明原子拆分完整。')
            for f in v.get('findings',[]):
                c=claims[f['claim_id']];lines.extend([f'- `{f["finding_id"]}` **{f["status"]}**；{c.get("proposition")}',
                    f'  角色 `{c.get("assertion_role")}`，依据目标 {c.get("component_basis_targets")}；原文 [{c["start_offset"]},{c["end_offset"]})；模型理由：{f["rationale"]}',
                    '```json',json.dumps({'component_reviews':f['component_reviews'],'bases':f['bases']},ensure_ascii=False,indent=2),'```'])
            for review in v.get('citation_reviews',[]):lines.extend(['原绑定引用审核（与独立检索分开）：','```json',json.dumps(review,ensure_ascii=False,indent=2),'```'])
            for f in d.get('findings',[]):lines.append(f'- 领域 `{f["finding_id"]}` [{f.get("check_status")}/{f["severity"]}] {f["rationale"]}；缺前提 {f["missing_prerequisites"]}')
            for check in v.get('consistency_checks',[]):lines.append('程序数量规则：`'+json.dumps(check,ensure_ascii=False)+'`')
            if run.get('tool_results'):lines.extend(['真实标量工具结果（不是仿真）：','```json',json.dumps(run['tool_results'],ensure_ascii=False,indent=2),'```'])
            if run['execution_issues']:lines.extend(['执行未完成：','```json',json.dumps(run['execution_issues'],ensure_ascii=False,indent=2),'```'])
            lines.append('业务/执行最终原因：`'+json.dumps(run['report'],ensure_ascii=False)+'`')
        if row.get('revision'):lines.extend(['#### Revision动作与正文','```json',json.dumps({k:row['revision'].get(k) for k in ('answer','finding_actions','changes','unresolved_finding_ids')},ensure_ascii=False,indent=2),'```'])
        lines.append('最终政策：`'+json.dumps(row.get('final_policy',row.get('initial_policy')),ensure_ascii=False)+'`')
    lines.extend(['## 用量与性能','|批次|请求|墙钟秒|','|---|---:|---:|'])
    lines.extend(f'|{name}|{b["actual_model_calls"]}|{b["wall_ms"]/1000:.3f}|' for name,b in zip(NAMES,batches))
    lines.append('服务返回 token 合计：`'+json.dumps(dict(tokens))+'`；未提供字段计数：`'+json.dumps(dict(unknown))+'`。不以字符数估造token。')
    lines.append(f'已知用量估算 USD **{low:.9f}–{high:.9f}**（非账单）。2026-10-04核实官方Flash峰/非峰价格仍与记录一致；周末为非峰，因归档不含逐请求服务计费时间戳，保留保守区间。[官方价格](https://api-docs.deepseek.com/quick_start/pricing/?tab=case-studies)。')
    lines.append(f'完整请求消息预归档 {archived_messages}/{len(ledger)}。早期版本只有实际Agent输入、候选/交付payload及冻结提示词，不伪造为请求时完整消息。最终版本请求前保存角色/正文，响应后绑定错误；没有凭据或请求头。')
    lines.extend(['候选数量、正文总字符/去重字符、消息字符、每阶段token与服务耗时见 all-request-ledger-v1.json；跨轮次消息省略明示，完整快照仍原样保存，不能称所有模型上下文已交付。',
        '## 验证、复现与限制',
        '最终离线378项通过（47.310s），项目解释器 D:\\PowerTrustAI\\.venv\\Scripts\\python.exe；普通测试不联网。源码/保护数据/原88档案hash核对通过。',
        '```powershell','Set-Location D:\\PowerTrustAI','.\\.venv\\Scripts\\python.exe -m unittest discover -q','.\\.venv\\Scripts\\python.exe -m evaluation.reliability_final_report','```',
        '报告入口只读模型结果，但输出使用独立文件名拒绝覆盖；已经执行过请阅读已有报告，不重复运行。真实入口和新目录/离线门槛见 docs/review-reliability-v1.md。',
        '主张目标仍由模型分类；语义支持、条件完整、地区范围和拒答是否充分需人工复核。程序锚点、类型和换算不会证明原文意思；标签不自动确认。',
        '概念问答可能仍被演示规则要求单位/仿真前提，这是潜在适用范围误报。用户数据真实、厂站可行性、未执行仿真都不由本轮证明。'])
    with (out/'full-report-v1.md').open('x',encoding='utf-8') as f:f.write('\n\n'.join(lines))
    print(json.dumps({'calls':len(ledger),'latest_calls':final['actual_model_calls'],'execution':dict(counters),'tokens':dict(tokens),'cost':[low,high]},ensure_ascii=False))

if __name__=='__main__':build()
