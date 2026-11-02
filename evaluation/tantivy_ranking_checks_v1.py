import asyncio,sqlite3,unittest,tempfile
from pathlib import Path
from evaluation import tantivy_adapter_checks_v1 as fixtures
from evaluation.tantivy_ranking_v1 import BoundedOriginalBM25
from rag.tantivy_manifest import sha,IndexIdentityError
from rag.storage import KnowledgeStore
from rag.tantivy_members import members
class RankingChecks(unittest.TestCase):
 def setUp(self):
  # Existing CorpusTests creates exactly 2 industry + 1 native synthetic members.
  fixtures.AdapterTests.setUp(self);self.ref=self.root/'reference.sqlite3'
  assert Path(self.source.p).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
  with KnowledgeStore(self.source.p,readonly=True) as s:
   assert s.connection.execute('select count(*) from corpus_chunks').fetchone()[0]==2
   assert s.connection.execute('select count(*) from corpus_native').fetchone()[0]==1
   rows=list(members(s,self.source.k));assert len(rows)==3
  c=sqlite3.connect(self.ref);c.execute("create virtual table corpus_fts using fts5(terms,content='')");c.executemany('insert into corpus_fts(rowid,terms) values(?,?)',[(r[1],r[-1]) for r in rows]);c.commit();c.close()
 def tearDown(self):fixtures.AdapterTests.tearDown(self)
 request=fixtures.AdapterTests.request
 def test_native_phase_metrics_release(self):
  async def run():
   await self.adapter.retrieve(self.request());t=self.adapter.last_trace
   self.assertTrue(all(t['worker_metrics'][n]>=0 for n in ('index_open_seconds','query_seconds','stored_hit_seconds')));self.assertGreaterEqual(t['release_seconds'],0);self.assertIsNone(self.adapter._native)
  asyncio.run(run())
 def test_protection_same_budget_and_exact_original_score_order(self):
  a=BoundedOriginalBM25(self.source.p,self.path,self.source.k,isolated=True,reference=self.ref,reference_sha=sha(self.ref))
  async def run():
   r=await a.retrieve(self.request());await a.validate_result(self.request(),r);self.assertLessEqual(len(r.hits),3);self.assertLessEqual(a.last_trace['candidate_count'],32);self.assertTrue(all(h.scoring_method=='T32-original-FTS-BM25-v1' for h in r.hits))
   c=sqlite3.connect(self.ref)
   try:
    from rag.topic_lanes import plan
    expected=c.execute('select -bm25(corpus_fts) from corpus_fts where corpus_fts match ? order by bm25(corpus_fts),rowid limit 3',(plan(self.request().query)[0][1],)).fetchall()
   finally:c.close()
   self.assertEqual([h.score for h in r.hits],[x[0] for x in expected])
  try:asyncio.run(run())
  finally:a.close()
 def test_wrong_reference_identity_refused(self):
  with self.assertRaises(IndexIdentityError):BoundedOriginalBM25(self.source.p,self.path,self.source.k,isolated=True,reference=self.ref,reference_sha='wrong')
if __name__=='__main__':unittest.main()
