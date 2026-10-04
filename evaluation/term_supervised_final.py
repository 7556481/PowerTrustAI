"""Import one supervised batch and symmetrically evaluate saved actual rankings."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from evaluation.body_priority_trial import BASE
from evaluation.term_expansion_trial import marked_score
from evaluation.supervised_retrieval import METRICS

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def require_keys(obj, allowed, path):
    extra=set(obj)-set(allowed)
    if extra:raise ValueError(path+': unknown fields '+str(sorted(extra)))

def merge_batch(old, mapping, batch, template):
    require_keys(batch,('version','status','questions','annotation_provenance','annotation_summary'),'$')
    require_keys(batch['annotation_provenance'],('reviewer','human_confirmed','new_mapping_seen','prior_experiment_summary_seen',
        'labels_frozen_before_mapping','input_sha256','coverage','prior_labels_changed','review_date','visual_review'),'$.annotation_provenance')
    require_keys(batch['annotation_summary'],('new_candidates_judged','contexts_unreviewed','relevance_counts'),'$.annotation_summary')
    if batch['version']!=template['version']:raise ValueError('$.version: template mismatch')
    qids=[q['question_id'] for q in batch['questions']]
    if len(set(qids))!=len(qids) or set(qids)!=set(mapping['questions']):raise ValueError('$.questions: exact development question set required')
    merged=deepcopy(old);byq={q['question_id']:q for q in merged['questions']};bindings={};count=0;contexts=0;grades=Counter()
    templateqs={q['question_id']:q for q in template['questions']}
    for q in batch['questions']:
        qid=q['question_id'];require_keys(q,('question_id','status','new_candidates'),qid)
        expected=mapping['questions'][qid];bids=[v['candidate_id'] for v in q['new_candidates']]
        if len(set(bids))!=len(bids) or set(bids)!=set(expected):raise ValueError(qid+': exact candidate coverage required')
        targets=byq[qid];seen={f['fragment_id'] for f in targets['fragment_relevance'] if f['role']!='adjacent_context'};bindings[qid]={}
        tmpl={c['candidate_id']:c for c in templateqs[qid]['new_candidates']}
        for candidate in q['new_candidates']:
            bid=candidate['candidate_id'];path=qid+'.'+bid
            require_keys(candidate,('candidate_id','fragment_id','status','relevance','support_relation','conditions','scope','reason','contexts','visual_checked'),path)
            if candidate['fragment_id']!=expected[bid]['fragment_id']:raise ValueError(path+'.fragment_id: mapping mismatch')
            if candidate['fragment_id'] in seen:raise ValueError(path+': old core label exists; refuse overwrite')
            seen.add(candidate['fragment_id'])
            if candidate['status'] not in ('ai_proposed','unreviewed'):raise ValueError(path+'.status: preserve AI supervision or unknown')
            grade=candidate['relevance']
            if grade is not None and (type(grade)!=int or not 0<=grade<=3):raise ValueError(path+'.relevance: integer0..3 or null required')
            if candidate['status']=='unreviewed' and grade is not None:raise ValueError(path+': unreviewed cannot receive numeric grade')
            if not isinstance(candidate['conditions'],list) or not all(isinstance(x,str) for x in candidate['conditions']):raise ValueError(path+'.conditions: string array required')
            if not isinstance(candidate['reason'],str):raise ValueError(path+'.reason: string required')
            if candidate['support_relation'] not in ('no_answer_basis','background_only','partial_answer_basis','direct_answer_basis',None):
                raise ValueError(path+'.support_relation: unknown classification')
            if candidate['scope'] is not None and not isinstance(candidate['scope'],str):raise ValueError(path+'.scope: string or null required')
            if candidate.get('visual_checked') is not None and type(candidate['visual_checked'])!=bool:raise ValueError(path+'.visual_checked: boolean or null required')
            ctxids=[x['id'] for x in candidate['contexts']]
            if len(set(ctxids))!=len(ctxids) or set(ctxids)!={x['id'] for x in tmpl[bid]['contexts']}:raise ValueError(path+'.contexts: mapping/template mismatch')
            for ctx in candidate['contexts']:
                require_keys(ctx,('id','status','relevance'),path+'.contexts')
                if ctx['status']!='unreviewed' or ctx['relevance'] is not None:raise ValueError(path+'.contexts: this batch leaves context unknown')
                contexts+=1
            targets['fragment_relevance'].append({**deepcopy(candidate),'blind_id':bid,'role':'candidate',
                'annotation_source':'term-expansion-27-supervised-v1; AI assisted, user supervised'})
            bindings[qid][bid]=deepcopy(expected[bid]);count+=1;grades[str(grade)]+=1
        # No recomputation or replacement of answerability or necessary combinations.
        assert targets['necessary_evidence_combinations']==next(q for q in old['questions'] if q['question_id']==qid)['necessary_evidence_combinations']
    summary=batch['annotation_summary']
    if (count,contexts)!=(summary['new_candidates_judged'],summary['contexts_unreviewed']) or dict(grades)!=summary['relevance_counts']:
        raise ValueError('$.annotation_summary: counts disagree with actual records')
    merged['supplementary_annotation_batch']=deepcopy(batch)
    return merged,bindings

def evaluate_saved(merged, oldmap, blindmap, experiment):
    qs={q['question_id']:q for q in merged['questions']};rows=[]
    for saved in experiment['results']:
        qid=saved['id'];qm=deepcopy(oldmap['questions'][qid])
        for bid,entry in blindmap['questions'][qid].items():qm['candidates'][bid]={'fragment_id':entry['fragment_id']}
        result={k:saved[k] for k in ('id','query','family','split','language')};result['variants']={}
        for variant,methods in saved['variants'].items():
            result['variants'][variant]={method:{'hits':deepcopy(v['hits']),
                'metrics':marked_score(qs[qid],qm,[h['fragment_id'] for h in v['hits']])} for method,v in methods.items()}
        result['necessary_evidence_combinations']=deepcopy(qs[qid]['necessary_evidence_combinations'])
        result['answerability']=qs[qid]['answerability'];result['combination_sufficiency']=qs[qid].get('evidence_combination_completeness')
        rows.append(result)
    return rows

def summarize(rows):
    summary={}
    groups={'all_development':rows,'natural':[r for r in rows if r['language']!='acronym'],'keyword':[r for r in rows if r['language']=='acronym'],
        'english':[r for r in rows if r['language']=='en'],'chinese':[r for r in rows if r['language']=='zh']}
    groups.update({'family:'+family:[r for r in rows if r['family']==family] for family in sorted({r['family'] for r in rows})})
    for group,subset in groups.items():
        summary[group]={}
        for variant in ('baseline','term_expansion'):
            summary[group][variant]={}
            for method in ('bm25','dense','rrf'):
                vs=[r['variants'][variant][method]['metrics'] for r in subset];metrics={}
                for metric in METRICS:
                    values=[v[metric] for v in vs if v[metric] is not None]
                    metrics[metric]={'mean':sum(values)/len(values) if values else None,'n':len(values)}
                total=sum(len(v['top5_ids']) for v in vs);known=total-sum(len(v['unknown_top5_ids']) for v in vs)
                metrics['annotation_slots']={'known':known,'total':total,'rate':known/total if total else None}
                metrics['unknown_questions']=sum(bool(v['unknown_top5_ids']) for v in vs)
                summary[group][variant][method]=metrics
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--annotations',required=True);p.add_argument('--review',required=True);p.add_argument('--output-dir',required=True)
    args=p.parse_args();out=Path(args.output_dir)
    if out.exists():raise FileExistsError('New version directory required')
    trial=BASE/'term-expansion-v1/development-v2';oldpath=BASE/'annotations/supervised-v3-eval-v3/annotations-30-supervised-v3.json'
    files=[oldpath,trial/'blind-mapping.json',trial/'experiment.json',trial/'annotations-template.json',BASE/'blind-review/mapping.json',BASE/'corpus.sqlite3',BASE/'vectors.sqlite3']
    before={str(p):digest(p) for p in files};batch=load(args.annotations);old=load(oldpath);mapping=load(trial/'blind-mapping.json');template=load(trial/'annotations-template.json')
    # Explicit aliases for upload filenames; checks compare exact original bytes.
    aliases={'questions(1).md':'questions.md','evidence-pool(1).md':'evidence-pool.md','annotations-template(1).json':'annotations-template.json'}
    declared=batch['annotation_provenance']['input_sha256']
    if set(declared)!=set(aliases):raise ValueError('$.annotation_provenance.input_sha256: unrecognized file aliases')
    for name,expected in declared.items():
        if digest(trial/aliases[name])!=expected:raise ValueError('Input hash mismatch: '+name)
    merged,bindings=merge_batch(old,mapping,batch,template)
    rows=evaluate_saved(merged,load(BASE/'blind-review/mapping.json'),mapping,load(trial/'experiment.json'));summary=summarize(rows)
    changes=[]
    for r in rows:
        for method in ('bm25','dense','rrf'):
            a=r['variants']['baseline'][method]['metrics'];b=r['variants']['term_expansion'][method]['metrics']
            deltas={name:b[name]-a[name] for name in METRICS if a[name] is not None and b[name] is not None}
            up=[n for n,v in deltas.items() if v>1e-10];down=[n for n,v in deltas.items() if v< -1e-10]
            changes.append({'question_id':r['id'],'method':method,'improved':up,'regressed':down,'deltas':deltas})
    # Conservative release gate: the deployed hybrid path cannot regress direct or full-basis coverage on any question.
    important=('hit_ge2_at5','direct_grade3_hit_at5','any_necessary_group_covered_at5','scope_limited_answer_basis_complete_at5')
    regressions=[c for c in changes if c['method']=='rrf' and any(n in c['regressed'] for n in important)]
    allstats=summary['all_development'];a=allstats['baseline']['rrf'];b=allstats['term_expansion']['rrf']
    gain=any(b[n]['mean']>a[n]['mean']+1e-10 for n in important)
    decision='adopt_experimental_configuration' if gain and not regressions and b['unknown_questions']==0 else 'keep_baseline_reject_default_switch'
    report={'evaluation_version':'term-supervised-final-v1','created_utc':datetime.now(timezone.utc).isoformat(),
        'knowledge_version':load(trial/'experiment.json')['knowledge_version'],'annotation_provenance':batch['annotation_provenance'],
        'source_sha256':digest(args.annotations),'review_sha256':digest(args.review),'protected_sha256':before,
        'summary':summary,'per_question':rows,'changes':changes,'important_hybrid_regressions':regressions,'decision':decision,
        'paid_api_calls':0,'retrieval_calls':0,'frozen_runs':0,'context_hit_credit':0,'original_combinations_unchanged':True,
        'scope':'same expanded question-specific judged pool for both variants; actual saved ranks, no unknown compression; AI-assisted supervised labels, not expert gold'}
    assert before=={str(p):digest(p) for p in files}
    out.mkdir(parents=True)
    (out/'term-expansion-27-supervised-v1.json').write_bytes(Path(args.annotations).read_bytes())
    (out/'term-expansion-27-review.md').write_bytes(Path(args.review).read_bytes())
    for name,value in [('merged-annotations.json',merged),('bound-mapping.json',bindings),('evaluation.json',report)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 27项监督标注：20题开发集最终对照','',
        'AI辅助、用户监督来源及批次反馈按原文件保留；human_confirmed:false不改为逐项专家确认。曾看到实验摘要，因此不是严格独立盲审。',
        '同一扩充池对两方案对称回算；原问题、可回答性、必要组合和充分性声明不变。不新增等价组合。上下文54条继续unknown，不计0，不计命中。',
        'Hit/MRR用相关性>=2；3分直接依据另列。Recall/nDCG仅限扩充的已标候选池，非全语料Recall；1分背景贡献nDCG。必要组合覆盖不等于完整支持。',
        '完整依据仍按旧组、原可回答性与partial_not_sufficient约束；未命中旧组即使有新相近片段，也不静默视为等价支持。','',
        '| 分组 | 方案/方法 | Hit>=2 | MRR>=2 | 3分Hit | 池Recall | 池nDCG | 组完整覆盖 | 完整依据 | 前五标注覆盖 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(v):return '未定义' if v['mean'] is None else f"{v['mean']:.4f} (n={v['n']})"
    columns=('hit_ge2_at5','mrr_ge2_at5','direct_grade3_hit_at5','recall_ge2_judged_core_pool_at5','ndcg_graded_judged_core_pool_at5','any_necessary_group_covered_at5','scope_limited_answer_basis_complete_at5')
    for group,variants in summary.items():
        for variant,methods in variants.items():
            for method,stats in methods.items():lines.append(f'| {group} | {variant}/{method} | '+' | '.join(fmt(stats[n]) for n in columns)+f" | {stats['annotation_slots']} |")
    lines+=['','## 逐题变化与原组合','']
    for r in rows:
        lines += [f"### {r['id']} / {r['family']}",r['query'],
            '旧必要组合：'+json.dumps(r['necessary_evidence_combinations'],ensure_ascii=False),
            '原充分性：'+str(r['combination_sufficiency']),'']
        for method in ('bm25','dense','rrf'):
            c=next(c for c in changes if c['question_id']==r['id'] and c['method']==method)
            lines+=['变化：'+json.dumps(c,ensure_ascii=False)]
            for variant in ('baseline','term_expansion'):
                v=r['variants'][variant][method];lines += [f"{variant}/{method} 实际排名：{v['metrics']['top5_ids']}",
                    '指标：'+json.dumps({m:v['metrics'][m] for m in columns},ensure_ascii=False)]
    lines+=['','## 决策','',decision,
        '采用门槛：部署的RRF有明确覆盖收益，且逐题相关性/直接依据/旧组合/完整依据无退步、无未标前五。评测只决定默认切换，不对事实支持作新的判定。',
        '重要RRF退步：'+json.dumps(regressions,ensure_ascii=False,indent=2),
        '不再调参、补第二批或执行冻结对照。保留术语扩展为实验记录；如拒绝默认切换，生产继续原基线。',
        '新标签没有3分，但旧3分仍保留；新2分正文能改善部分召回，不自动完成D05/D06/D12的整题依据。',
        '附件evaluation.json保留真实命中原文、排名和定位；bound-mapping.json保留新增候选映射。输入来源原样复制，原文件SHA前后一致。']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'output':str(out),'decision':decision,'all':summary['all_development'],'important_regressions':regressions},ensure_ascii=False,indent=2))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
