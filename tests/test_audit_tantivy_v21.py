import unittest
from evaluation.audit_tantivy_v21 import pack,expand,AuditRouter
from rag.contracts import RetrievalRequest,RetrievalPurpose
class AuditCandidateTests(unittest.IsolatedAsyncioTestCase):
 def test_identity_and_ranges(self):
  a=dict(evidence_id='a',text='same',start_offset=0,end_offset=4)
  p={'a':a,'repeat':dict(a),'other_source':dict(a,evidence_id='b'),'other_range':dict(a,start_offset=4,end_offset=8)}
  q=pack(p);self.assertEqual(expand(q),p);self.assertEqual(len(q['EVIDENCE_TEXTS']),1)
  self.assertIn('text',q['other_source']);self.assertIn('text',q['other_range'])
 async def test_stage_routes_and_validation(self):
  class R:
   def __init__(self):self.calls=[]
   async def retrieve(self,r):self.calls.append(r);return r
   async def validate_result(self,r,result):assert r==result
  sql=R();fast=R();router=AuditRouter(sql,fast)
  for purpose in RetrievalPurpose:
   r=RetrievalRequest('query','conceptual',purpose,'version',3);x=await router.retrieve(r);await router.validate_result(r,x)
  self.assertEqual([r.max_results for r in sql.calls],[3,3]);self.assertEqual([r.max_results for r in fast.calls],[6,6])

 async def test_unchanged_transport_preserves_final_message_bytes(self):
  from evaluation.audit_tantivy_v21 import install_client
  from model_adapter.contracts import ModelMessage,ModelSettings,ModelOutputError
  from model_adapter.runtime import ModelClient,ModelBudget
  seen=[]
  class Adapter:
   async def complete(self,r):seen.append(r);raise ModelOutputError()
  client=ModelClient(Adapter(),ModelSettings('synthetic-fixture'));install_client(client)
  messages=(ModelMessage('system','fixed prompt'),ModelMessage('user','{"scope_id":"s","QUOTE_CANDIDATES":[]}'))
  with self.assertRaises(ModelOutputError):await client.complete(messages,'fixture',ModelBudget(1))
  self.assertEqual(seen[0].messages,messages)

 async def test_saved_reference_validation_uses_sqlite(self):
  seen=[]
  class SQLite:
   async def validate_evidence(self,evidence,version):seen.append((evidence,version))
  router=AuditRouter(SQLite(),object())
  await router.validate_evidence(('frozen-evidence',),'frozen-version')
  self.assertEqual(seen,[(('frozen-evidence',),'frozen-version')])
