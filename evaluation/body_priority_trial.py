"""Read-only corpus experiment; no production defaults or labels are changed."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import time

BASE = Path(__file__).resolve().parents[1] / 'data/retrieval_local/semantic'
VERSION = 'body-priority-v1'

def structural_reason(text, repeated=False):
    """Conservative structural demotion, never deletion or semantic judgment."""
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    if repeated and len(text) < 180:
        return 'short_repeated_header'
    if len(text) < 240 and re.search(r'https?://', text):
        remaining = re.sub(r'https?://\S+', '', text)
        if len(re.findall(r'[A-Za-z]+', remaining)) <= 10:
            return 'isolated_link_footer'
    if sum(bool(re.search(r'\.{3,}\s*\d+', s)) for s in lines) >= 3:
        return 'table_of_contents'
    return None

def ranking(bm, dense, rows, flags, *, body=False, constant=60, weight=1):
    scores = {}
    for pairs, w in ((bm[:50], weight), (dense[:50], 1)):
        for rank, (i, _) in enumerate(pairs, 1):
            scores[i] = scores.get(i, 0) + w / (constant + rank)
    return sorted(scores, key=lambda i: (bool(flags[i]) if body else False, -scores[i],
        rows[i]['document_id'], rows[i]['version'], rows[i]['ordinal'], rows[i]['fragment_id']))

def main():
    from rag.embedding import E5ONNXEncoder
    from rag.semantic import VectorIndex
    from rag.storage import KnowledgeStore
    from rag.bm25 import score_corpus
    from evaluation.supervised_retrieval import score_question, METRICS
    p=argparse.ArgumentParser();p.add_argument('--output-dir', required=True);args=p.parse_args()
    out=Path(args.output_dir)
    if out.exists(): raise FileExistsError('New output directory required')
    out.mkdir(parents=True)
    start=time.perf_counter(); cpu=time.process_time()
    load=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
    dataset=load(BASE/'dataset-v1.json');mapping=load(BASE/'blind-review/mapping.json')
    labels=load(BASE/'annotations/supervised-v3-eval-v3/annotations-30-supervised-v3.json')
    qs={q['question_id']:q for q in labels['questions']};kv=dataset['knowledge_version']
    protected=[BASE/'corpus.sqlite3',BASE/'vectors.sqlite3',BASE/'comparison-v2.json',BASE/'blind-review/mapping.json',BASE/'annotations/supervised-v3-eval-v3/evaluation.json']
    hashes=lambda:{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in protected}
    before=hashes(); encoder=E5ONNXEncoder(BASE/'e5-small')
    checks=[]
    for kind,text in [('query','正常电压是否证明稳定？'),('query','voltage stability'),('passage','Reactive reserve must be sustained.')]:
        ids=encoder.tokenizer.encode(kind+': '+text).ids
        checks.append({'kind':kind,'text':text,'whole_tokenization_matches':ids==encoder.token_windows(text,kind)[0],
            'tokens':len(ids),'norm':float(encoder.np.linalg.norm(encoder.encode([text],kind)[0]))})
    audit={'official_card':'https://huggingface.co/intfloat/multilingual-e5-small/raw/'+encoder.profile['revision']+'/README.md',
        'profile':encoder.profile,'onnx_inputs':[{ 'name':x.name,'shape':x.shape,'type':x.type} for x in encoder.session.get_inputs()],
        'onnx_outputs':[{ 'name':x.name,'shape':x.shape,'type':x.type} for x in encoder.session.get_outputs()],
        'checks':checks,'pooling':'first ONNX output batch/sequence/384; attention-mask mean then L2',
        'intentional_deviation':'Long passages use 480-token windows, stride448, equal pooled-window mean then L2; official example truncates at512. Queries over512 are rejected.',
        'confirmed_encoding_error':False,'new_vector_index_required':False}
    (out/'encoder-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    with KnowledgeStore(BASE/'corpus.sqlite3',readonly=True) as store, VectorIndex(BASE/'vectors.sqlite3',readonly=True) as index:
        rows,vectors=index.load(store,kv,encoder)
        counts=Counter((r['document_id'],' '.join(r['raw_text'].split())) for r in rows)
        flags=[structural_reason(r['raw_text'],counts[(r['document_id'],' '.join(r['raw_text'].split()))]>=3) for r in rows]
        tokens=[tuple(json.loads(r['tokens'])) for r in rows]
        tie=lambda i:(rows[i]['document_id'],rows[i]['version'],rows[i]['ordinal'],rows[i]['fragment_id'])
        reports=[];selected=None
        # Stage one has fixed fusion; only after its dev results are saved do we try fusion parameters.
        configs=[('baseline',False,60,1),('body',True,60,1)]
        def run(query, configs):
            t=time.perf_counter(); qv=encoder.encode([query['query']],'query')[0]
            ds=[sum(x*y for x,y in zip(qv,v)) for v in vectors]; bs=score_corpus(query['query'],tokens)
            dense=sorted(((i,s) for i,s in enumerate(ds) if s>0),key=lambda x:(-x[1],tie(x[0])))
            bm=sorted(((i,s) for i,s in enumerate(bs) if s>0),key=lambda x:(-x[1],tie(x[0])))
            qm=mapping['questions'][query['id']]; byfid={v['fragment_id']:bid for bid,v in qm['candidates'].items()}
            q=qs[query['id']];methods={};allrank={}
            for name,body,k,w in configs:
                rr=ranking(bm,dense,rows,flags,body=body,constant=k,weight=w);allrank[name]=rr
                top=rr[:5];unknown=[rows[i]['fragment_id'] for i in top if rows[i]['fragment_id'] not in byfid]
                # Projection is explicitly auxiliary: never adds reference-only fragments to retrieval.
                projected=[byfid[rows[i]['fragment_id']] for i in rr if rows[i]['fragment_id'] in byfid]
                score=score_question(q,projected,qm['candidates'])
                methods[name]={'judged_pool_projection':score,'actual_unknown_top5':unknown,
                    'top5':[{'fragment_id':rows[i]['fragment_id'],'blind_id':byfid.get(rows[i]['fragment_id']),
                        'structural_flag':flags[i],'evidence':__import__('dataclasses').asdict(store.evidence(rows[i]['fragment_id'],kv))} for i in top]}
                known=[byfid.get(rows[i]['fragment_id']) for i in top]
                # Actual metrics unavailable when any core label is unknown; do not silently assign0.
                methods[name]['actual_metrics']=None if unknown else score_question(q,known,qm['candidates'])
            direct={f['blind_id'] for f in q['fragment_relevance'] if f['relevance']==3}
            lost=[]
            for bid in direct:
                fid=qm['candidates'][bid]['fragment_id']; idx=next((i for i,r in enumerate(rows) if r['fragment_id']==fid),None)
                bpos=next((n for n,(i,_) in enumerate(bm,1) if i==idx),None)
                dpos=next((n for n,(i,_) in enumerate(dense,1) if i==idx),None)
                rpos=next((n for n,i in enumerate(allrank['baseline'],1) if i==idx),None)
                if bpos and bpos<=5 and (rpos is None or rpos>5):lost.append({'blind_id':bid,'bm25_rank':bpos,'dense_rank':dpos,'rrf_rank':rpos,'class':'fusion_regression'})
            return {**query,'seconds':time.perf_counter()-t,'methods':methods,'bm25_direct_displaced':lost,
                'candidate_ranks':{'bm25':[rows[i]['fragment_id'] for i,_ in bm[:50]],'dense':[rows[i]['fragment_id'] for i,_ in dense[:50]]}}, (bm,dense)
        dev=[q for q in dataset['queries'] if q['split']=='development']; cached={}
        for query in dev:
            r,pairs=run(query,configs);reports.append(r);cached[query['id']]=pairs
        def mean(name,metric):
            values=[r['methods'][name]['judged_pool_projection'][metric] for r in reports
                if r['methods'][name]['judged_pool_projection'][metric] is not None]
            return sum(values)/len(values) if values else None
        stage1={name:{m:mean(name,m) for m in METRICS} for name,*_ in configs}
        (out/'development-stage1.json').write_text(json.dumps({'results':reports,'summary':stage1},ensure_ascii=False,indent=2),encoding='utf-8')
        # Predeclared finite comparison, body flag fixed. No model/split/depth changes.
        extra=[('body-k20',True,20,1),('body-bm2',True,60,2)]
        for r in reports:
            q=qs[r['id']];qm=mapping['questions'][r['id']];byfid={v['fragment_id']:bid for bid,v in qm['candidates'].items()}
            bm,dense=cached[r['id']]
            for name,body,k,w in extra:
                rr=ranking(bm,dense,rows,flags,body=body,constant=k,weight=w)
                projected=[byfid[rows[i]['fragment_id']] for i in rr if rows[i]['fragment_id'] in byfid]
                unknown=[rows[i]['fragment_id'] for i in rr[:5] if rows[i]['fragment_id'] not in byfid]
                r['methods'][name]={'judged_pool_projection':score_question(q,projected,qm['candidates']),
                    'actual_unknown_top5':unknown,'actual_metrics':None if unknown else score_question(q,[byfid[rows[i]['fragment_id']] for i in rr[:5]],qm['candidates']),
                    'top5':[{'fragment_id':rows[i]['fragment_id'],'blind_id':byfid.get(rows[i]['fragment_id']),'structural_flag':flags[i],
                    'evidence':__import__('dataclasses').asdict(store.evidence(rows[i]['fragment_id'],kv))} for i in rr[:5]]}
        configs+=extra
        # Selection is explicitly conditional on reviewed pool, not proof of full corpus quality.
        key=lambda c:tuple(mean(c[0],m) for m in ('scope_limited_answer_basis_complete_at5','direct_grade3_hit_at5','mrr_ge2_at5'))
        selected=max(configs,key=key)
        selection={'selected':selected,'criterion':'lexicographic full-basis, direct-hit, MRR on reviewed-pool projection; unknown actual candidates require annotation',
            'development':{c[0]:{m:mean(c[0],m) for m in METRICS} for c in configs},'frozen_comparisons_allowed':1}
        (out/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
        for query in dataset['queries']:
            if query['split']!='development':
                r,_=run(query,[configs[0]]+([selected] if selected[0]!='baseline' else []));reports.append(r)
    after=hashes();assert before==after
    result={'version':VERSION,'knowledge_version':kv,'selection':selection,'results':reports,'paid_api_calls':0,
        'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'protected_sha256':before,
        'history_unchanged':True,'scope':'reviewed-pool projection is conditional; actual top5 with unknown labels has undefined metrics'}
    (out/'experiment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','protected_sha256')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
