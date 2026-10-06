"""CPU streaming corpus builder. Resume by committed source row, publish explicitly."""
import argparse,hashlib,json,sqlite3,time
from contextlib import closing,contextmanager
from pathlib import Path
from rag.storage import KnowledgeStore,canonical,digest
from rag.corpus_index import SCHEMA,add_record
from rag.chinese_terms import VERSION,QUERY_VERSION,terms
IDENTITY_VERSION='corpus-row-identity-v2'

def source_identity(row,revision,shard,row_number):
    original=row.get('_id')
    missing=original is None or original==''
    if not missing:return str(original),False
    return 'industrycorpus2:row-v1:'+digest(canonical([revision,shard,row_number]).encode()),True

@contextmanager
def writer_lease(database):
    # OS lock survives a stale filename and is released on process exit.
    lock=Path(str(database)+'.writer-lock')
    with lock.open('a+b') as f:
        if not lock.stat().st_size:f.write(b'0');f.flush()
        f.seek(0)
        if __import__('os').name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            try:yield
            finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)

def build(args):
    with writer_lease(args.database):return _build(args)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def initialize(base,destination,base_k):
    destination=Path(destination)
    if not destination.exists():
        with closing(sqlite3.connect(f'file:{Path(base).resolve().as_posix()}?mode=ro',uri=True)) as src,closing(sqlite3.connect(destination)) as dst:src.backup(dst)
    with KnowledgeStore(destination) as store:
        con=store.connection;con.executescript(SCHEMA)
        if not con.execute('SELECT 1 FROM corpus_native LIMIT 1').fetchone():
            for i,row in enumerate(store.rows(base_k),1):
                e=store.evidence(row['fragment_id'],base_k)
                con.execute('INSERT INTO corpus_native VALUES(?,?)',(i,e.provenance.fragment_id))
                con.execute('INSERT INTO corpus_fts(rowid,terms) VALUES(?,?)',(-i,' '.join(terms(row['search_text']))))
            con.commit()
def _build(args):
    import pyarrow.parquet as pq
    initialize(args.base,args.database,args.base_knowledge)
    manifest=json.loads(Path(args.manifest).read_text());root=Path(args.shards)
    con=sqlite3.connect(args.database,timeout=60)
    try:
        return _build_connection(args,con,manifest,root)
    finally:con.close()

def _build_connection(args,con,manifest,root):
    import pyarrow.parquet as pq
    con.execute('PRAGMA journal_mode=WAL');con.execute('PRAGMA cache_size=-65536')
    con.execute('PRAGMA temp_store=FILE');started=time.time()
    for shard in manifest['files']:
        name=shard['path'];p=root/name
        if not p.resolve().is_relative_to(root.resolve()):raise ValueError('Shard path outside declared root')
        progress=con.execute('SELECT next_row,complete FROM corpus_progress WHERE shard=?',(name,)).fetchone()
        if progress and progress[1] in (1,-1):continue
        if not p.exists():
            print(json.dumps({'waiting_for_download':name}),flush=True)
            if args.wait:
                while not p.exists():time.sleep(5)
            else:continue
        expected=shard['lfs']['oid']
        if p.stat().st_size!=shard['size'] or sha(p)!=expected:raise ValueError('Shard integrity mismatch: '+name)
        try:pf=pq.ParquetFile(p)
        except Exception as exc:
            with con:
                con.execute('INSERT OR REPLACE INTO corpus_failures VALUES(?,?,?,?)',(name,expected,type(exc).__name__,'verified_bytes_unreadable_parquet'))
                con.execute('INSERT OR REPLACE INTO corpus_progress VALUES(?,0,-1)',(name,))
            print(json.dumps({'excluded_shard':name,'error_type':type(exc).__name__,'reason_code':'verified_bytes_unreadable_parquet'}),flush=True)
            continue
        offset=0;resume=progress[0] if progress else 0
        for batch in pf.iter_batches(batch_size=128):
            rows=batch.to_pylist()
            with con:
                con.execute('BEGIN IMMEDIATE')
                for i,row in enumerate(rows,offset):
                    if i<resume:continue
                    text=row.get('text')
                    if not isinstance(text,str) or not text.strip():raise ValueError('Invalid body at '+name+':'+str(i))
                    record_id,missing=source_identity(row,manifest['revision'],name,i)
                    add_record(con,text=text,shard=name,shard_sha=expected,record_id=record_id,row_number=i,revision=manifest['revision'])
                    if missing:
                        con.execute('INSERT OR IGNORE INTO corpus_identity VALUES(?,?,?,?,?,?,?)',(name,i,record_id,manifest['revision'],digest(text.encode()),1,IDENTITY_VERSION))
                offset+=len(rows)
                con.execute('INSERT OR REPLACE INTO corpus_progress VALUES(?,?,0)',(name,offset))
            if offset%4096==0:print(json.dumps({'shard':name,'committed_rows':offset,'seconds':round(time.time()-started,1)}),flush=True)
        with con:con.execute('INSERT OR REPLACE INTO corpus_progress VALUES(?,?,1)',(name,offset))
        print(json.dumps({'complete_shard':name,'rows':offset,'seconds':round(time.time()-started,1)}),flush=True)
    con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
def publish(args):
    manifest=json.loads(Path(args.manifest).read_text())
    with closing(sqlite3.connect(args.database,timeout=60)) as con:
        # Keep one read snapshot for manifest, root and backup while builder appends.
        con.execute("INSERT INTO corpus_fts(corpus_fts) VALUES('integrity-check')");con.commit()
        con.execute('BEGIN')
        progress=list(con.execute('SELECT shard,next_row,complete FROM corpus_progress ORDER BY shard'))
        excluded=list(con.execute('SELECT * FROM corpus_failures ORDER BY shard'))
        expected={f['path']:f['lfs']['oid'] for f in manifest['files']}
        verified_excluded={r[0] for r in excluded if r[0] in expected and r[1]==expected[r[0]] and r[3]=='verified_bytes_unreadable_parquet'}
        complete=bool(progress) and any(r[2]==1 for r in progress) and len(progress)==len(expected) and {r[0] for r in progress}==set(expected) and all(r[2]==1 or r[2]==-1 and r[0] in verified_excluded for r in progress)
        if not complete and not args.allow_partial:raise ValueError('Full corpus incomplete; --allow-partial explicitly labels coverage')
        if Path(args.publish).exists():raise ValueError('Publication is immutable; choose a new file')
        root=hashlib.sha256()
        for r in con.execute('SELECT fragment_id,text_hash FROM corpus_chunks ORDER BY id'):root.update(canonical(r).encode()+b'\n')
        data={'version':'industry-corpus-fts-v1','publication_version':'corpus-publication-v2-covered-exclusions','revision':manifest['revision'],'tokenizer':VERSION,
              'query_version':QUERY_VERSION,
              'base_knowledge_version':args.base_knowledge,'chunks_root':root.hexdigest(),'complete':complete,
              'progress':progress,'records':con.execute('SELECT count(*) FROM corpus_records').fetchone()[0],
              'excluded_shards':excluded,'coverage_definition':'all_manifest_shards_accounted_valid_rows_built_verified_unreadable_excluded',
              'chunks':con.execute('SELECT count(*) FROM corpus_chunks').fetchone()[0],
              'duplicates':con.execute('SELECT count(*) FROM corpus_duplicates').fetchone()[0],
              'has_english':any(r[0].startswith('english/') and r[1]>0 and r[2]!=-1 for r in progress),
              'shards':[{'path':x['path'],'sha256':x['lfs']['oid'],'bytes':x['size']} for x in manifest['files'] if any(r[0]==x['path'] for r in progress)]}
        k='kc-'+digest(canonical(data).encode())
        with closing(sqlite3.connect(args.publish)) as dst:
            con.backup(dst);dst.execute('INSERT INTO corpus_seal VALUES(?,?)',(k,canonical(data)));dst.commit()
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Publication integrity failure')
        Path(args.publish+'.manifest.json').write_text(json.dumps({'knowledge_version':k,'database_sha256':sha(args.publish),**data},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'knowledge_version':k,**data},ensure_ascii=False),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--base-knowledge',required=True)
    p.add_argument('--database',required=True);p.add_argument('--manifest',required=True);p.add_argument('--shards',required=True)
    p.add_argument('--wait',action='store_true');p.add_argument('--publish');p.add_argument('--allow-partial',action='store_true')
    p.add_argument('--after-pid',type=int,help='Windows: wait for an existing task-owned builder to exit, then resume; never kill it')
    a=p.parse_args()
    if a.after_pid:
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
        kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x100000,False,a.after_pid)
        if not handle and ctypes.get_last_error() not in (0,87):raise OSError('Cannot safely observe the declared builder process')
        if handle:
            try:
                while kernel.WaitForSingleObject(handle,1000)==258:pass
            finally:kernel.CloseHandle(handle)
    publish(a) if a.publish else build(a)
if __name__=='__main__':main()
