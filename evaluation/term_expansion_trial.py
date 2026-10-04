"""Fixed development-only experiment; actual ranks retain unknown candidates."""
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import sys
import time
from evaluation.body_priority_trial import BASE
from evaluation.recall_diagnosis import full_rank
from evaluation.supervised_retrieval import score_question, METRICS
from rag.query_terms import expand_query, VERSION, TERMS

def marked_score(q, qm, ids):
    """Unknown IDs retain their original rank and never receive a numeric label."""
    q=copy.deepcopy(q); candidates=copy.deepcopy(qm['candidates'])
    byfid={v['fragment_id']:bid for bid,v in candidates.items()};ranking=[]
    for fid in ids[:5]:
        bid=byfid.get(fid)
        if bid is None:
            bid='unknown:'+fid;candidates[bid]={'fragment_id':fid}
            q['fragment_relevance'].append({'blind_id':bid,'status':'unreviewed','relevance':None,'role':'core','reason':''})
        ranking.append(bid)
    result=score_question(q,ranking,candidates)
    grades={f['blind_id']:f['relevance'] for f in q['fragment_relevance']}
    def bounds(threshold):
        known=[n for n,bid in enumerate(ranking,1) if grades[bid] is not None and grades[bid]>=threshold]
        unknown=[n for n,bid in enumerate(ranking,1) if grades[bid] is None]
        first=min(known,default=None);possible=min(known+unknown,default=None)
        return {'hit_lower':int(bool(known)),'hit_upper':int(bool(known or unknown)),
            'mrr_lower':1/first if first else 0,'mrr_upper':1/possible if possible else 0}
    result['bounds_ge2']=bounds(2);result['bounds_grade3']=bounds(3)
    result['top5_annotation_coverage']=sum(grades[b] is not None for b in ranking)/len(ranking) if ranking else None
    return result

def main():
    from rag.embedding import E5ONNXEncoder
    from rag.semantic import VectorIndex,fuse_ranks
    from rag.storage import KnowledgeStore
    from rag.bm25 import score_corpus, tokenize
    from rag.context import read_adjacent_context
    from rag.contracts import ContextOptions
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args();out=Path(args.output_dir)
    if out.exists():raise FileExistsError('Independent new output directory required')
    out.mkdir(parents=True);start=time.perf_counter();cpu=time.process_time()
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    dataset=load(BASE/'dataset-v1.json');mapping=load(BASE/'blind-review/mapping.json')
    labels=load(BASE/'annotations/supervised-v3-eval-v3/annotations-30-supervised-v3.json');qs={q['question_id']:q for q in labels['questions']}
    protected=[BASE/'corpus.sqlite3',BASE/'vectors.sqlite3',BASE/'comparison-v2.json',BASE/'blind-review/mapping.json',BASE/'body-priority-v1/experiment.json',BASE/'annotations/supervised-v3-eval-v3/evaluation.json']
    hashes=lambda:{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in protected};before=hashes()
    encoder=E5ONNXEncoder(BASE/'e5-small');results=[];blindmap={};template=[];pool=['# 新增开发集候选盲审包','',
        '仅一批；原文和独立相邻上下文。候选顺序固定随机种子20261003。不要将上下文未标注视为不相关。',
        '这是已保存前五的有限候选池，不是完整相关集合；标签用于评价本轮，不更改旧标签或评分标准。','']
    with KnowledgeStore(BASE/'corpus.sqlite3',readonly=True) as store,VectorIndex(BASE/'vectors.sqlite3',readonly=True) as index:
        rows,vectors=index.load(store,dataset['knowledge_version'],encoder);byfid={r['fragment_id']:i for i,r in enumerate(rows)}
        tie=lambda i:(rows[i]['document_id'],rows[i]['version'],rows[i]['ordinal'],rows[i]['fragment_id'])
        tokens=[tuple(json.loads(r['tokens'])) for r in rows]
        for query in dataset['queries']:
            if query['split']!='development':continue
            rankings,scores,seconds=full_rank(query['query'],rows,vectors,encoder)
            expanded,triggers=expand_query(query['query']);t=time.perf_counter()
            newbm=score_corpus(expanded,tokens) if triggers else scores['bm25']
            bmrank=sorted(range(len(rows)),key=lambda i:(-newbm[i],tie(i)))
            variants={};unknown={};full={}
            for variant,bmr,bms in [('baseline',rankings['bm25'],scores['bm25']),('term_expansion',bmrank,newbm)]:
                bm=[(i,bms[i]) for i in bmr if bms[i]>0];dense=[(i,scores['dense'][i]) for i in rankings['dense'] if scores['dense'][i]>0]
                fused=fuse_ranks(bm[:50],dense[:50]);rrf=sorted(fused,key=lambda i:(-fused[i],tie(i)))
                methods={};full[variant]={'bm25':bmr,'dense':rankings['dense'],'rrf':rrf}
                for method,rank,values in [('bm25',[i for i,_ in bm],bms),('dense',[i for i,_ in dense],scores['dense']),('rrf',rrf,fused)]:
                    hits=[];known={v['fragment_id'] for v in mapping['questions'][query['id']]['candidates'].values()}
                    for n,i in enumerate(rank[:5],1):
                        evidence=store.evidence(rows[i]['fragment_id'],dataset['knowledge_version'])
                        hits.append({'rank':n,'score':values[i],'fragment_id':rows[i]['fragment_id'],'evidence':asdict(evidence)})
                        if rows[i]['fragment_id'] not in known:
                            entry=unknown.setdefault(rows[i]['fragment_id'],{'evidence':evidence,'origins':[]})
                            entry['origins'].append({'variant':variant,'method':method,'rank':n,'score':values[i]})
                    methods[method]={'hits':hits,'metrics':marked_score(qs[query['id']],mapping['questions'][query['id']],[h['fragment_id'] for h in hits])}
                variants[variant]=methods
            refs=[]
            if query['id'] in ('D05','D06','D12'):
                for ref in qs[query['id']]['supplementary_reference_evidence']:
                    i=byfid[ref['fragment_id']]
                    refs.append({'fragment_id':ref['fragment_id'],'before':{'bm25_rank_including_zero_ties':rankings['bm25'].index(i)+1,'bm25_score':scores['bm25'][i],
                        'dense_rank':rankings['dense'].index(i)+1,'dense_score':scores['dense'][i]},
                        'after':{'bm25_rank_including_zero_ties':bmrank.index(i)+1,'bm25_score':newbm[i],
                        'dense_rank':rankings['dense'].index(i)+1,'dense_score':scores['dense'][i]},
                        'expanded_term_overlap':sorted(set(tokenize(expanded))&set(tokens[i])),'reference_hit_credit':0})
            results.append({**query,'expanded_bm25_query':expanded,'triggers':triggers,'original_query_tokens':tokenize(query['query']),
                'expanded_query_tokens':tokenize(expanded),'baseline_retrieval_seconds':seconds,'expansion_and_ranking_seconds':time.perf_counter()-t,
                'variants':variants,'references':refs})
            items=list(unknown.items());random.Random('20261003:'+query['id']).shuffle(items);bidmap={};tl=[]
            if items:pool += [f"## {query['id']} / {query['family']}",'',query['query'],'']
            for n,(fid,item) in enumerate(items,1):
                bid=f"{query['id']}-N{n:02}";e=item['evidence'];context=read_adjacent_context(store,(e,),dataset['knowledge_version'],ContextOptions(max_chars=2400,max_fragments=2))
                bidmap[bid]={'fragment_id':fid,'origins':item['origins'],'context':asdict(context)}
                pool += [f'### {bid}',json.dumps(asdict(e)['provenance'],ensure_ascii=False),'```text',e.text,'```','']
                for cn,c in enumerate(context.items,1):
                    ce=c.evidence;pool += [f'独立相邻上下文 {bid}-X{cn}（不是检索命中）',json.dumps(asdict(ce)['provenance'],ensure_ascii=False),'```text',ce.text,'```','']
                tl.append({'candidate_id':bid,'fragment_id':fid,'status':'unreviewed','relevance':None,'support_relation':None,
                    'conditions':[],'scope':None,'reason':None,'contexts':[{'id':f'{bid}-X{cn}','status':'unreviewed','relevance':None} for cn,_ in enumerate(context.items,1)]})
            blindmap[query['id']]=bidmap;template.append({'question_id':query['id'],'status':'unreviewed','new_candidates':tl})
    assert hashes()==before
    report={'version':VERSION,'rules':TERMS,'knowledge_version':dataset['knowledge_version'],'profile':encoder.profile,'results':results,
        'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'protected_sha256':before,'history_unchanged':True,
        'frozen_runs':0,'decision':'Await this single bounded annotation batch; defaults unchanged; no frozen test until clear benefit without important regression.',
        'paid_api_calls':0,'scope':'Actual top5 including unknown; no rank compression; no automatic labels.'}
    for name,value in [('experiment.json',report),('blind-mapping.json',{'knowledge_version':dataset['knowledge_version'],'seed':20261003,'questions':blindmap}),
        ('annotations-template.json',{'version':VERSION,'status':'unreviewed','questions':template})]:
        with (out/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    (out/'evidence-pool.md').write_text('\n'.join(pool),encoding='utf-8')
    print(json.dumps({'output':str(out),'seconds':report['seconds'],'new_question_fragment_pairs':sum(len(v) for v in blindmap.values()),'frozen_runs':0},ensure_ascii=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()

