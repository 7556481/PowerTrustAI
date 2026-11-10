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
 seen.execute('create table ids(rowid integer primary key)');seen.execute('pragma cache_size=-8192');position=0;negative=0;manifests=[];started=time.time();global_hash=hashlib.sha256()
 try:
  for ordinal,entry in enumerate(inventory['shards']):
   g.check('full shard identity');start,end=entry['input_range']
   if start!=position or end-start!=entry['count']:raise RuntimeError('Gap/overlap in shard intervals')
   root=Path(entry['index']).parent
   if entry.get('acceptance_sha256') and sha(root/'acceptance.json')!=entry['acceptance_sha256']:raise RuntimeError('Sealed acceptance receipt changed')
   if entry.get('reader_manifest_sha256') and sha(entry['reader_manifest'])!=entry['reader_manifest_sha256']:raise RuntimeError('Initial reader manifest changed')
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
     h.update(json.dumps(row).encode());global_hash.update(json.dumps(row).encode());position+=1
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
  if global_hash.hexdigest()!=read(OLD/'input-complete.json')['mapping_hash']:raise RuntimeError('Original complete frozen input digest differs')
  # Dense namespace plus unique count proves the exact expected set.
  if seen.execute('select count(*) from ids where rowid between -674 and -1').fetchone()[0]!=674 or seen.execute('select count(*) from ids where rowid between 1 and 24620273').fetchone()[0]!=24620273:raise RuntimeError('Missing namespace members')
  atomic(HOME/'accepted-shard-group.json',{'complete':True,'count':position,'negative':negative,'input_mapping_hash':global_hash.hexdigest(),'manifests':manifests,'seconds':time.time()-started,'models':0})
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
 tree_limit=read(plan)['memory_limit']
 native_limit=min(2*1024**3,max(64*1024**2,tree_limit-192*1024**2))
 atomic(HOME/'offline-runtime-resource-freeze.json',{'tree_limit':tree_limit,'native_limit':native_limit,'parent_reserve':192*1024**2,'formula':'min2GiB/max64MiB/tree minus192MiB; before comparisons, independent of query results','deadline':read(plan)['deadline'],'models':0})
 def factory(source,manifest,k,isolated=True):return ShardedTantivyRetriever(source,group['manifests'],k,memory_limit=native_limit)
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

def wait_for_construction():
 """Same bounded postbuild-companion pattern as tantivy_full_finish_v1.

 It neither retries construction nor schedules any paid/production work.
 """
 import psutil
 from rag.tantivy_build import owner
 folder=HOME/'postbuild';folder.mkdir(exist_ok=True)
 identity=read(folder/'controller-identity.json');deadline=read(AUTH)['deadline'];last=time.time()
 def alive():
  try:return abs(psutil.Process(identity['pid']).create_time()-identity['created'])<.001
  except psutil.NoSuchProcess:return False
 with owner(folder):
  if (folder/'companion-result.json').exists():raise RuntimeError('Existing postbuild receipt; no repeat')
  atomic(folder/'companion-identity.json',{'pid':psutil.Process().pid,'created':psutil.Process().create_time(),'controller':identity,'deadline':deadline})
  try:
   with (folder/'waiting-heartbeats.jsonl').open('a') as log:
    while alive():
     guard();now=time.time();row={'wall':now,'deadline':deadline}
     if now-last>5:row.update(observation_gap=now-last,unobserved_resources=True)
     last=now;root=psutil.Process(identity['pid']);processes={p.pid:p for p in [psutil.Process(),root,*root.children(recursive=True)]};memory=0
     for process in processes.values():
      try:
       m=process.memory_info();memory+=max(m.rss,getattr(m,'private',m.rss))
      except psutil.NoSuchProcess:pass
     # This lightweight companion counts inside the actual active segment
     # tree budget, including the original outer-controller64MiB reserve.
     state=read(HOME/'continuous-state.json');active=[]
     for control in HOME.glob('control-*'):
      path=control/'plan.json'
      if path.exists():
       plan=read(path)
       if plan.get('shard_dir')==state.get('folder'):active.append((path.stat().st_mtime,plan))
     if active:
      plan=max(active,key=lambda x:x[0])[1];budget=plan['memory_limit']+64*1024**2
      if memory>budget:raise MemoryError('Controller plus postbuild companion exceeds active tree budget')
      row['combined_limit']=budget
     row['combined_memory']=memory;log.write(json.dumps(row)+'\n');log.flush();time.sleep(2)
   guard();state=read(HOME/'continuous-state.json');inventory=read(HOME/'shards.json')
   if state['state']!='construction-complete-awaiting-full-offline-acceptance' or inventory['covered']!=read(AUTH)['expected']:raise RuntimeError('Construction stopped/incomplete; no automatic retries')
   offline()
   atomic(folder/'companion-result.json',{'status':'offline_outputs_ready_for_in_task_semantic_review','wall':time.time(),'models':0})
  except BaseException as e:
   atomic(folder/'companion-result.json',{'status':'stopped_requires_inspection','error':repr(e),'wall':time.time(),'models':0});raise

if __name__=='__main__':
 import sys
 if sys.argv[1] in ['accept','measure']:
  guard()
  for f,h in read(sys.argv[2]).get('frozen_code',{}).items():
   if sha(f)!=h:raise RuntimeError('Full offline frozen code changed')
 if sys.argv[1]=='wait':wait_for_construction()
 elif sys.argv[1]=='offline':offline()
 elif sys.argv[1]=='accept':accept(sys.argv[2])
 elif sys.argv[1]=='measure':measure(sys.argv[2])
 else:raise SystemExit('accept PLAN | measure PLAN')
