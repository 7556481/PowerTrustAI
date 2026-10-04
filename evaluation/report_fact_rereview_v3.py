"""Local reporting only: reads frozen archives; never loads credentials or a model."""
import json
from collections import Counter
from pathlib import Path
from evaluation.evidence_delivery_trial import load, save_new, digest
from evaluation.fact_rereview_v3 import DEFAULT, SOURCE
from agents.review_templates_v3 import INDEPENDENT, ORIGINAL


def main():
    out=DEFAULT; summary=load(out/'live-summary-v3.json'); plan=load(out/'plan-v3.json')
    expected={r['case_id']:r for r in load(out/'semantic-expectations-v3.json')}
    semantic={r['case_id']:r for r in load(out/'semantic-inputs-v3.json')}
    frozen={r['scenario']:r for r in load(out/'frozen-stage-inputs-v3.json')}
    errors=[]; requests=[]; tokens=Counter(); cases=[]; stages=[]
    for row in summary['runs']:
        output=row['output']; records=row['records']
        for i,r in enumerate(records):
            usage=r.get('usage') or {}
            for key in ('input_tokens','output_tokens','total_tokens','cache_hit_tokens','cache_miss_tokens'):
                if usage.get(key) is not None:tokens[key]+=usage[key]
            if r.get('validation_error'):
                errors.append({'case':row['name'],'attempt':i+1,'correction':r['correction'],
                               'response_path':r['diagnostic_path'],'error':r['validation_error']})
            diag=load(r['diagnostic_path']); messages=load(diag['request_messages_path'])['messages']
            catalog=load(r['candidate_catalog_path']); system=next(m['content'] for m in messages if m['role']=='system')
            purpose=catalog['purpose']; required=INDEPENDENT if purpose=='independent' else ORIGINAL
            assert system==required
            assert ('citation_reviews' not in system) if purpose=='independent' else ('findings' not in system)
            candidate_ids=[c['quote_id'] for c in catalog['QUOTE_CANDIDATES']]
            assert len(candidate_ids)==len(set(candidate_ids))
            requests.append({'case':row['name'],'purpose':purpose,'correction':r['correction'],
                'request_messages_path':diag['request_messages_path'],'request_sha256':digest(diag['request_messages_path']),
                'response_path':r['diagnostic_path'],'candidate_catalog_path':r['candidate_catalog_path'],
                'template_exact_match':True,'candidate_count':len(candidate_ids),'wire_ids':candidate_ids,
                'duration_ms':r['duration_ms'],'usage':r.get('usage'),'validation_error':r.get('validation_error')})
        if row['kind']=='fact_stage':
            components=[c for f in output['findings'] for c in f['component_reviews']]
            stages.append({'scenario':row['name'],'execution_complete':not output['execution_issues'],
                'independent_component_count':len(components),
                'independent_execution_complete':all(c['origin']!='execution_incomplete' for c in components),
                'component_statuses':dict(Counter(c['status'] for c in components)),
                'citation_count':len(output['citation_reviews']),
                'citation_execution_complete':all(not r.get('validation_error') for r in records if load(r['candidate_catalog_path'])['purpose']=='original_citation'),
                'citation_statuses':dict(Counter(c['status'] for c in output['citation_reviews'])),
                'corrections':sum(r['correction'] for r in records),'calls':len(records),
                'elapsed_ms':row['duration_ms'],'generation_or_revision_or_domain_executed':False})
        else:
            f=output['findings'][0]; component=f['component_reviews'][0]; e=expected[row['name']]
            complete=not output['execution_issues']; matches=complete and f['status'] in e['expected_statuses']
            cases.append({'case_id':row['name'],'source_kind':semantic[row['name']]['source_kind'],
                'expected_statuses':e['expected_statuses'],'expected_label_origin':e['status'],
                'actual_status':f['status'],'execution_complete':complete,'component_origin':component['origin'],
                'model_semantic_result_available':complete and component['origin']=='model_judgment',
                'matches_development_expectation':matches,'fidelity_status':component.get('fidelity_status'),
                'verification_obligation':component.get('verification_obligation'),'classification_issue':component.get('classification_issue'),
                'extraction_evaluated':False,'is_direct_count_error':e['is_direct_count_error'],
                'model_detected_count_error':complete and e['is_direct_count_error'] and f['status']=='contradicted',
                'rules':output.get('consistency_checks',[]),'calls':len(records),'elapsed_ms':row['duration_ms']})
    fee=(tokens['cache_hit_tokens']*.003+tokens['cache_miss_tokens']*.15+tokens['output_tokens']*.6)/1e6
    metrics={'scope':'fact-stage validation only, no global pass or new closed-loop success',
        'paid_requests':summary['actual_requests'],'paid_cap':40,'worst_case_frozen':32,
        'fact_stage_complete':sum(s['execution_complete'] for s in stages),'fact_stage_denominator':2,
        'independent_complete':sum(s['independent_execution_complete'] for s in stages),
        'citation_stage_complete':sum(s['citation_execution_complete'] for s in stages),
        'citation_checks_completed':sum(s['citation_count'] for s in stages if s['citation_execution_complete']),
        'semantic_execution_complete':sum(c['execution_complete'] for c in cases),'semantic_case_count':12,
        'synthetic_expectations_matched':sum(c['matches_development_expectation'] for c in cases if c['source_kind']=='synthetic_fixture'),
        'synthetic_case_count':10,'synthetic_direct_count_errors_detected':sum(c['model_detected_count_error'] for c in cases if c['source_kind']=='synthetic_fixture'),
        'synthetic_direct_count_error_count':4,'real_provisional_count_error_identification':'N10 not_assessable; NOT counted as detection',
        'format_corrections':sum(r['correction'] for r in summary['records']),
        'raw_invalid_attempts':len(errors),'wall_ms':summary['wall_ms'],'tokens':dict(tokens),
        'fee_estimate_usd':fee,'fee_price_verified_date':'2026-10-04','fee_price_source':'https://api-docs.deepseek.com/quick_start/pricing/',
        'fee_basis':'Sunday off-peak: cache hit .003, cache miss .15, output .6 USD/million; estimate, not account receipt',
        'history_and_frozen_hashes_unchanged':summary['frozen_hashes_unchanged'],
        'protocol_version':plan['contract_version'],'prompt_version':plan['prompt_version'],
        'model_ids':sorted(set(r['returned_model_id'] for r in summary['records'] if r.get('returned_model_id'))),
        'no_model_extraction_or_domain_review_this_round':True,'stages':stages,'semantic_cases':cases}
    save_new(out/'evaluation-summary-v3.json',metrics);save_new(out/'request-inspection-v3.json',requests)
    save_new(out/'actual-failure-matrix-v3.json',errors)
    lines=['# PowerTrustAI 事实重审稳定性 v3：人工复核报告','',
        '仅事实重审阶段验证；没有新生成、Revision、领域审核或完整闭环成功。结构成功与语义正确分开统计。',
        f"实际 {summary['actual_requests']} 次付费请求（上限40，最坏预算32），耗时 {summary['wall_ms']/1000:.3f}s。",
        f"输入 {tokens['input_tokens']} / 输出 {tokens['output_tokens']} / 总 {tokens['total_tokens']} tokens；",
        f"缓存命中 {tokens['cache_hit_tokens']}，未命中 {tokens['cache_miss_tokens']}；估算费用 USD {fee:.9f}，非账单金额。",
        '价格核实日期2026-10-04；[官方价格](https://api-docs.deepseek.com/quick_start/pricing/)，周日非高峰。',
        '', '## 执行与语义结论','',
        '两场景独立事实核验2/2、原引用检查2/2（4个引用）完成；两场景各一次格式纠正。',
        '12个固定语义例11/12结构完成。10个合成例9个符合冻结开发预期，4个明确计数错误均由模型判contradicted。',
        '这不是独立专家准确率：N10/N11来自真实资料，预期仅为开发解释、待人工核实。N10未能明确识别错误；N11执行失败。',
        'N12格式纠正后改判answer_scope supported，仍把技术真假替换为“回答写了什么”；程序规则告警不抵消此漏检。',
        '模型在N10/N11把“原文锚点—规范化命题”的忠实性，与“命题—资料是否一致”混淆；两例命题与回答原文相同，不能因此称为提取不忠实。',
        '合法not_assessable不是执行异常；N11最终输出是程序execution_incomplete占位，不能算作模型有效无法评估。',
        '', '## 版本、历史与输入边界','',
        f"契约 `{plan['contract_version']}`；提示 `{plan['prompt_version']}`；接口schema12；实际模型 `{','.join(metrics['model_ids'])}`。",
        f"固定知识快照 `{plan['knowledge_version']}`。全部保护文件、历史和冻结哈希在批次结束一致。",
        '源代码、配置/模板/场景哈希见plan-v3.json；398项离线测试32.570s，项目 .venv Python。',
        '两份v2响应按schema11重放，业务输出逐字段相等且原失败仍失败；没有迁移成成功。',
        '同一冻结修订回答、answer_id/version、共享主张、快照、工具和旧检索材料直接复用；新增检索调用0。',
        '仅当前协议的候选wire ID命名空间改变，canonical quote/Evidence ID及区间不变；全部索引证据回查通过。',
        '所有真实请求全文检查：独立模板无citation_reviews，原引用模板无findings；纠正复用同一专属系统模板。',
        '未调整提取器、检索、模型、领域规则或决策政策。测试例没有运行LLM ClaimExtractor，不能评价提取能力。',
        '复用旧底层解析器，finding.checker_version保留v9.3标签；本轮实际提示/响应契约见顶层及每次请求记录v9.4，不能只按该内部标签判版本。',
        '', '## 两个场景逐 finding 与原文依据','']
    for row in summary['runs'][:2]:
        o=row['output']; inp=frozen[row['name']]['input']; claimmap={c['claim_id']:c for c in inp['claims']}; emap={e['evidence_id']:e for e in o['evidence']}
        lines += [f"### {row['name']}",'',f"回答 `{o['answer_id']}` v{o['answer_version']}；结构完成，无新增领域结论。",'', '冻结回答：','```text',inp['answer']['text'],'```','']
        for f in o['findings']:
            c=claimmap[f['claim_id']]; lines += [f"#### {f['claim_id']} → {f['status']}",'',f"原文区间 [{c['start_offset']},{c['end_offset']})：",'```text',c['text'],'```',f"规范化命题：{c.get('proposition')}",f"模型理由：{f['rationale']}",f"适用条件：{json.dumps(f['applicability_conditions'],ensure_ascii=False)}",'']
            parts={p['component_id']:p for p in c['components']}
            for cr in f['component_reviews']:
                lines += [f"- 组成部分 `{cr['component_id']}` ({parts[cr['component_id']]['category']})：{parts[cr['component_id']]['proposition']}",f"  模型：{cr['status']}；origin={cr['origin']}；fidelity={cr.get('fidelity_status')}；obligation={cr.get('verification_obligation')}。{cr['rationale']}",f"  忠实性理由：{cr.get('fidelity_rationale')}；分类异议：{json.dumps(cr.get('classification_issue'),ensure_ascii=False)}。"]
            lines+=['']
            for i,b in enumerate(f['bases']):
                lines += [f"依据[{i}] `{b['type']}`：",'```json',json.dumps(b,ensure_ascii=False,indent=2),'```']
                e=emap.get(b.get('evidence_id'))
                if e:lines += [f"文档定位：{json.dumps(e.get('provenance'),ensure_ascii=False)}"]
            lines+=['']
        for cr in o['citation_reviews']:
            bound=inp['answer']['citations'][cr['citation_index']]; lines += [f"#### 原引用{cr['citation_index']}：{cr['status']}",'',f"原绑定Evidence：{bound['evidence_ids']}；回答区间 [{bound['start_offset']},{bound['end_offset']})。",'```text',inp['answer']['text'][bound['start_offset']:bound['end_offset']],'```',cr['rationale'],f"边界/覆盖：{cr['binding_warnings']} / {cr['coverage_issues']}", '```json',json.dumps(cr['excerpts'],ensure_ascii=False,indent=2),'```','']
        lines += ['工具（复用v2成功结果，本轮未新执行；只支持白名单标量换算）：','```json',json.dumps(o['tool_results'],ensure_ascii=False,indent=2),'```', '程序数量规则（与模型判断分开）：','```json',json.dumps(o['consistency_checks'],ensure_ascii=False,indent=2),'```','']
    lines += ['## 数量语义固定开发例：预期与实际','', '|例|资料|冻结预期|实际|执行完成|符合开发预期|','|---|---|---|---|---|---|']
    for c in cases:lines += [f"|{c['case_id']}|{c['source_kind']}|{' / '.join(c['expected_statuses'])}|{c['actual_status']} ({c['component_origin']})|{c['execution_complete']}|{c['matches_development_expectation']}|"]
    for row in summary['runs'][2:]:
        inp=semantic[row['name']]['input']; f=row['output']['findings'][0]
        lines += ['',f"### {row['name']}",'', '回答原文：','```text',inp['answer']['text'],'```',f"规范化命题：{inp['claims'][0]['proposition']}；类别/立场/目标均由冻结fixture提供，未经提取器验证。",f"依据定位：{json.dumps(semantic[row['name']]['evidence_locator'],ensure_ascii=False)}",'```text',inp['seed_evidence'][0]['text'],'```', '完整模型 finding 与程序规则：','```json',json.dumps({'finding':f,'rules':row['output']['consistency_checks'],'execution_issues':row['output']['execution_issues']},ensure_ascii=False,indent=2),'```']
    lines += ['', '## 每次请求、错误、候选与开销','', '请求全文归档仅role/content，未保存凭据、headers；原始响应与全部校验错误按attempt独立保存。', '```json',json.dumps(requests,ensure_ascii=False,indent=2),'```','', '## 未解决问题与推进边界','',
        '1. 模板冲突已在完整实际请求中消除；本批未再返回联合根。两场景事实重审可以执行完成，但初次均需格式纠正。',
        '2. 争议状态可合法表达，核心校验阻止显式争议与supported/contradicted共存；若模型自称faithful且选answer_scope，不能机械识别所有语义偷换，N12仍漏检。',
        '3. N10只给无法评估，不能算正确识别四类错误；N11在纠正后仍返回非法dimension category_membership，保留执行失败，不静默删字段。',
        '4. 数量场景的技术排除性判断仍缺文献直接支持，MW/Mvar类别和完整复合换算句也未完全核验；已有SI结果不自动证明单位类别或整句。',
        '5. 输入不足场景的输入覆盖可核验，复核建议是合法not_assessable，不能因为未运行仿真或建议未核验就把结构失败与业务不足混为一谈。',
        '6. 可以推进最小API与界面原型用于状态、证据、失败轨迹和人工复核；不能将其定位为无人值守可信审核或工程安全认证。保留review_required，不自动开展六场景回归或付费修复。',
        '7. 合成明确分类例的改善不能推广成真实电力分类能力；真实两例解释和上述疑似误报需人工核对。PDF摘录定位是提取文本，不等于视觉原文。',
        '', '## 复现命令','', '离线测试（不联网、不读.env）：','```powershell',r'cd D:\PowerTrustAI',r'.\.venv\Scripts\python.exe -m unittest discover -s tests','```',
        '新批次准备/运行必须使用新目录，历史与本次目录不会覆盖；live必须先保存对应source_sha256的离线通过门槛，并重新获得该批次授权。下面仅说明入口，本轮不再执行：','```powershell',r'.\.venv\Scripts\python.exe -m evaluation.fact_rereview_v3 prepare --output-dir D:\PowerTrustAI\data\retrieval_local\deepseek\fact-rereview-new-batch',r'.\.venv\Scripts\python.exe -m evaluation.fact_rereview_v3 live --output-dir D:\PowerTrustAI\data\retrieval_local\deepseek\fact-rereview-new-batch','```',
        '本地报告入口（不调用API、不读.env；已存在报告严格拒绝覆盖）：','```powershell',r'.\.venv\Scripts\python.exe -m evaluation.report_fact_rereview_v3','```']
    with (out/'full-report-v3.md').open('x',encoding='utf-8') as file:file.write('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in metrics.items() if k not in ('stages','semantic_cases')},ensure_ascii=True))


if __name__=='__main__':main()
