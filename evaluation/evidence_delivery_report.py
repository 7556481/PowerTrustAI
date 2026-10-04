"""Offline report/backtrace for the paired development experiment; no model calls."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
from evaluation.evidence_delivery_trial import load,digest,save_new,DB
from harness.evidence_review_demo import restore_evidence,restore_answer,restore_snapshot
from core.validation import validate_answer
from services.evidence_scope import validate_snapshot
from rag.storage import KnowledgeStore


def stage_complete(result):
    return bool(result and result.get('extraction_output') and result.get('verification_output') and result.get('domain_output')
        and not result['execution_issues'] and not result['verification_output']['execution_issues'] and not result['domain_output']['execution_issues'])

def locator(e):
    p=e.get('provenance') or {}
    return f"{p.get('document_id')} @ {p.get('document_version')}, file page {p.get('file_page')}, extracted text [{p.get('start_offset')},{p.get('end_offset')})"

def answer_key(answer):
    return answer['answer_id'],answer['version'],hashlib.sha256(answer['text'].encode()).hexdigest()

def findings(result):
    rows=[]
    for label,key in (('fact','verification_output'),('domain','domain_output')):
        output=(result or {}).get(key) or {}
        for f in output.get('findings',[]):
            rows.append({'kind':label,**f})
    return rows

def report(out):
    out=Path(out);summary=load(out/'summary.json');plan=load(out/'plan.json')
    checked_evidence=checked_answers=checked_snapshots=checked_quotes=checked_original_scopes=0
    evidence_by_id={};answers={};snapshots={};stage_tables=[];delivery=[]
    with KnowledgeStore(DB,readonly=True) as store:
        for path in sorted(out.glob('*.json')):
            if path.name in ('plan.json','summary.json','progress.json'):continue
            value=load(path)
            for e in value.get('evidence',[]):
                store.verify_evidence(restore_evidence(e));evidence_by_id[e['evidence_id']]=e;checked_evidence+=1
            answer=value.get('answer')
            if answer:
                answers[answer_key(answer)]=answer
                validate_answer(restore_answer(answer),tuple(restore_evidence(e) for e in value.get('evidence',[])));checked_answers+=1
            snap=(value.get('generation_output') or {}).get('evidence_snapshot') or value.get('evidence_snapshot')
            if snap and answer:
                validate_snapshot(restore_snapshot(snap),restore_answer(answer));checked_snapshots+=1
                for e in snap['evidence']:store.verify_evidence(restore_evidence(e));evidence_by_id[e['evidence_id']]=e
                snapshots[(answer['answer_id'],answer['version'])]=snap
            for r in value.get('retrieval_records',[]):
                delivery.append({'stage':path.stem,**r})
        for run in summary['runs']:
            answer=run.get('frozen_answer')
            if answer:answers[answer_key(answer)]=answer
        for path in sorted((out/'response-diagnostics').glob('scope-*.json')):
            scope=load(path)
            a=answers[(scope['answer_id'],scope['answer_version'],scope['answer_sha256'])]
            assert scope['answer_sha256']==hashlib.sha256(a['text'].encode()).hexdigest()
            assert scope['knowledge_version']==plan['knowledge_version']
            for quote in scope['QUOTE_CANDIDATES']:
                e=evidence_by_id.get(quote['evidence_id'])
                if e is None:
                    raise ValueError('Scoped quote Evidence not in archived stage evidence')
                store.verify_evidence(restore_evidence(e))
                assert e['text'][quote['start_offset']:quote['end_offset']]==quote['text']
                checked_quotes+=1
            if scope['purpose']=='original_citation':
                allowed=set(a['citations'][scope['check_id']]['evidence_ids'])
                assert {q['evidence_id'] for q in scope['QUOTE_CANDIDATES']}<=allowed
                checked_original_scopes+=1
    assert all(digest(p)==h for p,h in plan['protected_sha256'].items())
    assert all(digest(p)==h for p,h in plan['source_sha256'].items())
    records=summary['model_records'];tokens={}
    for label in ('input_tokens','output_tokens','total_tokens','cache_hit_tokens','cache_miss_tokens'):
        known=[r['usage'][label] for r in records if r.get('usage') and r['usage'].get(label) is not None]
        tokens[label]={'known_total':sum(known),'known_requests':len(known),'unknown_requests':len(records)-len(known)}
    by_prompt=defaultdict(list)
    for r in records:by_prompt[r['prompt_version']].append(r)
    errors=[]
    for r in records:
        if r.get('validation_error'):
            d=r['validation_error'];errors.append({'prompt_version':r['prompt_version'],'correction':r['correction'],
                'diagnostic_path':r.get('diagnostic_path'),'field_path':d.get('field_path'),'constraint':d.get('constraint'),
                'all_errors':d.get('errors',[d]),'output_status':r.get('output_status')})
    audit={'scope':'OFFLINE TRACE/STRUCTURE VALIDATION, NOT SEMANTIC ACCEPTANCE',
        'evidence_checks':checked_evidence,'answer_checks':checked_answers,'snapshot_checks':checked_snapshots,
        'quote_checks':checked_quotes,'original_citation_scope_checks':checked_original_scopes,
        'protected_hashes_unchanged':True,'agent_protocol_hashes_unchanged':True,
        'actual_requests':len(records),'tokens':tokens,'errors':errors,'delivery':delivery,
        'initial_review_complete':sum(stage_complete(r.get('initial')) for r in summary['runs']),
        'rereview_complete':sum(stage_complete(r.get('rereview')) for r in summary['runs']),
        'loop_complete':sum(bool(r.get('loop_execution_complete')) for r in summary['runs'])}
    save_new(out/'offline-audit.json',audit)
    lines=['# 证据交付配对闭环：开发试运行',
        '', '只评估交付与执行，并人工待复核语义。不是独立验收集，不输出整体真实 pass 或工程安全认证。',
        '默认 BM25、知识快照、分词、Agent 协议、提示词、演示规则和政策均未切换。',
        '同一真实生成草稿和初次有效主张提取共享；数量、地区两例替换为明确标记的构造错误，原真实生成记录保留。',
        '仅比较既有邻接候选在相同字符/片段预算下的 storage_order 与 cross_page_next_first。后者优先物理下一页邻居，不表示语义续接。',
        '这是每分支最多一次业务修订的配对开发实验；重审均重新提取并独立双审核。它不是两个端到端自然生成批次的比较。',
        '',f"知识版本 `{plan['knowledge_version']}`；最坏预算 {plan['global_request_cap']} 请求；实际 {len(records)}。",
        f"初次双审完成 {audit['initial_review_complete']}/12；完整重审完成 {audit['rereview_complete']}；按既定政策需要修订时也完成重审的分支 {audit['loop_complete']}/12。",
        '若政策无需修订，分支完成只说明完成必需阶段；不足结果仍然保留。',
        '', '## 输入交付与限制',
        '核心片段与补充上下文 ID 独立保存；上下文不是新增检索命中。16000 字符单次、160000 累计预算按整片段省略，不截断原文。',
        '2400 字符、6 片段、1 跳上下文预算可能省略前置或续接条件。省略 ID/原因保存在 retrieval_records/context_omissions；当前审核提示词并未显式收到全部省略原因。这是现有可见性限制，本轮不修改审核协议。',
        'verification 的独立核验只选择本轮核验检索；原引用只选择原绑定 Evidence。domain 只选择当轮领域检索。旧轮次发现不能成为本轮可选 quote。',
        '完整生成输入 v2 保存全部实际输入。核验输入覆盖投影只有证据元数据与正文哈希，正文未再次交付；它不支持对未交付正文的完整语义覆盖推断。',
        '物理跨页相邻不证明句子续接；PDF 定位对应提取文本，视觉原文仍待人工检查。适用地区未知留空，不能默认通用。',
        '', '## 自动回查',
        f"Evidence {checked_evidence} 次、回答绑定 {checked_answers} 次、完整快照 {checked_snapshots} 次、quote 定位 {checked_quotes} 次、原引用范围 {checked_original_scopes} 次检查通过。",
        '语料、向量、标签、既有 Agent 和政策文件哈希未变。逐字定位正确不代表语义支持正确。',
        '', '## 分支状态', '|场景|模式|初次双审|修订|重审|必需阶段完成|停止/决策|','|---|---|---|---|---|---|---|']
    for run in summary['runs']:
        lines.append('|'+ '|'.join(str(v).replace('|','/') for v in (run['scenario'],run.get('mode','generation'),
            stage_complete(run.get('initial')),bool(run.get('revision')),stage_complete(run.get('rereview')),
            run.get('loop_execution_complete',False),run.get('stop_reason') or (run.get('final_decision') or {}).get('kind') or run.get('revision_status','')))+'|')
    lines+=['','## 调用、用量与交付成本','|提示词|请求|纠正|输入token|输出token|候选总数|证据字数（重复计入）|耗时合计ms|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for prompt,rs in sorted(by_prompt.items()):
        metrics=[r.get('request_metrics') or {} for r in rs]
        lines.append('|'+ '|'.join(map(str,(prompt,len(rs),sum(r['correction'] for r in rs),
            sum((r.get('usage') or {}).get('input_tokens',0) or 0 for r in rs),sum((r.get('usage') or {}).get('output_tokens',0) or 0 for r in rs),
            sum(m.get('candidate_count',0) for m in metrics),sum(m.get('evidence_chars_delivered',0) for m in metrics),sum(r['duration_ms'] for r in rs))))+'|')
    lines+=['',f"服务用量汇总：`{json.dumps(tokens,ensure_ascii=False)}`。未知不估造。",
        f"连接器保存价估计：`{json.dumps(summary['cost_summary_saved_price_estimate'],ensure_ascii=False)}`。",
        '2026-10-03 再核实 [DeepSeek 官方价格](https://api-docs.deepseek.com/quick_start/pricing/)：Flash 缓存命中/未命中/输出高峰 USD 0.006/0.30/1.20 每百万 token，非高峰半价；周末属于非高峰。估计不是账单。',
        '耗时为各请求之和，双审核可重叠，不能当成壁钟批次时间。候选/字符指标测量实际 JSON 交付，重复交付计入，不推断上下文被理解。',
        '', '## 精确执行错误（历史保留，无原样批次重试）']
    for error in errors:
        lines.append(f"- {error['prompt_version']} correction={error['correction']}: `{error['field_path']}` / `{error['constraint']}`；完整诊断 `{error['diagnostic_path']}`。")
    lines+=['','## 逐发现与修订对照（模型判断需人工复核）']
    for run in summary['runs']:
        lines+=['',f"### {run['scenario']} / {run.get('mode','generation')}"]
        answer=run.get('frozen_answer')
        if answer:lines+=['','原回答：','',answer['text']]
        for stage in ('initial','rereview'):
            result=run.get(stage)
            if not result:continue
            lines+=['',f"{stage}：执行完成={stage_complete(result)}；"]
            claims={c['claim_id']:c for c in (result.get('extraction_output') or {}).get('claims',[])}
            for f in findings(result):
                lines.append(f"- {f['kind']} `{f['finding_id']}` {f.get('status',f.get('check_status'))}: {f.get('rationale',f.get('explanation',''))}")
                if f.get('claim_id') in claims:lines.append('  主张：'+claims[f['claim_id']].get('text',''))
                for basis in f.get('bases',[]):
                    lines.append('  依据：`'+json.dumps(basis,ensure_ascii=False)+'`')
                if f.get('missing_prerequisites'):lines.append('  缺少：'+str(f['missing_prerequisites']))
            output=result.get('verification_output') or {}
            for c in output.get('citation_reviews',[]):
                lines.append('  原引用检查：`'+json.dumps(c,ensure_ascii=False)+'`')
            for c in output.get('consistency_checks',[]):lines.append('  数量/枚举检查：`'+json.dumps(c,ensure_ascii=False)+'`')
        revised=run.get('revision')
        if revised:
            lines+=['','修订回答：','',revised['answer']['text'],'','逐 finding 处理：']
            for action in revised.get('finding_actions',[]):lines.append('- `'+json.dumps(action,ensure_ascii=False)+'`')
            lines.append('模型仍声明未解决：'+str(revised['unresolved_finding_ids']))
        lines.append('最终决定/停止：`'+json.dumps(run.get('final_decision') or run.get('stop_reason') or run.get('revision_status'),ensure_ascii=False)+'`')
    lines+=['','## 实际检索交付清单','每次实际查询、核心/补充 ID、省略原因见 offline-audit.json 的 delivery；全部原文与定位见该分支原始 JSON 和 agent-inputs。']
    for row in delivery:
        lines+=['',f"### {row['stage']} / {row['purpose']}",f"查询：{row['query']}",
            f"核心 {len(row['core_evidence_ids'])}，上下文 {len(row['context_evidence_ids'])}，接受 {row['accepted_chars']} 字符；省略 `{row['omitted_evidence_ids']}` / `{row['context_omissions']}`。"]
        for origin,ids in (('core',row['core_evidence_ids']),('context_not_hit',row['context_evidence_ids'])):
            for eid in ids:
                e=evidence_by_id[eid];lines.append(f"- {origin} `{eid}`：{locator(e)}；告警 `{(e.get('provenance') or {}).get('warnings')}`；适用 `{e.get('applicability')}`。")
    (out/'report.md').open('x',encoding='utf-8').write('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k not in ('errors','delivery')},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args();report(args.output_dir)
