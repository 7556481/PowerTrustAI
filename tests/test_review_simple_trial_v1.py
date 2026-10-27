from tests.temp_paths import ignored_temporary_directory
"""Whole fixed plan rehearsal with the existing collector and temporary SQLite."""
import json,unittest,tempfile,asyncio,os
from pathlib import Path
from unittest.mock import patch
from evaluation import review_simple_trial_v1 as t
from evaluation import production_review_v2 as shared
from tests.test_review_simple_v1 import response
from services.review_simple_v1 import PROMPT,CONTRACT


class BatchTests(unittest.TestCase):
    def exercise(self,failure=None):
        # Reuse existing complete Factory/run-library rehearsal, not another collector.
        import tests.test_production_review_v2 as old
        with patch.object(old,'t',t),patch.object(old,'PROMPT',PROMPT),patch.object(old,'response',response):
            return old.BatchTests().exercise(failure)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_complete_28_slots_same_natural_draft_and_reference_isolation(self):
        s=self.exercise();self.assertEqual(len(s['control']),28);self.assertFalse(s['unexecuted'])
        self.assertEqual(len(t.materials()['A']),8);self.assertEqual(len(t.materials()['B']),4)
        for i in range(4):
            results=[s['outputs'][x['accepted']['run_id']] for x in s['control'] if x['case_id'].startswith(f'B{i+1}-')]
            self.assertEqual(results[0]['review_rounds'][0]['answer'],results[1]['review_rounds'][0]['answer'])
        self.assertEqual(t.materials()['A'],json.loads(json.dumps(shared.materials()['A'])))
        self.assertNotIn('reference',shared.wire(t.fixed_input(t.request(t.materials(),0,draft=True))))

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_shared_response_and_result_storage_stop(self):
        for reason in ('shared','response_storage','result_storage'):
            s=self.exercise(reason);self.assertEqual(len(s['control']),1);self.assertEqual(len(s['unexecuted']),27)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_repeated_local_contract_failure_stops_with_saved_evidence(self):
        # Two different candidate cases repeat the declared-root contract failure.
        s=self.exercise('local');self.assertEqual(len(s['control']),3);self.assertEqual(len(s['unexecuted']),25)
        self.assertTrue(s['control'][-1]['stop']);self.assertIn('contract_stop_evidence',s['outputs'][s['control'][-1]['accepted']['run_id']]['execution_issues'][-1])
        with patch.object(t,'ContractRecurrence',return_value=lambda spec,raw:None):
            s=self.exercise('local');self.assertEqual(len(s['control']),28)

    def test_repeated_specific_contract_stop_and_semantic_outcomes_continue(self):
        g=t.ContractRecurrence()
        spec=lambda i:dict(variant='simple_v1',line='A',case=i)
        raw={'execution_issues':[{'code':'MODEL_OUTPUT_ERROR'}],'model_records':[dict(prompt_version=PROMPT,validation_error={'stage':CONTRACT,'constraint':'required_field_missing','field_path':'$.judgments[0].conditions.instance'})]}
        self.assertIsNone(g(spec(0),raw));self.assertIsNone(g(dict(variant='production'),raw))
        stop=g(spec(1),raw);self.assertEqual(stop['code'],'SERVICE_EXECUTION_FAILED');self.assertIn('contract_stop_evidence',stop)
        g=t.ContractRecurrence();self.assertIsNone(g(spec(0),dict(execution_issues=[],model_records=[])));self.assertIsNone(g(spec(1),dict(execution_issues=[],model_records=[])))

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_actual_freeze_identity_filename_no_resume(self):
        from backend.config import ServiceConfig
        with ignored_temporary_directory(dir='data/retrieval_local',prefix='simple-freeze-') as tmp:
            root=Path(tmp);c=ServiceConfig();seen=[]
            async def batch(*args,**kw):seen.append(kw);return dict(control=[],unexecuted=[],send_log=[])
            with patch.object(t,'PUBLIC',root/'public'),patch.object(t,'LOCAL',root/'private'),patch.object(ServiceConfig,'from_environment',return_value=c),patch.object(shared.ComponentFactory,'preflight',return_value=c.knowledge_version),patch.object(shared.ComponentFactory,'manifest',return_value={'fixture':True}),patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch.object(shared,'batch',side_effect=batch):
                t.freeze();t.execute();self.assertEqual(len(seen[0]['rows']),28)
                with self.assertRaises(ValueError):t.execute()
