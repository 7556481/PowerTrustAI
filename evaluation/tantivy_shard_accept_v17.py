"""Full sealed-shard identity traversal and existing 24-query product comparison."""
import asyncio,hashlib,json,sqlite3,time,uuid
from pathlib import Path
from rag.tantivy_build import atomic,stored_ids
from rag.tantivy_manifest import sha,package_manifest
from evaluation.tantivy_shard_continuous_v17 import HOME,OLD,AUTH,guard,read

def accept(plan):
 import tantivy
 from evaluation.tantivy_supervision_v3 import Guard
 g=Guard(plan);g.check('full shard identity')
 from evaluation.tantivy_full_build_v1 import SOURCE,K
 from rag.storage import KnowledgeStore
 from rag.corpus_index import seal as source_seal
 with KnowledgeStore(SOURCE,readonly=True,validated_pdf_cache=True) as source:
  if source_seal(source,K) is None:raise RuntimeError('Original source seal missing')
 inventory=read(HOME/'shards.json');a=guard()
 if inventory['covered']!=a['expected'] or inventory['unbuilt']!=0:raise RuntimeError('Incomplete coverage')
 db=HOME/('full-seen-'+uuid.uuid4().hex+'.sqlite3');seen=sqlite3.connect(db.resolve().as_uri(),uri=True)
 sp=sqlite3.connect((OLD/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
 seen.execute('create table ids(rowid integer primary key)');seen.execute('pragma cache_size=-8192');position=0;negative=0;manifests=[];started=time.time()
 try:
  for ordinal,entry in enumerate(inventory['shards']):
   g.check('full shard identity');start,end=entry['input_range']
   if start!=position or end-start!=entry['count']:raise RuntimeError('Gap/overlap in shard intervals')
   root=Path(entry['index']).parent
   files=entry.get('files')
   if files:
    for name,v in files.items():
     if sha(root/name,lambda:g.check('full shard file hash'))!=v['sha256']:raise RuntimeError('Sealed file changed')
   else:
    if sha(entry['mapping'])!=entry['mapping_sha256']:raise RuntimeError('Initial sealed mapping changed')
    for name,v in entry['index_files'].items():
     if sha(Path(entry['index'])/name,lambda:g.check('initial shard file hash'))!=v['sha256']:raise RuntimeError('Initial sealed index changed')
   mapping=sqlite3.connect(Path(entry['mapping']).resolve().as_uri()+'?mode=ro',uri=True);h=hashlib.sha256()
   try:
    inputs=iter(sp.execute('select * from input where position>=? and position<? order by position',(start,end)))
    for row in mapping.execute('select * from rows order by position'):
     if position%1000==0:g.check('complete mapping/input proof')
     expected=next(inputs,None)
     if expected is None or row!=expected[:5] or row[0]!=position:raise RuntimeError('Input/mapping/position mismatch')
     rid=(-(position+1) if position<674 else position-673)
     if row[1]!=rid or hashlib.sha256(expected[5].encode()).hexdigest()!=row[4]:raise RuntimeError('Namespace/terms mismatch')
     h.update(json.dumps(row).encode());position+=1
    if position!=end or next(inputs,None) is not None:raise RuntimeError('Missing mapping member')
    index=tantivy.Index.open(entry['index']);n=0;batch=[]
    for rid in stored_ids(index,Path(entry['index'])):
     batch.append((rid,));n+=1;negative+=rid<0
     if len(batch)==1000:g.check('full native ID set');seen.executemany('insert into ids values(?)',batch);batch=[]
    if batch:seen.executemany('insert into ids values(?)',batch)
    if n!=end-start:raise RuntimeError('Native count mismatch')
    seen.commit();index=None
   finally:mapping.close()
   # A fresh complete traversal and immutable file identity bind prior body audits.
   proof=HOME/f'full-reader-proof-{ordinal:03d}.json';atomic(proof,{'passed':True,'complete_id_set':True,'n':end-start,'range':[start,end],'mapping_hash':h.hexdigest()})
   target=HOME/f'full-reader-manifest-{ordinal:03d}.json'
   package_manifest(entry['index'],proof,target,knowledge_version=K,source_total=a['expected'],scope='isolated',build={'range':[start,end]},source_identity={'prior_audit':entry.get('proof',entry.get('acceptance_sha256'))},check=lambda:g.check('full reader packaging'))
   manifests.append(str(target))
  if position!=24620947 or negative!=674 or seen.execute('select count(*) from ids').fetchone()[0]!=position:raise RuntimeError('Full ID scope mismatch')
  # Dense namespace plus unique count proves the exact expected set.
  if seen.execute('select count(*) from ids where rowid between -674 and -1').fetchone()[0]!=674 or seen.execute('select count(*) from ids where rowid between 1 and 24620273').fetchone()[0]!=24620273:raise RuntimeError('Missing namespace members')
  atomic(HOME/'accepted-shard-group.json',{'complete':True,'count':position,'negative':negative,'manifests':manifests,'seconds':time.time()-started,'models':0})
  atomic(HOME/'acceptance-complete.json',{'complete':True,'n':position,'models':0})
 finally:seen.close();sp.close()

def measure(plan):
 from rag.tantivy_sharded_v17 import ShardedTantivyRetriever
 import evaluation.tantivy_full_measure_v1 as existing
 group=read(HOME/'accepted-shard-group.json')
 if not group['complete']:raise RuntimeError('Unaccepted shard group')
 expected=read(OLD/'plan.json');assert len(expected['queries'])==24
 atomic(HOME/'plan.json',{'queries':expected['queries']})
 atomic(HOME/'construction-ledger.json',{'kind':'new60h-offline-budget-view-not-old-ledger','deadline':read(AUTH)['deadline']})
 (HOME/'accepted').mkdir(exist_ok=True);atomic(HOME/'accepted/manifest.json',group)
 def factory(source,manifest,k,isolated=True):return ShardedTantivyRetriever(source,group['manifests'],k)
 existing.ROOT=HOME;existing.FastTantivyRetriever=factory
 asyncio.run(existing.run())

def offline():
 import sys,psutil
 from evaluation.tantivy_shard_continuous_v17 import resources
 from evaluation.tantivy_supervision_v3 import supervise
 from evaluation.tantivy_full_controller_v1 import idle
 from evaluation.tantivy_checkpoint_recovery_v10 import dead
 a=guard()
 if read(HOME/'shards.json')['covered']!=a['expected']:raise RuntimeError('Construction not complete')
 for role in ['accept','measure']:
  a,limit=resources();control=HOME/'postbuild'/role;control.mkdir(parents=True,exist_ok=False)
  p={'deadline':min(a['deadline'],time.time()+14400),'grace_seconds':45,'kill_on_supervisor_exit':True,'cwd':str(Path.cwd()),
     'data_root':str(HOME),'extra_data_roots':[str(OLD),str((OLD/'build').resolve())],
     'memory_limit':limit-64*1024**2,'disk_limit':a['disk_limit'],'min_free':a['min_free'],'pressure_available':512*1024**2,
     'frozen_code':{f:sha(f) for f in ['evaluation/tantivy_shard_accept_v17.py','rag/tantivy_sharded_v17.py','evaluation/tantivy_full_measure_v1.py']}}
  atomic(control/'plan.json',p)
  rc=supervise(control/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_shard_accept_v17',role,str(control/'plan.json')],control/'logs',idle)
  if rc:raise RuntimeError('Full offline stage failed: '+role)
  dead(read(control/'process-identities.json'))
 atomic(HOME/'offline-stages-complete.json',{'wall':time.time(),'models':0,'needs_content_review':True})

if __name__=='__main__':
 import sys
 if sys.argv[1]=='offline':offline()
 elif sys.argv[1]=='accept':accept(sys.argv[2])
 elif sys.argv[1]=='measure':measure(sys.argv[2])
 else:raise SystemExit('accept PLAN | measure PLAN')
