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
 def test_expiry_and_immutable_input_sidefile_stop(self):
  import json,time
  from unittest.mock import patch
  import evaluation.tantivy_shard_continuous_v17 as controller
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);auth=root/'authorization.json';source=root/'source.sqlite3';source.write_bytes(b'public-fixture')
   stamp=source.stat();value={'deadline':time.time()+60,'min_free':0,'protected_inputs':[{'path':str(source),'bytes':stamp.st_size,'mtime_ns':stamp.st_mtime_ns}]};auth.write_text(json.dumps(value))
   with patch.multiple(controller,HOME=root,AUTH=auth):
    self.assertEqual(controller.guard()['deadline'],value['deadline'])
    side=Path(str(source)+'-wal');side.write_bytes(b'pending')
    with self.assertRaisesRegex(RuntimeError,'Nonempty immutable input'):controller.guard()
    side.unlink();source.write_bytes(b'changed-fixture')
    with self.assertRaisesRegex(RuntimeError,'Frozen input stamp changed'):controller.guard()
    value['deadline']=0;auth.write_text(json.dumps(value))
    with self.assertRaises(TimeoutError):controller.guard()
 def test_complete_audit_source_hash_hook_and_uri_mapping(self):
  import json,sqlite3
  from unittest.mock import patch
  import evaluation.tantivy_shard_v16 as worker
  import evaluation.tantivy_full_build_v1 as original
  from rag.tantivy_build import atomic
  fixture=fixtures.CorpusTests();fixture.setUp()
  try:
   with KnowledgeStore(fixture.p,readonly=True) as source:rows=list(members(source,fixture.k))
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);shard=root/'shard';spool=root/'input';spool.mkdir()
    with sqlite3.connect(spool/'spool.sqlite3') as con:
     con.execute('create table input(position integer primary key,rowid integer,fragment_id text,body_sha text,terms_sha text,terms text)')
     con.executemany('insert into input values(?,?,?,?,?,?)',rows)
    con.close()
    b=CheckpointBuild(shard,{'expected':len(rows)})
    try:b.append(rows);h=b.mapping_hash()
    finally:b.close()
    atomic(shard/'built.json',{'mapping_hash':h});calls=[]
    with patch.multiple(worker,HOME=root,SHARD=shard,OLD=spool,START=0,END=len(rows),AUDIT_CHECK=lambda:calls.append(True)),patch.multiple(original,SOURCE=fixture.p,K=fixture.k):
     worker.audit();before=(shard/'acceptance.json').read_bytes();worker.audit()
     self.assertIn(before,[p.read_bytes() for p in (shard/'audit-history').glob('*.json')])
     atomic(root/'shards.json',{'shards':[{'index':str(shard/'tantivy'),'state':'sealed-isolated-readonly'}]})
     with self.assertRaisesRegex(RuntimeError,'immutable'):worker.audit()
    proof=json.loads((shard/'acceptance.json').read_text());self.assertTrue(proof['passed']);self.assertEqual(proof['n'],3);self.assertTrue(calls);self.assertIn('source_seal_seconds',proof)
  finally:fixture.tearDown()
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
