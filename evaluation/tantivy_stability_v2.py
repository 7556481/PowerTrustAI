"""Separate v2 diagnostics and process-tree accounting; never edits v1 data."""
import argparse,ctypes,gc,hashlib,json,os,shutil,sqlite3,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
import psutil
from evaluation import tantivy_bounded_v1 as v1
ROOT=v1.ROOT
LOCAL=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2')

def save(p,x):return v1.save(p,x)
def read(p):return v1.read(p)
def system_commit():
 from ctypes import wintypes as w
 class Info(ctypes.Structure):
  _fields_=[('cb',w.DWORD)]+[(n,ctypes.c_size_t) for n in ['total','limit','peak','phys','available','cache','kernel','paged','nonpaged','page']]+[(n,w.DWORD) for n in ['handles','processes','threads']]
 x=Info();x.cb=ctypes.sizeof(x)
 if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(x),x.cb):return None
 return dict(used=x.total*x.page,limit=x.limit*x.page,peak=x.peak*x.page)

def health():
 d=json.load(urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=5));return not d['active_run'] and not d['queued'] and d['storage_healthy']
def configure():
 p=psutil.Process();p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS);p.cpu_affinity([0,1])
def checkpoint(writer=None):
 if (LOCAL/'stop.json').exists():
  if writer:writer.commit();writer.wait_merging_threads()
  raise RuntimeError('Resource/service stop at safe checkpoint')
 if (LOCAL/'pause.json').exists():
  if writer:writer.commit()
  while (LOCAL/'pause.json').exists():
   if (LOCAL/'stop.json').exists():raise RuntimeError('Stop while safely paused')
   time.sleep(.25)

def supervise(name,args):
 plan=read(LOCAL/'resource-and-diagnostic-plan.json');directory=LOCAL/name;directory.mkdir(parents=True,exist_ok=False);start=time.monotonic();peak_rss=peak_private=peak_disk=0
 if not health():raise RuntimeError('Service active; no diagnostic/build admission')
 with (directory/'stdout.log').open('w',encoding='utf-8') as out,(directory/'stderr.log').open('w',encoding='utf-8') as err,(directory/'resources.jsonl').open('w',encoding='utf-8') as metrics:
  env=os.environ.copy();env['RUST_BACKTRACE']='full';env['RUST_LOG']='tantivy=debug';env['PYTHONFAULTHANDLER']='1'
  child=subprocess.Popen([sys.executable,'-X','utf8','-m','evaluation.tantivy_stability_v2',*args],cwd=ROOT,stdout=out,stderr=err,env=env,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
  me=psutil.Process();last_service=last_disk=0;service_ok=True;disk=0
  while child.poll() is None:
   processes=[]
   for p in [me,*me.children(recursive=True)]:
    try:
     m=p.memory_info();processes.append(dict(pid=p.pid,parent=p.ppid(),rss=m.rss,private=getattr(m,'private',m.vms),threads=p.num_threads(),process_peak_rss=getattr(m,'peak_wset',m.rss),cpu_user=p.cpu_times().user,cpu_system=p.cpu_times().system))
    except psutil.Error:pass
   rss=sum(x['rss'] for x in processes);private=sum(x['private'] for x in processes);peak_rss=max(rss,peak_rss);peak_private=max(private,peak_private);vm=psutil.virtual_memory();commit=system_commit();now=time.monotonic()
   if now-last_service>2:
    try:service_ok=health()
    except Exception:service_ok=False
    last_service=now
   if now-last_disk>2:
    disk=sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file());peak_disk=max(peak_disk,disk);last_disk=now
   row=dict(elapsed=now-start,processes=processes,tree_rss=rss,tree_private=private,system_available=vm.available,system_commit=commit,disk=disk,service_idle=service_ok);metrics.write(json.dumps(row)+'\n');metrics.flush()
   hard=rss>plan['tree_budget'] or private>plan['tree_budget'] or disk>plan['disk_limit'] or shutil.disk_usage(LOCAL).free<plan['min_free'] or time.time()>plan['deadline']
   pressure=vm.available<plan['pressure_available'] or (commit and commit['used']>.92*commit['limit']) or not service_ok
   if hard:save(LOCAL/'stop.json',dict(reason='tree/disk/time budget',row=row))
   if pressure:save(LOCAL/'pause.json',dict(reason='system/service pressure',row=row))
   elif (LOCAL/'pause.json').exists():(LOCAL/'pause.json').unlink()
   time.sleep(.1)
  rc=child.wait()
 peak_disk=max(peak_disk,sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file()))
 result=dict(name=name,exit_code=rc,seconds=time.monotonic()-start,peak_tree_rss=peak_rss,peak_tree_private=peak_private,peak_disk=peak_disk,model_calls=0);save(directory/'supervision.json',result);print(json.dumps(result),flush=True);return result

def prepare_window():
 from rag.chinese_terms import terms
 p=LOCAL/'fixed-window.jsonl';assert not p.exists();h=hashlib.sha256();n=0
 with v1.source() as c,p.open('w',encoding='utf-8') as out:
  for rid,fid,body,text in v1.rows(c,start=48000,stop=49000,n=24620273):
   checkpoint();pre=' '.join(terms(text));row=dict(rowid=rid,fragment_id=fid,body_sha=v1.digest(body),terms_sha=v1.digest(pre),terms=pre);line=json.dumps(row,ensure_ascii=False);out.write(line+'\n');h.update(line.encode());n+=1
 save(LOCAL/'fixed-window.json',dict(start=48000,end=49000,n=n,sha256=h.hexdigest(),text_fields='identical pretokenized v1 terms; no raw original body copy'))

def errors(exc):
 result=[];seen=set()
 while exc is not None and id(exc) not in seen:seen.add(id(exc));result.append(dict(type=type(exc).__name__,repr=repr(exc),text=str(exc)));exc=exc.__cause__ or exc.__context__
 return result

def diagnose(which):
 import tantivy
 plan=read(LOCAL/'resource-and-diagnostic-plan.json');spec=next(x for x in plan['diagnostics'] if x['id']==which);folder=LOCAL/which;path=folder/'index';start=time.monotonic();writer=None;failure=None;join=None;commit=None;attempted=0
 if which=='D1':shutil.copytree(v1.LOCAL/'50000/tantivy',path)
 idx=v1.index(path);writer=idx.writer(heap_size=spec['heap'],num_threads=1)
 try:
  for line in (LOCAL/'fixed-window.jsonl').read_text(encoding='utf-8').splitlines():
   x=json.loads(line);checkpoint(writer);writer.add_document(tantivy.Document(terms=x['terms'],rowid=x['rowid']));attempted+=1
   if spec['lifecycle']=='reopen per100' and attempted%100==0:
    writer.commit();writer.wait_merging_threads();del writer;del idx;gc.collect();idx=v1.index(path);writer=idx.writer(heap_size=spec['heap'],num_threads=1)
  writer.commit();writer.wait_merging_threads();writer=None;idx.reload();count=idx.searcher().num_docs;save(folder/'result.json',dict(passed=True,attempted=attempted,visible=count,seconds=time.monotonic()-start,spec=spec))
 except Exception as e:
  failure=errors(e);traceback.print_exc()
  # prepare_commit preserves the worker's original error; wait_merging_threads
  # alone replaces it with generic ErrorInThread in Tantivy0.27.
  if writer is not None:
   try:writer.commit()
   except Exception as e:commit=errors(e);traceback.print_exc()
   try:writer.wait_merging_threads()
   except Exception as e:join=errors(e);traceback.print_exc()
  save(folder/'result.json',dict(passed=False,attempted=attempted,primary=failure,commit_detail=commit,join_detail=join,seconds=time.monotonic()-start,spec=spec));raise


def prepare(n):
 from rag.chinese_terms import terms
 folder=LOCAL/'input';folder.mkdir(exist_ok=True);db=folder/'spool.sqlite3';con=sqlite3.connect(db);con.executescript('PRAGMA cache_size=-4096; CREATE TABLE IF NOT EXISTS rows(position INTEGER PRIMARY KEY,rowid INTEGER UNIQUE,fragment_id TEXT,body_sha TEXT,terms_sha TEXT,terms TEXT);')
 done=con.execute('select count(*) from rows').fetchone()[0];start=time.monotonic();before=done;max_token=0
 with v1.source() as c:
  for pos,(rid,fid,body,text) in enumerate(v1.rows(c,start=done,stop=n,n=24620273),done):
   pre=' '.join(terms(text));max_token=max(max_token,max((len(t) for t in pre.split()),default=0));con.execute('insert into rows values(?,?,?,?,?,?)',(pos,rid,fid,v1.digest(body),v1.digest(pre),pre))
   if (pos+1)%1000==0:con.commit();checkpoint();print('prepared',pos+1,flush=True)
 con.commit();con.close();save(folder/('prepare-'+str(n)+'.json'),dict(start=before,end=n,incremental=before>0,seconds=time.monotonic()-start,max_token_chars=max_token));print('input prepared',n,flush=True)

def build_sample(name,n):
 import tantivy
 folder=LOCAL/name;assert not (folder/'built.json').exists(),'No retries/overwrites';folder.mkdir(exist_ok=True);con=sqlite3.connect(folder/'fts.sqlite3');con.execute('pragma cache_size=-4096');con.executescript("CREATE VIRTUAL TABLE corpus_fts USING fts5(terms,content=''); CREATE TABLE mapping(rowid INTEGER PRIMARY KEY,fragment_id TEXT,body_sha TEXT,terms_sha TEXT);")
 source=sqlite3.connect((LOCAL/'input/spool.sqlite3').as_uri()+'?mode=ro',uri=True);idx=v1.index(folder/'tantivy');plan=read(LOCAL/'resource-and-diagnostic-plan.json');writer=idx.writer(heap_size=plan['writer_heap'],num_threads=plan['index_threads']);start=time.monotonic();h=hashlib.sha256();done=0;tsql=tsend=0
 try:
  for pos,rid,fid,bodysha,termsha,pre in source.execute('select * from rows where position<? order by position',(n,)):
   assert v1.digest(pre)==termsha
   tick=time.monotonic();con.execute('insert into corpus_fts(rowid,terms) values(?,?)',(rid,pre));con.execute('insert into mapping values(?,?,?,?)',(rid,fid,bodysha,termsha));tsql+=time.monotonic()-tick
   tick=time.monotonic();writer.add_document(tantivy.Document(terms=pre,rowid=rid));tsend+=time.monotonic()-tick;h.update(json.dumps([pos,rid,fid,bodysha,termsha],ensure_ascii=False).encode());done+=1
   if done%1000==0:checkpoint(writer);print('indexed',name,done,flush=True)
  tick=time.monotonic();opstamp=writer.commit();commit_s=time.monotonic()-tick;tick=time.monotonic();writer.wait_merging_threads();merge_s=time.monotonic()-tick;writer=None;con.commit();idx.reload();count=idx.searcher().num_docs;assert count==n==done
  meta=read(folder/'tantivy/meta.json');save(folder/'built.json',dict(n=n,input_sha=h.hexdigest(),seconds=time.monotonic()-start,fts_insert_s=tsql,tantivy_enqueue_s=tsend,commit_s=commit_s,wait_merge_s=merge_s,opstamp=opstamp,segments=len(meta['segments']),heap=plan['writer_heap'],index_threads=1,from_zero=True,normal_close=True));print('built',name,n,flush=True)
 except Exception as e:
  root=errors(e);detail=None
  try:writer.commit()
  except Exception as inner:detail=errors(inner);traceback.print_exc()
  save(folder/'build-failure.json',dict(attempted=done,error=root,commit_detail=detail));traceback.print_exc();raise
 finally:
  if writer is not None:
   try:writer.wait_merging_threads()
   except Exception:traceback.print_exc()
  source.close();con.close()

def validate_sample(name,n):
 import tantivy
 folder=LOCAL/name;idx=v1.index(folder/'tantivy');idx.reload();meta=read(folder/'tantivy/meta.json');searcher=idx.searcher();assert searcher.num_docs==n
 spool=sqlite3.connect((LOCAL/'input/spool.sqlite3').as_uri()+'?mode=ro',uri=True);con=sqlite3.connect(folder/'acceptance.sqlite3');con.execute('create table seen(rowid INTEGER PRIMARY KEY)');matched=0
 # Each segment is deletion-free; streaming stored IDs avoids a million-hit heap.
 hits=searcher.search(tantivy.Query.all_query(),limit=n,count=False).hits
 for _,address in hits:
  rid=searcher.doc(address)['rowid'][0];con.execute('insert into seen values(?)',(rid,));row=spool.execute('select position from rows where rowid=?',(rid,)).fetchone();assert row and row[0]<n;matched+=1
  if matched%1000==0:checkpoint()
 con.commit();assert matched==con.execute('select count(*) from seen').fetchone()[0]==n
 h=hashlib.sha256()
 for row in spool.execute('select position,rowid,fragment_id,body_sha,terms_sha from rows where position<? order by position',(n,)):h.update(json.dumps(list(row),ensure_ascii=False).encode())
 assert h.hexdigest()==read(folder/'built.json')['input_sha'];save(folder/'acceptance.json',dict(passed=True,n=n,complete_id_set=True,input_sha=h.hexdigest(),new_process=True,normal_open=True));spool.close();con.close();print('accepted exact membership',name,n,flush=True)

if __name__=='__main__':
 a=sys.argv[1];configure()
 if a=='window':prepare_window()
 elif a=='diag':diagnose(sys.argv[2])
 elif a=='supervise':supervise(sys.argv[2],sys.argv[3:])
 elif a=='prepare':prepare(int(sys.argv[2]))
 elif a=='build':build_sample(sys.argv[2],int(sys.argv[3]))
 elif a=='validate':validate_sample(sys.argv[2],int(sys.argv[3]))
