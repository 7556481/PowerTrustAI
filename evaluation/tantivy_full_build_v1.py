"""Full-index streaming worker. Source is immutable; native writer protocol reused."""
import hashlib,json,sqlite3,time,sys
from pathlib import Path
from rag.tantivy_build import CheckpointBuild,InputSpool,atomic,digest
from rag.tantivy_manifest import IndexIdentityError
from rag.storage import KnowledgeStore
from rag.tantivy_members import inventory
from rag.corpus_index import corpus_evidence
from rag.chinese_terms import terms
ROOT=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1')
SOURCE=Path('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3')
K='kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e'
REUSE=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/input/spool.sqlite3')
class PauseCheckpoint(RuntimeError):pass

class StreamingCheckpoint(CheckpointBuild):
 def mapping_hash(self):
  # Native/mapping prefix is append-only under owner lock. Reconstruct once on
  # every process reopen; final new-process acceptance still hashes all rows.
  if not hasattr(self,'_digest_cache'):self._digest_cache=hashlib.sha256();self._digest_position=-1
  for row in self.con.execute('select * from rows where position>? order by position',(self._digest_position,)):
   self._digest_cache.update(json.dumps(row).encode());self._digest_position=row[0]
  return self._digest_cache.hexdigest()
class StreamingSpool(InputSpool):
 def append(self,rows):
  n=self.con.execute('select coalesce(max(position)+1,0) from input').fetchone()[0]
  with self.con:
   for row in rows:
    if self.checkpoint_admit:self.checkpoint_admit()
    if row[0]!=n or hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:raise IndexIdentityError('Spool order/terms mismatch')
    self.con.execute('insert into input values(?,?,?,?,?,?)',row);n+=1

def prepare(store,inv,start,limit,guard):
 out=[];native=inv['native'];s=inv['source_seal']
 if start<native:
  byfid={r['fragment_id']:r for r in store.rows(s['base_knowledge_version'])}
  for rid,fid in store.connection.execute('select id,fragment_id from corpus_native where id>? order by id limit ?',(start,limit)):
   guard();e=corpus_evidence(store,fid,K,s);pre=' '.join(terms(byfid[fid]['search_text']));out.append([len(out)+start,-rid,fid,hashlib.sha256(e.text.encode()).hexdigest(),hashlib.sha256(pre.encode()).hexdigest(),pre])
  return out
 last=start-native
 # Same original chunk spans, fixed ID and body SHA; reuse original pretokenized
 # rows only after fid/body/terms hash agreement. No title or text-field change.
 sql='''select c.id,c.fragment_id,c.text_hash,r.raw_text,c.start,c.end,p.fragment_id,p.body_sha,p.terms_sha,p.terms
 from corpus_chunks c join corpus_records r on r.id=c.record_id left join reuse.rows p on p.rowid=c.id where c.id>? order by c.id limit ?'''
 for rid,fid,bodysha,raw,begin,end,oldfid,oldbody,termsha,pre in store.connection.execute(sql,(last,limit)):
  body=raw[begin:end]
  guard()
  if hashlib.sha256(body.encode()).hexdigest()!=bodysha:raise IndexIdentityError('Original span body changed')
  if pre is not None:
   if oldfid!=fid or oldbody!=bodysha or hashlib.sha256(pre.encode()).hexdigest()!=termsha:raise IndexIdentityError('Reused input identity mismatch')
  else:pre=' '.join(terms(body));termsha=hashlib.sha256(pre.encode()).hexdigest()
  out.append([len(out)+start,rid,fid,bodysha,termsha,pre])
 return out

def run(plan_path):
 from evaluation.tantivy_supervision_v3 import Guard,Expired
 g=Guard(plan_path);plan=json.loads((ROOT/'plan.json').read_text(encoding='utf8'));identity=json.loads((ROOT/'build-identity.json').read_text());build=ROOT/'build';build.mkdir(exist_ok=True)
 started=time.monotonic();primary=None;b=None;sp=None
 feeding=False
 def check():
  if feeding and g.path.with_name('pause.json').exists():
   if time.time()>=g.plan['deadline'] or g.path.with_name('stop.json').exists():raise Expired('feed stopped')
   return # Finish the already bounded/durable batch, then close at checkpoint.
  g.check('prepare/feed')
 try:
  g.check('source identity')
  with KnowledgeStore(SOURCE,readonly=True) as store:
   from evaluation.tantivy_medium_measure_v2 import seal_checked
   # Existing hash implementation; cooperative guard at each8MiB.
   import evaluation.tantivy_medium_measure_v2 as old
   from unittest.mock import patch
   with patch.object(old,'checkpoint',check):seal_checked(store,K)
   inv=inventory(store,K)
   if inv['total']!=identity['expected'] or inv['industry']!=identity['industry'] or inv['native']!=identity['native']:raise IndexIdentityError('Source scope changed')
   store.connection.execute('pragma cache_size=-8192');store.connection.execute('attach database ? as reuse',(REUSE.resolve().as_uri()+'?mode=ro',))
   remaining=max(0,g.plan['deadline']-time.time()-60)
   b=StreamingCheckpoint(build,identity,total_seconds=plan['build']['total_seconds'],segment_seconds=remaining,authorized_full=True,checkpoint=check)
   sp=StreamingSpool(ROOT/'spool.sqlite3',identity,checkpoint=check);sp.con.execute('pragma cache_size=-4096')
   mapped=b.con.execute('select count(*) from rows').fetchone()[0];h=hashlib.sha256()
   for row in sp.con.execute('select * from input where position<? order by position',(mapped,)):
    check()
    if hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:raise IndexIdentityError('Spool terms changed on resume')
    h.update(json.dumps(row[:-1]).encode())
   if mapped and h.hexdigest()!=b.mapping_hash():raise IndexIdentityError('Spool/mapping committed prefix mismatch')
   while True:
    check();n=b.con.execute('select coalesce(max(position)+1,0) from rows').fetchone()[0]
    if n==identity['expected']:break
    batch=sp.con.execute('select * from input where position>=? order by position limit 10000',(n,)).fetchall()
    if not batch:
     batch=prepare(store,inv,n,10000,check)
     if not batch:raise IndexIdentityError('Incomplete prepared source')
     sp.append(batch)
    feeding=True
    try:b.append(batch)
    finally:feeding=False
    atomic(ROOT/'progress.json',{'mapped':n+len(batch),'expected':identity['expected'],'spooled':sp.con.execute('select max(position)+1 from input').fetchone()[0],'wall':time.time(),'worker_elapsed':time.monotonic()-started,'phase':'native committed and mapped','segment_plan':str(plan_path)})
    if g.path.with_name('pause.json').exists():raise PauseCheckpoint('user/resource pause after committed batch')
   atomic(ROOT/'built-complete.json',{'n':identity['expected'],'not_yet_accepted':True})
 except (Expired,TimeoutError,PauseCheckpoint) as e:
  primary=e;g.event('normal_segment_stop',error=type(e).__name__)
 except BaseException as e:
  primary=e;g.event('primary_failure',error=type(e).__name__);raise
 finally:
  if sp:sp.close()
  if b:b.close(primary=primary)
  g.event('worker_closed',primary=type(primary).__name__ if primary else None,elapsed=time.monotonic()-started)
if __name__=='__main__':run(sys.argv[1])
