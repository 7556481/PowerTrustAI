"""Read-only recovery admission: exact journal boundaries, input and native files.

Never opens a writer, deletes native files or repairs an uncertain checkpoint.
Orphan/uncommitted files are recorded and left to the original engine lifecycle.
"""
import hashlib
import json
import sqlite3
import struct
import time
import uuid
import zlib
from pathlib import Path

from rag.tantivy_build import atomic, digest, owner, stored_ids
from rag.tantivy_manifest import IndexIdentityError, sha

COMPONENTS = ('idx', 'pos', 'term', 'store', 'fast', 'fieldnorm')


def dead(roster):
    import psutil
    for pid, created in roster.items():
        try:
            if abs(psutil.Process(int(pid)).create_time()-created)<.001:
                raise RuntimeError('Prior owned process still alive: '+str(pid))
        except psutil.NoSuchProcess:
            pass


def component(path, check=lambda: None):
    """Tantivy0.27 Footer::extract_footer: JSON + little-endian length/magic."""
    size=path.stat().st_size
    if size<8:raise IndexIdentityError('Truncated component: '+path.name)
    with path.open('rb') as f:
        f.seek(-8,2);length,magic=struct.unpack('<II',f.read(8))
        if magic!=1337 or length>50000 or length+8>size:
            raise IndexIdentityError('Invalid native footer: '+path.name)
        body_size=size-length-8
        f.seek(body_size);footer=json.loads(f.read(length))
        if footer['version']!={'major':0,'minor':27,'patch':0,'index_format_version':7}:
            raise IndexIdentityError('Native format/version changed')
        f.seek(0);crc=0;h=hashlib.sha256();remaining=body_size
        while remaining:
            check();block=f.read(min(8*1024**2,remaining))
            if not block:raise IndexIdentityError('Native file shortened during audit')
            h.update(block);crc=zlib.crc32(block,crc);remaining-=len(block)
        h.update(f.read())
        if crc!=footer['crc']:raise IndexIdentityError('Native CRC mismatch: '+path.name)
    return {'bytes':size,'sha256':h.hexdigest(),'body_crc32':crc,'format':7}


def boundary(mapped,native,checkpoint,journal):
    if journal is None:
        if mapped!=native or checkpoint['count']!=mapped:
            raise IndexIdentityError('Unjournaled commit boundary mismatch')
        return 'already-mapped',mapped
    start,end=journal['start'],journal['end']
    if not 0<=start<end or len(journal['rows'])!=end-start:
        raise IndexIdentityError('Invalid journal interval')
    if native==mapped==start and checkpoint['count']==start:
        return 'discard-uncommitted-native-buffer-and-offer-journal',start
    if native==end and mapped==start and checkpoint['count']==start:
        return 'roll-forward-mapping-only-no-native-replay',end
    if native==mapped==end and checkpoint['count'] in (start,end):
        return 'finalize-already-mapped-journal-no-native-replay',end
    raise IndexIdentityError('Unknown native/mapping/journal boundary')


def audit(build, identity, spool, output, *, check=lambda: None, source=None):
    import tantivy
    started=time.time();build=Path(build);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with owner(build):
        check();cp=json.loads((build/'checkpoint.json').read_text())
        meta_path=build/'tantivy/meta.json';managed_path=build/'tantivy/.managed.json'
        meta_bytes=meta_path.read_bytes();managed_bytes=managed_path.read_bytes()
        meta=json.loads(meta_bytes);managed=json.loads(managed_bytes)
        expected_schema=[{'name':'terms','type':'text','options':{'indexing':{'record':'position','fieldnorms':True,'tokenizer':'existing_terms'},'stored':False,'fast':False}}, {'name':'rowid','type':'i64','options':{'indexed':False,'fieldnorms':False,'fast':True,'stored':True}}]
        if meta['schema']!=expected_schema or cp['identity']!=digest(identity):
            raise IndexIdentityError('Source/schema identity changed')
        if not isinstance(managed,list) or any(not isinstance(x,str) or Path(x).name!=x for x in managed):
            raise IndexIdentityError('Unsafe managed file list')
        if len(set(managed))!=len(managed):raise IndexIdentityError('Duplicate managed registration')
        required=set();files={}
        for segment in meta['segments']:
            if segment.get('deletes'):raise IndexIdentityError('Unexpected deleted members')
            sid=uuid.UUID(segment['segment_id']).hex
            for suffix in COMPONENTS:
                name=sid+'.'+suffix;required.add(name)
                if name not in managed:raise IndexIdentityError('Committed file not registered: '+name)
                files[name]=component(build/'tantivy'/name,check)
        check();con=sqlite3.connect((build/'mapping.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
        sp=sqlite3.connect(Path(spool).resolve().as_uri()+'?mode=ro',uri=True)
        seen_path=output.with_name(output.stem+'-seen.sqlite3')
        seen=sqlite3.connect(seen_path.resolve().as_uri(),uri=True);src=None
        try:
            con.execute('pragma cache_size=-8192');sp.execute('pragma cache_size=-4096')
            con.set_progress_handler(lambda:(check() or 0),10000)
            if con.execute('pragma quick_check').fetchall()!=[('ok',)]:raise IndexIdentityError('Mapping database integrity failure')
            if sp.execute('select identity from meta').fetchone()!=(digest(identity),):raise IndexIdentityError('Input spool identity changed')
            if source:
                src=sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True)
            journal_path=build/'prepared.json'
            journal=json.loads(journal_path.read_text()) if journal_path.exists() else None
            if journal and (journal['identity']!=digest(identity) or digest(journal['rows'])!=journal['payload_hash']):
                raise IndexIdentityError('Journal payload identity changed')
            mapped=con.execute('select count(*) from rows').fetchone()[0]
            native=sum(s['max_doc'] for s in meta['segments'])
            action,committed=boundary(mapped,native,cp,journal)
            if native>identity['expected']:raise IndexIdentityError('Native count outside frozen scope')
            end=max(mapped,journal['end'] if journal else mapped)
            inputs=iter(sp.execute('select * from input where position<? order by position',(end,)))
            mapping=iter(con.execute('select * from rows order by position'));h=hashlib.sha256();prefixes={0:h.hexdigest()}
            for pos in range(end):
                if pos%1000==0:check()
                row=next(inputs,None)
                if row is None or row[0]!=pos or row[1]!=(-(pos+1) if pos<674 else pos-674+1) or hashlib.sha256(row[-1].encode()).hexdigest()!=row[-2]:
                    raise IndexIdentityError('Input namespace/order/terms changed')
                if pos<mapped and tuple(row[:5])!=next(mapping,None):raise IndexIdentityError('Mapping differs from input')
                if journal and journal['start']<=pos<journal['end'] and list(row[:5])!=journal['rows'][pos-journal['start']]:
                    raise IndexIdentityError('Journal differs from input')
                if src and row[1]>0 and src.execute('select fragment_id,text_hash from corpus_chunks where id=?',(row[1],)).fetchone()!=tuple(row[2:4]):
                    raise IndexIdentityError('Input source fragment/body binding changed')
                h.update(json.dumps(row[:5]).encode())
                if pos+1 in (cp['count'],mapped,native):prefixes[pos+1]=h.hexdigest()
            if prefixes.get(cp['count'])!=cp['mapping_hash']:raise IndexIdentityError('Checkpoint input prefix digest changed')
            if cp['count']==native and cp['opstamp']!=meta['opstamp']:raise IndexIdentityError('Native checkpoint opstamp changed')
            if cp['count']<native and meta['opstamp']<=cp['opstamp']:raise IndexIdentityError('Journal commit lacks newer opstamp')
            seen.execute('pragma cache_size=-8192');seen.execute('create table seen(rowid integer primary key)')
            seen.execute('attach database ? as mapped',((build/'mapping.sqlite3').resolve().as_uri()+'?mode=ro',))
            seen.execute('create table extra(rowid integer primary key)')
            if journal and native>mapped:seen.executemany('insert into extra values(?)',((r[1],) for r in journal['rows']))
            index=tantivy.Index.open(str(build/'tantivy'));batch=[];n=0
            for rid in stored_ids(index,build/'tantivy'):
                batch.append((rid,));n+=1
                if len(batch)==5000:check();seen.executemany('insert into seen values(?)',batch);seen.commit();batch=[]
            if batch:seen.executemany('insert into seen values(?)',batch);seen.commit()
            seen.set_progress_handler(lambda: (check() or 0),10000)
            if n!=native:raise IndexIdentityError('Native metadata/stored IDs disagree')
            if seen.execute('select rowid from seen except select rowid from mapped.rows except select rowid from extra limit 1').fetchone():
                raise IndexIdentityError('Unknown native member')
            if seen.execute('select rowid from mapped.rows except select rowid from seen limit 1').fetchone():raise IndexIdentityError('Missing committed member')
            check()
            if meta_path.read_bytes()!=meta_bytes or managed_path.read_bytes()!=managed_bytes:raise IndexIdentityError('Native metadata changed during read-only audit')
            proof={'version':'bounded-recovery-v10','passed':True,'action':action,'mapped':mapped,'native_committed':committed,'checkpoint':cp,'journal':journal,
                'input_prefix_hashes':prefixes,'required_files':files,'meta_sha256':hashlib.sha256(meta_bytes).hexdigest(),'managed_sha256':hashlib.sha256(managed_bytes).hexdigest(),
                'mapping_file_sha256':sha(build/'mapping.sqlite3',check),'journal_sha256':sha(journal_path,check) if journal else None,
                'uncommitted_registrations':sorted(set(managed)-required-{'meta.json'}),'unique_all_ids_equal_bound_input':True,
                'terms_storage_limit':'terms not stored natively; all input terms hashes/bindings and committed component CRCs checked, not inverted-index reconstruction',
                'wall':time.time(),'seconds':time.time()-started,'models':0}
            atomic(output,proof);return proof
        finally:
            con.close();sp.close();seen.close()
            if src:src.close()


def classify(events, primary, native_root):
    """Direct trace only; generic worker text is never sufficient."""
    root=str(Path(native_root).resolve()).replace('/','\\').casefold().rstrip('\\')
    def path(p):return p.removeprefix('\\\\?\\').replace('/','\\').casefold()
    failures=[e for e in events if e.get('failed') and e.get('winerror') not in (2,3,18,38,183)]
    hits=[e for e in failures if e.get('operation')=='MoveFileExW' and e.get('winerror')==5 and path(e.get('to',''))==root+'\\.managed.json' and path(e.get('path','')).startswith(root+'\\.tmp')]
    if not hits or not primary or 'ValueError' not in primary:raise RuntimeError('Failure is not an identified metadata replacement error')
    first=hits[0]
    if any(e not in hits and not (e.get('winerror')==5 and e.get('operation') in ('NtSetInformationFile','SetFileInformationByHandle') and abs(e.get('wall_ms',0)-first['wall_ms'])<=20) for e in failures):
        raise RuntimeError('Additional native error requires inspection')
    return {'kind':'identified-managed-atomic-replace-win5','first':first,'primary':primary,'root':root}


def admit_recovery(state, committed, deadline, reason):
    if time.time()>=deadline:raise TimeoutError('Original96h deadline expired')
    entries=state['entries']
    if len(entries)>=3:raise RuntimeError('Three formal fault recoveries exhausted')
    if entries and committed<=entries[-1]['before_committed']:
        raise RuntimeError('No successful commit between consecutive recoveries')
    entry={'number':len(entries)+1,'before_committed':committed,'reason':reason,'admitted':time.time(),'state':'admitted-no-writer-yet'}
    entries.append(entry);return entry


if __name__=='__main__':
    import sys
    from evaluation.tantivy_supervision_v3 import Guard
    g=Guard(sys.argv[1]);p=g.plan
    for roster in p.get('prior_rosters',[]):dead(json.loads(Path(roster).read_text()))
    audit(Path(p['audit_build']),json.loads(Path(p['build_identity']).read_text()),p['audit_spool'],p['audit_output'],check=lambda:g.check('checkpoint recovery audit'),source=p.get('audit_source'))
