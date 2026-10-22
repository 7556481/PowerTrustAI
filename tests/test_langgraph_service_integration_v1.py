"""Service/Factory integration, fixed providers only; no credentials or paid calls."""
import asyncio,json,tempfile,unittest,socket,importlib.util
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from backend.service import ApplicationService
from backend.store import RunStore
from tests.test_local_service import task,terminal
from tests.test_schema14_factory_flow import FactoryFlowTests

@unittest.skipUnless(importlib.util.find_spec('langgraph'), 'Optional locked graph runtime not installed')
class FactoryGraph(unittest.TestCase):
    def exercise(self,**kwargs):
        config=ServiceConfig
        with patch('tests.test_schema14_factory_flow.ServiceConfig',side_effect=lambda **k:config(execution_path='langgraph_v1',**k)):
            return FactoryFlowTests('run').exercise(schema=13,**kwargs)
    def test_normal_actual_factory_worker_api_graph(self):
        r,p,events=self.exercise(two=True)
        self.assertEqual(r['configuration']['execution_path'],'langgraph_v1')
        self.assertEqual(r['execution']['execution_path'],'langgraph_v1')
        self.assertEqual(r['configuration']['protocols']['evidence_verification'],13)
        self.assertTrue(r['execution']['required_stages_complete'])
    def test_actual_factory_revision_and_full_reaudit(self):
        r,p,e=self.exercise(subject=True)
        self.assertEqual(len(r['answer']['versions']),2)
        self.assertEqual(len(r['review_rounds']),2)
        self.assertEqual(sum(x.prompt_version.startswith('bounded-revision') and not x.correction for x in p.requests),1)
    def test_actual_factory_hazard_no_revision(self):
        r,p,e=self.exercise(hazard=True)
        self.assertEqual(r['decision']['kind'],'reject')
        self.assertFalse(any(x.prompt_version.startswith('bounded-revision') for x in p.requests))
    def test_illegal_id_preserves_partial_and_no_fallback(self):
        r,p,e=self.exercise(illegal=True,two=True)
        self.assertFalse(r['execution']['required_stages_complete'])
        self.assertEqual(sum(x.correction for x in p.requests if x.prompt_version.startswith('evidence-verification')),1)
    def test_invalid_path_and_missing_graph_pre_admission(self):
        with self.assertRaises(ValueError):ServiceConfig(execution_path='automatic-fallback')
        c=ServiceConfig(profile='synthetic_fixture',execution_path='langgraph_v1')
        from backend.assembly import ConfigurationError
        with patch('harness.graph_runtime_v1.validate_versions',side_effect=ImportError('fixture')):
            with self.assertRaises(ConfigurationError):ComponentFactory(c).preflight()

@unittest.skipUnless(importlib.util.find_spec('langgraph'), 'Optional locked graph runtime not installed')
class Persistence(unittest.IsolatedAsyncioTestCase):
    async def test_graph_restart_queries_feedback_and_versions_do_not_execute(self):
        with tempfile.TemporaryDirectory() as temp:
            c=ServiceConfig(profile='synthetic_fixture',execution_path='langgraph_v1',run_db=Path(temp)/'runs.sqlite3')
            store=RunStore(c.run_db);svc=ApplicationService(c,store)
            await svc.start();rid=await svc.submit(task());await terminal(svc,rid)
            before=svc.result(rid);a=before['answer']['final']
            store.add_review(rid,{'answer_id':a['answer_id'],'answer_version':a['version'],'finding_id':None,'action':'note','source':'ai_assisted_user_supervised','reviewer_id':'fixture','note':'offline'})
            raw=store.get(rid)['result'];count=store.db.execute('SELECT count(*) FROM runs').fetchone()[0]
            await svc.stop();store.close()
            store=RunStore(c.run_db);svc=ApplicationService(c,store);await svc.start()
            self.assertEqual(store.get(rid)['result'],raw)
            self.assertEqual(store.db.execute('SELECT count(*) FROM runs').fetchone()[0],count)
            self.assertEqual(len(store.reviews(rid)),1)
            self.assertEqual(svc.result(rid)['answer']['versions'],before['answer']['versions'])
            self.assertEqual(svc.queue.qsize(),0)
            await svc.stop();store.close()

if __name__=='__main__':unittest.main()
