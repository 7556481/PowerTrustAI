import asyncio,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_corpus_index as corpus_fixtures
from rag.storage import KnowledgeStore
from rag.tantivy_members import members,inventory
from rag.tantivy_build import CheckpointBuild,accept_complete
from rag.tantivy_manifest import package_manifest,load_manifest,IndexIdentityError
from rag.tantivy_retriever import AsyncTantivyRetriever,UnsupportedQueryError
from rag.contracts import RetrievalRequest,RetrievalPurpose,ContextOptions

def stalled_worker(path,tree,k,pipe):time.sleep(20)
class AdapterTests(unittest.TestCase):
 def setUp(self):
  self.source=corpus_fixtures.CorpusTests();self.source.setUp();self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'manifest.json'
  with KnowledgeStore(self.source.p,readonly=True) as st:rows=list(members(st,self.source.k));inv=inventory(st,self.source.k)
  identity={'expected':len(rows),'snapshot':self.source.k};b=CheckpointBuild(self.root/'build',identity);b.append(rows);b.close();accept_complete(self.root/'build',identity)
  package_manifest(self.root/'build/tantivy',self.root/'build/acceptance.json',self.path,knowledge_version=self.source.k,source_total=inv['total'],scope='isolated',build=identity,source_identity={'selection':'all synthetic_fixture members'})
  self.adapter=AsyncTantivyRetriever(self.source.p,self.path,self.source.k,isolated=True)
 def tearDown(self):self.adapter.close();self.source.tearDown();self.tmp.cleanup()
 def request(self,q='无功功率'):
  return RetrievalRequest(q,'synthetic_fixture',RetrievalPurpose.GENERATION,self.source.k,3,ContextOptions())
 def test_factory_manifest_and_cleanup_without_encoder(self):
  from backend.config import ServiceConfig
  from backend.assembly import ComponentFactory
  config=ServiceConfig(index_db=self.source.p,knowledge_version=self.source.k,run_db=self.root/'runs.sqlite3',tantivy_manifest=self.path,tantivy_isolated=True)
  f=ComponentFactory(config);f.initialize_retrieval()
  try:
   m=f.manifest(self.source.k);self.assertEqual(m['retrieval_backend']['backend'],'tantivy');self.assertIsNone(m['embedding_profile']);self.assertEqual(m['protocols']['evidence_verification'],13)
   from tests.test_schema14_factory_flow import SyntheticProvider
   with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'synthetic-fixture'}),patch('model_adapter.deepseek.create_adapter',return_value=SyntheticProvider()):
    try:b=f.create('synthetic-check',None)
    except Exception as e:raise e.__context__ or e
    b.close()
  finally:asyncio.run(f.close())
  self.assertIsNone(f.semantic_resource)
 def test_api_native_timeout_is_persisted_not_empty_success(self):
  from backend.config import ServiceConfig
  from backend.assembly import ComponentFactory
  from backend.api import create_app
  from fastapi.testclient import TestClient
  from tests.test_schema14_factory_flow import SyntheticProvider
  config=ServiceConfig(index_db=self.source.p,knowledge_version=self.source.k,run_db=self.root/'api-runs.sqlite3',tantivy_manifest=self.path,tantivy_isolated=True)
  f=ComponentFactory(config);f.initialize_retrieval();f.semantic_resource.timeout_seconds=.1
  with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'synthetic-fixture'}),patch('model_adapter.deepseek.create_adapter',return_value=SyntheticProvider()),patch('rag.tantivy_retriever.search_worker',stalled_worker):
   with TestClient(create_app(config,factory=f,access_token='fixture')) as client:
    h={'Authorization':'Bearer fixture'};v=client.post('/runs',headers=h,json={'mode':'question_answer','question':'voltage'})
    self.assertEqual(v.status_code,202);rid=v.json()['run_id']
    for _ in range(100):
     state=client.get('/runs/'+rid,headers=h).json()
     if state['status'] not in ('running','queued'):break
     time.sleep(.05)
    r=client.get('/runs/'+rid+'/result',headers=h).json();self.assertFalse(r['execution']['required_stages_complete']);self.assertTrue(any(x['code']=='RETRIEVAL_TIMEOUT' for x in r['execution']['execution_issues']),r['execution'])
    self.assertEqual(client.get('/runs/page/0',headers=h).status_code,200)
 def test_default_sqlite_configuration_unchanged(self):
  from backend.config import ServiceConfig
  self.assertIsNone(ServiceConfig().tantivy_manifest);self.assertFalse(ServiceConfig().tantivy_isolated)
 def test_actual_search_body_context_certificate(self):
  async def run():
   r=await self.adapter.retrieve(self.request());self.assertTrue(r.evidence);self.assertTrue(all(h.scoring_method.startswith('tantivy') for h in r.hits));await self.adapter.validate_result(self.request(),r);self.assertEqual(self.adapter.last_trace['fallback'],False)
  asyncio.run(run())
 def test_partial_never_loads_as_production(self):
  with self.assertRaises(IndexIdentityError):load_manifest(self.path,self.source.k)
 def test_timeout_releases_native_slot(self):
  async def run():
   self.adapter.timeout_seconds=.1
   with patch('rag.tantivy_retriever.search_worker',stalled_worker):
    with self.assertRaises(TimeoutError):await self.adapter.retrieve(self.request())
   self.assertIsNone(self.adapter._native);self.adapter.timeout_seconds=30;self.assertTrue((await self.adapter.retrieve(self.request())).evidence)
  asyncio.run(run())
 def test_cancel_releases_native_slot(self):
  async def run():
   with patch('rag.tantivy_retriever.search_worker',stalled_worker):
    t=asyncio.create_task(self.adapter.retrieve(self.request()));await asyncio.sleep(.1);t.cancel()
    with self.assertRaises(asyncio.CancelledError):await t
   self.assertIsNone(self.adapter._native)
  asyncio.run(run())
 def test_unsupported_query_is_error(self):
  async def run():
   with patch('rag.topic_lanes.plan',return_value=[('scope','"a" NEAR "b"')]):
    with self.assertRaises(UnsupportedQueryError):await self.adapter.retrieve(self.request())
  asyncio.run(run())
 def test_changed_index_is_error_not_empty(self):
  m=load_manifest(self.path,self.source.k,isolated=True);file=Path(m['_index_path'])/'meta.json';file.write_text(file.read_text()+' ')
  async def run():
   with self.assertRaises(IndexIdentityError):await self.adapter.retrieve(self.request())
  asyncio.run(run())
if __name__=='__main__':unittest.main()
