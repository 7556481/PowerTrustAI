"""Actual Factory/Harness/Store with reusable worker, four synthetic members."""
import json,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from tests import test_corpus_index as source_fixture
from tests.test_schema14_factory_flow import GOOD
from evaluation.tantivy_product_isolation_v1 import OfflineProvider
from rag.storage import KnowledgeStore,canonical,digest
from rag.corpus_index import add_record
from rag.tantivy_members import members,inventory
from rag.tantivy_build import CheckpointBuild,accept_complete
from rag.tantivy_manifest import package_manifest
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from backend.api import create_app
class FactoryFast(unittest.TestCase):
 def test_product_versions_and_worker_reuse(self):
  source=source_fixture.CorpusTests();source.setUp()
  try:
   assert Path(source.p).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
   with KnowledgeStore(source.p) as st:
    add_record(st.connection,text=GOOD,record_id=3,row_number=2,**source.args);s=dict(source.seal,has_english=True);k='kc-'+digest(canonical(s).encode());st.connection.execute('insert into corpus_seal values(?,?)',(k,canonical(s)));st.connection.commit()
   with KnowledgeStore(source.p,readonly=True) as st:
    inv=inventory(st,k);self.assertEqual(inv['total'],4);rows=list(members(st,k))
   with tempfile.TemporaryDirectory() as t:
    root=Path(t);identity={'expected':4,'source':'synthetic_fixture'};b=CheckpointBuild(root/'build',identity);b.append(rows);b.close();accept_complete(root/'build',identity);manifest=root/'manifest.json';package_manifest(root/'build/tantivy',root/'build/acceptance.json',manifest,knowledge_version=k,source_total=4,scope='isolated',build=identity,source_identity={'kind':'four member fixture'})
    cfg=ServiceConfig(index_db=source.p,knowledge_version=k,run_db=root/'runs.sqlite3',tantivy_manifest=manifest,tantivy_isolated=True,tantivy_worker_mode='fast_v1',execution_path='langgraph_v1',model_budget_dir=root/'budget');factory=ComponentFactory(cfg);provider=OfflineProvider()
    with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=provider):
     with TestClient(create_app(cfg,factory=factory,access_token='fixture')) as client:
      h={'Authorization':'Bearer fixture'};pids=[]
      for bad in (False,True):
       body={'mode':'assess_existing' if bad else 'question_answer','question':'synthetic voltage','engineering_context':{'goal':'conceptual'}}
       if bad:body['existing_answer']='SYNTHETIC_WRONG permitted voltage is9 kV.'
       response=client.post('/runs',headers=h,json=body);self.assertEqual(response.status_code,202,response.text);rid=response.json()['run_id']
       for _ in range(400):
        state=client.get('/runs/'+rid,headers=h).json()
        if state['status'] not in ('queued','running'):break
        time.sleep(.02)
       r=client.get('/runs/'+rid+'/result',headers=h).json();self.assertTrue(r['execution']['required_stages_complete'],r['execution']);self.assertEqual(r['configuration']['protocols']['evidence_verification'],13);pids.append(factory.semantic_resource._native.pid)
       if bad:self.assertEqual(len(r['answer']['versions']),2);self.assertEqual(len(r['review_rounds']),2)
      self.assertEqual(pids[0],pids[1]);self.assertEqual(client.get('/runs/page/0',headers=h).status_code,200)
    self.assertIsNone(factory.semantic_resource)
    from model_adapter.call_budget_v1 import shared_gate
    gate=shared_gate(root/'budget');self.assertGreater(gate.state['calls'],0);self.assertTrue(all(not e['inflight'] for e in gate.state['entries'].values()));self.assertEqual(gate.held(),sum(e['reserved'] for e in gate.state['entries'].values()))
  finally:source.tearDown()
if __name__=='__main__':unittest.main()
