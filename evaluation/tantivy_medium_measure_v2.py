"""Frozen v2 measurements: kernel, original body, neighbors, independent counts."""
import gc,hashlib,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
from evaluation import tantivy_bounded_v1 as v1
from evaluation.tantivy_stability_v2 import LOCAL,ROOT,read,save,checkpoint,configure,supervise

def seal_checked(store,k):
 from rag.corpus_index import seal
 original=hashlib.sha256
 class Checked:
  def __init__(self,*a,**kw):self.inner=original(*a,**kw)
  def update(self,b):checkpoint();return self.inner.update(b)
  def __getattr__(self,n):return getattr(self.inner,n)
 # Same SHA256 and existing seal; only add pause checks per8MiB, not bypass.
 with patch.object(hashlib,'sha256',Checked):return seal(store,k)

def quality():
 import tantivy
 from rag.chinese_terms import terms
 folder=LOCAL/'quality';folder.mkdir(exist_ok=False);con=sqlite3.connect(folder/'fts.sqlite3');con.executescript("create virtual table corpus_fts using fts5(terms,content='');create table mapping(rowid integer primary key,fragment_id text,body_sha text,terms_sha text);");idx=v1.index(folder/'tantivy');writer=idx.writer(heap_size=128000000,num_threads=1);n=0;start=time.monotonic()
 with v1.source() as c:
  for rid,fid,body,text in v1.rows(c,native=True):
   pre=' '.join(terms(text));con.execute('insert into corpus_fts(rowid,terms) values(?,?)',(rid,pre));con.execute('insert into mapping values(?,?,?,?)',(rid,fid,v1.digest(body),v1.digest(pre)));writer.add_document(tantivy.Document(terms=pre,rowid=rid));n+=1;checkpoint(writer)
 writer.commit();writer.wait_merging_threads();con.commit();con.close();assert n==674;save(folder/'built.json',dict(n=n,from_zero=True,heap=128000000,seconds=time.monotonic()-start));print('quality built674',flush=True)

def measure(name,n):
 from rag.storage import KnowledgeStore
 from rag.corpus_index import corpus_evidence
 from rag.context import read_adjacent_context
 from rag.contracts import ContextOptions
 folder=LOCAL/name;assert not (folder/'results.json').exists(),'No performance repeat';f=read(v1.LOCAL/'freeze.json');con=sqlite3.connect(folder/'fts.sqlite3');con.row_factory=sqlite3.Row;con.execute('pragma cache_size=-4096');idx=v1.index(folder/'tantivy');idx.reload();searcher=idx.searcher();assert searcher.num_docs==n;store=KnowledgeStore(v1.DB,readonly=True);t=time.monotonic();sealed=seal_checked(store,f['source']['knowledge_version']);save(folder/'source-startup-seal.json',dict(seconds=time.monotonic()-t,per_process=True,not_per_query=True));out=[];counts=[]
 try:
  for rd in range(3):
   for q in f['queries']:
    for backend in (['fts','tantivy'] if rd%2==0 else ['tantivy','fts']):
     checkpoint();all_start=time.monotonic();start=time.monotonic();obj=v1.query(idx,q['tantivy_tree']) if backend=='tantivy' else None;compile_s=time.monotonic()-start;start=time.monotonic()
     if backend=='fts':hits=[(r['rowid'],-r['score']) for r in con.execute('select rowid,bm25(corpus_fts) score from corpus_fts where corpus_fts match ? order by score,rowid limit3'.replace('limit3','limit 3'),(q['fts_expression'],))]
     else:hits=[(searcher.doc(a)['rowid'][0],float(score)) for score,a in searcher.search(obj,limit=3,count=False).hits]
     kernel_s=time.monotonic()-start;start=time.monotonic();roots=[];delivered=[]
     for rid,score in hits:
      row=con.execute('select * from mapping where rowid=?',(rid,)).fetchone();assert row; e=corpus_evidence(store,row['fragment_id'],f['source']['knowledge_version'],sealed);assert v1.digest(e.text)==row['body_sha'];roots.append(e);delivered.append(dict(rowid=rid,fragment_id=row['fragment_id'],body_sha=row['body_sha'],evidence_id=e.evidence_id,source_id=e.source_id,locator=e.locator,text=e.text,score=score))
     body_s=time.monotonic()-start;core_total=time.monotonic()-all_start;start=time.monotonic();context=read_adjacent_context(store,tuple(roots),f['source']['knowledge_version'],ContextOptions(2400,6,1,True,'storage_order'));context_s=time.monotonic()-start
     for e in context.items:store.verify_evidence(e.evidence)
     # Semantic membership assertion is intentionally OUTSIDE timed body path.
     for rid,_ in hits:assert con.execute('select 1 from corpus_fts where rowid=? and corpus_fts match ?',(rid,q['fts_expression'])).fetchone()
     out.append(dict(query=q['id'],round=rd,backend=backend,compile_s=compile_s,kernel_s=kernel_s,body_s=body_s,search_body_s=core_total,context_s=context_s,search_body_context_s=core_total+context_s,hits=delivered,neighbors=[dict(fragment_id=x.evidence.provenance.fragment_id,body_sha=v1.digest(x.evidence.text),text=x.evidence.text) for x in context.items]));save(folder/'partial-results.json',out);print('measured',name,q['id'],rd,backend,round(kernel_s,4),flush=True)
  for q in f['queries']:
   for backend in ['fts','tantivy']:
    checkpoint();start=time.monotonic();count=con.execute('select count(*) from corpus_fts where corpus_fts match ?',(q['fts_expression'],)).fetchone()[0] if backend=='fts' else searcher.search(v1.query(idx,q['tantivy_tree']),limit=1,count=True).count;counts.append(dict(query=q['id'],backend=backend,count=count,seconds=time.monotonic()-start))
  assert all(counts[i]['count']==counts[i+1]['count'] for i in range(0,len(counts),2)),'Matching-set count differs'
  save(folder/'results.json',dict(population=n,topk=out,counts=counts));print('measure complete',name,n,flush=True)
 finally:con.close();store.close()

def child_stage(stage,args):
 save(LOCAL/'current-stage.json',dict(stage=stage,start_epoch=time.time()));start=time.monotonic();folder=LOCAL/'campaign-logs';folder.mkdir(exist_ok=True)
 with (folder/(stage+'.stdout.log')).open('w',encoding='utf-8') as o,(folder/(stage+'.stderr.log')).open('w',encoding='utf-8') as e:
  rc=subprocess.run([sys.executable,'-X','utf8','-m','evaluation.tantivy_stability_v2',*args],cwd=ROOT,stdout=o,stderr=e).returncode
 save(folder/(stage+'.receipt.json'),dict(exit_code=rc,wall_seconds=time.monotonic()-start));assert rc==0,stage+' failed, no retry'

def stage_measure(name,n):
 save(LOCAL/'current-stage.json',dict(stage='measure-'+name,start_epoch=time.time()));measure(name,n);gc.collect()

def await_gate(name):
 print('Awaiting',name,'review; no expansion before gate',flush=True)
 p=LOCAL/(name+'-review.json')
 while not p.exists():checkpoint();time.sleep(1)
 return read(p).get('grow',False)

def campaign():
 a=read(LOCAL/'50000-a/acceptance.json');b=read(LOCAL/'50000-b/acceptance.json');assert a['passed'] and b['passed'] and a['input_sha']==b['input_sha'];stage_measure('50000-a',50000);stage_measure('50000-b',50000);quality();stage_measure('quality',674)
 if not await_gate('50000'):return
 for n in [250000,1000000]:
  child_stage('prepare-'+str(n),['prepare',str(n)]);child_stage('build-'+str(n),['build',str(n),str(n)]);child_stage('validate-'+str(n),['validate',str(n),str(n)]);stage_measure(str(n),n)
  if n==250000 and not await_gate('250000'):return
 save(LOCAL/'campaign-complete.json',dict(completed=True,maximum=1000000,model_calls=0))

if __name__=='__main__':
 configure()
 if sys.argv[1]=='campaign':campaign()
 elif sys.argv[1]=='supervise':raise SystemExit('Use external supervisor importing this campaign module')
