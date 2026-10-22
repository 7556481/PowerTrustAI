"""Pre-paid gates for the fixed six-run service entry, with no live connection."""
import json,os,socket,unittest,tempfile
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from backend.config import ServiceConfig
from rag.storage import KnowledgeStore,SourceMetadata
from evaluation import langgraph_service_trial_v1 as trial
from tests.test_schema14_factory_flow import SyntheticProvider,GOOD
from model_adapter.contracts import ModelResponse

class Gates(unittest.TestCase):
    def exercise(self,bad=False):
        root=trial.ROOT/'data/retrieval_local';root.mkdir(exist_ok=True,parents=True)
        with tempfile.TemporaryDirectory(dir=root,prefix='graph-service-gate-') as t:
            p=Path(t);doc=p/'fixture.md';doc.write_text(GOOD,encoding='utf8')
            with KnowledgeStore(p/'knowledge.sqlite3') as k:kv=k.ingest(doc,'synthetic-fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            cfg=ServiceConfig(index_db=p/'knowledge.sqlite3',knowledge_version=kv,run_db=p/'daily.sqlite3')
            provider=SyntheticProvider()
            if bad:
                async def invalid(request):provider.requests.append(request);return ModelResponse('{bad')
                provider.complete=invalid
            with ExitStack() as stack:
                stack.enter_context(patch.object(trial,'PUBLIC',p/'public'))
                stack.enter_context(patch.object(trial,'LOCAL',p/'batch'))
                stack.enter_context(patch.object(trial,'PRIVATE',p/'messages'))
                stack.enter_context(patch.object(ServiceConfig,'from_environment',return_value=cfg))
                stack.enter_context(patch.dict(os.environ,{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'synthetic-fixture'}))
                stack.enter_context(patch('model_adapter.deepseek.create_adapter',return_value=provider))
                trial.prepare();trial.execute()
                result=trial.read(p/'batch/summary.json')
                with self.assertRaises(ValueError):trial.execute()
                return result,provider
    def test_final_failure_stops_remaining_five_no_resume(self):
        s,p=self.exercise(True)
        self.assertEqual([x['status'] for x in s['branches']],['execution_failed']+['unexecuted']*5)
        self.assertEqual(len(p.requests),2)
    def test_successful_service_collection_reads_separate_connection_all_six_once(self):
        s,p=self.exercise(False)
        self.assertEqual([x['status'] for x in s['branches']],['complete']*6)
        self.assertEqual(len({x['run_id'] for x in s['branches']}),6)
        for b in s['branches']:
            self.assertTrue(b['result'])
            self.assertEqual(len(b['sent']),len(b['result']['model_records']))
    def test_plan_has_exact_six_alternating_runs_unchanged_payload_per_pair(self):
        self.assertEqual(len(trial.ORDER),6)
        self.assertEqual([r[2] for r in trial.ORDER],['sequential','langgraph_v1','langgraph_v1','sequential','sequential','langgraph_v1'])
        tasks=trial.tasks();self.assertEqual(len(tasks),3)
        self.assertEqual(tasks['LSI-03']['mode'],'assess_existing')
        self.assertIn('0.1',tasks['LSI-03']['existing_answer'])
        self.assertNotIn('execution_path',tasks['LSI-01'])
if __name__=='__main__':unittest.main()
