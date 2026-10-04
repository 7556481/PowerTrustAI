"""Summarize real ranks from the one saved development experiment."""
import argparse
import json
from pathlib import Path
from evaluation.body_priority_trial import BASE
from evaluation.supervised_retrieval import METRICS

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',required=True);args=p.parse_args();folder=Path(args.input_dir)
    load=lambda p:json.loads(p.read_text(encoding='utf-8'));data=load(folder/'experiment.json')
    diagnosis=load(BASE/'term-expansion-v1/diagnosis.json');summary={};regressions=[]
    subset_groups={'all_development':data['results'],'natural':[r for r in data['results'] if r['language']!='acronym'],
        'keyword':[r for r in data['results'] if r['language']=='acronym'],
        'english':[r for r in data['results'] if r['language']=='en'],'chinese':[r for r in data['results'] if r['language']=='zh']}
    lines=['# 受控电力术语查询扩展：开发集单变量实验','',
        '只改变BM25查询；Dense仍编码原问题，模型、切分、搜索文本、候选深度50、RRF(k60等权)、正文过滤均不变。默认配置未采用新方案。',
        '规则由开发集暴露的中英术语匹配问题设计；中英同义问题属于同族，不是独立泛化证据。没有答案文本、金片段ID或页码进入查询。','',
        '## 三题逐片段诊断','',
        '所有参考片段在固定快照中，Evidence回查成功；没有索引资格/版本过滤错误。索引search_text保存英文正文，中文原查询没有交集。',
        'BM25零分片段的“完整排名”仅为稳定并列位置，不是正分检索命中；两者分别记录。',
        'Dense沿用同一固定E5模型与tokenizer版本，query:/passage:前缀正确；已知参考最长299 token，只有一个窗口、没有尾部截断。其排名落后于结构噪声及语义邻近内容，说明本查询的匹配/排序不足，不能推断模型普遍不支持中文。','',
        '| 问题 | 片段 | BM25原位置/分数 | Dense原位置/分数 | BM25新位置/分数 | Dense新位置/分数 |',
        '|---|---|---|---|---|---|']
    for r in data['results']:
        for ref in r['references']:
            b,a=ref['before'],ref['after']
            lines.append(f"| {r['id']} | {ref['fragment_id']} | {b['bm25_rank_including_zero_ties']}/{b['bm25_score']:.5f} | {b['dense_rank']}/{b['dense_score']:.5f} | {a['bm25_rank_including_zero_ties']}/{a['bm25_score']:.5f} | {a['dense_rank']}/{a['dense_score']:.5f} |")
    for q in diagnosis['questions']:
        lines += [f"### {q['id']} 实际查询与编码",'',q['query'],'query编码：'+q['query_encoding'],
            'BM25词项：'+json.dumps(q['query_tokens'],ensure_ascii=False),'']
        for ref in q['references']:
            e=ref['evidence'];lines += [json.dumps(e['provenance'],ensure_ascii=False),
                '匹配词项：'+json.dumps(ref['term_overlap'],ensure_ascii=False)+'；passage窗口长度：'+str(ref['passage_token_lengths']),
                '实际passage输入：`passage: ` + 以下search_text（不是改写Evidence）：','```text',ref['search_text'],'```','原始Evidence：','```text',e['text'],'```','']
        lines += ['原Dense前五噪声/邻近候选：','']
        for n in q['noise_top5']['dense']:
            e=n['evidence'];lines += [f"rank{n['rank']} cosine={n['score']:.6f}",json.dumps(e['provenance'],ensure_ascii=False),'```text',e['text'],'```','']
    lines += ['## 实际前五统计（不压缩排名）','',
        '有unknown时Hit/MRR/Recall/nDCG点估计未定义。Hit和MRR另给上下界，已命中的已标候选只保证下界，未知候选不记0。点估计有效分母可能不同，不应直接据它宣称改善。',
        '必要组合按原标注组内AND、组间OR；组合成员位置使用真实top5。完整依据还受可回答性和partial_not_sufficient限制；观察到组合完整不等于语义事实验证。',
        'Recall/nDCG只针对既有已标核心池，未知候选仍留位；相邻上下文不补算，跨题参考没有额外信用。','',
        '| 分组 | 方案/方法 | Hit>=2区间 | MRR区间 | 3分Hit区间 | 标注覆盖率 | 组覆盖/有效n | 完整依据/题数 |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for group,subset in subset_groups.items():
        summary[group]={}
        for variant in ('baseline','term_expansion'):
            summary[group][variant]={}
            for method in ('bm25','dense','rrf'):
                vals=[r['variants'][variant][method]['metrics'] for r in subset];agg={}
                for metric in METRICS+('top5_annotation_coverage',):
                    present=[v[metric] for v in vals if v[metric] is not None]
                    agg[metric]={'mean':sum(present)/len(present) if present else None,'n':len(present)}
                for name in ('bounds_ge2','bounds_grade3'):
                    agg[name]={k:sum(v[name][k] for v in vals)/len(vals) for k in ('hit_lower','hit_upper','mrr_lower','mrr_upper')}
                coverage_slots=sum(len(v['top5_ids'])-len(v['unknown_top5_ids']) for v in vals);slots=sum(len(v['top5_ids']) for v in vals)
                agg['annotated_top5_slots']={'known':coverage_slots,'total':slots,'rate':coverage_slots/slots if slots else None}
                agg['unknown_questions']=sum(bool(v['unknown_top5_ids']) for v in vals)
                summary[group][variant][method]=agg
                interval=lambda name,a,b:f"{agg[name][a]:.4f}–{agg[name][b]:.4f}"
                comb=agg['any_necessary_group_covered_at5'];full=agg['scope_limited_answer_basis_complete_at5']
                lines.append(f"| {group}/{len(subset)} | {variant}/{method} | {interval('bounds_ge2','hit_lower','hit_upper')} | {interval('bounds_ge2','mrr_lower','mrr_upper')} | {interval('bounds_grade3','hit_lower','hit_upper')} | {agg['annotated_top5_slots']['rate'] if slots else None} | {comb['mean']} (n={comb['n']}) | {full['mean']} (n={full['n']}) |")
    lines+=['','## 全部逐题变化与退步（按已知标签，不自动判断unknown）','']
    for r in data['results']:
        lines += [f"### {r['id']} / {r['family']} / {r['language']}",'',r['query'],'BM25扩展查询：'+r['expanded_bm25_query'],
            '触发规则：'+json.dumps(r['triggers'],ensure_ascii=False),'']
        for method in ('bm25','dense','rrf'):
            a=r['variants']['baseline'][method]['metrics'];b=r['variants']['term_expansion'][method]['metrics']
            downs=[m for m in METRICS if a[m] is not None and b[m] is not None and b[m]<a[m]-1e-10]
            lost=set(a['top5_ids'])-set(b['top5_ids']);knownlost=[bid for bid in lost if not bid.startswith('unknown:')]
            if downs:regressions.append({'id':r['id'],'method':method,'decreased_defined_metrics':downs})
            lines += [f"{method}: 改前 {a['top5_ids']}；改后 {b['top5_ids']}；退步指标 {downs}；离开前五的已标候选 {knownlost}。",'']
            for variant in ('baseline','term_expansion'):
                for h in r['variants'][variant][method]['hits']:
                    e=h['evidence'];lines += [f"{variant}/{method} rank{h['rank']} score={h['score']:.6f} / {h['fragment_id']}",json.dumps(e['provenance'],ensure_ascii=False),'```text',e['text'],'```','']
    lines += ['## 决策、耗时与盲审','',data['decision'],
        f"20题开发集，冻结家族运行0次，付费调用0。墙钟{data['seconds']:.3f}s，进程CPU{data['cpu_seconds']:.3f}s；CPU4线程。内存峰值本轮未测量。",
        '该实验先计算原始两路排名，再复用Dense向量计算扩展BM25；新增时间含排序、证据回查和导出，不是独立冷启动延迟。每题两阶段耗时在experiment.json。',
        '新增候选只导出这一批，按问题—片段去重；evidence-pool.md与annotations-template.json可上传，blind-mapping.json不可混入盲审。旧标注直接复用。',
        '第一次导出因随机种子类型错误终止，修复后使用独立development-v2目录；没有改写历史或运行冻结题。',
        '建议：等待这一批补标后决定是否采用。方案已实现和验证，最终语义结论仍受unknown限制；不以候选前移或部分组合覆盖代替完整答案支持。']
    for name,value in [('summary.json',summary),('regressions.json',regressions)]:
        with (folder/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    with (folder/'report.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines))
    queries=['# 固定开发集问题','']
    for r in data['results']:queries += [f"## {r['id']} / {r['family']} / development",r['query'],'']
    with (folder/'questions.md').open('x',encoding='utf-8') as f:f.write('\n'.join(queries))
    print(json.dumps({'overall':summary['all_development'],'regressions':regressions},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
