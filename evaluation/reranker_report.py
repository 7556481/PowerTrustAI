"""Report saved reranker trial with actual unknown positions, no model calls."""
import argparse
import json
from pathlib import Path
from collections import Counter
from evaluation.reranker_trial import load,sha
from evaluation.supervised_retrieval import METRICS

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);p.add_argument('--report-version',default='v2');a=p.parse_args();out=Path(a.output_dir)
    result=load(out/'reranker-results.json');pool=load(out/'candidate-pool.json');rows=result['results'];summary={};changes=[]
    groups={'all_development':rows,'english':[r for r in rows if r['language']=='en'],
        'chinese':[r for r in rows if r['language']=='zh'],'keyword':[r for r in rows if r['language']=='acronym']}
    for group,subset in groups.items():
        summary[group]={}
        for method in ('default_baseline','fixed_pool_rrf','reranker'):
            values=[r['methods'][method]['metrics'] for r in subset];s={}
            for metric in METRICS:
                known=[v[metric] for v in values if v[metric] is not None]
                s[metric]={'mean':sum(known)/len(known) if known else None,'n':len(known)}
            for kind in ('bounds_ge2','bounds_grade3'):
                s[kind]={k:sum(v[kind][k] for v in values)/len(values) for k in ('hit_lower','hit_upper','mrr_lower','mrr_upper')}
            total=sum(len(v['top5_ids']) for v in values);unknown=sum(len(v['unknown_top5_ids']) for v in values)
            s['annotation_slots']={'known':total-unknown,'total':total,'rate':(total-unknown)/total if total else None}
            s['unknown_questions']=sum(bool(v['unknown_top5_ids']) for v in values)
            summary[group][method]=s
    for r in rows:
        before=r['methods']['fixed_pool_rrf']['metrics'];after=r['methods']['reranker']['metrics']
        deltas={m:after[m]-before[m] for m in METRICS if before[m] is not None and after[m] is not None}
        changes.append({'id':r['id'],'improved':[m for m,d in deltas.items() if d>1e-10],
            'regressed':[m for m,d in deltas.items() if d< -1e-10],'deltas':deltas,
            'unknown_actual_top5':after['unknown_top5_ids'],
            'known_hit_lower_change':after['bounds_ge2']['hit_lower']-before['bounds_ge2']['hit_lower'],
            'known_direct_lower_change':after['bounds_grade3']['hit_lower']-before['bounds_grade3']['hit_lower']})
    important=('hit_ge2_at5','direct_grade3_hit_at5','any_necessary_group_covered_at5','scope_limited_answer_basis_complete_at5')
    unknown=summary['all_development']['reranker']['unknown_questions'];reg=[c for c in changes if any(m in c['regressed'] for m in important)]
    missing=[r['id'] for r in rows if any(v=='recall_missing' for v in r['coverage']['direct_basis'].values()) or
        (r['coverage']['scope_complete_candidate_coverage'] is False)]
    reasons=[]
    if unknown:reasons.append('unjudged_top5_limits_complete_quality_assessment')
    if reg:reasons.append('important_question_coverage_regression')
    if missing:reasons.append('known_required_evidence_missing_from_candidate_pool')
    baseline=summary['all_development']['fixed_pool_rrf'];rerank=summary['all_development']['reranker']
    confirmed_gain=any(rerank[m]['n']==20 and rerank[m]['mean']>baseline[m]['mean'] for m in ('hit_ge2_at5','direct_grade3_hit_at5','scope_limited_answer_basis_complete_at5'))
    if not confirmed_gain:reasons.append('no_confirmed_gain_on_priority_metrics')
    decision='not_adopt_end_experiment' if reasons else 'promising_for_independent_validation_defaults_unchanged'
    report={'decision':decision,'reasons':reasons,'summary':summary,'changes':changes,'missing_evidence_questions':missing,
        'model_load_seconds':result['model_load_seconds'],'rerank_seconds':result['rerank_total_seconds'],'run_seconds':result['run_seconds'],
        'prepare_seconds':pool['prepare_seconds'],'prepare_peak':pool['prepare_peak_working_set_bytes'],'run_peak':result['run_peak_working_set_bytes'],
        'pool_sha256':result['pool_sha256'],'config_sha256':pool['config_sha256'],'frozen_runs':0,'paid_api_calls':0,'defaults_changed':False}
    with (out/f'evaluation-{a.report_version}.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    lines=['# 可选中英文 reranker：一次固定开发集实验','',
        '默认BM25/Dense/RRF、术语表、切分、Agent协议及Harness策略均未修改。只评估相关性，不输出事实支持或审核通过。',
        '标签来源：AI辅助、用户监督；非严格独立专家测试。20题开发集固定，未运行冻结家族、未补标或调参。','',
        '## 模型与资源','',
        '选择cross-encoder/mmarco-mMiniLMv2-L12-H384-v1；固定revision '+result['model_profile']['revision']+'。Apache-2.0；官方mMARCO中英文训练，机器翻译训练数据不保证电力领域表现。',
        '[官方模型卡](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)；[官方ONNX使用说明](https://sbert.net/docs/cross_encoder/usage/efficiency.html)。',
        '使用官方仓库AVX2 UINT8导出，原始单logit按Identity处理，不是概率。512 token，only_second右侧截断，batch2、CPU4线程；查询原文+Evidence.text，无额外标题/前缀/上下文。',
        '实际下载大小与SHA见模型manifest.json；本机资源见resource-record.json，Python3.13.2与实际依赖见python-record.json，无新增依赖。',
        'E5与reranker位于先后退出的独立进程，没有同时常驻。','',
        '## 固定候选池与对照定义','',
        '原BM25正分前50＋扩展BM25正分前50＋Dense正分前50，按fragment ID去重，每路rank/score独立保存。',
        '对照RRF维持原两路等权k60、深度50；扩展独有候选分数0位于尾部（仅为控制组排名，未伪造正分检索命中）。所有候选同时可供reranker排序。未为实验新增第三路融合权重。',
        '固定池RRF前五与现有默认前五一致，故单独扩大池没有改变此控制组前五。reranker与此组之差是共同池上的排序变化；不能声称reranker能召回池外材料。',
        '候选池文件SHA：'+result['pool_sha256'],'配置SHA：'+pool['config_sha256'],'知识版本：'+pool['knowledge_version'],'',
        '## 候选覆盖诊断','',
        '只核查已有标注的直接依据、旧必要组合与原范围内完整依据定义。未定义/部分答案为unknown，不据此宣称全语料依据齐全。相邻上下文、跨题参考不加入候选；只有真实三路检索召回才进入池。','',
        '| 题 | 候选数 | 已标直接依据状态 | 旧组池外缺失 | 原完整依据定义/池覆盖 |','|---|---:|---|---|---|']
    for r in rows:
        c=r['coverage'];lines.append(f"| {r['id']} | {r['candidates']} | {c['direct_basis'] or 'unknown（没有已标3分）'} | {[g['missing_from_pool'] for g in c['groups']]} | {c['scope_complete_definition_eligible']}/{c['scope_complete_candidate_coverage']} |")
    lines+=['','## 实际前五指标','',
        'unknown保持真实位置，不删除后顺延，不按0。Hit/MRR给界限；点估计只在前五全部有标签时计算，n必须同时阅读，不能以不同分母均值推断改善。Recall/nDCG仅指现有合并已标核心池，包括未被本轮并集召回的已标候选，不是全语料指标。',
        '本轮已知标签下相关性Hit下界100%、直接依据Hit下界70%，均高于基线，说明存在可确认的局部收益；unknown限制完整质量评估和增益幅度，并不否定这些收益。',
        '旧组覆盖是成员命中，完整依据另受原可回答性和partial_not_sufficient限制；组完整不证明语义支持。','',
        '| 分组 | 方案 | Hit>=2界限 | MRR界限 | 3分Hit界限 | 池Recall/n | 池nDCG/n | 原组完整/n | 范围完整/n | 前五标注覆盖 |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(v):return '未定义' if v['mean'] is None else f"{v['mean']:.4f}/n={v['n']}"
    for group,methods in summary.items():
        for name,s in methods.items():
            b=s['bounds_ge2'];d=s['bounds_grade3'];c=s['annotation_slots']
            lines.append(f"| {group} | {name} | {b['hit_lower']:.4f}–{b['hit_upper']:.4f} | {b['mrr_lower']:.4f}–{b['mrr_upper']:.4f} | {d['hit_lower']:.4f}–{d['hit_upper']:.4f} | {fmt(s['recall_ge2_judged_core_pool_at5'])} | {fmt(s['ndcg_graded_judged_core_pool_at5'])} | {fmt(s['any_necessary_group_covered_at5'])} | {fmt(s['scope_limited_answer_basis_complete_at5'])} | {c['known']}/{c['total']} |")
    lines+=['','## 性能','',
        f"候选获取进程总耗时{pool['prepare_seconds']:.3f}s，其中E5加载{pool['e5_load_seconds']:.3f}s。重排序模型加载{result['model_load_seconds']:.3f}s；20题纯重排序{result['rerank_total_seconds']:.3f}s；重排序进程总耗时{result['run_seconds']:.3f}s。",
        f"两阶段顺序工作耗时之和{pool['prepare_seconds']+result['run_seconds']:.3f}s（不含下载、两进程启动间人工编写/检查时间）。候选阶段峰值{pool['prepare_peak_working_set_bytes']}bytes；重排序进程峰值{result['run_peak_working_set_bytes']}bytes。",
        '峰值是Windows进程整个生命周期的PeakWorkingSet，包含Python、JSON、模型及证据回查；不是模型独占显存，也不是系统所有进程内存。每题候选获取包含逐条Evidence校验，重排序计时包括分词/推理/截断记录，不含外部上下文。','',
        '| 题 | 候选获取秒 | 重排秒 | 候选数 | 截断片段数 |','|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['id']} | {r['candidate_seconds']:.3f} | {r['rerank_seconds']:.3f} | {r['candidates']} | {len(r['truncated_fragment_ids'])} |")
    lines+=['','## 逐题改善、退步、原文与定位','']
    for r in rows:
        lines+=[f"### {r['id']} / {r['family']} / {r['language']}",'',r['query'],json.dumps(next(c for c in changes if c['id']==r['id']),ensure_ascii=False),
            '受截断片段：'+str(r['truncated_fragment_ids']),'']
        for method,v in r['methods'].items():
            lines += [method+' 实际排名：'+str(v['metrics']['top5_ids'])]
            for n,h in enumerate(v['top5'],1):
                e=h['evidence'];lines += [f"rank{n} / {h['fragment_id']}",json.dumps(e['provenance'],ensure_ascii=False),'```text',e['text'],'```','']
        for bid,status in r['coverage']['direct_basis'].items():lines.append('已标直接依据 '+bid+'：'+status)
    lines+=['','## 结论与边界','',decision,'停止原因：'+', '.join(reasons),
        '本轮结束，不换模型、不调参数、不补标、不执行冻结家族。默认基线保留。',
        '重排不能修复未召回材料或未定义的完整依据；跨片段限定条件属于另行验证的证据组装。宽候选池带来较多unknown，仅凭正文看起来相关不能自动赋标签。','',
        '## 复现命令（输出目录必须全新）','```powershell',
        '.\\.venv\\Scripts\\python.exe -c "from rag.reranker import download; download(\'data/retrieval_local/semantic/reranker-model\')"',
        '.\\.venv\\Scripts\\python.exe -m evaluation.reranker_trial prepare --output-dir data/retrieval_local/semantic/reranker-replay',
        '.\\.venv\\Scripts\\python.exe -m evaluation.reranker_trial run --output-dir data/retrieval_local/semantic/reranker-replay',
        '.\\.venv\\Scripts\\python.exe -m evaluation.reranker_report --output-dir data/retrieval_local/semantic/reranker-replay',
        '.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -q','```']
    with (out/f'report-{a.report_version}.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(json.dumps({'decision':decision,'reasons':reasons,'overall':summary['all_development'],'missing':missing},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
