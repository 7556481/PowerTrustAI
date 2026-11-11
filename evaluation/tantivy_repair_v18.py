"""One bounded diagnostic and one saved-union global-IDF scoring feasibility check."""
import json,time,sys,asyncio,sqlite3,math,collections,traceback
from pathlib import Path
from rag.tantivy_build import atomic
from evaluation.tantivy_shard_continuous_v17 import HOME,OLD,guard,read,resources
R=HOME.parent/'tantivy-query-repair-v18'

async def diagnose(plan):
 from rag.tantivy_diagnostic_v18 import DiagnosticRetriever,event
 from evaluation.tantivy_full_build_v1 import SOURCE,K
 from evaluation.tantivy_supervision_v3 import Guard
 from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
 g=Guard(plan);group=read(HOME/'accepted-shard-group.json');old=list(map(json.loads,(HOME/'full-measurements.jsonl').read_text(encoding='utf8').splitlines()))
 sequence=[x for x in old if x['backend']=='fast'];qs={q['id']:q for q in read(HOME/'offline-freeze.json')['queries']}
 atomic(R/'diagnostic-freeze.json',{'sequence':[(x['query'],x['round']) for x in sequence],'native_limit':read(plan)['native_limit'],'max_restarts':2,'deadline':read(plan)['deadline'],'models':0})
 a=DiagnosticRetriever(SOURCE,group['manifests'],K,memory_limit=read(plan)['native_limit'],diagnostic_path=R/'native-events.jsonl',trim_owned_working_set=read(plan).get('trim_owned_working_set',False));out=[]
 try:
  a.warm()
  for x in sequence:
   g.check('diagnostic query');q=qs[x['query']];t=time.monotonic();r={'query':x['query'],'round':x['round']}
   try:
    request=RetrievalRequest(q['query'],'voltage_stability_reactive_support',RetrievalPurpose.GENERATION,K,6,ContextOptions());z=await a.retrieve(request);await a.validate_result(request,z);r.update(status='ok',trace=a.last_trace)
   except Exception as e:r.update(status='error',type=type(e).__name__,message=str(e),chain=traceback.format_exc())
   r['seconds']=time.monotonic()-t;out.append(r)
   with (R/'diagnostic-slots.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(r)+'\n')
   if not a.available:break
 except BaseException as e:
  event(R/'native-events.jsonl','primary_error',type=type(e).__name__,message=str(e),stage='diagnostic query admission');raise
 finally:
  stop=Path(plan).with_name('stop.json')
  if stop.exists():a.stop_initiator='supervisor:'+read(stop).get('reason','unknown')
  a.close();atomic(R/'diagnostic-receipt.json',{'slots':len(out),'released':a._native is None,'models':0})

from rag.tantivy_global_rank_v18 import positive,score

def ranking(plan):
 import tantivy
 from evaluation.tantivy_supervision_v3 import Guard
 g=Guard(plan);started=time.time();freeze=read(HOME/'offline-freeze.json');queries={q['id']:q for q in freeze['queries']};records=list(map(json.loads,(HOME/'full-measurements.jsonl').read_text(encoding='utf8').splitlines()));selected={}
 for r in records:
  if r['backend']=='fast' and r['status']=='ok':selected.setdefault(r['query'],r)
 vocabulary=sorted({t for q in queries.values() for t in positive(q['tantivy_tree'])});counts=[];sizes=[]
 for path in read(HOME/'accepted-shard-group.json')['manifests']:
  g.check('dictionary DF');m=read(path);idx=tantivy.Index.open(m.get('index_path',m.get('path','')) if 'index_path' in m or 'path' in m else str(Path(path)))
  s=idx.searcher();sizes.append(s.num_docs);counts.append({t:s.doc_freq('terms',t) for t in vocabulary});idx=None
 atomic(R/'term-statistics.json',{'sizes':sizes,'df':counts,'scope':'exact single-token document frequency; not phrase DF','seconds':time.time()-started})
 total=sum(sizes);globaldf={t:sum(c[t] for c in counts) for t in vocabulary};db=sqlite3.connect((OLD/'spool.sqlite3').as_uri()+'?mode=ro',uri=True);results=[]
 try:
  for qid,r in selected.items():
   g.check('saved union scoring');words=set(positive(queries[qid]['tantivy_tree']));weights={t:math.log(1+(total-globaldf[t]+.5)/(globaldf[t]+.5)) for t in words};rows=[]
   for shard,local in enumerate(r['trace']['worker_metrics']['per_shard_candidates']):
    for rid,oldscore in local:
     pos=-rid-1 if rid<0 else rid+673;row=db.execute('select rowid,terms from input where position=?',(pos,)).fetchone();assert row[0]==rid
     tf=collections.Counter(row[1].split());rows.append((rid,score(tf,weights),oldscore,shard))
   rows.sort(key=lambda z:(-z[1],z[0]));results.append({'query':qid,'weights':weights,'ranked_union':rows,'mechanism':'global token IDF times tf/(tf+1), no length normalization; original Boolean/phrase eligibility from saved native candidates; not exact BM25'})
 finally:db.close()
 atomic(R/'ranking-results.json',{'results':results,'seconds':time.time()-started,'models':0})

def launch(role):
 from evaluation.tantivy_supervision_v3 import supervise
 from evaluation.tantivy_full_controller_v1 import idle
 a,limit=resources();control=R/'comparison/postbuild/measure' if role=='full' else R/role;control.mkdir(parents=True,exist_ok=False)
 old=read(HOME/'postbuild/measure/plan.json');p={**old,'deadline':min(a['deadline'],time.time()+3600),'cwd':str(Path.cwd()),'memory_limit':min(limit-64*1024**2,old['memory_limit']),'native_limit':min(756807680,limit-256*1024**2),'frozen_code':{}}
 p['extra_data_roots']=[*p['extra_data_roots'],str(R)]
 p['trim_owned_working_set']=role.startswith('diagnose-fixed')
 from rag.tantivy_manifest import sha
 p['frozen_code']={str(f):sha(f) for f in [*Path('rag').glob('*.py'),Path(__file__),Path('evaluation/tantivy_full_measure_v1.py'),Path('evaluation/tantivy_supervision_v3.py')]}
 atomic(control/'plan.json',p);rc=supervise(control/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_repair_v18',role,str(control/'plan.json')],control/'logs',idle);print(role,rc,flush=True)

def replay(plan):
 import dataclasses,threading
 from types import SimpleNamespace
 from evaluation.tantivy_full_build_v1 import SOURCE,K
 from evaluation.tantivy_supervision_v3 import Guard
 from rag.tantivy_fast_v1 import FastTantivyRetriever
 from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
 g=Guard(plan);qs={q['id']:q for q in read(HOME/'offline-freeze.json')['queries']};out=[];started=time.time()
 for r in read(R/'ranking-results.json')['results']:
  g.check('saved candidates evidence delivery');rows=[(z[0],z[1]) for z in r['ranked_union'][:16]];adapter=SimpleNamespace(path=SOURCE,knowledge_version=K,_cancel_work=threading.Event(),last_trace={},_rank=lambda tree,k:rows)
  request=RetrievalRequest(qs[r['query']]['query'],'voltage_stability_reactive_support',RetrievalPurpose.GENERATION,K,6,ContextOptions())
  result=FastTantivyRetriever._work(adapter,request,None,False)
  out.append({'query':r['query'],'roots':[dataclasses.asdict(e) for e in result.evidence],'neighbors':[dataclasses.asdict(x.evidence) for x in result.context.items],'trace':adapter.last_trace})
 atomic(R/'delivery-replay.json',{'scope':'saved candidate scoring plus unchanged product evidence delivery only; no native search/performance claim','seconds':time.time()-started,'results':out})

def full(plan):
 from rag.tantivy_global_rank_v18 import GlobalIDFRetriever
 from rag.tantivy_manifest import sha
 import evaluation.tantivy_full_measure_v1 as run
 for f,h in read(plan)['frozen_code'].items():
  if sha(f)!=h:raise RuntimeError('Frozen implementation changed')
 group=read(HOME/'accepted-shard-group.json');folder=R/'comparison';(folder/'accepted').mkdir(exist_ok=True)
 atomic(folder/'accepted/manifest.json',group);atomic(folder/'acceptance-complete.json',read(HOME/'acceptance-complete.json'));atomic(folder/'plan.json',{'queries':read(HOME/'offline-freeze.json')['queries']});atomic(folder/'construction-ledger.json',{'deadline':read(plan)['deadline']})
 def factory(source,manifest,k,isolated=True):return GlobalIDFRetriever(source,group['manifests'],k,spool_path=OLD/'spool.sqlite3',memory_limit=read(plan)['native_limit'],diagnostic_path=folder/'native-events.jsonl',trim_owned_working_set=True)
 run.ROOT=folder;run.FastTantivyRetriever=factory;run.ALLOW_UNAVAILABLE_SLOT_RECORDS=True;asyncio.run(run.run())

if __name__=='__main__':
 guard();R.mkdir(exist_ok=True)
 if sys.argv[1]=='launch':launch(sys.argv[2])
 elif sys.argv[1]=='diagnose':asyncio.run(diagnose(sys.argv[2]))
 elif sys.argv[1].startswith('diagnose-fixed'):
  R=R/(sys.argv[1]+'-output');R.mkdir(exist_ok=False);asyncio.run(diagnose(sys.argv[2]))
 elif sys.argv[1]=='ranking':ranking(sys.argv[2])
 elif sys.argv[1]=='replay':replay(sys.argv[2])
 elif sys.argv[1]=='full':full(sys.argv[2])
