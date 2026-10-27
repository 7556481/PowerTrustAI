from tests.temp_paths import ignored_temporary_directory
"""Complete frozen plan rehearsal; no paid model, no separate controller."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from evaluation import strict_review_tool_trial_v1 as t
from evaluation import production_review_v2 as shared
from tests.test_review_simple_v1 import response
from model_adapter.strict_review_tool import map_null,VERSION,NAME
from model_adapter.contracts import ModelResponse


class BatchTests(unittest.TestCase):
    def exercise(self,failure=None):
        import tests.test_production_review_v2 as old
        original=old.SyntheticProvider.complete
        async def complete(provider,r):
            if r.result_tool is not None:
                d=json.loads(r.messages[1].content);args=json.dumps(map_null(response(d),encode=True))
                return ModelResponse(args,r.model_id,finish_reason='tool_calls',result_transport=dict(version=VERSION,tool_calls=[dict(id='batch-call',type='function',function=dict(name=NAME,arguments=args))],content=None))
            return await original(provider,r)
        with patch.object(old,'t',t),patch.object(old,'PROMPT','not-intercepted'),patch.object(old.SyntheticProvider,'complete',complete):return old.BatchTests().exercise(failure)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_all28_no_repeat_admission_same_draft_and_saved_raw_parameters(self):
        self.assertEqual([x['id'] for x in t.order()[:2]],['A1-strict_tool_v1','A3-strict_tool_v1'])
        self.assertEqual(len({x['id'] for x in t.order()}),28)
        s=self.exercise();self.assertEqual(len(s['control']),28);self.assertFalse(s['unexecuted'])
        for i in range(4):
            r=[s['outputs'][x['accepted']['run_id']] for x in s['control'] if x['case_id'].startswith(f'B{i+1}-')]
            self.assertEqual(r[0]['review_rounds'][0]['answer'],r[1]['review_rounds'][0]['answer'])
        strict=[r for out in s['outputs'].values() for r in out.get('model_records',[]) if r.get('result_transport')]
        self.assertTrue(strict);self.assertTrue(all(r['result_transport']['tool_calls'][0]['function']['arguments'] for r in strict))

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_shared_rejection_storage_and_incomplete_admission_stop(self):
        for reason in ('shared','response_storage','result_storage','local'):
            s=self.exercise(reason);self.assertEqual(len(s['control']),1);self.assertEqual(len(s['unexecuted']),27)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_actual_freeze_schema_identity_and_no_resume(self):
        from backend.config import ServiceConfig
        with ignored_temporary_directory(dir='data/retrieval_local',prefix='strict-review-freeze-') as tmp:
            root=Path(tmp);c=ServiceConfig();seen=[]
            async def batch(*args,**kwargs):seen.append(kwargs);return dict(control=[],unexecuted=[],send_log=[])
            with patch.object(t,'PUBLIC',root/'public'),patch.object(t,'LOCAL',root/'private'),patch.object(ServiceConfig,'from_environment',return_value=c),patch.object(shared.ComponentFactory,'preflight',return_value=c.knowledge_version),patch.object(shared.ComponentFactory,'manifest',return_value={'fixture':True}),patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch.object(shared,'batch',side_effect=batch):
                t.freeze();t.execute();self.assertEqual(len(seen[0]['rows']),28)
                with self.assertRaises(ValueError):t.execute()
