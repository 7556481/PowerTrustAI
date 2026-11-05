"""Full production member order; metadata and text follow original source readers."""
import hashlib,json
from rag.chinese_terms import terms
from rag.corpus_index import seal,corpus_evidence
from rag.tantivy_manifest import IndexIdentityError

def inventory(store,knowledge_version):
 s=seal(store,knowledge_version)
 if s is None:raise IndexIdentityError('Sealed production corpus required')
 con=store.connection;p=tuple(con.execute('select '+expression+' from corpus_chunks').fetchone()[0] for expression in ('count(*)','min(id)','max(id)'));n=tuple(con.execute('select '+expression+' from corpus_native').fetchone()[0] for expression in ('count(*)','min(id)','max(id)'))
 if (p[0] and (p[1]!=1 or p[2]!=p[0])) or (n[0] and (n[1]!=1 or n[2]!=n[0])):raise IndexIdentityError('Member IDs not dense; explicit cursor migration required')
 return {'knowledge_version':knowledge_version,'base_knowledge_version':s['base_knowledge_version'],'industry':p[0],'native':n[0],'total':p[0]+n[0],'order':'native id ascending (negative search ID), then industry id ascending','excluded_shards':s.get('excluded_shards',[]),'duplicates_not_reindexed':s.get('duplicates',0),'tokenizer':s['tokenizer'],'source_seal':s}

def members(store,knowledge_version,*,start=0):
 inv=inventory(store,knowledge_version);s=inv['source_seal'];con=store.connection
 if not 0<=start<=inv['total']:raise IndexIdentityError('Member cursor outside fixed scope')
 native={r['fragment_id']:r for r in store.rows(s['base_knowledge_version'])};pos=start
 if start<inv['native']:
  for rid,fid in con.execute('select id,fragment_id from corpus_native where id>? order by id',(start,)):
   e=corpus_evidence(store,fid,knowledge_version,s);text=' '.join(terms(native[fid]['search_text']));yield (pos,-rid,fid,hashlib.sha256(e.text.encode()).hexdigest(),hashlib.sha256(text.encode()).hexdigest(),text);pos+=1
 for rid,fid,expected in con.execute('select id,fragment_id,text_hash from corpus_chunks where id>? order by id',(max(0,start-inv['native']),)):
  e=corpus_evidence(store,fid,knowledge_version,s)
  if hashlib.sha256(e.text.encode()).hexdigest()!=expected:raise IndexIdentityError('Original member body hash mismatch')
  text=' '.join(terms(e.text));yield (pos,rid,fid,expected,hashlib.sha256(text.encode()).hexdigest(),text);pos+=1
