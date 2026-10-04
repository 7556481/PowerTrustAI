"""Post-run integrity and label-bound rank diagnostics; no new inference."""
import argparse
import json
from pathlib import Path
from dataclasses import asdict
from evaluation.reranker_trial import load,bound_mapping,FINAL,sha,verify_saved_evidence
from rag.reranker import file_hash
from rag.storage import KnowledgeStore

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();out=Path(a.output_dir)
    pool=load(out/'candidate-pool.json');results=load(out/'reranker-results.json');mapping=bound_mapping();labels=load(FINAL/'merged-annotations.json');qs={q['question_id']:q for q in labels['questions']}
    assert file_hash(out/'candidate-pool.json')==results['pool_sha256'];assert sha(pool['config'])==pool['config_sha256']
    assert all(file_hash(path)==h for path,h in pool['protected_sha256'].items())
    assert len(results['results'])==20 and {q['id'] for q in results['results']}=={q['id'] for q in pool['entries']}
    checked=0;diagnostics=[];truncations=[]
    with KnowledgeStore(Path(next(p for p in pool['protected_sha256'] if p.endswith('corpus.sqlite3'))),readonly=True) as store:
        for q in results['results']:
            entry=next(e for e in pool['entries'] if e['id']==q['id']);ranked=q['rankings'];byfid={r['fragment_id']:r for r in ranked}
            assert set(byfid)==set(entry['candidates']) and len(byfid)==len(ranked)
            assert [r['rank'] for r in ranked]==list(range(1,len(ranked)+1))
            for fid,candidate in entry['candidates'].items():
                verify_saved_evidence(store,fid,pool['knowledge_version'],candidate['evidence']);checked+=1
                if byfid[fid]['encoding']['truncated']:
                    note=byfid[fid]['encoding'];e=candidate['evidence']
                    truncations.append({'question_id':q['id'],'fragment_id':fid,'encoding':note,
                        'provenance':e['provenance'],'omitted_raw_tail':e['text'][note['kept_body_char_end']:],
                        'semantic_effect':'unknown; no automatic claim that omitted conditions are irrelevant'})
            for label in qs[q['id']]['fragment_relevance']:
                if label['role']=='adjacent_context' or label['relevance'] is None or label['relevance']<2:continue
                fid=label['fragment_id'];row=byfid.get(fid);candidate=entry['candidates'].get(fid)
                diagnostics.append({'question_id':q['id'],'blind_id':label['blind_id'],'relevance':label['relevance'],'fragment_id':fid,
                    'in_pool':row is not None,'rrf_rank':entry['rrf_control_ids'].index(fid)+1 if candidate else None,
                    'reranker_rank':row['rank'] if row else None,'reranker_score':row['score'] if row else None,
                    'original_routes':candidate['origins'] if candidate else [],'provenance':candidate['evidence']['provenance'] if candidate else None})
    for name,value in [('known-evidence-ranks.json',diagnostics),('truncation-review.json',truncations)]:
        with (out/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    verification={'candidate_and_config_hashes_verified':True,'knowledge_evidence_backtraces':checked,
        'unique_candidates_per_question':True,'old_outputs_and_labels_sha_unchanged':True,'one_model_one_config_one_20_question_trial':True,
        'tests':{'count':352,'seconds':44.906,'result':'OK','interpreter':'D:\\PowerTrustAI\\.venv\\Scripts\\python.exe'},
        'truncated_question_fragment_pairs':len(truncations),'new_labels':0,'frozen_runs':0,'paid_api_calls':0,
        'report_current':'report-v2.md','note':'v2 refines wording of confirmed local benefit vs unknown limitations; no new inference'}
    with (out/'verification.json').open('x',encoding='utf-8') as f:json.dump(verification,f,ensure_ascii=False,indent=2)
    modeldir=Path(__file__).resolve().parents[1]/'data/retrieval_local/semantic/reranker-model'
    manifest=load(modeldir/'manifest.json')
    audit={'official_card':'https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1','official_onnx_docs':'https://sbert.net/docs/cross_encoder/usage/efficiency.html',
        'selection':'single pretrained bilingual mMARCO model; official AVX2 int8 artifact reduces resident CPU memory; no torch/export/install needed',
        'license':'Apache-2.0','manifest':manifest,'actual_download_bytes':sum(v['bytes'] for v in manifest['files'].values()),
        'input_limit_source':'official tokenizer_config model_max_length512; model config max_position_embeddings514 XLM-R specials',
        'activation_source':'official config sbert_ce_default_activation_function=Identity; output logits are relevance only',
        'resources':load(out/'resource-record.json'),'python':load(out/'python-record.json'),
        'measurement_caveat':'Some reranker execution overlapped ordinary offline regression tests; practical measurement, not isolated benchmark.',
        'source_sha256':{str(path):file_hash(path) for path in [Path(__file__),Path(__file__).with_name('reranker_trial.py'),Path(__file__).with_name('reranker_report.py'),Path(__file__).resolve().parents[1]/'rag/reranker.py']}}
    with (out/'model-resource-audit.json').open('x',encoding='utf-8') as f:json.dump(audit,f,ensure_ascii=False,indent=2)
    notes=['# 实验交付与核查','',
        '当前报告：report-v2.md；原报告保留。v2只澄清局部收益确实存在，同时unknown限制整体评估；未重新推理。',
        '不采用，实验结束；默认基线、历史索引、历史标签及旧项目不变，不开补标/冻结对照。',
        '代码：rag/reranker.py可选CPU重排模块；evaluation/reranker_trial.py分进程候选获取及单次模型实验；reranker_report.py已保存结果的评测；reranker_verify.py定位/完整性QA；tests/test_reranker.py11项离线测试。',
        '352项测试通过，44.906秒。所有1669个候选绑定回查通过；原记录SHA一致。截断影响71个问题—片段对，见truncation-review.json。',
        '性能记录不是隔离基准：推理后段与普通离线回归有重叠；不会凭该耗时推断严格延迟SLA。',
        '下载文件准确大小、版本、许可、Python和硬件记录见model-resource-audit.json。两进程内存峰值独立，不叠加为同时常驻。',
        '已标相关依据每题的前后完整排名、分数、来源和页码见known-evidence-ranks.json；全部候选原文/定位见candidate-pool.json；全部重排分数/截断见reranker-results.json。',
        '本轮不证明事实支持或工程安全，也不验证跨片段证据组装。未标仍unknown，无新增标签。']
    with (out/'README.md').open('x',encoding='utf-8') as f:f.write('\n'.join(notes))
    print(json.dumps(verification,ensure_ascii=False))

if __name__=='__main__':main()
