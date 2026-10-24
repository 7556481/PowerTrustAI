"""Whole fixed batch rehearsal; no live service or provider calls."""
import asyncio,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.config import ServiceConfig
from rag.storage import KnowledgeStore,SourceMetadata
from tests.test_schema14_factory_flow import SyntheticProvider,GOOD
from tests.test_review_scope_v2 import response
from services.review_scope_v2 import PROMPT
from model_adapter.contracts import ModelResponse,ModelConnectionError
from evaluation import production_review_v2 as t
from evaluation import answer_review_net_benefit_v1 as base


class BatchTests(unittest.TestCase):
    def exercise(self,failure=None):
        from harness.graph_runtime_v1 import validate_versions,build_graph
        validate_versions();build_graph()
        with tempfile.TemporaryDirectory(dir='data/retrieval_local',prefix='production-review-v2-gate-') as tmp:
            root=Path(tmp).resolve();doc=root/'fixture.md';doc.write_text(GOOD,encoding='utf8')
            with KnowledgeStore(root/'knowledge.sqlite3') as k:version=k.ingest(doc,'synthetic-fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            c=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=version,execution_path='langgraph_v1')
            class Provider(SyntheticProvider):
                async def complete(self,r):
                    if failure=='shared':raise ModelConnectionError()
                    if failure=='local':return ModelResponse('{}',r.model_id,finish_reason='stop')
                    if r.prompt_version==PROMPT:return ModelResponse(json.dumps(response(json.loads(r.messages[1].content))),r.model_id,finish_reason='stop')
                    return await super().complete(r)
            old_write=base.write;old_mark=base.RunStore.mark
            def write(p,v):
                if failure=='response_storage' and p.parent.name=='responses':raise OSError('synthetic response failure')
                return old_write(p,v)
            def mark(s,rid,status,**kw):
                if failure=='result_storage' and status=='finished':raise OSError('synthetic result failure')
                return old_mark(s,rid,status,**kw)
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'synthetic-fixture','DEEPSEEK_API_KEY':'fixture'}),patch('backend.assembly.ROOT',root),patch.object(base,'write',side_effect=write),patch.object(base.RunStore,'mark',mark):
                s=asyncio.run(t.batch(c,t.materials(),root/'batch',lambda settings:Provider(),rows=t.order(),request_builder=t.request,variant_config=t.variants,task_runner=t.task_runner))
            (root/'batch/runs.sqlite3').rename(root/'closed.sqlite3')
            return s

    def test_complete_34_tasks_same_draft_scope_and_no_semantic_reference_leak(self):
        s=self.exercise();self.assertEqual(len(s['control']),34);self.assertFalse(s['unexecuted'])
        for i in range(6):
            results=[s['outputs'][x['accepted']['run_id']] for x in s['control'] if x['case_id'].startswith(f'B{i+1}-')]
            self.assertEqual(results[0]['review_rounds'][0]['answer'],results[1]['review_rounds'][0]['answer'])
        self.assertEqual(len(s['send_log']),sum(len(r.get('model_records',[])) for r in s['outputs'].values()))
        for i in range(8):
            inp=t.fixed_input(t.request(t.materials(),i,draft=True))
            self.assertEqual(len(inp.claims),len(t.materials()['A'][i]['reference']))
            self.assertNotIn('reference',t.wire(inp))

    def test_local_failure_continue_and_unknown_shared_stop(self):
        local=self.exercise('local');self.assertEqual(len(local['control']),34)
        for reason in ('shared','response_storage','result_storage'):
            s=self.exercise(reason);self.assertEqual(len(s['control']),1);self.assertEqual(len(s['unexecuted']),33)
            self.assertTrue(s['control'][0]['accepted']['run_id'])

    def test_actual_freeze_filename_identity_and_no_resume(self):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local',prefix='v2-freeze-') as tmp:
            root=Path(tmp);c=ServiceConfig();seen=[]
            async def batch(*args,**kw):seen.append(kw);return dict(control=[],unexecuted=[],send_log=[])
            with patch.object(t,'PUBLIC',root/'public'),patch.object(t,'LOCAL',root/'private'),patch.object(ServiceConfig,'from_environment',return_value=c),patch.object(t.ComponentFactory,'preflight',return_value=c.knowledge_version),patch.object(t.ComponentFactory,'manifest',return_value={'fixture':True}),patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch.object(t,'batch',side_effect=batch):
                t.freeze();t.execute();self.assertEqual(len(seen),1)
                self.assertEqual(len(seen[0]['rows']),34)
                with self.assertRaises(ValueError):t.execute()
