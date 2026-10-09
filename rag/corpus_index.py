"""Resumable immutable-publication FTS corpus, retaining native Evidence contracts.

Build database is never served. Publication is a SQLite backup plus a content seal.
Corpus row provenance locates an exact record/character span in a verified shard.
"""
import hashlib,json,sqlite3
from pathlib import Path
from dataclasses import replace
from core.models import Evidence,EvidenceProvenance
from core.validation import require,validate_types
from rag.storage import canonical,digest
from rag.chinese_terms import VERSION,terms,query_expression
from rag.contracts import RetrievalRequest,RetrievalResult,RetrievalHit
from rag.timing import span,timed
SCORING='sqlite-fts5-bm25-jieba-electric-semantic-query-v2'
_OPENED={}
SCHEMA='''
CREATE TABLE IF NOT EXISTS corpus_identity(shard TEXT,row_number INTEGER,internal_id TEXT NOT NULL,revision TEXT NOT NULL,body_sha256 TEXT NOT NULL,original_id_missing INTEGER NOT NULL,identity_version TEXT NOT NULL,PRIMARY KEY(shard,row_number));
CREATE TABLE IF NOT EXISTS corpus_records(id INTEGER PRIMARY KEY, text_hash TEXT UNIQUE NOT NULL,
 raw_text TEXT NOT NULL, shard TEXT NOT NULL, shard_sha TEXT NOT NULL, record_id TEXT NOT NULL,
 row_number INTEGER NOT NULL, revision TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_duplicates(shard TEXT,row_number INTEGER,record_id TEXT,canonical_id INTEGER,
 PRIMARY KEY(shard,row_number));
CREATE TABLE IF NOT EXISTS corpus_chunks(id INTEGER PRIMARY KEY,record_id INTEGER NOT NULL,
 start INTEGER NOT NULL,end INTEGER NOT NULL,text_hash TEXT NOT NULL,fragment_id TEXT UNIQUE NOT NULL);
CREATE INDEX IF NOT EXISTS corpus_chunk_record ON corpus_chunks(record_id,start);
CREATE VIRTUAL TABLE IF NOT EXISTS corpus_fts USING fts5(terms,content='');
CREATE TABLE IF NOT EXISTS corpus_progress(shard TEXT PRIMARY KEY,next_row INTEGER NOT NULL,complete INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_failures(shard TEXT PRIMARY KEY,sha256 TEXT NOT NULL,error_type TEXT NOT NULL,reason_code TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_native(id INTEGER PRIMARY KEY,fragment_id TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_seal(knowledge_version TEXT PRIMARY KEY,manifest TEXT NOT NULL);
'''
def exists(store):
    return store.connection.execute("SELECT 1 FROM sqlite_master WHERE name='corpus_seal'").fetchone() is not None
@timed('immutable_seal')
def seal(store,k):
    if not exists(store):return None
    r=store.connection.execute('SELECT manifest FROM corpus_seal WHERE knowledge_version=?',(k,)).fetchone()
    if not r:return None
    value=json.loads(r[0]);require(k=='kc-'+digest(canonical(value).encode()),'Corpus seal identity mismatch')
    require(value['tokenizer']==VERSION,'Corpus tokenizer mismatch')
    if store._readonly:
        stat=store._path.stat();stamp=(stat.st_size,stat.st_mtime_ns)
        key=(str(store._path),k)
        if key in _OPENED:require(_OPENED[key]==stamp,'Published corpus changed; explicit revalidation/republication required')
        else:
            # Publisher's byte seal binds the complete FTS and body database,
            # checked once per process/open identity, never for every query.
            published=value.get('version')=='industry-corpus-fts-v1'
            if published:
                sidecar=json.loads(Path(str(store._path)+'.manifest.json').read_text(encoding='utf-8'))
                require(sidecar.get('knowledge_version')==k and type(sidecar.get('database_sha256')) is str,'Published database byte seal required')
                require({name:v for name,v in sidecar.items() if name not in ('knowledge_version','database_sha256')}==value,'Published manifest differs from database seal')
                h=hashlib.sha256()
                with store._path.open('rb') as f:
                    for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
                require(h.hexdigest()==sidecar['database_sha256'],'Published FTS/body byte seal mismatch')
                require((store._path.stat().st_size,store._path.stat().st_mtime_ns)==stamp,'Corpus changed during open validation')
            # Publication already checked SQLite/FTS integrity and membership.
            # An exact whole-file byte seal binds those checks; scanning again
            # adds no protection against a changed body/index. Unpublished test
            # fixtures still receive the direct SQLite checks below.
            if not published:
                require(store.connection.execute('PRAGMA quick_check').fetchone()[0]=='ok','Corpus SQLite integrity failure')
            if not published and 'chunks' in value:
                require(store.connection.execute('SELECT count(*) FROM corpus_chunks').fetchone()[0]==value['chunks'],'Corpus sealed chunk count mismatch')
                require(store.connection.execute('SELECT count(*) FROM corpus_records').fetchone()[0]==value['records'],'Corpus sealed record count mismatch')
                indexed=store.connection.execute('SELECT count(*) FROM corpus_fts').fetchone()[0]
                native=store.connection.execute('SELECT count(*) FROM corpus_native').fetchone()[0]
                require(indexed==value['chunks']+native,'Corpus index/content membership mismatch')
            _OPENED[key]=stamp
    return value
def chunks(text,max_chars=1200):
    start=0
    while start<len(text):
        end=min(start+max_chars,len(text))
        if end<len(text):
            candidates=[text.rfind(c,start+max_chars//2,end) for c in ('。','\n','. ','！','？')]
            boundary=max(candidates)
            if boundary>=0:end=boundary+1
        yield start,end
        start=end
def add_record(con,*,text,shard,shard_sha,record_id,row_number,revision):
    h=digest(text.encode());old=con.execute('SELECT id FROM corpus_records WHERE text_hash=?',(h,)).fetchone()
    if old:
        con.execute('INSERT OR IGNORE INTO corpus_duplicates VALUES(?,?,?,?)',(shard,row_number,str(record_id),old[0]));return False
    rid=con.execute('INSERT INTO corpus_records(text_hash,raw_text,shard,shard_sha,record_id,row_number,revision) VALUES(?,?,?,?,?,?,?)',
        (h,text,shard,shard_sha,str(record_id),row_number,revision)).lastrowid
    for start,end in chunks(text):
        body=text[start:end];fid='fc-'+digest(canonical([revision,shard,shard_sha,row_number,str(record_id),h,start,end]).encode())
        cid=con.execute('INSERT INTO corpus_chunks(record_id,start,end,text_hash,fragment_id) VALUES(?,?,?,?,?)',(rid,start,end,digest(body.encode()),fid)).lastrowid
        con.execute('INSERT INTO corpus_fts(rowid,terms) VALUES(?,?)',(cid,' '.join(terms(body))))
    return True
def corpus_evidence(store,fid,k,s):
    con=store.connection
    native=con.execute('SELECT 1 FROM corpus_native WHERE fragment_id=?',(fid,)).fetchone()
    if native:
        original=store.evidence(fid,s['base_knowledge_version'])
        return replace(original,evidence_id='e-'+digest(canonical([k,fid]).encode()),
                       provenance=replace(original.provenance,knowledge_version=k))
    row=con.execute('SELECT c.*,r.raw_text,r.shard,r.shard_sha,r.record_id AS original_id,r.row_number,r.revision,r.text_hash AS record_hash FROM corpus_chunks c JOIN corpus_records r ON r.id=c.record_id WHERE fragment_id=?',(fid,)).fetchone()
    require(row is not None,'Unknown corpus fragment')
    text=row['raw_text'][row['start']:row['end']]
    require(digest(row['raw_text'].encode())==row['record_hash'] and digest(text.encode())==row['text_hash'],'Corpus original/span hash mismatch')
    expected='fc-'+digest(canonical([row['revision'],row['shard'],row['shard_sha'],row['row_number'],row['original_id'],row['record_hash'],row['start'],row['end']]).encode())
    require(fid==expected,'Corpus record/fragment identity mismatch')
    doc='dataset-record-'+digest(canonical([row['revision'],row['shard'],row['row_number'],row['original_id']]).encode())
    neighbors=con.execute('SELECT fragment_id,start FROM corpus_chunks WHERE record_id=? ORDER BY start',(row['record_id'],)).fetchall()
    pos=next(i for i,r in enumerate(neighbors) if r['fragment_id']==fid)
    url='https://huggingface.co/datasets/BAAI/IndustryCorpus2_electric_power_energy/blob/'+row['revision']+'/'+row['shard']
    missing_identity=con.execute("SELECT 1 FROM sqlite_master WHERE name='corpus_identity'").fetchone() and con.execute('SELECT original_id_missing FROM corpus_identity WHERE shard=? AND row_number=?',(row['shard'],row['row_number'])).fetchone()
    identity_warning=('original_id_missing','stable_internal_row_identity') if missing_identity else ()
    p=EvidenceProvenance(doc,row['record_hash'],row['shard_sha'],fid,k,row['start'],row['end'],
        row['raw_text'][:row['start']].count('\n')+1,row['raw_text'][:row['end']].count('\n')+1,
        source_uri=url,document_title='IndustryCorpus2 record '+row['original_id'],
        parser_version='parquet-record-character-v1',text_basis='dataset_record_original_text',
        previous_fragment_id=neighbors[pos-1]['fragment_id'] if pos else None,
        next_fragment_id=neighbors[pos+1]['fragment_id'] if pos+1<len(neighbors) else None,
        quality_status='original_source_unverified',quality_warnings=('original_publisher_url_date_unknown','not_sole_authority_for_normative_settings_or_engineering_guarantees')+identity_warning)
    locator=f"shard={row['shard']};row={row['row_number']};record={row['original_id']};chars[{row['start']}:{row['end']})"
    return Evidence('e-'+digest(canonical([k,fid]).encode()),doc,row['record_hash'],locator,text,'industry_corpus_unverified',
        ('RAG explanation coverage; original source unverified; not sole normative/engineering authority',),p)
class CorpusRetriever:
    def __init__(self,store,*,query_version=None,rank_cache=None):
        self.store=store;self.query_version=query_version;self.rank_cache=rank_cache
    @timed('corpus_retrieve')
    def _retrieve(self,request):
        with span('query_prepare'):
            validate_types(request,RetrievalRequest);require(request.max_results>0,'Positive result count required')
            s=seal(self.store,request.knowledge_version);require(s is not None,'Sealed corpus required')
            if self.query_version=='topic-subject-and-bm25-v1':
                from rag.topic_lanes import plan
                expression=canonical(plan(request.query))
            else:expression=query_expression(request.query,self.query_version or s.get('query_version','electric-topic-query-v1'))
        if not expression:return RetrievalResult((),request.knowledge_version)
        con=self.store.connection
        with span('fts_execute_fetch_sort') as measured:
            key=(str(self.store._path),request.knowledge_version,self.store._path.stat().st_size,self.store._path.stat().st_mtime_ns,self.query_version,expression,request.max_results)
            ranked=None if self.rank_cache is None else self.rank_cache.get(key)
            measured['rank_cache_hit']=ranked is not None
            if ranked is None:
                if self.query_version=='topic-subject-and-bm25-v1':
                    from rag.topic_lanes import rank as lane_rank
                    ranked=lane_rank(con,request.query,request.max_results)
                else:
                    ranked=con.execute('SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?',
                        (expression,request.max_results)).fetchall()
                if self.rank_cache is not None:self.rank_cache.put(key,ranked)
            measured['result_count']=len(ranked)
        evidence=[];hits=[]
        with span('body_evidence_construct') as measured:
            for rank,row in enumerate(ranked,1):
                if row['rowid']<0:fid=con.execute('SELECT fragment_id FROM corpus_native WHERE id=?',(-row['rowid'],)).fetchone()[0]
                else:fid=con.execute('SELECT fragment_id FROM corpus_chunks WHERE id=?',(row['rowid'],)).fetchone()[0]
                e=corpus_evidence(self.store,fid,request.knowledge_version,s);evidence.append(e)
                scoring='fts-subject-constrained-bm25-v1' if self.query_version=='topic-subject-and-bm25-v1' else SCORING if self.query_version is None else SCORING+';'+self.query_version
                hits.append(RetrievalHit(e.evidence_id,fid,rank,-row['score'],scoring))
            measured['body_count']=len(evidence)
        context=None
        if request.context_options is not None:
            from rag.context import read_adjacent_context
            with span('adjacent_context'):
                context=read_adjacent_context(self.store,tuple(evidence),request.knowledge_version,request.context_options)
        return RetrievalResult(tuple(evidence),request.knowledge_version,hits=tuple(hits),context=context)
    def _validate_result(self,request,result):
        require(result==self._retrieve(request),'Corpus result differs from immutable FTS index')
