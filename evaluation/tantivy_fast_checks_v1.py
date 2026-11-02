import asyncio,unittest,time
from unittest.mock import patch
from evaluation import tantivy_adapter_checks_v1 as fixture
from rag.tantivy_fast_v1 import FastTantivyRetriever

def wrong_worker(path,identity,pipe):pipe.send(('ready','wrong',0));time.sleep(2)
def late_worker(path,identity,pipe):
 pipe.send(('ready',identity,3));pipe.recv();time.sleep(3)
def crossed_worker(path,identity,pipe):
 pipe.send(('ready',identity,3));pipe.recv();pipe.send(('result','previous-request',identity,[],{}));time.sleep(2)
class FastChecks(unittest.TestCase):
 setUp=fixture.AdapterTests.setUp
 tearDown=fixture.AdapterTests.tearDown
 request=fixture.AdapterTests.request
 def fast(self,**kw):return FastTantivyRetriever(self.source.p,self.path,self.source.k,isolated=True,**kw)
 def test_reuse_identity_and_final_budget(self):
  a=self.fast()
  async def run():
   x=await a.retrieve(self.request());pid=a._native.pid;await a.validate_result(self.request(),x);y=await a.retrieve(self.request());self.assertEqual(a._native.pid,pid);self.assertEqual(a._starts,1);self.assertFalse(a.last_trace['worker_cold']);self.assertLessEqual(sum(len(e.text) for e in y.evidence),8000);self.assertLessEqual(len(y.evidence),3);self.assertEqual(x.evidence,y.evidence)
  try:asyncio.run(run())
  finally:a.close()
  self.assertIsNone(a._native)
 def test_timeout_no_replay_then_bounded_restart(self):
  a=self.fast(timeout_seconds=.5,max_restarts=1)
  async def run():
   with patch('rag.tantivy_fast_v1.serve',late_worker):
    with self.assertRaises(TimeoutError):await a.retrieve(self.request())
   self.assertIsNone(a._native);a.timeout_seconds=10;self.assertTrue((await a.retrieve(self.request())).evidence);self.assertEqual(a._starts,2)
   a._native.terminate();a._native.join()
   with self.assertRaises(Exception):await a.retrieve(self.request())
   self.assertEqual(a._starts,2)
  try:asyncio.run(run())
  finally:a.close()
 def test_crossed_request_rejected(self):
  a=self.fast()
  async def run():
   with patch('rag.tantivy_fast_v1.serve',crossed_worker):
    with self.assertRaises(Exception):await a.retrieve(self.request())
   self.assertIsNone(a._native);self.assertFalse(a.available)
  try:asyncio.run(run())
  finally:a.close()
 def test_wrong_index_ready_rejected(self):
  a=self.fast()
  async def run():
   with patch('rag.tantivy_fast_v1.serve',wrong_worker):
    with self.assertRaises(Exception):await a.retrieve(self.request())
   self.assertIsNone(a._native)
  try:asyncio.run(run())
  finally:a.close()
 def test_cancel_destroys_owned_request_not_next(self):
  a=self.fast()
  async def run():
   with patch('rag.tantivy_fast_v1.serve',late_worker):
    t=asyncio.create_task(a.retrieve(self.request()));await asyncio.sleep(.5);t.cancel()
    with self.assertRaises(asyncio.CancelledError):await t
   self.assertIsNone(a._native);self.assertTrue((await a.retrieve(self.request())).evidence)
  try:asyncio.run(run())
  finally:a.close()
 def test_fatal_identity_and_exhausted_restarts_are_not_ready(self):
  from backend.config import ServiceConfig
  from backend.assembly import ComponentFactory,ConfigurationError
  a=self.fast();cfg=ServiceConfig(index_db=self.source.p,knowledge_version=self.source.k,tantivy_manifest=self.path,tantivy_isolated=True,tantivy_worker_mode='fast_v1');factory=ComponentFactory(cfg);factory.semantic_resource=a
  try:
   with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}):
    factory.preflight();a._starts=a.max_restarts+1
    with self.assertRaises(ConfigurationError):factory.preflight()
    a._starts=0;a._closed=True
    with self.assertRaises(ConfigurationError):factory.preflight()
  finally:a.close()
if __name__=='__main__':unittest.main()
