"""Read-only v19 request replay; no model, QA scheduler, or production change."""
import asyncio, collections, datetime, hashlib, json, subprocess, time
from dataclasses import replace
from pathlib import Path
from backend.serialization import wire
from rag.tantivy_build import atomic

PRIOR=Path('D:/PowerTrustAI/data/runtime_local/tantivy-product-v19')
HOME=PRIOR.parent/'tantivy-delivery-replay-v20'
GROUP=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-shards-v16/accepted-shard-group.json')
DEADLINE=datetime.datetime(2026,11,13,5,1,22,tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp()

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp(p):
 s=Path(p).stat();return [s.st_size,s.st_mtime_ns]
def epoch(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def union(intervals):
 parts=[]
 for a,b in sorted(intervals):
  if b<a:raise ValueError('Reversed interval')
  if parts and a<=parts[-1][1]:parts[-1][1]=max(parts[-1][1],b)
  else:parts.append([a,b])
 return sum(b-a for a,b in parts)

def timeline():
 summary=read(PRIOR/'summary.json');out=[]
 for pair in summary['pairs']:
  for backend in ('baseline','fast'):
   label=pair['case']+'-'+backend;x=read(PRIOR/(label+'-result.json'));events=[e['event'] for e in read(PRIOR/(label+'-trace.json'))['events']]
   stages=[];rs=[];base=epoch(x['execution']['created_utc'])
   for e in events:
    if e['component'] in ('generation','claim_extraction','evidence_verification','power_domain_review'):
     end=epoch(e['timestamp_utc']);start=end-e['duration_ms']/1000
     stages.append({'component':e['component'],'start':start-base,'end':end-base,'seconds':end-start})
   for z in x['retrieval']:
    matches=[]
    for e in events:
     d=e.get('detail')
     if isinstance(d,str):
      try:d=json.loads(d)
      except (ValueError,TypeError):continue
     if isinstance(d,dict):
      d=d.get('supplement',d)
      if d.get('retrieval_id')==z['retrieval_id']:matches.append(e)
    end=min((epoch(e['timestamp_utc']) for e in matches),default=None)
    start=None if end is None else end-z['duration_ms']/1000
    rs.append({'id':z['retrieval_id'],'purpose':z['purpose'],'start':None if start is None else start-base,'end':None if end is None else end-base,'seconds':z['duration_ms']/1000,'accepted_chars':z['accepted_chars'],'offered_chars':z['offered_chars'],'roots':len(z['core_evidence_ids']),'context':len(z['context_evidence_ids'])})
   models=x['model_usage'];by={}
   for purpose,components in [('generation',('generation',)),('verification',('claim_extraction','evidence_verification')),('domain_review',('power_domain_review',))]:
    rr=[z for z in rs if z['purpose']==purpose];mm=[m for m in models if m['component'] in components]
    by[purpose]={'retrieval_count':len(rr),'retrieval_seconds':sum(z['seconds'] for z in rr),'retrieval_union_seconds':union([(z['start'],z['end']) for z in rr if z['start'] is not None]),'accepted_chars':sum(z['accepted_chars'] for z in rr),'model_evidence_chars':sum(m.get('request_metrics',{}).get('evidence_chars_delivered',0) for m in mm),'model_calls':len(mm),'corrections':sum(bool(m['correction']) for m in mm),'model_wait_sum_seconds':sum(m['duration_ms'] or 0 for m in mm)/1000,'model_request_intervals':None}
   intervals=[(z['start'],z['end']) for z in stages]+[(z['start'],z['end']) for z in rs if z['start'] is not None]
   audit=next(e for e in reversed(events) if e['component']=='audit_policy');wall=epoch(audit['timestamp_utc'])-base
   overlap=[(z['start'],z['end']) for z in stages if z['component'] in ('evidence_verification','power_domain_review')]
   out.append({'case':pair['case'],'backend':backend,'created_utc':x['execution']['created_utc'],'by_purpose':by,'stages':stages,'retrievals':rs,'server_to_audit_seconds':wall,'stage_and_retrieval_union_seconds':union(intervals),'uncovered_seconds':wall-union(intervals),'audit_overlap_seconds':sum(b-a for a,b in overlap)-union(overlap),'model_records':[{k:m.get(k) for k in ('component','call_number','correction','duration_ms','request_metrics','usage')} for m in models]})
 atomic(HOME/'timeline.json',{'rows':out,'notes':['Stage endpoints are actual completion events; starts derived from measured duration, millisecond precision.','Retrieval record endpoints use earliest matching actual event, may include small observer gap.','model_request events are emitted after invoke returns; individual network intervals unknown, never subtract duration from that timestamp.','Uncovered time includes orchestration, observer/store and non-selected operations; not attributed to CPU or network.']})

def freeze():
 HOME.mkdir(parents=True,exist_ok=True)
 if (HOME/'freeze.json').exists():raise RuntimeError('Existing frozen replay; no replacement')
 old=read(PRIOR/'freeze.json');summary=read(PRIOR/'summary.json');requests=[];inputs={}
 for pair in summary['pairs']:
  for backend in ('baseline','fast'):
   name=pair['case']+'-'+backend;p=PRIOR/(name+'-result.json');inputs[str(p)]=sha(p)
   x=read(p)
   for n,r in enumerate(x['retrieval']):
    if r['reused_from_retrieval_id']:raise RuntimeError('Cached record requires separate classification')
    requests.append({'slot':len(requests),'case':pair['case'],'origin':backend,'ordinal':n,'original_retrieval_id':r['retrieval_id'],'query':r['query'],'query_sha256':hashlib.sha256(r['query'].encode()).hexdigest(),'purpose':r['purpose'],'knowledge_version':r['knowledge_version'],'options':r['request_options']})
 assert len(requests)==56
 assert sha(GROUP)==old['index_manifest_sha256']
 for p,h in old['sources'].items():
  if sha(p)!=h:raise RuntimeError('v19 application changed: '+p)
 from evaluation.tantivy_full_build_v1 import SOURCE,ROOT
 files={str(p):sha(p) for p in [Path(__file__),Path('rag/tantivy_global_rank_v18.py'),Path('rag/tantivy_fast_v1.py'),Path('backend/assembly.py')]}
 atomic(HOME/'freeze.json',{'version':'v20-evidence-limit-only','commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'sources':files,'group_sha256':sha(GROUP),'source_stat':stamp(SOURCE),'spool_stat':stamp(ROOT/'spool.sqlite3'),'inputs':inputs,'requests':requests,'routes':{'sqlite':{'final_roots':3},'v18':{'final_roots':6},'v18_k3':{'final_roots':3}},'unchanged':'same v18 bounded16 ranking, exact dedup,8000 root chars,2400 context chars/max6/depth1; no reranking or query rewrite','production_budget':'max_results3; context2400/max6/depth1; Harness16000 per call/160000 total. Existing v18 root8000 remains stricter; counts aligned, actual chars must be reported.','order':'one replay per saved request per route; rotate SQLite/v18/v18_k3 by slot modulo3; both originating chains retained; no filtering on outcome','repeats':1,'cache':'OS caches not cleared; native one reusable worker shared by two v18 delivery limits; SQLite numeric rank cache cleared per saved request to avoid cross-origin warm ranking; immediate output certificate validation included','limits':{'deadline':DEADLINE,'run_max_seconds':5400,'memory_limit':756807680,'worker_restarts':2,'disk_free_min':30*1024**3,'new_output_max':128*1024**2},'model_calls':0})
 timeline()

async def run():
 import psutil,shutil
 from backend.assembly import ComponentFactory
 from evaluation.tantivy_product_v19 import configs
 from rag.retriever import AsyncSQLiteBM25Retriever
 from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
 from rag.timing import capture_timing
 f=read(HOME/'freeze.json');out=HOME/'measurements.jsonl'
 if out.exists():raise RuntimeError('One frozen replay already started')
 for p,h in f['sources'].items():
  if sha(p)!=h:raise RuntimeError('Frozen replay code changed')
 for p,h in f['inputs'].items():
  if sha(p)!=h:raise RuntimeError('Saved input changed')
 if sha(GROUP)!=f['group_sha256']:raise RuntimeError('Group changed')
 started=time.monotonic();deadline=min(DEADLINE,time.time()+5400);cs=configs(HOME,load_real=False)
 factory=ComponentFactory(cs['fast']);sql=AsyncSQLiteBM25Retriever(cs['baseline'].index_db,execution_profile=cs['baseline'].retrieval_execution_profile)
 peak={'tree_rss':0,'available_min':psutil.virtual_memory().available};stop=None
 try:
  factory.initialize_retrieval();fast=factory.semantic_resource
  atomic(HOME/'startup.json',{'seconds':time.monotonic()-started,'models':0,'worker_pid':fast._native.pid,'deadline':deadline,'cache':'source seal once and90 index files validated on load; request stamps retained'})
  for item in f['requests']:
   if time.time()>=deadline:raise TimeoutError('Frozen replay deadline')
   if shutil.disk_usage('D:/').free<30*1024**3:raise RuntimeError('Disk margin')
   if psutil.virtual_memory().available<256*1024**2:raise RuntimeError('System memory pressure')
   sql.rank_cache.clear();order=['sqlite','v18','v18_k3'];shift=item['slot']%3;order=order[shift:]+order[:shift]
   for route in order:
    opt=item['options'];req=RetrievalRequest(item['query'],opt['scenario_id'],RetrievalPurpose(item['purpose']),item['knowledge_version'],6 if route=='v18' else 3,None if opt['context_options'] is None else ContextOptions(**opt['context_options']))
    target=sql if route=='sqlite' else fast;t=time.monotonic();row={'slot':item['slot'],'case':item['case'],'origin':item['origin'],'purpose':item['purpose'],'route':route,'query_sha256':item['query_sha256']}
    try:
     with capture_timing(run_id='v20',retrieval_id=str(item['slot'])) as spans:
      result=await asyncio.wait_for(target.retrieve(req),110);retrieved=time.monotonic();await asyncio.wait_for(target.validate_result(req,result),110)
     if route!='sqlite' and (target.last_trace.get('backend')!='tantivy-global-idf-v18' or target.last_trace.get('fallback') is not False):raise RuntimeError('Unexpected backend')
     roots=sum(len(e.text) for e in result.evidence);ctx=0 if result.context is None else result.context.char_count
     row.update(status='ok',retrieve_seconds=retrieved-t,total_seconds=time.monotonic()-t,root_chars=roots,context_chars=ctx,root_count=len(result.evidence),result=wire(result),trace=None if route=='sqlite' else dict(target.last_trace),timing=spans.records)
    except BaseException as exc:
     row.update(status='error',error_type=type(exc).__name__,message=str(exc),total_seconds=time.monotonic()-t)
     with out.open('a',encoding='utf8') as handle:handle.write(json.dumps(row,ensure_ascii=False)+'\n')
     raise
    with out.open('a',encoding='utf8') as handle:handle.write(json.dumps(row,ensure_ascii=False)+'\n')
    tree=[psutil.Process()]+psutil.Process().children(recursive=True);rss=sum(p.memory_info().rss for p in tree if p.is_running());peak['tree_rss']=max(peak['tree_rss'],rss);peak['available_min']=min(peak['available_min'],psutil.virtual_memory().available)
   atomic(HOME/'progress.json',{'completed_requests':item['slot']+1,'completed_slots':(item['slot']+1)*3,'expected_slots':168,'seconds':time.monotonic()-started,'last_case':item['case'],'peak_sampled':peak,'models':0})
 except BaseException as exc:
  stop={'type':type(exc).__name__,'message':str(exc)};raise
 finally:
  sql.close();await factory.close()
  atomic(HOME/'receipt.json',{'seconds':time.monotonic()-started,'stopped':stop,'peak_sampled_between_requests':peak,'model_calls':0,'worker_released':factory.semantic_resource is None,'notes':'memory peak sampled between operations; not continuous native/process-tree high water; native hard monitor remains active'})

if __name__=='__main__':
 import sys
 if sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='run':asyncio.run(run())
 elif sys.argv[1]=='timeline':timeline()
