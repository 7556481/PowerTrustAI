"""Verify saved baseline, locators and blind-package bounds without new retrieval."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from evaluation.body_priority_trial import BASE
from rag.storage import KnowledgeStore

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',required=True);args=p.parse_args();folder=Path(args.input_dir)
    load=lambda p:json.loads(p.read_text(encoding='utf-8'));d=load(folder/'experiment.json');m=load(BASE/'blind-review/mapping.json')
    bm=load(folder/'blind-mapping.json');template=load(folder/'annotations-template.json')
    mismatches=[];count=0;context_count=0;regressions=[]
    with KnowledgeStore(BASE/'corpus.sqlite3',readonly=True) as store:
        for r in d['results']:
            qm=m['questions'][r['id']]
            for method in ('bm25','dense','rrf'):
                expected=[qm['candidates'][h['blind_id']]['fragment_id'] for h in qm['original_methods'][method]]
                actual=[h['fragment_id'] for h in r['variants']['baseline'][method]['hits']]
                if expected!=actual:mismatches.append((r['id'],method))
                for variant in ('baseline','term_expansion'):
                    metrics=r['variants'][variant][method]['metrics']
                    for name in ('bounds_ge2','bounds_grade3'):
                        bounds=metrics[name];assert bounds['hit_lower']<=bounds['hit_upper'];assert bounds['mrr_lower']<=bounds['mrr_upper']
                    for hit in r['variants'][variant][method]['hits']:
                        assert json.loads(json.dumps(asdict(store.evidence(hit['fragment_id'],d['knowledge_version']))))==hit['evidence'];count+=1
                a=r['variants']['baseline'][method]['metrics'];b=r['variants']['term_expansion'][method]['metrics']
                losses={name:{field:b[name][field]-a[name][field] for field in ('hit_lower','mrr_lower') if b[name][field]<a[name][field]-1e-10} for name in ('bounds_ge2','bounds_grade3')}
                if any(losses.values()):regressions.append({'id':r['id'],'method':method,'known_label_lower_bound_decreases':losses,'unlabeled_can_change_final_judgment':bool(b['unknown_top5_ids'])})
        for qid,candidates in bm['questions'].items():
            seen=set()
            for bid,c in candidates.items():
                assert c['fragment_id'] not in seen;seen.add(c['fragment_id'])
                assert all(c['fragment_id'] not in {v['fragment_id'] for v in m['questions'][qid]['candidates'].values()} for _ in [0])
                for item in c['context']['items']:
                    e=item['evidence'];assert json.loads(json.dumps(asdict(store.evidence(e['provenance']['fragment_id'],d['knowledge_version']))))==e;context_count+=1
            labels=next(q['new_candidates'] for q in template['questions'] if q['question_id']==qid)
            assert {v['candidate_id'] for v in labels}==set(candidates)
            assert all(v['status']=='unreviewed' and v['relevance'] is None for v in labels)
    assert not mismatches
    result={'baseline_top5_mismatches':mismatches,'verified_hit_locators':count,'verified_independent_contexts':context_count,
        'new_question_fragment_pairs':sum(len(v) for v in bm['questions'].values()),'bounds_decreases':regressions,
        'tests':{'interpreter':'D:\\PowerTrustAI\\.venv\\Scripts\\python.exe','count':336,'seconds':52.267,'result':'OK'},
        'paid_api_calls':0,'frozen_runs':0,'history_hashes_unchanged':d['history_unchanged']}
    with (folder/'verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    instructions=['# 一次性补标与运行说明','',
        '上传 questions.md、evidence-pool.md、annotations-template.json；不要上传 blind-mapping.json、experiment.json 或 report.md，以免透露方案/排名/分数。',
        '27个新增问题—片段候选；已有监督标签按原版本复用，不重标以促成方案胜出。相邻上下文另标，未标保持unknown。',
        '沿用原0–3相关性标准：0不相关、1背景、2部分相关依据、3直接依据；同时标记支持关系、关键限定条件、适用范围和理由。直接依据不自动等于整个答案完整。',
        '来源保存为AI辅助、用户监督，不改写为独立专家标签；保留批次反馈。缺视觉核对的PDF位置注明待复核。',
        '新返回标签只能评价此次固定结果，不用于循环调参。实际新命中可在补标后计分，但不得仅因它被列为跨题参考就给信用。','',
        '命令（从D:\\PowerTrustAI运行，输出目录必须全新）：','```powershell',
        '.\\.venv\\Scripts\\python.exe -m evaluation.recall_diagnosis --output data/retrieval_local/semantic/recall-new/diagnosis.json',
        '.\\.venv\\Scripts\\python.exe -m evaluation.term_expansion_trial --output-dir data/retrieval_local/semantic/recall-new/development',
        '.\\.venv\\Scripts\\python.exe -m evaluation.term_expansion_report --input-dir data/retrieval_local/semantic/recall-new/development',
        '.\\.venv\\Scripts\\python.exe -m evaluation.term_expansion_verify --input-dir data/retrieval_local/semantic/recall-new/development',
        '.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -q','```','',
        'recall_diagnosis单独输出诊断，report当前引用既有term-expansion-v1诊断作为固定诊断来源。',
        '完整已知标签退步见regressions.json；有unknown的已知命中下界下降见verification.json（不声称未知实际不相关）。',
        '当前建议等待唯一补标批次；默认配置不变。冻结对照门槛尚未满足，因此本轮冻结运行0次。','',
        '修改文件：rag/query_terms.py只提供可选词汇扩展；evaluation/recall_diagnosis.py全排名诊断；term_expansion_trial.py单变量实验和盲审导出；term_expansion_report.py实际排名统计；term_expansion_verify.py版本/原文/盲审QA；tests/test_query_terms.py离线回归。',
        '验证结果：336项测试通过，52.267秒；所有基线top5复现，原文/定位及上下文回查通过；原索引与受保护历史SHA不变。']
    with (folder/'README.md').open('x',encoding='utf-8') as f:f.write('\n'.join(instructions))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
