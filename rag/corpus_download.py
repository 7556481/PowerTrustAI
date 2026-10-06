"""Pinned public HF shards, bounded streaming/resume, never credentials or headers."""
import argparse,hashlib,json,time
from pathlib import Path,PurePosixPath
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
DATASET='BAAI/IndustryCorpus2_electric_power_energy'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def download(entry,root,revision,proxy):
    name=PurePosixPath(entry['path'])
    if name.is_absolute() or '..' in name.parts or '\\' in str(name):raise ValueError('Unsafe shard path')
    p=root.joinpath(*name.parts);part=p.with_suffix('.partial')
    if not p.resolve().is_relative_to(root.resolve()):raise ValueError('Shard path outside declared root')
    p.parent.mkdir(parents=True,exist_ok=True)
    expected=entry['lfs']['oid'];size=entry['size'];start=time.monotonic()
    try:
        reused=p.exists()
        if reused:
            if p.stat().st_size!=size or sha(p)!=expected:raise ValueError('existing_integrity_mismatch')
        else:
            n=part.stat().st_size if part.exists() else 0
            opener=build_opener(ProxyHandler({'https':proxy} if proxy else {}))
            url=f'https://huggingface.co/datasets/{DATASET}/resolve/{revision}/'+quote(str(name),safe='/')+'?download=true'
            with opener.open(Request(url,headers={'Range':f'bytes={n}-'}),timeout=60) as r:
                if n and (r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {n}-')):raise ValueError('resume_range_not_honored')
                with part.open('ab' if n else 'wb') as f:
                    for b in iter(lambda:r.read(4*1024*1024),b''):
                        f.write(b)
                        if f.tell()>size:raise ValueError('declared_size_exceeded')
            if part.stat().st_size!=size or sha(part)!=expected:raise ValueError('download_integrity_mismatch')
            part.rename(p)
        import pyarrow.parquet as pq
        try:pf=pq.ParquetFile(p)
        except Exception as exc:
            return {'path':str(name),'status':'verified_bytes_unreadable_parquet','bytes':size,'sha256':expected,'error_type':type(exc).__name__,'seconds':time.monotonic()-start}
        return {'path':str(name),'status':'verified','reused':reused,'bytes':size,'sha256':expected,'rows':pf.metadata.num_rows,'seconds':time.monotonic()-start}
    except Exception as exc:
        # Network exceptions can contain signed redirect URLs; do not archive them.
        return {'path':str(name),'status':'failed','error_type':type(exc).__name__,'partial_bytes':part.stat().st_size if part.exists() else 0}
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--shards',required=True)
    p.add_argument('--output',required=True);p.add_argument('--proxy');p.add_argument('--workers',type=int,default=2)
    a=p.parse_args();m=json.loads(Path(a.manifest).read_text(encoding='utf-8'));root=Path(a.shards).resolve();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if not 1<=a.workers<=4:raise ValueError('Workers must be 1..4')
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs=[pool.submit(download,x,root,m['revision'],a.proxy) for x in m['files']]
        results=[]
        for j in jobs:
            r=j.result();results.append(r);(out/('download-'+r['path'].replace('/','_')+'.json')).write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r),flush=True)
    (out/'download-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
if __name__=='__main__':main()
