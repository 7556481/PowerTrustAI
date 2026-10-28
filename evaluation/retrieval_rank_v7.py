"""Fixed read-only rank diagnostic, bounded SQL/counts; no model or env loader."""
import json,sqlite3,subprocess,time,threading,statistics
from pathlib import Path
from backend.config import ROOT
from backend.assembly import ComponentFactory
from backend.launcher import health_at
from evaluation.source_first_modality_v6 import material
from evaluation.source_first_real_v3 import configuration
from evaluation.natural_draft_audit_v1 import save,sha
from rag.topic_lanes import plan

LOCAL=ROOT/'data/retrieval_local/retrieval-rank-and-audit-reference-v7/sql'
BASE='SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?'
RANK='SELECT rowid,rank AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY rank LIMIT ?'
def idle():
    h=health_at('http://127.0.0.1:8765')
    # A live service is not treated as idle without its explicit lifecycle.
    if h:
        life=h.get('service_lifecycle',{})
        if life.get('active_run_id') or life.get('active') or life.get('queue_size',0):return False
        # Persisted state is independently checked below, including older services.
    db=sqlite3.connect((ROOT/'data/runtime_local/runs.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    try:return db.execute("SELECT 1 FROM runs WHERE status IN ('queued','running') LIMIT 1").fetchone() is None
    finally:db.close()
def bounded(db,sql,args,seconds):
    start=time.monotonic();deadline=start+seconds
    db.set_progress_handler(lambda:int(time.monotonic()>=deadline),10000)
    timer=threading.Timer(seconds,db.interrupt);timer.daemon=True;timer.start()
    try:return dict(status='ok',rows=[list(r) for r in db.execute(sql,args).fetchall()],seconds=time.monotonic()-start)
    except sqlite3.OperationalError as exc:
        if 'interrupt' not in str(exc).lower():raise
        return dict(status='timeout_unknown',rows=None,seconds=time.monotonic()-start)
    finally:timer.cancel();timer.join();db.set_progress_handler(None,0)
def run():
    if LOCAL.exists():raise RuntimeError('Unique SQL attempt, no overwrite/resume')
    assert idle(),'User task active; do not benchmark'
    old=json.loads((ROOT/'data/maintenance_local/audit-retrieval-final-v1/requests-private.json').read_text(encoding='utf-8'))
    requests=[]
    for g in old['groups']:
        record=g['audit_records'][0];opts=record['request_options']
        assert opts['execution_profile']=='topic_v4_subject_v1' and opts['max_results']==3
        requests.append(dict(id=g['run_id'][:8],record=record,query=record['query'],expression=plan(record['query'])[0][1],k=opts['max_results'],knowledge_version=g['knowledge_version'],budget=g['budget'],input_sha=sha(dict(record=record,budget=g['budget'],scenario_id=g['scenario_id']))))
    schedule=[dict(round=n,query=q['id'],paths=['base','rank'] if (n+i)%2 else ['rank','base']) for n in (1,2,3) for i,q in enumerate(requests)]
    c=configuration(material());f=ComponentFactory(c);start=time.monotonic();f.warm_corpus_index();seal=time.monotonic()-start
    db=sqlite3.connect(c.index_db.resolve().as_uri()+'?mode=ro',uri=True)
    config=db.execute('SELECT * FROM corpus_fts_config').fetchall();mapping=next((r[1] for r in config if r[0]=='rank'),None)
    assert mapping in (None,'bm25()'),'Rank mapping is not unweighted bm25; diagnostic equivalence unproved'
    freeze=dict(version='retrieval-rank-v7',sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sqlite_version=sqlite3.sqlite_version,compile_options=db.execute('pragma compile_options').fetchall(),rank_config=config,rank_mapping='bm25() default verified by absence of override' if mapping is None else mapping,requests=requests,schedule=schedule,seal_seconds=seal,cache='No ranking cache; original sealed database; OS caches not cleared',rank_execution_cap=27,count_cap=3,count_seconds=60,total_seconds=1800,
        stage3_condition='Diagnostic must meet potential adoption gate (slowest >=20% and >=2s, at least two improving rounds, no repeated material regressions) before one equivalent implementation; otherwise no stage3',
        stage3_schedule=[dict(round=n,query=q['id'],path='equivalent') for n in (1,2,3) for q in requests],
        legacy='Old rank cursor explicitly bm25(), no SQL LIMIT, closes after full K boundary or >4096 fallback. Old output lacks examined/fallback flags: whether fallback fired cannot be established. Old timings included Python fetch/sort and any fallback; old query version differs.')
    save(LOCAL/'freeze.json',freeze);save(LOCAL/'attempt.json',dict(unique=True,no_resume=True))
    began=time.monotonic();records=[];counts=[];plans=[]
    try:
        for slot in schedule:
            q=next(x for x in requests if x['id']==slot['query'])
            for path in slot['paths']:
                assert idle(),'User work became active; stop without refill'
                assert len(records)<27 and time.monotonic()-began<1800,'SQL limit'
                save(LOCAL/'admissions'/f'{len(records)+1:02d}.json',dict(slot=slot,path=path))
                result=bounded(db,BASE if path=='base' else RANK,(q['expression'],q['k']),min(q['budget']['step_timeout_seconds'],1800-(time.monotonic()-began)))
                rec=dict(query=q['id'],round=slot['round'],path=path,**result);records.append(rec);save(LOCAL/'rank-results.json',records)
                print(q['id'],slot['round'],path,result['status'],round(result['seconds'],3),flush=True)
                if result['status']!='ok':raise RuntimeError('Ranking failed; no refill')
        for q in requests:
            assert idle() and time.monotonic()-began<1800
            result=bounded(db,'SELECT count(*) FROM corpus_fts WHERE corpus_fts MATCH ?',(q['expression'],),min(60,1800-(time.monotonic()-began)))
            counts.append(dict(query=q['id'],**result));save(LOCAL/'counts.json',counts)
            for path,sql in [('base',BASE),('rank',RANK)]:plans.append(dict(query=q['id'],path=path,plan=[list(r) for r in db.execute('EXPLAIN QUERY PLAN '+sql,(q['expression'],q['k']))]))
        save(LOCAL/'plans.json',plans)
        comparisons=[]
        for q in requests:
            pairs=[]
            for n in (1,2,3):
                a=next(x for x in records if x['query']==q['id'] and x['round']==n and x['path']=='base');b=next(x for x in records if x['query']==q['id'] and x['round']==n and x['path']=='rank')
                pairs.append(dict(round=n,base_seconds=a['seconds'],rank_seconds=b['seconds'],same_rows=a['rows']==b['rows'],saving=a['seconds']-b['seconds'],reduction=1-b['seconds']/a['seconds']))
            a=statistics.median(x['base_seconds'] for x in pairs);b=statistics.median(x['rank_seconds'] for x in pairs)
            comparisons.append(dict(query=q['id'],pairs=pairs,base_median=a,rank_median=b,saving=a-b,reduction=1-b/a,positive_rounds=sum(x['saving']>0 for x in pairs),material_regression_rounds=sum(x['rank_seconds']>x['base_seconds']*1.1 and x['rank_seconds']-x['base_seconds']>.5 for x in pairs)))
        s=comparisons[0];potential=s['saving']>=2 and s['reduction']>=.2 and s['positive_rounds']>=2 and all(x['material_regression_rounds']<2 for x in comparisons[1:])
        save(LOCAL/'diagnostic-summary.json',dict(comparisons=comparisons,potential_gate=potential,rank_executions=len(records),count_executions=len(counts),rank_seconds=time.monotonic()-began,adopted=False,stage3='required next' if potential else 'not implemented: diagnostic failed potential gate',all_diag_rows_equal=all(p['same_rows'] for x in comparisons for p in x['pairs'])))
        print('Diagnostic complete; potential gate',potential,flush=True)
    finally:db.close()
if __name__=='__main__':run()
