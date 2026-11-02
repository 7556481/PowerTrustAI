"""Bounded native prefix membership proof stored under the supervised data root."""
import sqlite3,uuid,json,time
from evaluation.tantivy_full_build_v1 import StreamingCheckpoint
from rag.tantivy_build import stored_ids
from rag.tantivy_manifest import IndexIdentityError
class DiagnosticWriter:
 def __init__(self,inner,root):self.inner=inner;self.root=root;self.closed=False
 def __getattr__(self,name):return getattr(self.inner,name)
 def record(self,operation,error):
  row={'operation':operation,'wall':time.time(),'error':repr(error),'cause':repr(error.__cause__),'context':repr(error.__context__)}
  try:
   with (self.root/'native-errors.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row)+'\n')
  except Exception as logging_error:
   import sys
   try:sys.stderr.write(json.dumps(dict(row,logging_error=type(logging_error).__name__))+'\n')
   except Exception:pass # Never replace the original native failure with logging failure.
 def commit(self):
  try:return self.inner.commit()
  except BaseException as e:self.record('commit',e);raise
 def wait_merging_threads(self):
  if self.closed:return
  self.closed=True
  try:return self.inner.wait_merging_threads()
  except BaseException as e:self.record('wait_merging_threads',e);raise
class FullCheckpoint(StreamingCheckpoint):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.writer=DiagnosticWriter(self.writer,self.root)
 def _proof(self,extra):
  self.admit();path=self.root/('recovery-seen-'+uuid.uuid4().hex+'.sqlite3');path.touch(exist_ok=False)
  seen=sqlite3.connect(path.resolve().as_uri(),uri=True);success=False
  try:
   seen.execute('pragma cache_size=-8192');seen.execute('create table seen(rowid integer primary key)');seen.execute('create table expected(rowid integer primary key)')
   seen.executemany('insert into expected values(?)',((r[1],) for r in extra));seen.commit();batch=[];n=0
   for rid in stored_ids(self.index,self.root/'tantivy'):
    batch.append((rid,));n+=1
    if len(batch)>=5000:self.admit();seen.executemany('insert into seen values(?)',batch);seen.commit();batch=[]
   if batch:seen.executemany('insert into seen values(?)',batch);seen.commit()
   self.admit();seen.execute('attach database ? as mapping',((self.root/'mapping.sqlite3').resolve().as_uri()+'?mode=ro',))
   def progress():
    try:self.admit();return 0
    except BaseException:return 1
   seen.set_progress_handler(progress,10000)
   try:unknown=seen.execute('select 1 from seen where not exists(select 1 from mapping.rows m where m.rowid=seen.rowid) and not exists(select 1 from expected e where e.rowid=seen.rowid) limit 1').fetchone()
   except sqlite3.OperationalError:self.admit();raise
   if unknown or n!=self.con.execute('select count(*) from rows').fetchone()[0]+len(extra):raise IndexIdentityError('Native/mapping prefix mismatch')
   self.admit();success=True
  finally:
   seen.close()
   if success:path.unlink() # only this proof's owned temporary file; failures retained
