"""Bounded checkpoint protocol. No full-build CLI and no implicit budget grant."""
import gc,hashlib,json,os,sqlite3,time
from pathlib import Path
from contextlib import contextmanager
from rag.tantivy_manifest import sha,IndexIdentityError

def atomic(path,value):
 path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,sort_keys=True),encoding='utf8');os.replace(tmp,path)
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

@contextmanager
def owner(root):
 file=open(Path(root)/'writer.lock','a+b');file.seek(0);file.write(b'0');file.flush();file.seek(0)
 try:
  if os.name=='nt':
   import msvcrt;msvcrt.locking(file.fileno(),msvcrt.LK_NBLCK,1)
  else:
   import fcntl;fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
  yield
 finally:file.close()

def create_index(path):
 import tantivy
 Path(path).mkdir(exist_ok=True)
 if (Path(path)/'meta.json').exists():idx=tantivy.Index.open(str(path))
 else:
  b=tantivy.SchemaBuilder();b.add_text_field('terms',tokenizer_name='existing_terms',index_option='position');b.add_integer_field('rowid',stored=True,fast=True);idx=tantivy.Index(b.build(),path=str(path))
 idx.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());return idx

def stored_ids(index,path):
 import tantivy
 index.reload();s=index.searcher();meta=json.loads((Path(path)/'meta.json').read_text());assert sum(x['max_doc'] for x in meta['segments'])==s.num_docs
 if any(x.get('deletes') for x in meta['segments']):raise IndexIdentityError('Unexpected deleted segments')
 for ordinal,segment in enumerate(meta['segments']):
  for n in range(segment['max_doc']):yield s.doc(tantivy.DocAddress(ordinal,n))['rowid'][0]

class CheckpointBuild:
 def __init__(self,root,identity,*,total_seconds=60,segment_seconds=30,authorized_full=False,wall=time.time,checkpoint=None):
  self.root=Path(root);self.root.mkdir(exist_ok=True);self.wall=wall;self.identity=identity;self.external_checkpoint=checkpoint
  if identity['expected']>10000 and not authorized_full:raise PermissionError('Full build requires separate explicit resource authorization')
  self._owner=owner(self.root);self._owner.__enter__();self.closed=False;self.writer=None;self.index=None
  try:
   ledger=self.root/'budget.json';now=wall()
   if ledger.exists():
    budget=json.loads(ledger.read_text())
    if budget['identity']!=digest(identity):raise IndexIdentityError('Resume source/config identity mismatch')
    # Charge an interrupted interval through recovery, including unseen downtime.
    if budget.get('active_since') is not None:budget['spent']+=max(0,now-budget['active_since'])
   else:budget={'identity':digest(identity),'total':total_seconds,'spent':0,'active_since':None}
   remaining=budget['total']-budget['spent']
   if remaining<=0:raise TimeoutError('Cumulative build budget exhausted; no renewal')
   self.deadline=now+min(segment_seconds,remaining);budget['active_since']=now;self.budget=budget;atomic(ledger,budget)
   self.con=sqlite3.connect(self.root/'mapping.sqlite3');self.con.execute('create table if not exists rows(position integer primary key,rowid integer unique,fragment_id text,body_sha text,terms_sha text)');self.con.commit();self.index=create_index(self.root/'tantivy');self.recover();self.writer=self.index.writer(heap_size=128000000,num_threads=1)
  except BaseException:
   if hasattr(self,'con'):self.con.close()
   self.index=None;gc.collect()
   self._owner.__exit__(None,None,None);raise
 def admit(self):
  if self.wall()>=self.deadline:raise TimeoutError('Segment deadline expired; no new work')
  if self.external_checkpoint:self.external_checkpoint()
  if self.wall()>=self.deadline:raise TimeoutError('Segment expired after pause/resume')
 def _proof(self,extra):
  self.admit();self.con.execute('drop table if exists temp.seen');self.con.execute('create temp table seen(rowid integer primary key)');expected={r[1] for r in extra};n=0
  for rid in stored_ids(self.index,self.root/'tantivy'):
   if n%1000==0:self.admit()
   self.con.execute('insert into seen values(?)',(rid,));known=self.con.execute('select 1 from rows where rowid=?',(rid,)).fetchone()
   if not known and rid not in expected:raise IndexIdentityError('Unexpected native member')
   n+=1
  if n!=self.con.execute('select count(*) from rows').fetchone()[0]+len(extra):raise IndexIdentityError('Native/mapping prefix mismatch')
 def recover(self):
  self.admit();pending=self.root/'prepared.json';count=self.con.execute('select count(*) from rows').fetchone()[0];self.index.reload();native=self.index.searcher().num_docs
  if not pending.exists():
   if count!=native:raise IndexIdentityError('Unjournaled commit mismatch; quarantine')
   checkpoint=self.root/'checkpoint.json'
   if checkpoint.exists() and json.loads(checkpoint.read_text())['mapping_hash']!=self.mapping_hash():raise IndexIdentityError('Checkpoint mapping changed')
   self._proof([]);return
  p=json.loads(pending.read_text())
  if p['identity']!=digest(self.identity) or digest(p['rows'])!=p['payload_hash']:raise IndexIdentityError('Prepared batch changed')
  start,end=p['start'],p['end']
  if count==native==start:
   checkpoint=self.root/'checkpoint.json'
   if checkpoint.exists() and json.loads(checkpoint.read_text())['mapping_hash']!=self.mapping_hash():raise IndexIdentityError('Prior checkpoint changed')
   self._proof([]);return # known uncommitted batch; caller must reoffer identical payload
  if native!=end or count not in (start,end):raise IndexIdentityError('Inconsistent commit boundary; quarantine')
  self._proof(p['rows'] if count==start else [])
  if count==start:
   self.con.executemany('insert into rows values(?,?,?,?,?)',p['rows']);self.con.commit()
  self.checkpoint();pending.unlink()
 def mapping_hash(self):
  h=hashlib.sha256()
  for row in self.con.execute('select * from rows order by position'):h.update(json.dumps(row).encode())
  return h.hexdigest()
 def checkpoint(self):
  atomic(self.root/'checkpoint.json',dict(identity=digest(self.identity),count=self.con.execute('select count(*) from rows').fetchone()[0],mapping_hash=self.mapping_hash(),opstamp=json.loads((self.root/'tantivy/meta.json').read_text())['opstamp']))
 def append(self,rows,*,fail_after_native=False):
  import tantivy
  self.admit();start=self.con.execute('select count(*) from rows').fetchone()[0];mapped=[]
  if not rows or start+len(rows)>self.identity['expected']:raise IndexIdentityError('Batch exceeds frozen member scope')
  for pos,rid,fid,bodysha,termsha,terms in rows:
   if pos!=start+len(mapped) or hashlib.sha256(terms.encode()).hexdigest()!=termsha:raise IndexIdentityError('Input order/hash mismatch')
   mapped.append([pos,rid,fid,bodysha,termsha])
  p={'identity':digest(self.identity),'start':start,'end':start+len(rows),'rows':mapped,'payload_hash':digest(mapped)};file=self.root/'prepared.json'
  if file.exists() and json.loads(file.read_text())!=p:raise IndexIdentityError('Resume payload differs')
  atomic(file,p)
  for row in rows:self.admit();self.writer.add_document(tantivy.Document(terms=row[-1],rowid=row[1]))
  self.admit();self.writer.commit()
  if fail_after_native:raise RuntimeError('synthetic interrupted native-before-mapping boundary')
  self.con.executemany('insert into rows values(?,?,?,?,?)',mapped);self.con.commit();self.checkpoint();file.unlink()
 def close(self,primary=None):
  if self.closed:return []
  self.closed=True;failures=[]
  try:
   if self.writer is not None:
    writer=self.writer;self.writer=None
    try:writer.wait_merging_threads()
    except Exception as e:failures.append(type(e).__name__)
   if hasattr(self,'con'):
    try:self.con.close()
    except Exception as e:failures.append(type(e).__name__)
   self.index=None;gc.collect()
  finally:
   try:
    self.budget['spent']+=max(0,self.wall()-self.budget['active_since']);self.budget['active_since']=None;atomic(self.root/'budget.json',self.budget)
    atomic(self.root/'cleanup.json',{'primary':type(primary).__name__ if primary else None,'cleanup_errors':failures})
   finally:self._owner.__exit__(None,None,None)
  if failures and primary is None:raise RuntimeError('Build cleanup failed: '+','.join(failures))
  return failures


class PreparationStage:
 """Preparation consumes the same cumulative ledger as the later writer."""
 def __init__(self,root,identity,*,total_seconds,segment_seconds,wall=time.time,checkpoint=None):
  self.root=Path(root);self.root.mkdir(exist_ok=True);self.wall=wall;self.checkpoint=checkpoint;self.closed=False
  self._owner=owner(self.root);self._owner.__enter__()
  try:
   file=self.root/'budget.json';now=wall()
   b=json.loads(file.read_text()) if file.exists() else {'identity':digest(identity),'total':total_seconds,'spent':0,'active_since':None}
   if b['identity']!=digest(identity):raise IndexIdentityError('Preparation identity mismatch')
   if b.get('active_since') is not None:b['spent']+=max(0,now-b['active_since'])
   remaining=b['total']-b['spent']
   if remaining<=0:raise TimeoutError('Preparation total budget exhausted')
   self.deadline=now+min(segment_seconds,remaining);b['active_since']=now;self.budget=b;atomic(file,b)
  except BaseException:self._owner.__exit__(None,None,None);raise
 def admit(self):
  if self.wall()>=self.deadline:raise TimeoutError('Preparation segment expired')
  if self.checkpoint:self.checkpoint()
  if self.wall()>=self.deadline:raise TimeoutError('Preparation expired after resume')
 def close(self):
  if self.closed:return
  self.closed=True
  try:
   self.budget['spent']+=max(0,self.wall()-self.budget['active_since']);self.budget['active_since']=None;atomic(self.root/'budget.json',self.budget)
  finally:self._owner.__exit__(None,None,None)

class InputSpool:
 """Durable ordered input with an identity-bound cumulative prefix hash."""
 def __init__(self,path,identity,checkpoint=None):
  self.checkpoint_admit=checkpoint
  self.con=sqlite3.connect(path);self.identity=digest(identity);self.con.executescript('create table if not exists meta(identity text);create table if not exists input(position integer primary key,rowid integer unique,fragment_id text,body_sha text,terms_sha text,terms text);')
  old=self.con.execute('select identity from meta').fetchone()
  if old and old[0]!=self.identity:raise IndexIdentityError('Spool source/config identity mismatch')
  if not old:self.con.execute('insert into meta values(?)',(self.identity,));self.con.commit()
 def append(self,rows):
  n=self.con.execute('select count(*) from input').fetchone()[0]
  with self.con:
   for row in rows:
    if self.checkpoint_admit:self.checkpoint_admit()
    if row[0]!=n or hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:raise IndexIdentityError('Spool order/terms mismatch')
    self.con.execute('insert into input values(?,?,?,?,?,?)',row);n+=1
 def checkpoint(self):
  h=hashlib.sha256();n=0
  for row in self.con.execute('select * from input order by position'):
   if row[0]!=n or hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:raise IndexIdentityError('Spool prefix changed')
   h.update(json.dumps(row[:-1]).encode());n+=1
  return {'identity':self.identity,'count':n,'prefix_hash':h.hexdigest()}
 def close(self):self.con.close()

def accept_complete(root,identity):
 """Read-only new-process complete enumeration; no native writer is opened."""
 root=Path(root);started=time.time();budget=json.loads((root/'budget.json').read_text())
 if budget.get('active_since') is not None:budget['spent']+=max(0,started-budget['active_since'])
 if budget['identity']!=digest(identity):raise IndexIdentityError('Validation identity mismatch')
 remaining=budget['total']-budget['spent']
 if remaining<=0:raise TimeoutError('No validation budget remains')
 def admit():
  if time.time()-started>=remaining:raise TimeoutError('Validation budget exhausted')
 with owner(root):
  budget['active_since']=started;atomic(root/'budget.json',budget)
  import tantivy
  idx=tantivy.Index.open(str(root/'tantivy'));con=sqlite3.connect((root/'mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
  try:
   count=con.execute('select count(*) from rows').fetchone()[0]
   if count!=identity['expected']:raise IndexIdentityError('Incomplete build')
   con.execute('create temp table seen(rowid integer primary key)');n=0
   for rid in stored_ids(idx,root/'tantivy'):
    if n%1000==0:admit()
    con.execute('insert into seen values(?)',(rid,))
    if not con.execute('select 1 from rows where rowid=?',(rid,)).fetchone():raise IndexIdentityError('Unknown member')
    n+=1
   if n!=count:raise IndexIdentityError('Missing members')
   h=hashlib.sha256()
   for row in con.execute('select * from rows order by position'):h.update(json.dumps(row).encode())
   if h.hexdigest()!=json.loads((root/'checkpoint.json').read_text())['mapping_hash']:raise IndexIdentityError('Mapping proof changed')
   admit();proof={'passed':True,'complete_id_set':True,'n':n,'mapping_hash':h.hexdigest(),'identity':digest(identity)}
   proof['native_files']={str(f.relative_to(root/'tantivy')).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f,admit)} for f in (root/'tantivy').rglob('*') if f.is_file() and not f.name.endswith('.lock')}
   admit()
  finally:
   con.close();idx=None;gc.collect();budget['spent']+=max(0,time.time()-started);budget['active_since']=None;atomic(root/'budget.json',budget)
 atomic(root/'acceptance.json',proof);return proof

def publish(root,target,identity,*,knowledge_version,source_total,scope):
 root=Path(root);target=Path(target)
 if target.exists():raise FileExistsError('Immutable published version already exists')
 proof=json.loads((root/'acceptance.json').read_text())
 if proof.get('identity')!=digest(identity) or proof.get('n')!=identity['expected']:raise IndexIdentityError('Publication identity/acceptance mismatch')
 # Rename only on same volume. No serving manifest exists until all final hashes pass.
 root.rename(target)
 from rag.tantivy_manifest import package_manifest
 return _publish_manifest(target,identity,knowledge_version,source_total,scope)


def finalize_publish(target,identity,*,knowledge_version,source_total,scope):
 """Recover a rename completed before serving-manifest publication."""
 target=Path(target)
 if (target/'manifest.json').exists():raise FileExistsError('Serving version is immutable')
 proof=json.loads((target/'acceptance.json').read_text())
 if proof.get('identity')!=digest(identity):raise IndexIdentityError('Publication recovery identity mismatch')
 from rag.tantivy_manifest import package_manifest
 return _publish_manifest(target,identity,knowledge_version,source_total,scope)


def _publish_manifest(target,identity,knowledge_version,source_total,scope):
 from rag.tantivy_manifest import package_manifest
 with owner(target):
  file=target/'budget.json';budget=json.loads(file.read_text());started=time.time()
  if budget['identity']!=digest(identity):raise IndexIdentityError('Publication budget identity mismatch')
  if budget.get('active_since') is not None:budget['spent']+=max(0,started-budget['active_since'])
  remaining=budget['total']-budget['spent'];budget['active_since']=started;atomic(file,budget)
  def admit():
   if time.time()-started>=min(14400,remaining):raise TimeoutError('Publication budget exhausted')
  try:
   admit()
   return package_manifest(target/'tantivy',target/'acceptance.json',target/'manifest.json',knowledge_version=knowledge_version,source_total=source_total,scope=scope,build=identity,source_identity=identity,check=admit)
  finally:
   budget['spent']+=max(0,time.time()-started);budget['active_since']=None;atomic(file,budget)
