import unittest,tempfile,threading,multiprocessing as mp,os,json,time
from pathlib import Path
from types import SimpleNamespace
from rag.tantivy_diagnostic_v18 import DiagnosticRetriever,serve
from rag.tantivy_retriever import NativeSearchError

class Checks(unittest.TestCase):
 def test_live_global_statistics_and_product_source_certificate(self):
  import sqlite3,asyncio
  from tests import test_corpus_index as fixtures
  from rag.storage import KnowledgeStore
  from rag.tantivy_members import members
  from rag.tantivy_build import CheckpointBuild,accept_complete
  from rag.tantivy_manifest import package_manifest
  from rag.tantivy_global_rank_v18 import GlobalIDFRetriever
  from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions
  f=fixtures.CorpusTests();f.setUp()
  try:
   with KnowledgeStore(f.p,readonly=True) as st:rows=list(members(st,f.k))
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);paths=[];spool=root/'input.sqlite3';con=sqlite3.connect(spool);con.execute('create table input(position integer primary key,rowid integer,terms_sha text,terms text)')
    for r in rows:con.execute('insert into input values(?,?,?,?)',(-r[1]-1 if r[1]<0 else r[1]+673,r[1],r[4],r[5]))
    con.commit();con.close()
    for i,subset in enumerate([rows[:1],rows[1:]]):
     p=root/str(i);identity={'expected':len(subset)};b=CheckpointBuild(p,identity)
     try:b.append([(j,*r[1:]) for j,r in enumerate(subset)])
     finally:b.close()
     accept_complete(p,identity);manifest=p/'manifest.json';package_manifest(p/'tantivy',p/'acceptance.json',manifest,knowledge_version=f.k,source_total=3,scope='isolated',build=identity,source_identity={'fixture':True});paths.append(manifest)
    a=GlobalIDFRetriever(f.p,paths,f.k,spool_path=spool,diagnostic_path=root/'events')
    async def run():
     try:
      q=RetrievalRequest('继电保护','fixture',RetrievalPurpose.GENERATION,f.k,6,ContextOptions());z=await a.retrieve(q);await a.validate_result(q,z);self.assertTrue(z.evidence);self.assertTrue(a.last_trace['worker_metrics']['global_token_df']);self.assertTrue(all(h.scoring_method=='global-token-idf-saturated-tf-v18' for h in z.hits))
     finally:a.close()
    asyncio.run(run())
  finally:f.tearDown()
 def test_positive_phrase_and_negative_words_are_distinct(self):
  from rag.tantivy_global_rank_v18 import positive,score
  from rag.tantivy_query import ast
  import collections
  self.assertEqual(positive(ast('"alpha beta" NOT "gamma"')),['alpha','beta'])
  self.assertEqual(score(collections.Counter('alpha alpha gamma'.split()),{'alpha':3,'beta':1}),2)
 def test_reclaim_is_bounded_and_does_not_allow_private_overflow(self):
  from unittest.mock import patch,Mock
  with tempfile.TemporaryDirectory() as t:
   a=object.__new__(DiagnosticRetriever);a.diagnostic_path=str(Path(t)/'events');a.memory_limit=10;a.timeout_seconds=10;a._cancel_work=threading.Event();a._native=SimpleNamespace(pid=os.getpid(),is_alive=lambda:True);a.trim_owned_working_set=True;a.trim=Mock()
   info=SimpleNamespace(rss=20,private=5)
   with patch('psutil.Process') as proc:
    proc.return_value.memory_info.return_value=info
    with self.assertRaises(NativeSearchError):a._wait(time.monotonic())
   a.trim.assert_called_once();a.trim.reset_mock();a._trim_used=False;info.private=30
   with patch('psutil.Process') as proc:
    proc.return_value.memory_info.return_value=info
    with self.assertRaises(NativeSearchError):a._wait(time.monotonic())
   a.trim.assert_not_called();a._cancel_work.set()
   with self.assertRaises(InterruptedError):a._wait(time.monotonic())
 def test_actual_memory_trigger_is_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   a=object.__new__(DiagnosticRetriever);a.diagnostic_path=str(Path(t)/'events');a.memory_limit=1;a.timeout_seconds=10;a._cancel_work=threading.Event();a._native=SimpleNamespace(pid=os.getpid(),is_alive=lambda:True)
   with self.assertRaisesRegex(NativeSearchError,'memory admission'):a._wait(time.monotonic())
   rows=[json.loads(l) for l in Path(a.diagnostic_path).read_text().splitlines()];hit=next(r for r in rows if r['kind']=='memory_limit');self.assertGreater(hit['value'],hit['threshold']);self.assertEqual(rows[-1]['message'],'Worker memory admission exceeded')
 def test_native_error_message_and_stage_survive_channel(self):
  import tantivy
  from rag.tantivy_build import create_index
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);idx=create_index(p/'idx');w=idx.writer(heap_size=16000000,num_threads=1);w.add_document(tantivy.Document(terms='alpha',rowid=1));w.commit();w.wait_merging_threads()
   parent,child=mp.Pipe();worker=threading.Thread(target=serve,args=([str(p/'idx')],'v',child,str(p/'events')));worker.start();self.assertEqual(parent.recv()[0],'ready');parent.send(('search','r','wrong',None,16));r=parent.recv();worker.join(5);parent.close();self.assertFalse(worker.is_alive());self.assertEqual(r[0],'error');self.assertIn('identity',r[3]);self.assertEqual(r[4]['stage'],'request_validation')
