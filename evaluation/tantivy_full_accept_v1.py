"""Full source/spool/map/native proof, bounded rows, supervised resource envelope."""
import gc,hashlib,json,sqlite3,time,sys
from pathlib import Path
from rag.tantivy_build import atomic,digest,owner,stored_ids
from rag.storage import KnowledgeStore
from rag.corpus_index import corpus_evidence
from rag.tantivy_manifest import IndexIdentityError,sha,package_manifest
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K

def audited_history(root,ledger):
 proofs={}
 for s in ledger['segments']:
  if s.get('exit_code')==0 and s['status']=='complete':continue
  key=s['index'];file=root/('recovery-audit-%d.json'%key)
  if key not in (1,3) or not file.exists():raise IndexIdentityError('Unresolved construction segment')
  a=json.loads(file.read_text())
  if not a.get('passed'):raise IndexIdentityError('Failed recovery proof')
  if key==1 and (not a.get('native_unique_id_set_matches') or not a.get('source_and_spool_prefix_matches') or a.get('committed')!=150674):raise IndexIdentityError('Native recovery boundary not proven')
  if key==3 and (not a.get('source_positive_members_match') or not a.get('native_unchanged')):raise IndexIdentityError('Preparation recovery not proven')
  proofs[str(key)]={'audit_sha256':sha(file),'status':s['status'],'exit_code':s.get('exit_code')}
 return proofs

def run(plan_path):
 from evaluation.tantivy_supervision_v3 import Guard
 g=Guard(plan_path);identity=json.loads((ROOT/'build-identity.json').read_text());ledger=json.loads((ROOT/'construction-ledger.json').read_text());started=time.time();history=audited_history(ROOT,ledger)
 if not (ROOT/'built-complete.json').exists():raise IndexIdentityError('Build not completed')
 def admit():
  if time.time()>=ledger['deadline']:raise TimeoutError('Global construction budget exhausted')
  g.check('complete acceptance')
 admit()
 with owner(ROOT/'build'):
  budget_file=ROOT/'build/budget.json';b=json.loads(budget_file.read_text())
  if b['active_since'] is not None or b['identity']!=digest(identity):raise IndexIdentityError('Writer still active or wrong identity')
  b['active_since']=started;atomic(budget_file,b)
  try:
   with KnowledgeStore(SOURCE,readonly=True,validated_pdf_cache=True) as source:
    from evaluation.tantivy_medium_measure_v2 import seal_checked
    import evaluation.tantivy_medium_measure_v2 as old
    from unittest.mock import patch
    with patch.object(old,'checkpoint',admit):sealed=seal_checked(source,K)
    admit();mapping=sqlite3.connect((ROOT/'build/mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);spool=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    try:
     for c in (mapping,spool):c.execute('pragma cache_size=-8192')
     def expected():
      for rid,fid in source.connection.execute('select id,fragment_id from corpus_native order by id'):
       admit();e=corpus_evidence(source,fid,K,sealed);yield -rid,fid,hashlib.sha256(e.text.encode()).hexdigest()
      yield from source.connection.execute('select id,fragment_id,text_hash from corpus_chunks order by id')
     mi=iter(mapping.execute('select * from rows order by position'));si=iter(spool.execute('select * from input order by position'));h=hashlib.sha256();n=0
     for rid,fid,bodysha in expected():
      if n%1000==0:admit()
      m=next(mi,None);r=next(si,None)
      if m is None or r is None or tuple(r[:5])!=tuple(m) or tuple(m[:4])!=(n,rid,fid,bodysha):raise IndexIdentityError('Source/member/spool mismatch')
      if hashlib.sha256(r[-1].encode()).hexdigest()!=r[-2]:raise IndexIdentityError('Terms SHA mismatch')
      h.update(json.dumps(m).encode());n+=1
     if n!=identity['expected'] or next(mi,None) is not None or next(si,None) is not None:raise IndexIdentityError('Extra/missing members')
     if h.hexdigest()!=json.loads((ROOT/'build/checkpoint.json').read_text())['mapping_hash']:raise IndexIdentityError('Mapping digest mismatch')
     atomic(ROOT/'full-source-proof.json',{'n':n,'passed':True,'mapping_hash':h.hexdigest(),'source_verified':True,'terms_verified':True,'seconds':time.time()-started,'historical_failures_retained':history})
     import tantivy
     index=tantivy.Index.open(str(ROOT/'build/tantivy'));seen_path=ROOT/'native-seen.sqlite3'
     if seen_path.exists():raise IndexIdentityError('Prior acceptance artifact requires explicit investigation')
     seen=sqlite3.connect(seen_path.resolve().as_uri(),uri=True);seen.execute('pragma cache_size=-8192');seen.execute('create table seen(rowid integer primary key)');count=0;batch=[];native_start=time.time()
     try:
      for rid in stored_ids(index,ROOT/'build/tantivy'):
       batch.append((rid,));count+=1
       if len(batch)>=5000:
        admit();seen.executemany('insert into seen values(?)',batch);seen.commit();batch=[]
      if batch:seen.executemany('insert into seen values(?)',batch);seen.commit()
      admit();seen.execute('attach database ? as mapping',((ROOT/'build/mapping.sqlite3').resolve().as_uri()+'?mode=ro',))
      # Unique seen + unique mapping + equal counts and zero unknowns proves entire ID set equality.
      if count!=n or seen.execute('select 1 from seen where not exists(select 1 from mapping.rows m where m.rowid=seen.rowid) limit 1').fetchone():raise IndexIdentityError('Native ID set mismatch')
      admit()
     finally:seen.close();index=None;gc.collect()
     proof={'passed':True,'complete_id_set':True,'n':n,'mapping_hash':h.hexdigest(),'identity':digest(identity),'native_seconds':time.time()-native_start,'input_terms_binding':'All input terms SHA verified against committed spool/mapping; native stored IDs exhaustively verified; files sealed. Native postings are not reverse-decoded.'}
     proof['native_files']={str(f.relative_to(ROOT/'build/tantivy')).replace(chr(92),'/'):{'bytes':f.stat().st_size,'sha256':sha(f,admit)} for f in (ROOT/'build/tantivy').rglob('*') if f.is_file() and not f.name.endswith('.lock')}
     admit();atomic(ROOT/'build/acceptance.json',proof)
    finally:mapping.close();spool.close()
  finally:
   b['spent']+=max(0,time.time()-started);b['active_since']=None;atomic(budget_file,b)
 admit();target=ROOT/'accepted'
 if target.exists():raise IndexIdentityError('Existing publication requires explicit investigation')
 # Local same-volume rename; service manifest appears only after all proofs and hashes.
 (ROOT/'build').rename(target);admit()
 manifest=package_manifest(target/'tantivy',target/'acceptance.json',target/'manifest.json',knowledge_version=K,source_total=n,scope='full',build=identity,source_identity=identity,check=admit)
 manifest.update(quality_gate='unreviewed_fast_delivery_v1',delivery_profile='fast-evidence-v1');atomic(target/'manifest.json',manifest)
 admit();atomic(ROOT/'acceptance-complete.json',{'n':n,'passed':True,'manifest':str(target/'manifest.json'),'seconds':time.time()-started,'quality_release':'not yet approved'})
if __name__=='__main__':run(sys.argv[1])
