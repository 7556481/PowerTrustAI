import unittest
from unittest.mock import patch
from backend.managed import OverlapFactory
from tests import test_schema14_factory_flow as fixture
class OverlapProductTests(unittest.TestCase):
 def test_source_bound_revision_and_full_reaudit_store(self):
  with patch('tests.test_schema14_factory_flow.ComponentFactory',OverlapFactory):
   r,p,t=fixture.FactoryFlowTests().exercise(schema=13,subject=True)
  self.assertTrue(r['execution']['required_stages_complete'])
  self.assertEqual(len(r['answer']['versions']),2)
  self.assertEqual(len(r['review_rounds']),2)

 def test_domain_failure_keeps_fact_settlement_but_not_complete(self):
  from backend.store import RunStore
  from backend.serialization import wire
  from rag.retriever import AsyncSQLiteBM25Retriever
  original=AsyncSQLiteBM25Retriever.retrieve;mark=RunStore.mark;results=[]
  async def retrieve(obj,r):
   if r.purpose.value=='domain_review':
    import asyncio
    await asyncio.sleep(.05)
    raise RuntimeError('synthetic domain retrieval failure')
   return await original(obj,r)
  def save(store,rid,status,**kw):
   if kw.get('result') is not None:results.append(wire(kw['result']))
   return mark(store,rid,status,**kw)
  with patch('tests.test_schema14_factory_flow.ComponentFactory',OverlapFactory),patch.object(AsyncSQLiteBM25Retriever,'retrieve',retrieve),patch.object(RunStore,'mark',save):
   with self.assertRaises(AssertionError):fixture.FactoryFlowTests().exercise(schema=13,subject=True)
  self.assertTrue(results)
  self.assertTrue(any(m['component']=='evidence_verification' for m in results[-1]['model_records']))
  self.assertNotEqual(results[-1]['state'],'passed')
  self.assertTrue(results[-1]['execution_issues'])

 def test_user_cancel_settles_pending_fact_and_never_completes(self):
  import asyncio,threading
  from fastapi.testclient import TestClient
  from backend.store import RunStore
  from backend.serialization import wire
  from rag.retriever import AsyncSQLiteBM25Retriever
  started=threading.Event();settled=threading.Event();domain=threading.Event();cancelled=[];results=[]
  retrieve=AsyncSQLiteBM25Retriever.retrieve;complete=fixture.SubjectProvider.complete;get=TestClient.get;mark=RunStore.mark
  async def slow_model(obj,r):
   if r.prompt_version.startswith('evidence-verification'):
    started.set()
    try:await asyncio.sleep(1)
    finally:settled.set()
   return await complete(obj,r)
  async def slow_retrieve(obj,r):
   if r.purpose.value=='domain_review':domain.set();await asyncio.sleep(1)
   return await retrieve(obj,r)
  def poll(client,url,*a,**kw):
   if started.is_set() and domain.is_set() and not cancelled and str(url).startswith('/runs/') and str(url).count('/')==2:
    cancelled.append(client.post(str(url)+'/cancel',headers={'Authorization':'Bearer fixture'}).status_code)
   return get(client,url,*a,**kw)
  def save(store,rid,status,**kw):
   if kw.get('result') is not None:results.append(wire(kw['result']))
   return mark(store,rid,status,**kw)
  with patch('tests.test_schema14_factory_flow.ComponentFactory',OverlapFactory),patch.object(AsyncSQLiteBM25Retriever,'retrieve',slow_retrieve),patch.object(fixture.SubjectProvider,'complete',slow_model),patch.object(TestClient,'get',poll),patch.object(RunStore,'mark',save):
   with self.assertRaises(AssertionError):fixture.FactoryFlowTests().exercise(schema=13,subject=True)
  self.assertTrue(cancelled);self.assertTrue(settled.is_set());self.assertTrue(results)
  self.assertEqual(results[-1]['state'],'cancelled')
