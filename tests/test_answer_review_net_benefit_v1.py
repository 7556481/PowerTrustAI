"""Paid-entry rehearsal with real local Factory/SQLite and synthetic responses."""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.config import ServiceConfig
from evaluation import answer_review_net_benefit_v1 as t
from rag.storage import KnowledgeStore, SourceMetadata
from tests.test_schema14_factory_flow import SyntheticProvider, GOOD, BAD
from model_adapter.contracts import ModelResponse, ModelConnectionError


class BatchTests(unittest.TestCase):
    def exercise(self,failure=None):
        from harness.graph_runtime_v1 import validate_versions,build_graph
        validate_versions();build_graph()
        with tempfile.TemporaryDirectory(dir='data/retrieval_local',prefix='net-benefit-gate-') as tmp:
            root=Path(tmp).resolve();doc=root/'fixture.md';doc.write_text(GOOD,encoding='utf-8')
            with KnowledgeStore(root/'knowledge.sqlite3') as store:
                k=store.ingest(doc,'synthetic-fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            c=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=k,execution_path='langgraph_v1')
            evidence=dict(evidence_id='fixture-e',source_id='fixture',source_version='v1',locator='paragraph 1',text=GOOD,source_type='synthetic_fixture')
            m=dict(evidence=[evidence],questions=['Explain synthetic voltage']*4,drafts=[BAD,GOOD,GOOD,BAD])
            providers=[]
            class Provider(SyntheticProvider):
                async def complete(self,r):
                    if failure=='shared':raise ModelConnectionError()
                    if failure=='local':return ModelResponse('{}',r.model_id,finish_reason='stop')
                    return await super().complete(r)
            def factory(settings):
                p=Provider();providers.append(p);return p
            original_write=t.write
            def write(path,value):
                if failure=='response_storage' and path.parent.name=='responses':raise OSError('fixture response persistence failure')
                return original_write(path,value)
            original_mark=t.RunStore.mark
            def mark(store,rid,status,**kw):
                if failure=='result_storage' and status=='finished':raise OSError('fixture final storage failure')
                return original_mark(store,rid,status,**kw)
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'synthetic-fixture','DEEPSEEK_API_KEY':'fixture'}),patch('backend.assembly.ROOT',root),patch.object(t,'write',side_effect=write),patch.object(t.RunStore,'mark',mark):
                summary=asyncio.run(t.batch(c,m,root/'batch',factory))
            # Successful and exceptional independent readers are closed (Windows rename).
            db=root/'batch/runs.sqlite3';db.rename(root/'moved.sqlite3')
            return summary

    def test_successful_collection_unique_acceptance_and_same_natural_input(self):
        s=self.exercise()
        self.assertEqual(len(s['control']),20)
        self.assertFalse(s['unexecuted'])
        self.assertEqual(len({r['accepted']['run_id'] for r in s['control']}),20)
        for i in range(4):
            branches=[s['outputs'][r['accepted']['run_id']] for r in s['control'] if r['case_id'].startswith(f'B{i+1}-')]
            self.assertEqual(branches[0]['review_rounds'][0]['answer'],branches[1]['review_rounds'][0]['answer'])
        self.assertEqual(len(s['send_log']),sum(len(r.get('model_records',[])) for r in s['outputs'].values()))
    def test_local_final_structure_failure_continues(self):
        s=self.exercise('local');self.assertEqual(len(s['control']),20)
        self.assertFalse(s['unexecuted'])
        self.assertEqual(sum(r['state']=='unexecuted' for r in s['outputs'].values()),8)
    def test_shared_connection_stops_no_resubmit(self):
        s=self.exercise('shared');self.assertEqual(len(s['control']),1)
        self.assertEqual(len(s['unexecuted']),19)
        self.assertEqual(len(s['send_log']),1)
    def test_response_and_result_storage_stop_preserving_accepted_partial(self):
        for kind in ('response_storage','result_storage'):
            s=self.exercise(kind)
            self.assertEqual(len(s['control']),1)
            self.assertEqual(len(s['unexecuted']),19)
            self.assertTrue(s['control'][0]['accepted']['run_id'])
            self.assertTrue(s['outputs'])
    def test_order_and_materials_are_pre_prediction(self):
        rows=t.order();self.assertEqual(len(rows),20)
        self.assertEqual(sum(r['input']['line']=='G' for r in rows),4)
        m=t.materials();self.assertEqual(len(m['reference']),4)
        self.assertEqual(len(m['questions']),4)
        request=t.initial_request(m,0,draft=True)
        self.assertNotIn('reference',t.wire(request))
        self.assertEqual(len(request.existing_answer.citations),1)
    def test_freeze_execute_same_filename_identity_and_no_resume(self):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local',prefix='net-freeze-gate-') as tmp:
            root=Path(tmp);c=ServiceConfig()
            seen=[]
            async def batch(config,m,directory,provider):
                seen.append((config,m,directory))
                return dict(control=[],unexecuted=[],send_log=[])
            with patch.object(t,'PUBLIC',root/'public'),patch.object(t,'LOCAL',root/'private'),patch.object(ServiceConfig,'from_environment',return_value=c),patch('harness.deepseek_trial.load_project_env'),patch.object(t.ComponentFactory,'preflight',return_value=c.knowledge_version),patch.object(t.ComponentFactory,'manifest',return_value={'offline_fixture':True}),patch.object(t,'batch',side_effect=batch),patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):
                t.freeze();t.execute()
                self.assertEqual(len(seen),1)
                self.assertEqual(seen[0][1],t.materials())
                self.assertEqual(seen[0][2],root/'private/batch')
                with self.assertRaises(ValueError):t.execute()
