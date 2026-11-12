from pathlib import Path
import json,hashlib,sqlite3,time
HOME=Path('D:/PowerTrustAI/data/runtime_local/fast-overlap-v27');ROOT=Path('D:/PowerTrustAI/data/retrieval_local');GROUP=ROOT/'tantivy-shards-v16/accepted-shard-group.json'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def file_hash(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def main():
 start=time.monotonic();g=read(GROUP);assert file_hash(GROUP)==read(HOME/'freeze.json')['group_sha256'];total=0;native_files=0;maps=[];overall=hashlib.sha256()
 for number,path in enumerate(g['manifests']):
  m=read(path);index=Path(m['index_path']);proof=read(m['acceptance']['proof_path']);assert file_hash(m['acceptance']['proof_path'])==m['acceptance']['proof_sha256']
  for name,identity in m['files'].items():
   f=index/name;assert f.is_file() and f.stat().st_size==identity['bytes'];assert file_hash(f)==identity['sha256'];native_files+=1
  p=index.parent/'mapping.sqlite3';db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);h=hashlib.sha256();n=0
  for row in db.execute('select * from rows order by position'):
   b=json.dumps(row).encode();h.update(b);overall.update(b);n+=1
  db.close();assert h.hexdigest()==proof['mapping_hash'] and n==proof['n'];total+=n;maps.append(dict(path=str(p),rows=n,mapping_hash=h.hexdigest()))
  (HOME/'asset-progress.json').write_text(json.dumps({'shards_verified':number+1,'native_files':native_files,'rows':total}),encoding='utf-8')
 assert total==g['count'] and overall.hexdigest()==g['input_mapping_hash']
 spool=ROOT/'tantivy-full-fast-v1/spool.sqlite3';db=sqlite3.connect(spool.as_uri()+'?mode=ro',uri=True);h=hashlib.sha256();n=0
 for row in db.execute('select * from input order by position'):
  assert hashlib.sha256(row[5].encode()).hexdigest()==row[4];h.update(json.dumps(row[:5]).encode());n+=1
  if n%1000000==0:(HOME/'spool-progress.json').write_text(json.dumps({'terms_rows_verified':n}),encoding='utf-8')
 db.close();assert n==total and h.hexdigest()==g['input_mapping_hash']
 result=dict(passed=True,shards=90,native_files=native_files,mappings=maps,count=total,global_mapping_hash=overall.hexdigest(),spool=dict(path=str(spool),bytes=spool.stat().st_size,mtime_ns=spool.stat().st_mtime_ns,all_terms_rows_hash_verified=n),seconds=time.monotonic()-start,changes=False,model_requests=0)
 (HOME/'asset-identity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='mappings'}))
if __name__=='__main__':main()
