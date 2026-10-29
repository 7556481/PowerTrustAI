"""Isolated, resource-bounded, same-token FTS/Tantivy feasibility; no models."""
import argparse,subprocess,sys,gc,ctypes,hashlib,json,math,os,re,shutil,sqlite3,time,urllib.request
from pathlib import Path
from ctypes import wintypes
ROOT=Path(__file__).resolve().parents[1]
LOCAL=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-bounded-v1')
DB=Path('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3')
VERSION='tantivy-bounded-v1'

def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');q.replace(p)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def native_process():
 class Memory(ctypes.Structure):
  _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ('peak','rss','pp','p','np','n','page','peakpage')]
 k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=wintypes.HANDLE
 m=Memory();m.cb=ctypes.sizeof(m);fn=ctypes.windll.psapi.GetProcessMemoryInfo;fn.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
 if not fn(k.GetCurrentProcess(),ctypes.byref(m),m.cb):raise OSError('Process memory unavailable')
 return dict(rss=m.rss,peak=m.peak,private_commit=m.page)
def available():
 class Status(ctypes.Structure):_fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[(x,ctypes.c_ulonglong) for x in ('total','free','page','freepage','virt','freevirt','extended')]
 m=Status();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.free

def source():
 c=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('pragma cache_size=-4096');c.execute('pragma query_only=ON');return c

def ast(expression):
 """Supported actual one-field FTS subset; fail explicitly on extensions."""
 pattern=re.compile(r'\s*("(?:[^"\n]|"")*"|AND\b|OR\b|NOT\b|terms:|[()])')
 tokens=[];pos=0
 while pos<len(expression):
  if not expression[pos:].strip():break
  m=pattern.match(expression,pos)
  if not m:raise ValueError('Unsupported FTS syntax at '+str(pos))
  tokens.append(m[1]);pos=m.end()
 i=0
 def primary():
  nonlocal i
  if i>=len(tokens):raise ValueError('Missing operand')
  t=tokens[i];i+=1
  if t=='terms:':return primary()
  if t=='(':
   x=or_expr()
   if i>=len(tokens) or tokens[i]!=')':raise ValueError('Unbalanced parentheses')
   i+=1;return x
  if not t.startswith('"'):raise ValueError('Expected quoted term/phrase')
  words=t[1:-1].replace('""','"').split()
  if not words or any(not re.fullmatch(r'[a-z0-9\u3400-\u4dbf\u4e00-\u9fff]+',w) for w in words):raise ValueError('Not pretokenized vocabulary')
  return ['phrase',words]
 def not_expr():
  nonlocal i
  x=primary()
  while i<len(tokens) and tokens[i]=='NOT':i+=1;x=['not',x,primary()]
  return x
 def and_expr():
  nonlocal i
  x=not_expr()
  while i<len(tokens) and tokens[i]=='AND':i+=1;x=['and',x,not_expr()]
  return x
 def or_expr():
  nonlocal i
  x=and_expr()
  while i<len(tokens) and tokens[i]=='OR':i+=1;x=['or',x,and_expr()]
  return x
 if not tokens:return None
 tree=or_expr()
 if i!=len(tokens):raise ValueError('Unconsumed FTS syntax')
 return tree

def query(index,tree):
 import tantivy as t
 if tree is None:return t.Query.empty_query()
 op=tree[0]
 if op=='phrase':return t.Query.term_query(index.schema,'terms',tree[1][0]) if len(tree[1])==1 else t.Query.phrase_query(index.schema,'terms',tree[1])
 a,b=query(index,tree[1]),query(index,tree[2])
 return t.Query.boolean_query([(t.Occur.Must if op!='or' else t.Occur.Should,a),(t.Occur.MustNot if op=='not' else t.Occur.Must if op=='and' else t.Occur.Should,b)])

def index(path,reuse=True):
 import tantivy as t
 Path(path).mkdir(parents=True,exist_ok=True)
 b=t.SchemaBuilder();b.add_text_field('terms',tokenizer_name='existing_terms',index_option='position');b.add_integer_field('rowid',stored=True,fast=True);idx=t.Index(b.build(),path=str(path),reuse=reuse)
 idx.register_tokenizer('existing_terms',t.TextAnalyzerBuilder(t.Tokenizer.whitespace()).build());return idx

def freeze():
 assert not (LOCAL/'freeze.json').exists()
 from rag.topic_lanes import plan
 old=read(DB.parents[0].parent/'selective-match-retrieval-v1/materials.json');cs=old['selection']['cases'];prior=read(LOCAL.parent.parent/'maintenance_local/production-evidence-decoupling-v1/live/summary.json');selected=[]
 def add(name,q,category,origin,expected=None):
  expression=plan(q)[0][1];selected.append(dict(id=name,query=q,category=category,origin=origin,fts_expression=expression,tantivy_tree=ast(expression),expected=expected))
 for i in [0,1]:add('Q'+str(len(selected)+1),cs[i]['query'],'wide',dict(batch='selective-match-v1',id=cs[i]['id']),cs[i]['goals'])
 for slot in ['S5-baseline','S8-baseline']:
  a=next(x['accepted'] for x in prior['control'] if x['case_id']==slot);r=prior['outputs'][a['run_id']]['retrieval_records'][0];add('Q'+str(len(selected)+1),r['query'],'wide',dict(batch='production-evidence-decoupling-v1',slot=slot,retrieval_id=r['retrieval_id']))
 for i in [2,3,5,8]:add('Q'+str(len(selected)+1),cs[i]['query'],'normal',dict(batch='selective-match-v1',id=cs[i]['id']),cs[i]['goals'])
 for i in [6,9]:add('Q'+str(len(selected)+1),cs[i]['query'],'specified-document',dict(batch='selective-match-v1',id=cs[i]['id']),cs[i]['goals'])
 for i in [10,11]:add('Q'+str(len(selected)+1),cs[i]['query'],'low-hit-or-insufficient',dict(batch='selective-match-v1',id=cs[i]['id']),cs[i]['goals'])
 with source() as c:n=c.execute('select max(id) from corpus_chunks').fetchone()[0];k=c.execute('select knowledge_version from corpus_seal').fetchone()[0]
 assert math.gcd(48271,n)==1
 stat=DB.stat();free=available();cap=min(224*1048576,free//4)
 f=dict(version=VERSION,tantivy_binding='0.27.0',source=dict(path=str(DB),bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,knowledge_version=k,max_chunk=n),resources=dict(available_memory=free,process_memory_limit=cap,writer_heap=16_000_000,writer_threads=1,foreground_feeder_threads=1,disk_limit=30*1024**3,min_free_disk=30*1024**3,build_time_limit=14400,priority='below-normal',service_pause='active_run or queued; no force stop',scales=[50000,250000,1000000,4000000],scale_reason='~1GiB initially available: start50k to validate224MiB process envelope before250k'),sample=dict(kind='affine-permutation-prefix-v1',formula='id=((position*48271+12345)%24620273)+1',nested=True,seed=12345),queries=selected,top_k=3,rounds=3,order='alternate B/T, T/B, B/T by round; queries fixed order',count='once each backend after all three TopK rounds, separately timed',cache='OS cache unchanged; first observed after build, not cold-disk claim',thresholds=dict(semantic='all exact counts equal, mapper valid, no unexplained membership change',speed='wide-query median >=2x at current sample, no unexplained key quality loss',resources='within frozen caps; quality gate before growth'),quality_set='separate all674 native fragments, never injected into random sample',model_calls=0)
 save(LOCAL/'freeze.json',f);print('Frozen 12 queries and resource plan',cap,flush=True)

class Budget:
 def __init__(self,f):self.f=f;self.start=time.monotonic();self.peak=0
 def check(self,building=True):
  m=native_process();self.peak=max(self.peak,m['peak']);cap=self.f['resources'];used=sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file())
  if m['rss']>cap['process_memory_limit'] or m['private_commit']>cap['process_memory_limit']:raise RuntimeError('memory_budget')
  if used>cap['disk_limit'] or shutil.disk_usage(LOCAL).free<cap['min_free_disk']:raise RuntimeError('disk_budget')
  if building and time.time()>cap['campaign_deadline_epoch']:raise RuntimeError('build_time_budget')
  st=DB.stat()
  if (st.st_size,st.st_mtime_ns)!=(self.f['source']['bytes'],self.f['source']['mtime_ns']):raise RuntimeError('source_identity_changed')
  health=json.load(urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=5))
  if health['active_run'] or health['queued']:raise RuntimeError('service_became_active; normal checkpoint stop')
  return dict(**m,disk_bytes=used,elapsed=time.monotonic()-self.start)

def rows(c,native=False,start=0,stop=0,n=0):
 if native:
  from rag.storage import KnowledgeStore
  f=read(LOCAL/'freeze.json');seal=read(Path(str(DB)+'.manifest.json'));store=KnowledgeStore(DB,readonly=True)
  try:
   for r in c.execute('select id,fragment_id from corpus_native order by id'):
    e=store.evidence(r['fragment_id'],seal['base_knowledge_version']);search=c.execute('select search_text from fragments where fragment_id=?',(r['fragment_id'],)).fetchone()[0]
    yield -r['id'],r['fragment_id'],e.text,search
  finally:store.close()
 else:
  for position in range(start,stop):
   rid=(position*48271+12345)%n+1
   r=c.execute('select c.fragment_id,c.start,c.end,c.text_hash,r.raw_text from corpus_chunks c join corpus_records r on r.id=c.record_id where c.id=?',(rid,)).fetchone()
   body=r['raw_text'][r['start']:r['end']]
   if digest(body)!=r['text_hash']:raise ValueError('Original body hash mismatch')
   yield rid,r['fragment_id'],body,body

def build(folder,count,f,budget,native=False):
 if (Path(folder)/'results.json').exists():raise RuntimeError('Timed population is immutable; never resume building it')
 from rag.chinese_terms import terms
 folder.mkdir(parents=True,exist_ok=True)
 if (folder/'ready.json').exists():raise RuntimeError('Do not rebuild ready sample')
 con=sqlite3.connect(folder/'fts.sqlite3');con.executescript("pragma cache_size=-4096; pragma temp_store=FILE; CREATE VIRTUAL TABLE IF NOT EXISTS corpus_fts USING fts5(terms,content=''); CREATE TABLE IF NOT EXISTS mapping(rowid INTEGER PRIMARY KEY,fragment_id TEXT,body_sha TEXT,terms_sha TEXT); CREATE TABLE IF NOT EXISTS progress(n INTEGER);")
 # Replays only the last uncommitted batch after a normal interrupted checkpoint.
 prior=con.execute('select n from progress').fetchone();done=prior[0] if prior else 0
 idx=index(folder/'tantivy');writer=idx.writer(heap_size=f['resources']['writer_heap'],num_threads=1);beg=time.monotonic();chain=hashlib.sha256();tfts=ttant=ttokens=0
 try:
  with source() as c:
   for rid,fid,body,text in rows(c,native=native,start=done,stop=f.get('batch_end',count),n=f['source']['max_chunk']):
    tick=time.monotonic();pre=' '.join(terms(text));ttokens+=time.monotonic()-tick
    tick=time.monotonic();con.execute('insert into corpus_fts(rowid,terms) values(?,?)',(rid,pre));con.execute('insert into mapping values(?,?,?,?)',(rid,fid,digest(body),digest(pre)));tfts+=time.monotonic()-tick
    tick=time.monotonic();import tantivy;writer.add_document(tantivy.Document(terms=pre,rowid=rid));ttant+=time.monotonic()-tick
    chain.update((str(rid)+fid+digest(body)+digest(pre)).encode());done+=1
    if done%1000==0:
     r=budget.check();print(folder.name,done,r['rss']//1048576,flush=True)
  writer.commit();writer.wait_merging_threads();con.execute('delete from progress');con.execute('insert into progress values(?)',(done,));con.commit();idx.reload();chain=hashlib.sha256()
  for r in con.execute('select rowid,fragment_id,body_sha,terms_sha from mapping order by rowid'):chain.update(json.dumps(tuple(r),ensure_ascii=False).encode())
  result=dict(complete=done==count,n=done,stream_sha=chain.hexdigest(),seconds=time.monotonic()-beg,preprocess_s=ttokens,fts_insert_s=tfts,tantivy_add_s=ttant,source=f['source'],resources=budget.check());save(folder/('ready.json' if done==count else 'progress.json'),result);return result
 except Exception as failure:
  detail=None
  try:writer.wait_merging_threads()
  except Exception as inner:detail=str(inner)
  save(folder/'native-error.json',dict(primary=str(failure),join_detail=detail,committed_start=prior[0] if prior else 0,attempted=done,resources=native_process()))
  raise
 finally:
  try:writer.rollback();writer.wait_merging_threads()
  except Exception:pass
  con.close()

def build_isolated(folder,count,f,budget):
 # Fresh process per checkpoint: Python/Rust handle teardown must finish before
 # the next writer opens. No overlapping writer/merge pools, no new query logic.
 folder.mkdir(parents=True,exist_ok=True)
 while not (folder/'ready.json').exists():
  budget.check();reserved=max(native_process()['rss'],native_process()['private_commit'])+16*1048576
  result=subprocess.run([sys.executable,'-X','utf8','-m','evaluation.tantivy_bounded_v1','append',str(folder),str(count),str(reserved)],cwd=ROOT)
  if result.returncode:raise RuntimeError('Isolated checkpoint child failed; preserve committed progress')

def bench(folder,f,budget):
 if (folder/'results.json').exists():raise RuntimeError('No timing repeat')
 from rag.storage import KnowledgeStore
 from rag.corpus_index import corpus_evidence,seal
 store=KnowledgeStore(DB,readonly=True);t=time.monotonic();sealed=seal(store,f['source']['knowledge_version']);save(folder/'source-seal.json',dict(seconds=time.monotonic()-t,process_only=True))
 con=sqlite3.connect(folder/'fts.sqlite3');con.row_factory=sqlite3.Row;con.execute('pragma cache_size=-4096');idx=index(folder/'tantivy');idx.reload();searcher=idx.searcher();results=[];counts=[]
 try:
  for rd in range(3):
   for q in f['queries']:
    for backend in (['fts','tantivy'] if rd%2==0 else ['tantivy','fts']):
     query_obj=query(idx,q['tantivy_tree']);beg=time.monotonic()
     if backend=='fts':hits=[(r['rowid'],-r['score']) for r in con.execute('select rowid,bm25(corpus_fts) score from corpus_fts where corpus_fts match ? order by score,rowid limit 3',(q['fts_expression'],))]
     else:hits=[(searcher.doc(a)['rowid'][0],float(score)) for score,a in searcher.search(query_obj,limit=3,count=False).hits]
     search_s=time.monotonic()-beg;beg=time.monotonic();delivered=[]
     for rid,score in hits:
      m=con.execute('select * from mapping where rowid=?',(rid,)).fetchone();e=corpus_evidence(store,m['fragment_id'],f['source']['knowledge_version'],sealed)
      if digest(e.text)!=m['body_sha']:raise ValueError('Evidence mapping hash mismatch')
      # Membership cross-check, not used for ranking or timing search.
      if not con.execute('select 1 from corpus_fts where rowid=? and corpus_fts match ?',(rid,q['fts_expression'])).fetchone():raise ValueError('Tantivy hit violates frozen FTS semantics')
      delivered.append(dict(rowid=rid,fragment_id=m['fragment_id'],score=score,evidence_id=e.evidence_id,source_id=e.source_id,locator=e.locator,text=e.text,body_sha=m['body_sha']))
     row=dict(query=q['id'],round=rd,backend=backend,search_s=search_s,lookup_s=time.monotonic()-beg,hits=delivered,resources=budget.check(building=False));results.append(row);save(folder/'partial-results.json',results);print('topk',folder.name,q['id'],rd,backend,round(search_s,4),flush=True)
  for q in f['queries']:
   for backend in ['fts','tantivy']:
    beg=time.monotonic();n=con.execute('select count(*) from corpus_fts where corpus_fts match ?',(q['fts_expression'],)).fetchone()[0] if backend=='fts' else searcher.search(query(idx,q['tantivy_tree']),limit=1,count=True).count
    counts.append(dict(query=q['id'],backend=backend,count=n,seconds=time.monotonic()-beg))
  save(folder/'results.json',dict(topk=results,counts=counts));return results,counts
 finally:con.close();store.close()

def run():
 f=read(LOCAL/'freeze.json');native_process();k=ctypes.windll.kernel32;k.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000);k.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t];assert k.SetProcessAffinityMask(k.GetCurrentProcess(),3);budget=Budget(f)
 try:
  budget.check();folder=LOCAL/'quality'
  if not (folder/'ready.json').exists():build(folder,674,f,budget,True)
  if not (folder/'results.json').exists():bench(folder,f,budget)
  for n in f['resources']['scales']:
   folder=LOCAL/str(n)
   if not (folder/'ready.json').exists():build_isolated(folder,n,f,budget)
   if not (folder/'results.json').exists():bench(folder,f,budget)
   print('Awaiting quality/performance gate',n,flush=True)
   decision=folder/'review.json'
   while not decision.exists():time.sleep(1)
   if not read(decision).get('grow'):break
  save(LOCAL/'finished.json',dict(status='complete',resources=budget.check(building=False),model_calls=0))
 except Exception as e:
  save(LOCAL/'stopped.json',dict(type=type(e).__name__,reason=str(e),resources=native_process(),model_calls=0));raise
if __name__=='__main__':
 args=argparse.ArgumentParser();args.add_argument('action',choices=['freeze','run','append']);args.add_argument('folder',nargs='?');args.add_argument('count',nargs='?',type=int);args.add_argument('reserved',nargs='?',type=int);a=args.parse_args()
 if a.action=='freeze':freeze()
 elif a.action=='run':run()
 else:
  f=read(LOCAL/'freeze.json');folder=Path(a.folder);done=0
  if (folder/'fts.sqlite3').exists():
   con=sqlite3.connect(folder/'fts.sqlite3');prior=con.execute('select n from progress').fetchone();done=prior[0] if prior else 0;con.close()
  f['batch_end']=min(a.count,done+1000);f['resources']['process_memory_limit']-=a.reserved;build(folder,a.count,f,Budget(f))
