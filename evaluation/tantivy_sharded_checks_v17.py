"""Public fixture: single reusable worker reads two disjoint native indexes."""
import asyncio,tempfile,unittest
from pathlib import Path
from tests import test_corpus_index as fixtures
from rag.storage import KnowledgeStore
from rag.tantivy_members import members
from rag.tantivy_build import CheckpointBuild,accept_complete
from rag.tantivy_manifest import package_manifest
from rag.tantivy_sharded_v17 import ShardedTantivyRetriever
from rag.tantivy_query import ast
from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions

class ShardedTests(unittest.TestCase):
 def test_two_shards_one_worker_source_and_release(self):
  fixture=fixtures.CorpusTests();fixture.setUp()
  try:
   with KnowledgeStore(fixture.p,readonly=True) as st:rows=list(members(st,fixture.k))
   with tempfile.TemporaryDirectory() as tmp:
    manifests=[]
    for number,subset in enumerate([rows[:1],rows[1:]]):
     root=Path(tmp)/str(number);identity={'expected':len(subset),'scope':'synthetic-sharded-v17'}
     b=CheckpointBuild(root,identity)
     try:b.append([(i,*r[1:]) for i,r in enumerate(subset)])
     finally:b.close()
     accept_complete(root,identity);manifest=root/'manifest.json'
     package_manifest(root/'tantivy',root/'acceptance.json',manifest,knowledge_version=fixture.k,source_total=3,scope='isolated',build=identity,source_identity={'kind':'public fixture'})
     manifests.append(manifest)
    adapter=ShardedTantivyRetriever(fixture.p,manifests,fixture.k)
    async def run():
     try:
      a=await asyncio.to_thread(adapter._rank,ast('"电压"'),16);pid=adapter._native.pid
      self.assertIn(-1,[r for r,s in a])
      b=await asyncio.to_thread(adapter._rank,ast('"继电保护"'),16)
      self.assertIn(2,[r for r,s in b]);self.assertEqual(pid,adapter._native.pid)
      req=RetrievalRequest('继电保护','synthetic-sharded-v17',RetrievalPurpose.GENERATION,fixture.k,6,ContextOptions())
      result=await adapter.retrieve(req);await adapter.validate_result(req,result)
      self.assertTrue(result.evidence);self.assertEqual(adapter.last_trace['worker_metrics']['shard_count'],2)
     finally:adapter.close()
     self.assertIsNone(adapter._native)
    asyncio.run(run())
  finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
