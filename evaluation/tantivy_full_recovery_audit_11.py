"""Read-only prefix recovery proof; no native writer or input regeneration."""
import hashlib,json,sqlite3,time,psutil
from rag.tantivy_build import atomic,digest,stored_ids,owner
from rag.tantivy_manifest import sha,IndexIdentityError
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE

def run():
 start=time.time();ledger=json.loads((ROOT/'construction-ledger.json').read_text());assert time.time()<ledger['deadline']
 ids=json.loads((ROOT/'controls/11/process-identities.json').read_text())
 for pid,created in ids.items():
  try:
   if abs(psutil.Process(int(pid)).create_time()-created)<.001:raise RuntimeError('Prior build process alive')
  except psutil.NoSuchProcess:pass
 with owner(ROOT/'build'):
  identity=json.loads((ROOT/'build-identity.json').read_text());assert [SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns]==identity['source_stat']
  cp=json.loads((ROOT/'build/checkpoint.json').read_text());assert cp['count']==680674,'This audit is bounded to the frozen680674-member prefix, not full-corpus enumeration';pending=json.loads((ROOT/'build/prepared.json').read_text());assert pending['identity']==cp['identity']==digest(identity) and digest(pending['rows'])==pending['payload_hash']
  c=sqlite3.connect((ROOT/'build/mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);sp=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);source=sqlite3.connect(SOURCE.resolve().as_uri()+'?mode=ro',uri=True)
  h=hashlib.sha256();n=0;si=iter(sp.execute('select * from input order by position'))
  for m in c.execute('select * from rows order by position'):
   if time.time()>=ledger['deadline']:raise TimeoutError('Original budget expired')
   row=next(si);assert tuple(row[:5])==m and m[0]==n and hashlib.sha256(row[-1].encode()).hexdigest()==row[-2]
   if m[1]>0:assert source.execute('select fragment_id,text_hash from corpus_chunks where id=?',(m[1],)).fetchone()==m[2:4]
   h.update(json.dumps(m).encode());n+=1
  assert n==cp['count']==pending['start'] and h.hexdigest()==cp['mapping_hash']
  for m in pending['rows']:
   row=next(si);assert tuple(row[:5])==tuple(m) and hashlib.sha256(row[-1].encode()).hexdigest()==row[-2]
   assert source.execute('select fragment_id,text_hash from corpus_chunks where id=?',(m[1],)).fetchone()==tuple(m[2:4])
  import tantivy
  index=tantivy.Index.open(str(ROOT/'build/tantivy'));seen=set()
  for rid in stored_ids(index,ROOT/'build/tantivy'):
   assert rid not in seen;seen.add(rid)
  expected=set(row[0] for row in c.execute('select rowid from rows'));assert seen==expected and len(seen)==n
  c.close();sp.close();source.close();index=None
  proof={'version':'full-prefix-recovery-v1','segment':11,'passed':True,'committed':n,'native_matches_mapping':True,'mapping_matches_spool':True,'positive_source_metadata_matches':True,'mapping_hash':h.hexdigest(),'pending_start':pending['start'],'pending_end':pending['end'],'pending_payload_sha256':pending['payload_hash'],'native_files':{p.name:sha(p) for p in (ROOT/'build/tantivy').glob('*') if p.is_file() and not p.name.endswith('.lock')},'seconds':time.time()-start,'wall':time.time(),'memory_stop_not_native_failure':False,'native_file_creation_fault_unresolved':True}
  atomic(ROOT/'recovery-audit-11.json',proof);print(json.dumps({k:v for k,v in proof.items() if k!='native_files'}))
if __name__=='__main__':run()
