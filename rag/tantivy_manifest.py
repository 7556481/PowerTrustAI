"""Accepted derived-index identity. Not a substitute for source-byte sealing."""
import hashlib,json
from pathlib import Path

class IndexIdentityError(RuntimeError):
 code='TANTIVY_IDENTITY_ERROR'

def sha(path,check=None):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):
   if check:check()
   h.update(block)
 return h.hexdigest()

def tokenizer_identity():
 import jieba,importlib.metadata
 if importlib.metadata.version('jieba')!='0.42.1':raise IndexIdentityError('Jieba version mismatch')
 from rag.chinese_terms import TERMS
 return {'jieba':'0.42.1','dictionary_sha256':sha(Path(jieba.__file__).parent/'dict.txt'),'custom_terms_sha256':hashlib.sha256(json.dumps(TERMS,ensure_ascii=False).encode()).hexdigest(),'hmm':False,'filter':'ascii-alnum-cjk-casefold-v1'}

def query_identity():
 root=Path(__file__).resolve().parent
 return {name:hashlib.sha256((root/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in ('chinese_terms.py','topic_lanes.py','tantivy_query.py')}

def load_manifest(path,knowledge_version,*,isolated=False):
 try:
  import importlib.metadata
  p=Path(path).resolve();m=json.loads(p.read_text(encoding='utf8'))
  required={'version','knowledge_version','scope','members','tokenizer','query','engine','schema','build','files','index_path','acceptance','state'}
  if not required<=m.keys() or m['version']!='tantivy-product-manifest-v1':raise ValueError('manifest version/fields')
  if m['state']!='serviceable' or m['acceptance'].get('complete') is not True:raise ValueError('index not accepted/serviceable')
  if m['knowledge_version']!=knowledge_version:raise ValueError('knowledge snapshot mismatch')
  if m['scope'] not in ('full','isolated'):raise ValueError('Unknown member scope')
  if m['scope']!='full' and not isolated:raise ValueError('partial index prohibited for production')
  if not isolated and m.get('quality_gate')!='approved':raise ValueError('retrieval quality release gate not approved')
  if m['scope']=='full' and m['members']['total']!=m['members']['source_total']:raise ValueError('full member scope mismatch')
  if m.get('query_implementation')!=query_identity():raise ValueError('Query implementation identity mismatch')
  if m.get('tokenizer_config')!=tokenizer_identity() or m.get('index_format')!=7:raise ValueError('Dictionary or index-format mismatch')
  if m['tokenizer']!='jieba-0.42.1-electric-terms-v1' or m['query']!='topic_v4_subject_v1':raise ValueError('unsupported preprocessing/query identity')
  if m['engine']!='tantivy-0.27.0' or importlib.metadata.version('tantivy')!='0.27.0':raise ValueError('engine version mismatch')
  root=Path(m['index_path']).resolve()
  if not root.is_dir() or not m['files']:raise ValueError('index files unavailable')
  actual={str(f.relative_to(root)).replace('\\','/') for f in root.rglob('*') if f.is_file() and not f.name.endswith('.lock')}
  if set(m['files'])!=actual:raise ValueError('incomplete or unexpected index file inventory')
  proof=Path(m['acceptance']['proof_path']).resolve()
  if not (proof.is_relative_to(root.parent) or proof.is_relative_to(p.parent)) or sha(proof)!=m['acceptance']['proof_sha256']:raise ValueError('acceptance proof identity mismatch')
  accepted=json.loads(proof.read_text())
  if accepted.get('passed') is not True or accepted.get('complete_id_set') is not True or accepted.get('n')!=m['members']['total']:raise ValueError('complete member proof missing')
  for name,record in m['files'].items():
   file=(root/name).resolve()
   if not file.is_relative_to(root) or not file.is_file() or file.stat().st_size!=record['bytes'] or sha(file)!=record['sha256']:raise ValueError('index file integrity mismatch')
  if accepted.get('native_files') is not None and accepted['native_files']!=m['files']:raise ValueError('Index differs from accepted file hashes')
  meta=json.loads((root/'meta.json').read_text());signature=hashlib.sha256(json.dumps(meta['schema'],sort_keys=True).encode()).hexdigest()
  if signature!=m['schema']:raise ValueError('index schema mismatch')
  if sum(x['max_doc'] for x in meta['segments'])!=m['members']['total']:raise ValueError('index document count mismatch')
  m['_identity']=sha(p);m['_index_path']=str(root);m['_stamps']={n:((root/n).stat().st_size,(root/n).stat().st_mtime_ns) for n in m['files']};return m
 except IndexIdentityError:raise
 except Exception as e:raise IndexIdentityError(str(e)) from None

def package_manifest(index_path,proof_path,output,*,knowledge_version,source_total,scope,build,source_identity,check=None):
 root=Path(index_path).resolve();proof_path=Path(proof_path).resolve();proof=json.loads(proof_path.read_text());meta=json.loads((root/'meta.json').read_text())
 if proof.get('passed') is not True or not proof.get('complete_id_set'):raise IndexIdentityError('Unaccepted member inventory')
 count=sum(x['max_doc'] for x in meta['segments'])
 if count!=proof['n']:raise IndexIdentityError('Acceptance member count differs')
 files={str(f.relative_to(root)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f,check)} for f in root.rglob('*') if f.is_file() and not f.name.endswith('.lock')}
 if proof.get('native_files') is not None and proof['native_files']!=files:raise IndexIdentityError('Files changed after complete acceptance')
 m=dict(version='tantivy-product-manifest-v1',knowledge_version=knowledge_version,scope=scope,query_implementation=query_identity(),index_format=7,tokenizer_config=tokenizer_identity(),members={'total':count,'source_total':source_total},tokenizer='jieba-0.42.1-electric-terms-v1',query='topic_v4_subject_v1',engine='tantivy-0.27.0',schema=hashlib.sha256(json.dumps(meta['schema'],sort_keys=True).encode()).hexdigest(),build=build,source_identity=source_identity,files=files,index_path=str(root),acceptance={'complete':True,'proof_path':str(proof_path),'proof_sha256':sha(proof_path)},state='serviceable',quality_gate='blocked_known_coverage_risks')
 from rag.tantivy_build import atomic
 pending=Path(str(output)+'.pending');atomic(pending,m)
 try:
  load_manifest(pending,knowledge_version,isolated=True)
  if check:check()
  atomic(output,m)
 finally:pending.unlink(missing_ok=True)
 return m
