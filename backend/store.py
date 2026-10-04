"""Short SQLite transactions, one event-loop thread, append-only stage/review data."""
from contextlib import contextmanager
from datetime import datetime,timezone
import json
import sqlite3
from uuid import uuid4
from backend.serialization import dumps,wire,SCHEMA_VERSION

def now():return datetime.now(timezone.utc).isoformat()

class StorageError(RuntimeError):
    code='RUN_STORAGE_FAILED'

class BindingError(ValueError):pass

def read_boundary(function):
    def wrapped(self,*args,**kwargs):
        try:return function(self,*args,**kwargs)
        except sqlite3.Error:raise StorageError('Run database unavailable') from None
    return wrapped

class RunStore:
    def __init__(self,path):
        self.path=path
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            self.db=sqlite3.connect(path,timeout=2)
            self.db.row_factory=sqlite3.Row
            self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA journal_mode=WAL')
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,status TEXT NOT NULL,created TEXT NOT NULL,
              started TEXT,ended TEXT,request TEXT NOT NULL,config TEXT NOT NULL,snapshot TEXT,result TEXT,
              error_code TEXT,cancel_requested INTEGER NOT NULL DEFAULT 0,harness_state TEXT);
            CREATE TABLE IF NOT EXISTS events(run_id TEXT NOT NULL REFERENCES runs,id TEXT NOT NULL,
              ordinal INTEGER NOT NULL,payload TEXT NOT NULL,stage_output TEXT,PRIMARY KEY(run_id,id));
            CREATE TABLE IF NOT EXISTS objects(run_id TEXT NOT NULL REFERENCES runs,kind TEXT NOT NULL,
              id TEXT NOT NULL,answer_id TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 0,
              payload TEXT NOT NULL,PRIMARY KEY(run_id,kind,id,answer_id,version));
            CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs,
              created TEXT NOT NULL,payload TEXT NOT NULL);
            ''')
            with self.tx():
                self.db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)',('schema_version',SCHEMA_VERSION))
                if self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]!=SCHEMA_VERSION:
                    raise StorageError('Unsupported run database schema')
        except (sqlite3.Error,OSError):raise StorageError('Run database unavailable') from None

    @contextmanager
    def tx(self):
        try:
            self.db.execute('BEGIN IMMEDIATE');yield;self.db.commit()
        except BaseException as exc:
            self.db.rollback()
            if isinstance(exc,sqlite3.Error):raise StorageError('Run transaction failed') from None
            raise

    def recover(self):
        with self.tx():
            self.db.execute("UPDATE runs SET status='interrupted',ended=?,error_code='PROCESS_INTERRUPTED' WHERE status IN ('queued','running')",(now(),))

    def create(self,rid,request,config):
        with self.tx():
            self.db.execute('INSERT INTO runs(id,status,created,request,config) VALUES (?,?,?,?,?)',
                (rid,'queued',now(),dumps(request),dumps(config)))
            self.index(rid,request)

    def index(self,rid,value):
        def visit(v):
            if isinstance(v,list):
                for item in v:visit(item)
            elif isinstance(v,dict):
                kind=None;ident=None;aid=v.get('answer_id','');version=v.get('answer_version',v.get('version',0))
                if 'answer_id' in v and 'text' in v and 'version' in v:kind='answer';ident=v['answer_id']
                elif 'evidence_id' in v and 'text' in v and 'source_id' in v:kind='evidence';ident=v['evidence_id'];aid='';version=0
                elif 'finding_id' in v:kind='finding';ident=v['finding_id']
                elif 'claim_id' in v and 'text' in v and 'answer_version' in v:kind='claim';ident=v['claim_id']
                elif 'result_id' in v and 'tool_name' in v:kind='tool';ident=v['result_id'];aid='';version=0
                if kind:
                    encoded=dumps(v)
                    old=self.db.execute('SELECT payload FROM objects WHERE run_id=? AND kind=? AND id=? AND answer_id=? AND version=?',(rid,kind,ident,aid,version)).fetchone()
                    # findings can progress from an explicit unexecuted placeholder; keep events immutable
                    if old and old[0]!=encoded and kind in ('answer','evidence','claim','tool'):
                        raise BindingError('Immutable object binding conflict')
                    self.db.execute('INSERT OR REPLACE INTO objects VALUES (?,?,?,?,?,?)',(rid,kind,ident,aid,version,encoded))
                for item in v.values():visit(item)
        visit(wire(value))

    def checkpoint(self,rid,snapshot):
        v=wire(snapshot);event=v['event']
        with self.tx():
            ordinal=self.db.execute('SELECT COUNT(*) FROM events WHERE run_id=?',(rid,)).fetchone()[0]+1
            self.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(rid,event['event_id'],ordinal,dumps(event),dumps(v.get('stage_output'))))
            self.db.execute('UPDATE runs SET snapshot=?,harness_state=? WHERE id=?',(dumps(v),v['state'],rid))
            # Bind domain finding IDs to this frozen answer; domain findings already have explicit bindings.
            self.index(rid,v)
            if v.get('stage_output') and event['component']=='evidence_verification':
                answer=v['stage_output'];aid=answer['answer_id'];version=answer['answer_version']
                for f in answer['findings']:
                    self.index(rid,dict(f,answer_id=aid,answer_version=version))

    def mark(self,rid,status,*,error_code=None,result=None):
        with self.tx():
            if status=='running':self.db.execute('UPDATE runs SET status=?,started=? WHERE id=?',(status,now(),rid))
            else:
                self.db.execute('UPDATE runs SET status=?,ended=?,error_code=?,result=? WHERE id=?',
                    (status,now(),error_code,None if result is None else dumps(result),rid))
            if result is not None:self.index(rid,result)

    def cancellation(self,rid):
        with self.tx():self.db.execute('UPDATE runs SET cancel_requested=1 WHERE id=?',(rid,))

    def get(self,rid):
        try:row=self.db.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
        except sqlite3.Error:raise StorageError('Run database unavailable') from None
        if row is None:raise KeyError(rid)
        result=dict(row)
        for key in ('request','config','snapshot','result'):result[key]=None if result[key] is None else json.loads(result[key])
        return result

    @read_boundary
    def list_runs(self,offset=0,limit=20):
        rows=self.db.execute('SELECT id,status,created,request,config FROM runs ORDER BY created DESC,id DESC LIMIT ? OFFSET ?',
                             (limit+1,offset)).fetchall()
        items=[{'run_id':r['id'],'status':r['status'],'created_utc':r['created'],
                'mode':json.loads(r['request'])['mode'],'profile':json.loads(r['config'])['profile']} for r in rows[:limit]]
        return {'items':items,'offset':offset,'next_offset':offset+limit if len(rows)>limit else None}

    @read_boundary
    def events(self,rid):
        self.get(rid)
        return [{'event':json.loads(r['payload']),'stage_output':json.loads(r['stage_output']) if r['stage_output'] else None} for r in self.db.execute('SELECT * FROM events WHERE run_id=? ORDER BY ordinal',(rid,))]

    @read_boundary
    def objects(self,rid,kind):
        self.get(rid)
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM objects WHERE run_id=? AND kind=? ORDER BY version,id',(rid,kind))]

    @read_boundary
    def evidence(self,rid,eid):
        self.get(rid)
        row=self.db.execute("SELECT payload FROM objects WHERE run_id=? AND kind='evidence' AND id=?",(rid,eid)).fetchone()
        if row is None:raise KeyError(eid)
        return json.loads(row[0])

    def add_review(self,rid,payload):
        self.get(rid);aid=payload['answer_id'];version=payload['answer_version'];fid=payload.get('finding_id')
        with self.tx():
            if not self.db.execute("SELECT 1 FROM objects WHERE run_id=? AND kind='answer' AND id=? AND version=?",(rid,aid,version)).fetchone():
                raise BindingError('Answer/version not associated with this run')
            if fid and not self.db.execute("SELECT 1 FROM objects WHERE run_id=? AND kind='finding' AND id=? AND answer_id=? AND version=?",(rid,fid,aid,version)).fetchone():
                raise BindingError('Finding not associated with this answer/version')
            value=dict(payload,review_id=uuid4().hex,run_id=rid,created_utc=now(),identity_status='local_user_not_authenticated_expert',affects_model_decision=False)
            self.db.execute('INSERT INTO reviews VALUES (?,?,?,?)',(value['review_id'],rid,value['created_utc'],dumps(value)))
        return value

    @read_boundary
    def reviews(self,rid):
        self.get(rid)
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM reviews WHERE run_id=? ORDER BY created,id',(rid,))]

    def healthy(self):
        try:return self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]==SCHEMA_VERSION
        except (sqlite3.Error,TypeError):return False

    def close(self):self.db.close()

