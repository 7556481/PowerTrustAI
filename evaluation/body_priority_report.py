"""Render saved experiment only; no retrieval/model calls."""
import json
from pathlib import Path
from evaluation.body_priority_trial import BASE
from evaluation.supervised_retrieval import METRICS

def main():
    folder=BASE/'body-priority-v1'; data=json.loads((folder/'experiment.json').read_text(encoding='utf-8'))
    original=json.loads((BASE/'annotations/supervised-v3-eval-v3/evaluation.json').read_text(encoding='utf-8'))
    selected=data['selection']['selected'][0];rs=data['results']
    lines=['# 检索失败分析与开发集实验','',
        '标签来源：ChatGPT 辅助、用户监督；冻结家族仍称监督标注验收候选，不是严格独立专家测试集。',
        '原评测与检索算法默认值、审核协议、SQLite 原文和向量索引均保持不变。', '',
        '## 分母与含义','',
        '原30题 Hit/MRR 与3分命中分母30（无正例题计未命中）；相关性>=2包含部分依据，3分表示标注的直接依据，但单个直接片段不保证完整答案。',
        '池内 Recall 分母是各题已评分核心候选中>=2的数量，28题有正例；nDCG 使用2^grade-1和log2折扣，29题有非零理想增益，1分背景也贡献分值。',
        '必要组合：28题提供非空组，组内AND、组间OR；成员覆盖不是答案充分性。完整依据另要求范围内可回答、组合非partial_not_sufficient；21题具备该标注资格。',
        'D02/D12 即使命中标注组合全部成员，仍是部分依据；D05无充分组。不得将这些组覆盖解释为完整答案支持。跨题参考不补算命中，相邻上下文仍unknown。','',
        '## 编码核查','',
        '固定官方模型卡已核对query:/passage:（中英文相同）、attention-mask平均池化、L2、384维与512长度。实际ONNX输出为token hidden states，非已池化向量。模型和tokenizer按同一提交与SHA固定。',
        '本地中英tokenization与整句编码一致；范数约1。未发现需重建索引的确认错误。长文480/448滑窗等权平均不同于官方截断示例，属于既有版本化取舍；没有证明其与官方长文效果等价。',
        '详见encoder-audit.json，原索引未覆盖。','',
        '## 实验边界','',
        '正文优先仅将短重复页眉、孤立链接页脚、明显目录放在正文之后，不删除候选；有实质内容的脚注、图注和表格保留。编码、切分、语料、候选深度50固定。',
        '阶段1仅改变正文优先；阶段2固定正文处理，独立比较k20或BM25权重2。开发集预设选择顺序：范围完整依据、3分命中、MRR。',
        f'选定 {selected}；选择依据是已标注池投影的条件指标，仅作为暂定实验方案，不上线替换默认值。冻结家族只比较一次。',
        '新排序暴露未标注核心片段，实际top5指标未定义；另列池内投影（将未标注结果移出后再取前5），不能与真实top5改善等同。没有自动给新增片段打标签。',
        '实验原summary对未定义值错误使用0；本报告重新按有效分母聚合，不改实验历史JSON。选择涉及的三项在20道开发题均有定义，故选择不受该聚合错误影响。','',
        '## 指标（已标注池投影，附有效分母）','',
        '| 分组 | 方案 | Hit>=2 | MRR | 3分Hit | 池Recall | 池nDCG | 组完整覆盖 | 范围完整依据 | 未标注实际top5题数 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    summary={}
    groups={'development':[r for r in rs if r['split']=='development'],
        'frozen':[r for r in rs if r['split']!='development'],
        'development_natural':[r for r in rs if r['split']=='development' and r['language']!='acronym'],
        'development_keyword':[r for r in rs if r['split']=='development' and r['language']=='acronym']}
    for group,subset in groups.items():
        summary[group]={}
        names=list(subset[0]['methods'])
        for name in names:
            vals={}
            for metric in METRICS:
                present=[r['methods'][name]['judged_pool_projection'][metric] for r in subset if r['methods'][name]['judged_pool_projection'][metric] is not None]
                vals[metric]={'mean':sum(present)/len(present) if present else None,'n':len(present)}
            unknown=sum(bool(r['methods'][name]['actual_unknown_top5']) for r in subset)
            summary[group][name]={'projected':vals,'actual_unknown_questions':unknown}
            cols=['hit_ge2_at5','mrr_ge2_at5','direct_grade3_hit_at5','recall_ge2_judged_core_pool_at5','ndcg_graded_judged_core_pool_at5','any_necessary_group_covered_at5','scope_limited_answer_basis_complete_at5']
            lines.append(f'| {group}/{len(subset)} | {name} | '+' | '.join(f"{vals[m]['mean']:.4f} (n={vals[m]['n']})" if vals[m]['mean'] is not None else '未定义' for m in cols)+f' | {unknown} |')
    lines+=['','## 失败清单与逐题原文','',
        'D05：BM25无命中；Dense以PNNL孤立链接页脚及NERC重复页眉为主。标注核心池没有>=2，不可称通过排序已解决。正文处理可移走结构噪声，但新正文需要补标。',
        'D06：同步发电机运行条件查询匹配非同步资源正文/结构噪声；材料中存在相关同步约束，不等于本次候选召回成功。需检查独立候选排名，不能把D02跨题参考记命中。',
        'D12：PMU/VIP/RPM/FIDVR分类片段只给类别，缺监测机制；命中分类不等于解释方法。PNNL第24页相关机制需另行核对，D11参考不补算本题命中。','']
    baseline_rows={r['id']:r for r in original['evaluation']['per_question']}
    for r in rs:
        lines += [f"### {r['id']} / {r['family']} / {r['split']}",'',r['query'],'']
        for lost in r['bm25_direct_displaced']:
            lines += ['融合退步（候选已召回而被挤出）：'+json.dumps(lost,ensure_ascii=False),'']
        for name,v in r['methods'].items():
            base=r['methods']['baseline']['judged_pool_projection'];cur=v['judged_pool_projection']
            delta={m:cur[m]-base[m] for m in METRICS if cur[m] is not None and base[m] is not None and abs(cur[m]-base[m])>1e-10}
            lines += [f"{name}：条件指标变化 {json.dumps(delta,ensure_ascii=False)}；实际top5未标注 {len(v['actual_unknown_top5'])}；实际指标{'未定义' if v['actual_metrics'] is None else '可计算'}。",'']
        if r['id'] in ('D05','D06','D12') or r['bm25_direct_displaced'] or r['split']!='development':
            for name in ('baseline',selected):
                if name not in r['methods']:continue
                for n,hit in enumerate(r['methods'][name]['top5'],1):
                    e=hit['evidence'];lines += [f"{name} #{n} / {hit['blind_id'] or 'unknown'} / {hit['structural_flag']}",json.dumps(e.get('provenance'),ensure_ascii=False),'```text',e['text'],'```','']
        lines+=['基线失败分类：'+json.dumps({m:v['failure_classes'] for m,v in baseline_rows[r['id']]['methods'].items()},ensure_ascii=False),'']
    lines += ['## 耗时、资源与限制','',f"本地实验墙钟 {data['seconds']:.3f}s，进程CPU {data['cpu_seconds']:.3f}s；4线程CPU，GPU未使用，付费调用0。包括初始化、哈希核对、30题查询编码与原文回查；正文/RRF重排复用同一计算结果。",'峰值内存未在该运行内采集，不能以事后进程值冒充峰值。原文件受保护SHA前后相同。',
        '正文处理没有解决所有语义错配、版本错配或机制缺失；BM25权重2提高部分命中却降低完整组合，故未选。k20的变化很小，不能凭小样本宣称总体检索质量提高。',
        '下一步应补标新增actual top5，重点核对D05定义、D06同步边界、D12机制及旧标准替代现行标准问题。保持默认排名参数不变。']
    for path,value in ((folder/'report.md','\n'.join(lines)),(folder/'corrected-summary.json',json.dumps(summary,ensure_ascii=False,indent=2))):
        with path.open('x',encoding='utf-8') as f:f.write(value)

if __name__=='__main__':main()
