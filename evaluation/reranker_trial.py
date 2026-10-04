"""One fixed development-only reranker trial, separated retrieval/inference processes."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
from evaluation.body_priority_trial import BASE
from rag.reranker import CONFIG, MODEL_ID, REVISION, file_hash, peak_working_set, stable_order

FINAL=BASE/'annotations/term-expansion-27-final-v1'
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def union_candidates(routes):
    result={}
    for name,hits in routes.items():
        for rank,hit in enumerate(hits,1):
            result.setdefault(hit['fragment_id'],{'fragment_id':hit['fragment_id'],'origins':[]})['origins'].append(
                {'route':name,'rank':rank,'score':hit['score']})
    return result

def verify_saved_evidence(store,fid,knowledge_version,saved):
    p=saved.get('provenance') or {}
    if p.get('knowledge_version')!=knowledge_version or p.get('fragment_id')!=fid:
        raise ValueError('Evidence binding mismatch: '+fid)
    actual=json.loads(json.dumps(asdict(store.evidence(fid,knowledge_version))))
    if actual!=saved:raise ValueError('Evidence/version integrity mismatch: '+fid)
    return actual

def bound_mapping():
    mapping=load(BASE/'blind-review/mapping.json')
    extra=load(FINAL/'bound-mapping.json')
    for qid,candidates in extra.items():
        mapping['questions'][qid]['candidates'].update({bid:{'fragment_id':v['fragment_id']} for bid,v in candidates.items()})
    return mapping

def coverage(question,candidates,pool,baseline):
    fid=lambda bid:candidates[bid]['fragment_id']
    direct=[f['blind_id'] for f in question['fragment_relevance'] if f['role']!='adjacent_context' and f['relevance']==3]
    classify=lambda bid:'recall_missing' if fid(bid) not in pool else 'already_top5' if fid(bid) in baseline else 'ranking_failure'
    groups=question['necessary_evidence_combinations']['groups']
    eligible=question['answerability']['value']=='answerable_with_scope_limits' and question.get('evidence_combination_completeness')!='partial_not_sufficient' and bool(groups)
    return {'direct_basis':{bid:classify(bid) for bid in direct},'direct_definition':'known grade3 candidates only; empty => unknown, not corpus-wide absence',
        'groups':[{'ids':g,'missing_from_pool':[bid for bid in g if fid(bid) not in pool],
            'missing_from_default_top5':[bid for bid in g if fid(bid) not in baseline]} for g in groups],
        'necessary_group_definition':'known original groups' if groups else 'unknown: no original complete group definition',
        'scope_complete_definition_eligible':eligible,
        'scope_complete_candidate_coverage':any(all(fid(bid) in pool for bid in g) for g in groups) if eligible else None}

def prepare(out):
    from rag.embedding import E5ONNXEncoder
    from rag.semantic import VectorIndex
    from rag.storage import KnowledgeStore
    from rag.bm25 import score_corpus, INDEX_CONFIG
    from rag.query_terms import expand_query,VERSION
    from evaluation.recall_diagnosis import full_rank
    out=Path(out)
    if out.exists():raise FileExistsError('Independent output version required')
    out.mkdir(parents=True);start=time.perf_counter();cpu=time.process_time()
    dataset=load(BASE/'dataset-v1.json');labels=load(FINAL/'merged-annotations.json');mapping=bound_mapping()
    qs={q['question_id']:q for q in labels['questions']};oldresults={r['id']:r for r in load(FINAL/'evaluation.json')['per_question']}
    protected=[BASE/'corpus.sqlite3',BASE/'vectors.sqlite3',FINAL/'merged-annotations.json',FINAL/'evaluation.json',BASE/'comparison-v2.json',BASE/'body-priority-v1/experiment.json',BASE/'term-expansion-v1/development-v2/experiment.json']
    hashes={str(p):file_hash(p) for p in protected};t=time.perf_counter();encoder=E5ONNXEncoder(BASE/'e5-small');encoder_load=time.perf_counter()-t
    config={'model_id':MODEL_ID,'revision':REVISION,'reranker':CONFIG,'knowledge_version':dataset['knowledge_version'],
        'pool':'positive original BM25 top50 + positive expanded BM25 top50 + positive Dense top50, fragment-ID union',
        'bm25':INDEX_CONFIG,'query_expansion':VERSION,'dense':encoder.profile,
        'rrf_control':'existing two-route k60 equal weights depth50; expanded-only candidates retain score0 at tail; same complete union available to both rankers',
        'tie':'reranker: fragment_id; RRF: existing document/version/ordinal/fragment_id',
        'freeze':'20 development queries only; no frozen-family, no parameter selection; labels never enter model input'}
    entries=[]
    with KnowledgeStore(BASE/'corpus.sqlite3',readonly=True) as store,VectorIndex(BASE/'vectors.sqlite3',readonly=True) as index:
        rows,vectors=index.load(store,dataset['knowledge_version'],encoder);byfid={r['fragment_id']:r for r in rows};tokens=[tuple(json.loads(r['tokens'])) for r in rows]
        for query in dataset['queries']:
            if query['split']!='development':continue
            t=time.perf_counter();rankings,scores,inference_time=full_rank(query['query'],rows,vectors,encoder)
            expanded,rules=expand_query(query['query']);bs=score_corpus(expanded,tokens) if rules else scores['bm25']
            tie=lambda i:(rows[i]['document_id'],rows[i]['version'],rows[i]['ordinal'],rows[i]['fragment_id'])
            exrank=sorted(range(len(rows)),key=lambda i:(-bs[i],tie(i)))
            routes={name:[{'fragment_id':rows[i]['fragment_id'],'score':vals[i]} for i in rr if vals[i]>0][:50]
                for name,rr,vals in [('bm25',rankings['bm25'],scores['bm25']),('expanded_bm25',exrank,bs),('dense',rankings['dense'],scores['dense'])]}
            pool=union_candidates(routes)
            for fid,item in pool.items():
                item['evidence']=asdict(store.evidence(fid,dataset['knowledge_version']))
                r=byfid[fid];item['tie']=[r['document_id'],r['version'],r['ordinal'],fid]
                item['rrf_score']=sum(1/(60+origin['rank']) for origin in item['origins'] if origin['route'] in ('bm25','dense'))
            control=sorted(pool,key=lambda fid:(-pool[fid]['rrf_score'],pool[fid]['tie']))
            default=oldresults[query['id']]['variants']['baseline']['rrf']['hits']
            assert control[:5]==[h['fragment_id'] for h in default]
            for method in ('bm25','dense'):
                assert [h['fragment_id'] for h in routes[method][:5]]==[h['fragment_id'] for h in oldresults[query['id']]['variants']['baseline'][method]['hits']]
            entries.append({**query,'expanded_query':expanded,'routes':routes,'candidates':pool,'rrf_control_ids':control,
                'default_baseline':oldresults[query['id']]['variants']['baseline'],'candidate_seconds':time.perf_counter()-t,
                'query_encoding_seconds':inference_time,'coverage':coverage(qs[query['id']],mapping['questions'][query['id']]['candidates'],set(pool),set(control[:5]))})
    assert all(file_hash(p)==h for p,h in hashes.items())
    value={'config':config,'config_sha256':sha(config),'knowledge_version':dataset['knowledge_version'],
        'query_set_sha256':sha([{k:q[k] for k in ('id','query','family','split','language')} for q in entries]),
        'entries':entries,'protected_sha256':hashes,'e5_load_seconds':encoder_load,
        'prepare_seconds':time.perf_counter()-start,'prepare_cpu_seconds':time.process_time()-cpu,
        'prepare_peak_working_set_bytes':peak_working_set(),'paid_api_calls':0}
    (out/'candidate-pool.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'pool-hash.json').write_text(json.dumps({'candidate_pool_sha256':file_hash(out/'candidate-pool.json'),'config_sha256':value['config_sha256']},indent=2),encoding='utf-8')
    print(json.dumps({'phase':'prepare','seconds':value['prepare_seconds'],'peak':value['prepare_peak_working_set_bytes'],'counts':{q['id']:len(q['candidates']) for q in entries}},ensure_ascii=False))

def run(out,modeldir):
    from rag.reranker import ONNXReranker
    from rag.storage import KnowledgeStore
    from evaluation.term_expansion_trial import marked_score
    out=Path(out);resultfile=out/'reranker-results.json'
    if resultfile.exists():raise FileExistsError('One run only; result exists')
    start=time.perf_counter();cpu=time.process_time();pool=load(out/'candidate-pool.json');savedhash=load(out/'pool-hash.json')
    if file_hash(out/'candidate-pool.json')!=savedhash['candidate_pool_sha256'] or sha(pool['config'])!=savedhash['config_sha256']:raise ValueError('Frozen candidate/config hash mismatch')
    if pool['config']['reranker']!=CONFIG or pool['config']['revision']!=REVISION:raise ValueError('Frozen reranker configuration mismatch')
    model=ONNXReranker(modeldir);labels=load(FINAL/'merged-annotations.json');qs={q['question_id']:q for q in labels['questions']};mapping=bound_mapping();results=[]
    with KnowledgeStore(BASE/'corpus.sqlite3',readonly=True) as store:
        for entry in pool['entries']:
            if entry['split']!='development':raise ValueError('Frozen-family not allowed')
            ids=sorted(entry['candidates']);texts=[]
            for fid in ids:
                saved=entry['candidates'][fid]['evidence'];verify_saved_evidence(store,fid,pool['knowledge_version'],saved)
                texts.append(saved['text'])
            t=time.perf_counter();scores,notes=model.score(entry['query'],texts);elapsed=time.perf_counter()-t
            rr=stable_order(scores,ids);ordered=[ids[i] for i in rr]
            methods={}
            for name,ranking in [('default_baseline',[h['fragment_id'] for h in entry['default_baseline']['rrf']['hits']]),('fixed_pool_rrf',entry['rrf_control_ids']),('reranker',ordered)]:
                methods[name]={'metrics':marked_score(qs[entry['id']],mapping['questions'][entry['id']],ranking),
                    'top5':[{'fragment_id':fid,'evidence':entry['candidates'][fid]['evidence']} for fid in ranking[:5]]}
            results.append({k:entry[k] for k in ('id','query','family','split','language','coverage','candidate_seconds') }|
                {'methods':methods,'rerank_seconds':elapsed,'candidates':len(ids),
                'rankings':[{'rank':n,'fragment_id':ids[i],'score':scores[i],'encoding':notes[i]} for n,i in enumerate(rr,1)],
                'truncated_fragment_ids':[ids[i] for i,n in enumerate(notes) if n['truncated']]})
            print(json.dumps({'id':entry['id'],'candidates':len(ids),'seconds':elapsed,'truncated':sum(n['truncated'] for n in notes)},ensure_ascii=False),flush=True)
            # Save each completed question before the next; no silent retry of failed inference.
            with (out/f"question-{entry['id']}.json").open('x',encoding='utf-8') as f:json.dump(results[-1],f,ensure_ascii=False,indent=2)
    if file_hash(out/'candidate-pool.json')!=savedhash['candidate_pool_sha256']:raise ValueError('Pool changed during execution')
    assert all(file_hash(p)==h for p,h in pool['protected_sha256'].items())
    value={'config':pool['config'],'model_profile':model.profile,'results':results,'pool_sha256':savedhash['candidate_pool_sha256'],
        'model_load_seconds':model.load_seconds,'rerank_total_seconds':sum(q['rerank_seconds'] for q in results),
        'run_seconds':time.perf_counter()-start,'run_cpu_seconds':time.process_time()-cpu,'run_peak_working_set_bytes':peak_working_set(),
        'paid_api_calls':0,'frozen_runs':0,'defaults_changed':False,'notes':'memory peaks belong to separate prepare and rerank process lifetimes; raw logits not factual support'}
    resultfile.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k not in ('results','config','model_profile')},ensure_ascii=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('phase',choices=('prepare','run'));p.add_argument('--output-dir',required=True);p.add_argument('--model-dir',default=str(BASE/'reranker-model'));a=p.parse_args()
    prepare(a.output_dir) if a.phase=='prepare' else run(a.output_dir,a.model_dir)
