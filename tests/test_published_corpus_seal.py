"""Public synthetic immutable-publication regressions, never production data."""
import json,hashlib
from pathlib import Path
from test_corpus_index import CorpusTests
from rag.storage import KnowledgeStore,canonical,digest
from rag.corpus_index import seal,_OPENED
from core.validation import ContractError
class PublishedSealTests(CorpusTests):
 def publish_fixture(self):
  value={**self.seal,'version':'industry-corpus-fts-v1','chunks':2,'records':2}
  k='kc-'+digest(canonical(value).encode())
  with KnowledgeStore(self.p) as st:
   st.connection.execute('INSERT INTO corpus_seal VALUES(?,?)',(k,canonical(value)));st.connection.commit()
  side={'knowledge_version':k,'database_sha256':hashlib.sha256(self.p.read_bytes()).hexdigest(),**value}
  Path(str(self.p)+'.manifest.json').write_text(json.dumps(side),encoding='utf-8')
  return k,side
 def test_exact_published_bytes_do_not_repeat_full_sql_scans(self):
  k,_=self.publish_fixture()
  with KnowledgeStore(self.p,readonly=True) as st:
   sql=[];st.connection.set_trace_callback(sql.append);seal(st,k)
   self.assertFalse(any('quick_check' in s.lower() or 'count(*)' in s.lower() for s in sql))
   self.assertEqual(seal(st,k)['records'],2)
 def test_sidecar_must_match_database_manifest(self):
  k,side=self.publish_fixture();side['records']=999
  Path(str(self.p)+'.manifest.json').write_text(json.dumps(side),encoding='utf-8')
  with KnowledgeStore(self.p,readonly=True) as st:
   with self.assertRaises(ContractError):seal(st,k)
 def test_changed_bytes_are_rejected_by_a_fresh_process_cache(self):
  k,_=self.publish_fixture();_OPENED.clear()
  with self.p.open('ab') as f:f.write(b'tampered')
  with KnowledgeStore(self.p,readonly=True) as st:
   with self.assertRaises(ContractError):seal(st,k)
