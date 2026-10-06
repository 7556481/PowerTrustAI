"""Public synthetic_fixture checks: Chinese segmentation, immutable scope, FTS."""
import tempfile,sqlite3,json,asyncio,importlib.util
from pathlib import Path
from dataclasses import replace
import unittest
from contextlib import closing
from rag.storage import KnowledgeStore,canonical,digest
from rag.corpus_index import SCHEMA,add_record,CorpusRetriever,corpus_evidence
from rag.chinese_terms import terms,VERSION
from rag.contracts import RetrievalRequest,RetrievalPurpose
from rag.retriever import AsyncSQLiteBM25Retriever
from core.validation import ContractError
@unittest.skipUnless(importlib.util.find_spec('jieba'),'Optional corpus dependencies not installed')
class CorpusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'db.sqlite3';self.doc=Path(self.tmp.name)/'body.md'
  self.doc.write_text('# synthetic_fixture\n\n电压与无功资源有关系。',encoding='utf-8')
  with KnowledgeStore(self.p) as st:
   self.base=st.ingest(self.doc,'native').knowledge_version;st.connection.executescript(SCHEMA)
   for row in st.rows(self.base):
    st.connection.execute('INSERT INTO corpus_native VALUES(?,?)',(1,row['fragment_id']))
    st.connection.execute('INSERT INTO corpus_fts(rowid,terms) VALUES(-1,?)',(' '.join(terms(row['search_text'])),))
   self.args=dict(shard='chinese/high/s.parquet',shard_sha='a'*64,revision='r'*40)
   add_record(st.connection,text='synthetic_fixture：感性负载的无功功率可以由并联电容补偿。',record_id=1,row_number=0,**self.args)
   add_record(st.connection,text='synthetic_fixture：继电保护在短路故障时动作。',record_id=2,row_number=1,**self.args)
   self.seal={'tokenizer':VERSION,'query_version':'electric-topic-query-v2','base_knowledge_version':self.base,'has_english':False}
   self.k='kc-'+digest(canonical(self.seal).encode());st.connection.execute('INSERT INTO corpus_seal VALUES(?,?)',(self.k,canonical(self.seal)));st.connection.commit()
 def tearDown(self):self.tmp.cleanup()
 def request(self,q):return RetrievalRequest(q,'synthetic_fixture',RetrievalPurpose.GENERATION,self.k,3)
 def test_chinese_electric_terms_and_normal_questions(self):
  self.assertIn('无功功率',terms('什么是无功功率？'));self.assertIn('功率因数',terms('怎样提高功率因数？'))
  with KnowledgeStore(self.p,readonly=True) as st:
   result=CorpusRetriever(st)._retrieve(self.request('并联电容为什么能补偿感性负载？'))
   self.assertIn('并联电容',result.evidence[0].text)
   self.assertNotIn('继电保护',result.evidence[0].text)
   self.assertEqual(CorpusRetriever(st)._retrieve(self.request('xyznotpresent')).evidence,())
   self.assertEqual(CorpusRetriever(st)._retrieve(self.request('为什么？')).evidence,())
 def test_small_alias_and_format_cleanup_do_not_write_or_modify_question(self):
  from rag.chinese_terms import query_expression
  self.assertIn('"无功功率"',query_expression('无功'))
  self.assertIn('"功率因数"',query_expression('功率因素'))
  self.assertNotIn('200',query_expression('无功功率是什么？请用普通中文回答，控制在200字以内'))
  self.assertIn('"厂"',query_expression('厂站无功补偿方案'));self.assertIn('"站"',query_expression('厂站无功补偿方案'))
 def test_no_full_snapshot_scan_and_async_saved_evidence(self):
  async def run():
   retriever=AsyncSQLiteBM25Retriever(self.p)
   try:
    r=await retriever.retrieve(self.request('无功功率'));await retriever.validate_result(self.request('无功功率'),r)
    await retriever.validate_evidence(r.evidence,self.k)
   finally:retriever.close()
  asyncio.run(run())
 def test_dedup_retains_alias_and_hit_tampering_rejected(self):
  with KnowledgeStore(self.p) as st:
   body=st.connection.execute('SELECT raw_text FROM corpus_records WHERE id=1').fetchone()[0]
   self.assertFalse(add_record(st.connection,text=body,record_id=3,row_number=2,**self.args))
   self.assertEqual(st.connection.execute('SELECT count(*) FROM corpus_duplicates').fetchone()[0],1)
   result=CorpusRetriever(st)._retrieve(self.request('无功功率'));e=result.evidence[0]
   self.assertIsNone(e.provenance.publisher);self.assertIn('original_source_unverified',e.provenance.quality_status)
   with self.assertRaises(ContractError):st.verify_evidence(replace(e,text='forged'))
   st.connection.execute("UPDATE corpus_records SET raw_text='forged' WHERE id=1")
   with self.assertRaises(ContractError):st.evidence(e.provenance.fragment_id,self.k)
 def test_old_snapshot_native_provenance_stays_available(self):
  with KnowledgeStore(self.p,readonly=True) as st:
   old=st.evidence(st.rows(self.base)[0]['fragment_id'],self.base)
   new=st.evidence(old.provenance.fragment_id,self.k)
   self.assertEqual(new.text,old.text);self.assertNotEqual(new.evidence_id,old.evidence_id)
 def test_chunk_spans_are_complete_reversible_and_conditions_preserved(self):
  from rag.corpus_index import chunks
  text=('在正弦稳态、固定电压和理想元件条件下，结论才成立。'*100)
  spans=list(chunks(text));self.assertEqual(''.join(text[a:b] for a,b in spans),text)
  self.assertTrue(all(b-a<=1200 for a,b in spans))
 @unittest.skipUnless(importlib.util.find_spec('pyarrow'),'Optional Parquet dependency not installed')
 def test_streaming_resume_and_immutable_publication(self):
  import pyarrow as pa,pyarrow.parquet as pq
  from types import SimpleNamespace
  from rag.corpus_build import build,publish,sha
  folder=Path(self.tmp.name);shards=folder/'shards';shards.mkdir();p=shards/'sample.parquet'
  pq.write_table(pa.table({'_id':[1,2,3],'text':['synthetic_fixture 电压','synthetic_fixture 无功','synthetic_fixture 电压']}),p)
  manifest=folder/'manifest.json';manifest.write_text(json.dumps({'revision':'r'*40,'files':[{'path':p.name,'size':p.stat().st_size,'lfs':{'oid':sha(p)}}]}))
  args=SimpleNamespace(base=str(self.p),database=str(folder/'build.sqlite3'),base_knowledge=self.base,manifest=str(manifest),shards=str(shards),wait=False,publish=str(folder/'sealed.sqlite3'),allow_partial=False)
  build(args)
  with closing(sqlite3.connect(args.database)) as con:before=con.execute('SELECT count(*) FROM corpus_records').fetchone()[0]
  build(args)
  with closing(sqlite3.connect(args.database)) as con:self.assertEqual(before,con.execute('SELECT count(*) FROM corpus_records').fetchone()[0])
  publish(args)
  from rag.corpus_index import seal,_OPENED
  m=json.loads(Path(args.publish+'.manifest.json').read_text(encoding='utf-8'))
  with KnowledgeStore(args.publish,readonly=True) as st:self.assertIsNotNone(seal(st,m['knowledge_version']))
  with closing(sqlite3.connect(args.publish)) as con:
   con.execute("UPDATE corpus_records SET raw_text='synthetic_fixture tampered' WHERE id=1");con.commit()
  _OPENED.pop((str(Path(args.publish).resolve()),m['knowledge_version']),None)
  with KnowledgeStore(args.publish,readonly=True) as st:
   with self.assertRaises(ContractError):seal(st,m['knowledge_version'])
  with self.assertRaises(ValueError):publish(args)
 @unittest.skipUnless(importlib.util.find_spec('pyarrow'),'Optional Parquet dependency not installed')
 def test_verified_bytes_with_bad_footer_are_excluded_not_declared_complete(self):
  from types import SimpleNamespace
  from rag.corpus_build import build,publish,sha
  folder=Path(self.tmp.name);shards=folder/'bad';shards.mkdir();p=shards/'bad.parquet';p.write_bytes(b'PAR1synthetic_fixture_missing_footer')
  manifest=folder/'bad.json';manifest.write_text(json.dumps({'revision':'r'*40,'files':[{'path':p.name,'size':p.stat().st_size,'lfs':{'oid':sha(p)}}]}))
  a=SimpleNamespace(base=str(self.p),database=str(folder/'bad-build.sqlite3'),base_knowledge=self.base,manifest=str(manifest),shards=str(shards),wait=False,publish=str(folder/'bad-publication.sqlite3'),allow_partial=False)
  build(a)
  with self.assertRaises(ValueError):publish(a)
  with closing(sqlite3.connect(a.database)) as con:
   self.assertEqual(con.execute('SELECT complete FROM corpus_progress').fetchone()[0],-1)
   self.assertEqual(con.execute('SELECT reason_code FROM corpus_failures').fetchone()[0],'verified_bytes_unreadable_parquet')
 @unittest.skipUnless(importlib.util.find_spec('pyarrow'),'Optional Parquet dependency not installed')
 def test_public_downloader_reuses_verified_shard_without_network(self):
  import pyarrow as pa,pyarrow.parquet as pq
  from rag.corpus_download import download,sha
  from unittest.mock import patch
  folder=Path(self.tmp.name);p=folder/'valid.parquet';pq.write_table(pa.table({'_id':[1],'text':['synthetic_fixture']}),p)
  entry={'path':p.name,'size':p.stat().st_size,'lfs':{'oid':sha(p)}}
  with patch('rag.corpus_download.build_opener',side_effect=AssertionError('Offline fixture must not access network')):
   result=download(entry,folder,'r'*40,None)
  self.assertEqual(result['status'],'verified');self.assertTrue(result['reused'])
 @unittest.skipUnless(importlib.util.find_spec('pyarrow'),'Optional Parquet dependency not installed')
 def test_publication_accounts_for_valid_and_verified_excluded_shards(self):
  import pyarrow as pa,pyarrow.parquet as pq
  from types import SimpleNamespace
  from rag.corpus_build import build,publish,sha
  folder=Path(self.tmp.name);shards=folder/'mixed';shards.mkdir()
  valid=shards/'good.parquet';pq.write_table(pa.table({'_id':[1],'text':['Synthetic_fixture: constant pressure is required.']}),valid)
  (shards/'english').mkdir();bad=shards/'english/bad.parquet';bad.write_bytes(b'PAR1synthetic_fixture_bad_footer')
  manifest=folder/'mixed.json';manifest.write_text(json.dumps({'revision':'r'*40,'files':[{'path':p.relative_to(shards).as_posix(),'size':p.stat().st_size,'lfs':{'oid':sha(p)}} for p in (valid,bad)]}))
  args=SimpleNamespace(base=str(self.p),database=str(folder/'mixed.sqlite3'),base_knowledge=self.base,manifest=str(manifest),shards=str(shards),wait=False,publish=str(folder/'mixed-published.sqlite3'),allow_partial=False)
  with closing(sqlite3.connect(self.p)) as con:base_records=con.execute('SELECT count(*) FROM corpus_records').fetchone()[0]
  build(args);publish(args)
  m=json.loads(Path(args.publish+'.manifest.json').read_text(encoding='utf-8'))
  self.assertTrue(m['complete']);self.assertEqual(m['records'],base_records+1);self.assertEqual(len(m['excluded_shards']),1)
  self.assertIn('verified_unreadable_excluded',m['coverage_definition'])
  self.assertFalse(m['has_english']);self.assertEqual(m['publication_version'],'corpus-publication-v2-covered-exclusions')
