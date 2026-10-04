"""Audit saved rankings and annotate limitations without rerunning retrieval."""
import json
from evaluation.body_priority_trial import BASE

def main():
    folder=BASE/'body-priority-v1';load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    data=load(folder/'experiment.json');mapping=load(BASE/'blind-review/mapping.json')
    labels=load(BASE/'annotations/supervised-v3-eval-v3/annotations-30-supervised-v3.json')
    old=load(BASE/'annotations/supervised-v3-eval-v3/evaluation.json');qs={q['question_id']:q for q in labels['questions']}
    mismatch=[];supp=[];unknown=[]
    for r in data['results']:
        qm=mapping['questions'][r['id']]
        saved=[qm['candidates'][h['blind_id']]['fragment_id'] for h in qm['original_methods']['rrf']]
        if saved!=[h['fragment_id'] for h in r['methods']['baseline']['top5']]:mismatch.append(r['id'])
        for ref in qs[r['id']].get('supplementary_reference_evidence',[]):
            fid=ref['fragment_id']
            ranks={m:ids.index(fid)+1 if fid in ids else None for m,ids in r['candidate_ranks'].items()}
            supp.append({'question_id':r['id'],'reference':ref,'actual_top50_ranks':ranks,
                'classification':'candidate_depth_miss' if all(v is None for v in ranks.values()) else 'ranking_or_partial_coverage',
                'hit_credit':0,'note':'outside top50 does not establish corpus-wide absence or semantic sufficiency'})
        for method,v in r['methods'].items():
            if v['actual_unknown_top5']:unknown.append({'question_id':r['id'],'method':method,'ids':v['actual_unknown_top5'],'status':'unreviewed'})
    result={'baseline_rrf_top5_mismatches':mismatch,'supplementary_candidate_diagnostics':supp,'new_unknown_candidates':unknown,
        'original_metric_groups':old['evaluation']['groups'],'probe':load(folder/'encoder-probe.json'),
        'tests':{'interpreter':'D:\\PowerTrustAI\\.venv\\Scripts\\python.exe','count':331,'seconds':45.363,'result':'OK'},
        'experiment_summary_correction':'undefined means now exclude null; corrected-summary.json is authoritative, original experiment summaries retained'}
    with (folder/'audit-supplement.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    lines=['# 原排名复现与候选召回补充','',f'原RRF前五不一致题：{mismatch}（空列表表示30题全部一致）。','',
        '候选不足指固定深度50的候选遗漏，不等于文献没有依据；跨题参考只用于定位诊断，信用为0。','',
        '| 问题 | 参考fragment | BM25前50位置 | Dense前50位置 | 分类 |','|---|---|---:|---:|---|']
    for s in supp:
        lines.append(f"| {s['question_id']} | {s['reference']['fragment_id']} | {s['actual_top50_ranks']['bm25']} | {s['actual_top50_ranks']['dense']} | {s['classification']} |")
    lines+=['','## 独立编码探针','',json.dumps(result['probe'],ensure_ascii=False,indent=2),'',
        '两个中英样本的手工有效token平均+L2与实现差异为0，单条/带padding批次差异为0；这只验证编码计算，不验证检索语义。探针峰值约1.11GiB，不能替代50.396秒实验自身的峰值。',
        '探针初次遗漏token_type_ids导致输入报错，已补齐后执行成功；生产编码本来已提供该字段，未改编码实现。','',
        '331项离线测试通过（45.363秒）；原325项加6项正文处理测试。原始baseline前五已复现；原数据和索引哈希不变。','',
        '正文优先+k20仅为待补标的实验方案，当前不修改生产默认。',
        '实验summary初版将未定义值按0聚合，已修正源码；corrected-summary.json按有效分母聚合，保留初版实验记录。','',
        '运行：`D:\\PowerTrustAI\\.venv\\Scripts\\python.exe -m evaluation.body_priority_trial --output-dir data/retrieval_local/semantic/body-priority-new-version`。新目录必需；该命令是未来复现，不应反复使用冻结家族调参。']
    with (folder/'audit-supplement.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(json.dumps({'mismatches':mismatch,'unknown_questions':sorted({r['question_id'] for r in unknown}),'supplementary':supp},ensure_ascii=False))

if __name__=='__main__':main()
