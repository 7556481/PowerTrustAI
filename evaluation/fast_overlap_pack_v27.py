"""Small self-contained native index prototype, not a full-corpus build."""
import collections,hashlib,json,math,sys,time
from pathlib import Path
from dataclasses import replace
from evaluation.fast_overlap_v27 import HOME,select,enable_v18
from evaluation.archive_replay import restore
from backend.serialization import wire
from core.models import Evidence
from rag.context import read_adjacent_context
from rag.contracts import ContextOptions

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
 return h.hexdigest()

class PackedCatalog:
 def __init__(self,root):
  import tantivy
  self.root=Path(root);self.manifest=read(self.root/'asset.json');self.k=self.manifest['knowledge_version']
  for name,expected in self.manifest['files'].items():assert sha(self.root/'index'/name)==expected
  self.index=tantivy.Index.open(str(self.root/'index'));self.index.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());self.searcher=self.index.searcher();self.cache={}
 def decode(self,document):
  payload=json.loads(bytes(document['payload'][0]).decode());terms=document['terms'][0]
  assert hashlib.sha256(terms.encode()).hexdigest()==payload['terms_sha']
  evidence=restore(payload['evidence'],Evidence);assert hashlib.sha256(evidence.text.encode()).hexdigest()==payload['body_sha']
  return evidence,terms
 def evidence(self,fid,k):
  import tantivy
  assert k==self.k
  if fid not in self.cache:
   hits=self.searcher.search(tantivy.Query.term_query(self.index.schema,'fid',fid),limit=2).hits;assert len(hits)==1
   self.cache[fid]=self.decode(self.searcher.doc(hits[0][1]))[0]
  return self.cache[fid]
 def verify_evidence(self,evidence):
  assert self.evidence(evidence.provenance.fragment_id,evidence.provenance.knowledge_version)==evidence
  return evidence
 def retrieve(self,text):
  enable_v18()
  from rag.topic_lanes import plan
  from rag.tantivy_query import ast,query
  from rag.tantivy_global_rank_v18 import positive
  tree=ast(plan(text)[0][1]);hits=self.searcher.search(query(self.index,tree),limit=6,count=False).hits;targets=set(positive(tree));count=self.searcher.num_docs
  weights={t:math.log(1+(count-self.searcher.doc_freq('terms',t)+.5)/(self.searcher.doc_freq('terms',t)+.5)) for t in targets};ranked=[]
  for _,address in hits:
   evidence,terms=self.decode(self.searcher.doc(address));tf=collections.Counter(terms.split());score=sum(w*tf[t]/(tf[t]+1) for t,w in weights.items() if tf[t]);ranked.append((score,evidence))
  ranked.sort(key=lambda row:(-row[0],row[1].evidence_id));selected,trace=select(text,tuple(e for _,e in ranked));context=read_adjacent_context(self,selected,self.k,ContextOptions());return selected,context,trace


def build():
 import tantivy,sqlite3
 from evaluation.fast_overlap_replay_v27 import SourceCatalog,SOURCE
 root=HOME/'single-asset-sample-v4';root.mkdir(exist_ok=False);index_root=root/'index';index_root.mkdir();catalog=SourceCatalog();data=read(HOME/'frozen56-candidate-results.json');evidence={}
 for row in data:
  for value in row['result']['evidence']:evidence[value['evidence_id']]=restore(value,Evidence)
 materials=read(Path('D:/PowerTrustAI/data/retrieval_local/tantivy-query-repair-v18/delivery-replay.json'))
 for item in materials['results']:
  for value in item['roots']:evidence[value['evidence_id']]=restore(value,Evidence)
 sources={}
 for e in evidence.values():sources.setdefault(e.source_id,e)
 order=lambda e:hashlib.sha256(e.source_id.encode()).hexdigest()
 native=sorted((e for e in sources.values() if e.provenance.text_basis!='dataset_record_original_text'),key=order)[:2]
 corpus=sorted((e for e in sources.values() if e.provenance.text_basis=='dataset_record_original_text'),key=order)[:6]
 chosen=native+corpus
 for value in data[0]['result']['evidence']:
  e=restore(value,Evidence)
  if all(e.source_id!=x.source_id for x in chosen):chosen.append(e)
 members={}
 for core in chosen:
  if core in native:
   rows=catalog.connection.execute('select fragment_id from fragments where document_id=? and version=?',(core.provenance.document_id,core.provenance.document_version)).fetchall()
  else:
   rid=catalog.connection.execute('select record_id from corpus_chunks where fragment_id=?',(core.provenance.fragment_id,)).fetchone()[0];rows=catalog.connection.execute('select fragment_id from corpus_chunks where record_id=?',(rid,)).fetchall()
  for row in rows:
   e=catalog.evidence(row[0],core.provenance.knowledge_version);members[e.provenance.fragment_id]=e
 builder=tantivy.SchemaBuilder();builder.add_integer_field('rowid',stored=True,indexed=True);builder.add_text_field('fid',stored=True,tokenizer_name='raw',index_option='basic');builder.add_text_field('terms',stored=True,tokenizer_name='existing_terms',index_option='position');builder.add_bytes_field('payload',stored=True)
 index=tantivy.Index(builder.build(),path=str(index_root));index.register_tokenizer('existing_terms',tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.whitespace()).build());writer=index.writer(heap_size=20000000,num_threads=1)
 spool=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1/spool.sqlite3');db=sqlite3.connect(spool.as_uri()+'?mode=ro',uri=True);body_bytes=terms_bytes=payload_bytes=0;expected=[]
 try:
  for fid,e in sorted(members.items()):
   nr=catalog.connection.execute('select id from corpus_native where fragment_id=?',(fid,)).fetchone()
   rid=-nr[0] if nr else catalog.connection.execute('select id from corpus_chunks where fragment_id=?',(fid,)).fetchone()[0]
   position=-rid-1 if rid<0 else rid+673
   row=db.execute('select * from input where position=?',(position,)).fetchone();assert row[1]==rid and row[2]==fid and row[3]==hashlib.sha256(e.text.encode()).hexdigest();assert hashlib.sha256(row[5].encode()).hexdigest()==row[4]
   payload=json.dumps({'evidence':wire(e),'terms_sha':row[4],'body_sha':row[3]},ensure_ascii=False,separators=(',',':')).encode();document=tantivy.Document();document.add_integer('rowid',rid);document.add_text('fid',fid);document.add_text('terms',row[5]);document.add_bytes('payload',payload);writer.add_document(document)
   body_bytes+=len(e.text.encode());terms_bytes+=len(row[5].encode());payload_bytes+=len(payload)
   if len(expected)<3:expected.append({'fragment_id':fid,'evidence_id':e.evidence_id,'payload_sha256':hashlib.sha256(json.dumps(wire(e),sort_keys=True,ensure_ascii=False).encode()).hexdigest()})
  writer.commit();writer.wait_merging_threads();index.reload()
 finally:db.close();catalog.close()
 files={p.name:sha(p) for p in index_root.iterdir() if p.is_file() and not p.name.endswith('.lock')}
 k=next(iter(members.values())).provenance.knowledge_version;freeze=read(HOME.parent/'tantivy-delivery-replay-v20/freeze.json');probe_query=freeze['requests'][0]['query']
 manifest=dict(version='self-contained-native-sample-v27',knowledge_version=k,members=len(members),documents=len(chosen),native_documents=len(native),source_bodies_utf8=body_bytes,terms_utf8=terms_bytes,payload_utf8=payload_bytes,index_bytes=sum(p.stat().st_size for p in index_root.iterdir() if p.is_file()),files=files,legacy_examples=expected,probe_query=probe_query,runtime_dependencies=['this asset directory','same installed Python/Tantivy/jieba runtime'],forbidden_runtime=['old SQLite knowledge/FTS','frozen spool','build export'])
 (root/'asset.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','legacy_examples','probe_query')},ensure_ascii=False))


def probe():
 import sqlite3,os
 root=HOME/'single-asset-sample-v4';denied=[]
 def unavailable(*a,**kw):denied.append('sqlite3.connect');raise PermissionError('Old source and frozen spool unavailable in isolated runtime')
 sqlite3.connect=unavailable
 def guard(event,args):
  if event=='open' and args and isinstance(args[0],str):
   path=str(Path(args[0]).absolute()).replace('\\','/').lower()
   if '/data/retrieval_local/' in path or path.endswith('.sqlite3'):
    denied.append(path);raise PermissionError('Old source/spool path unavailable')
  if event=='socket.connect':raise PermissionError('No network in zero-model asset probe')
 sys.addaudithook(guard)
 # Assert the old SQLite paths really fail in this process before native loading.
 for forbidden in ('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3','D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1/spool.sqlite3'):
  try:sqlite3.connect(forbidden);raise AssertionError('Forbidden store opened')
  except PermissionError:pass
 catalog=PackedCatalog(root)
 enable_v18()
 from rag.tantivy_query import query
 phrase_hits=catalog.searcher.search(query(catalog.index,('phrase',['reactive','power'])),limit=2,count=False).hits
 assert phrase_hits,'Native historical multi-token phrase contract not preserved'
 selected,context,trace=catalog.retrieve(catalog.manifest['probe_query']);assert selected and context.items
 for row in catalog.manifest['legacy_examples']:
  e=catalog.evidence(row['fragment_id'],catalog.k);assert e.evidence_id==row['evidence_id'];assert hashlib.sha256(json.dumps(wire(e),sort_keys=True,ensure_ascii=False).encode()).hexdigest()==row['payload_sha256']
 result=dict(passed=True,sqlite_and_spool_unavailable=True,denied_old_connect_attempts=len(denied),runtime_asset=str(root),selected_roots=len(selected),neighbors=len(context.items),neighbor_chars=context.char_count,legacy_id_version_span_payload_equal=True,legacy_examples=len(catalog.manifest['legacy_examples']),multi_token_phrase_read_passed=True,runtime_uses_old_sqlite=False,runtime_uses_spool=False,model_requests=0,full_rebuild_started=False)
 (HOME/'single-asset-proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
 if sys.argv[1]=='build':build()
 elif sys.argv[1]=='probe':probe()
