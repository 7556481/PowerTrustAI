"""Frozen deliveries through source replay and final production client recorder."""
import asyncio,json,time,hashlib
from pathlib import Path
from dataclasses import replace
from evaluation.fast_overlap_replay_v27 import SourceCatalog,read
from evaluation.tantivy_acceptance_v28 import select_span,verify_span,VERSION
from evaluation.archive_replay import restore
from backend.serialization import wire
from core.models import Evidence
from rag.contracts import RetrievalResult,ContextOptions
from rag.context import read_adjacent_context
HOME=Path('D:/PowerTrustAI/data/runtime_local/tantivy-acceptance-v28')
OLD=HOME.parent/'fast-overlap-v27';FROZEN=HOME.parent/'tantivy-delivery-replay-v20'
def transform(catalog,query,pool,options):
    tick=time.perf_counter();roots=[];trace=[];idmap={}
    for e in pool.evidence:
        catalog.verify_evidence(e);new,row=select_span(query,e);verify_span(new,catalog.evidence(e.provenance.fragment_id,e.provenance.knowledge_version));roots.append(new);trace.append(row);idmap[e.evidence_id]=new.evidence_id
    context=None if options is None else read_adjacent_context(catalog,pool.evidence,pool.knowledge_version,options)
    if context is not None:context=replace(context,items=tuple(replace(item,links=tuple(replace(link,core_evidence_id=idmap[link.core_evidence_id]) for link in item.links)) for item in context.items))
    hits=tuple(replace(hit,evidence_id=root.evidence_id,scoring_method=hit.scoring_method+';'+VERSION) for hit,root in zip(pool.hits,roots))
    return replace(pool,evidence=tuple(roots),hits=hits,context=context),{'excerpts':trace,'selection_source_replay_and_context_seconds':time.perf_counter()-tick}

def replay():
    freeze=read(FROZEN/'freeze.json');records=[json.loads(s) for s in (FROZEN/'measurements.jsonl').read_text(encoding='utf-8').splitlines()];by={(r['slot'],r['route']):r for r in records};catalog=SourceCatalog();rows=[];extra=[]
    try:
        for item in freeze['requests']:
            native=by[(item['slot'],'v18')];pool=restore(native['result'],RetrievalResult);opt=item['options'].get('context_options');opt=None if opt is None else restore(opt,ContextOptions)
            result,trace=transform(catalog,item['query'],pool,opt)
            rows.append(dict(slot=item['slot'],case=item['case'],origin=item['origin'],purpose=item['purpose'],query_sha256=item['query_sha256'],result=wire(result),selection=trace,historical_native6_seconds=native['total_seconds'],sqlite_seconds=by[(item['slot'],'sqlite')]['total_seconds']))
        (HOME/'frozen56-candidate-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        for old in read(OLD/'offline24-candidate-delivery.json'):
            full=tuple(restore(v,Evidence) for v in old['pool']);from rag.contracts import RetrievalHit
            pool=RetrievalResult(full,full[0].provenance.knowledge_version,hits=tuple(RetrievalHit(e.evidence_id,e.provenance.fragment_id,i+1,1.0,'frozen-six-v18') for i,e in enumerate(full)))
            result,trace=transform(catalog,old['query'],pool,ContextOptions())
            extra.append(dict(batch=old['batch'],case=old['case'],question_sha256=old['question_sha256'],query=old['query'],pool=old['pool'],result=wire(result),selection=trace))
        (HOME/'offline24-delivery-private.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:catalog.close()
    units=[u for row in rows+extra for u in row['selection']['excerpts']]
    print(json.dumps({'frozen_requests':len(rows),'offline24_deliveries':len(extra),'roots':len(units),'shortened_roots':sum(u['selected_chars']<u['parent_chars'] for u in units),'parent_chars':sum(u['parent_chars'] for u in units),'selected_chars':sum(u['selected_chars'] for u in units),'source_replay_context_seconds':sum(r['selection']['selection_source_replay_and_context_seconds'] for r in rows+extra)},indent=2))

async def boundary():
    import evaluation.fast_overlap_boundary_v27 as prior
    prior.HOME=HOME
    await prior.run()

if __name__=='__main__':replay();asyncio.run(boundary())
