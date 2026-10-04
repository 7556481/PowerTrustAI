"""Full-corpus rank diagnosis, read-only pinned index; no generation API."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
from evaluation.body_priority_trial import BASE

def full_rank(query,rows,vectors,encoder):
    from rag.bm25 import score_corpus
    t=time.perf_counter();vec=encoder.encode([query],'query')[0]
    bm=score_corpus(query,[tuple(json.loads(r['tokens'])) for r in rows])
    dense=[sum(x*y for x,y in zip(vec,v)) for v in vectors]
    tie=lambda i:(rows[i]['document_id'],rows[i]['version'],rows[i]['ordinal'],rows[i]['fragment_id'])
    sort=lambda values:sorted(range(len(rows)),key=lambda i:(-values[i],tie(i)))
    return {'bm25':sort(bm),'dense':sort(dense)}, {'bm25':bm,'dense':dense},time.perf_counter()-t

def main():
    from rag.embedding import E5ONNXEncoder
    from rag.semantic import VectorIndex
    from rag.storage import KnowledgeStore
    from rag.bm25 import tokenize
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    path=Path(args.output)
    if path.exists():raise FileExistsError(path)
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    dataset=load(BASE/'dataset-v1.json');labels=load(BASE/'annotations/supervised-v3-eval-v3/annotations-30-supervised-v3.json')
    qs={q['question_id']:q for q in labels['questions']};encoder=E5ONNXEncoder(BASE/'e5-small');out=[]
    with KnowledgeStore(BASE/'corpus.sqlite3',readonly=True) as store,VectorIndex(BASE/'vectors.sqlite3',readonly=True) as index:
        rows,vectors=index.load(store,dataset['knowledge_version'],encoder);byfid={r['fragment_id']:i for i,r in enumerate(rows)}
        for query in dataset['queries']:
            if query['id'] not in ('D05','D06','D12'):continue
            ranks,scores,seconds=full_rank(query['query'],rows,vectors,encoder);refs=[]
            for ref in qs[query['id']]['supplementary_reference_evidence']:
                i=byfid.get(ref['fragment_id']);assert i is not None
                r=rows[i];windows=encoder.token_windows(r['search_text'],'passage')
                refs.append({'reference':ref,'eligible':True,'evidence':asdict(store.evidence(r['fragment_id'],dataset['knowledge_version'])),
                    'search_text':r['search_text'],'stored_tokens':json.loads(r['tokens']),
                    'term_overlap':sorted(set(tokenize(query['query']))&set(json.loads(r['tokens']))),
                    'full_rank':{m:rank.index(i)+1 for m,rank in ranks.items()},'scores':{m:s[i] for m,s in scores.items()},
                    'positive_bm25_hit':scores['bm25'][i]>0,'passage_token_lengths':list(map(len,windows)),
                    'full_content_tokens':len(encoder.tokenizer.encode('passage: '+r['search_text']).ids),
                    'coverage':'all content tokens represented by versioned windows; no dropped tail'})
            out.append({**query,'query_tokens':tokenize(query['query']),'query_encoding':'query: '+query['query'],
                'query_token_lengths':list(map(len,encoder.token_windows(query['query'],'query'))),'seconds':seconds,
                'references':refs,'noise_top5':{m:[{'rank':n,'score':scores[m][i],'search_text':rows[i]['search_text'],
                    'evidence':asdict(store.evidence(rows[i]['fragment_id'],dataset['knowledge_version']))} for n,i in enumerate(rank[:5],1)] for m,rank in ranks.items()}})
    result={'knowledge_version':dataset['knowledge_version'],'profile':encoder.profile,'questions':out,'paid_api_calls':0}
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps([{'id':q['id'],'tokens':q['query_tokens'],'refs':[{'rank':r['full_rank'],'score':r['scores'],'overlap':r['term_overlap'],'lengths':r['passage_token_lengths']} for r in q['references']]} for q in out],ensure_ascii=False))

if __name__=='__main__':main()
