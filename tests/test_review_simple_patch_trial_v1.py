from tests.temp_paths import ignored_temporary_directory
"""Frozen admission uses the existing batch/Factory/SQLite, not a paid probe."""
import json,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from evaluation import review_simple_patch_trial_v1 as t
from evaluation import production_review_v2 as shared
from tests.test_review_simple_v1 import response
from services.review_simple_v1 import PROMPT
from model_adapter.contracts import ModelRequestError


class PatchBatchTests(unittest.TestCase):
    def exercise(self,fail=None,build=response):
        import tests.test_production_review_v2 as old
        with patch.object(old,'t',t),patch.object(old,'PROMPT',PROMPT),patch.object(old,'response',build):return old.BatchTests().exercise(fail)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/batch/summary.json').is_file(), 'Private historical archive unavailable')
    def test_27_slots_admission_once_same_draft_and_reused_a1_identity(self):
        self.assertEqual([x['id'] for x in t.order()[:2]],['A1-simple_v1','A2-simple_v1'])
        self.assertNotIn('A1-production',[x['id'] for x in t.order()])
        try:identity=t.history_identity()
        except ValueError as e:self.assertIn('Historical A1 business identity differs',str(e))
        else:self.assertTrue(identity['historical_reference'])
        s=self.exercise();self.assertEqual(len(s['control']),27);self.assertFalse(s['unexecuted'])
        for i in range(4):
            rows=[s['outputs'][x['accepted']['run_id']] for x in s['control'] if x['case_id'].startswith(f'B{i+1}-')]
            self.assertEqual(rows[0]['review_rounds'][0]['answer'],rows[1]['review_rounds'][0]['answer'])

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/batch/summary.json').is_file(), 'Private historical archive unavailable')
    def test_rejection_preserves_accepted_and_returned_result_then_stops_run_and_batch(self):
        n=0
        def build(data):
            nonlocal n
            n+=1
            if n==3:raise ModelRequestError()
            return response(data)
        s=self.exercise(build=build);self.assertEqual(len(s['control']),2);self.assertEqual(len(s['unexecuted']),25)
        self.assertEqual(len(s['send_log']),3);self.assertEqual(n,3)
        first=s['control'][0]['accepted']['run_id'];self.assertEqual(s['outputs'][first]['state'],'completed')
        self.assertTrue(s['control'][-1]['stop'])

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/batch/summary.json').is_file(), 'Private historical archive unavailable')
    def test_gate_incomplete_and_shared_storage_failure_stop_without_retry(self):
        for failure in ('local','shared','response_storage','result_storage'):
            s=self.exercise(failure);self.assertEqual(len(s['control']),1);self.assertEqual(len(s['unexecuted']),26)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/batch/summary.json').is_file(), 'Private historical archive unavailable')
    def test_new_freeze_filename_no_resume_and_all_old_materials_unchanged(self):
        from backend.config import ServiceConfig
        from evaluation.review_simple_trial_v1 import materials
        self.assertEqual(t.materials(),materials())
        with ignored_temporary_directory(dir='data/retrieval_local',prefix='simple-patch-freeze-') as tmp:
            root=Path(tmp);c=ServiceConfig();seen=[]
            async def batch(*args,**kwargs):seen.append(kwargs);return dict(control=[],unexecuted=[],send_log=[])
            with patch.object(t,'PUBLIC',root/'public'),patch.object(t,'LOCAL',root/'private'),patch.object(t,'history_identity',return_value={'synthetic_identity':True}),patch.object(ServiceConfig,'from_environment',return_value=c),patch.object(shared.ComponentFactory,'preflight',return_value=c.knowledge_version),patch.object(shared.ComponentFactory,'manifest',return_value={'fixture':True}),patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch.object(shared,'batch',side_effect=batch):
                t.freeze();t.execute();self.assertEqual(len(seen[0]['rows']),27)
                with self.assertRaises(ValueError):t.execute()

    def test_corrected_initial_error_is_not_a_repeated_final_constraint(self):
        from evaluation.review_simple_trial_v1 import ContractRecurrence
        from services.review_simple_v1 import CONTRACT
        g=ContractRecurrence()
        diag=dict(stage=CONTRACT,field_path='$.judgments[0].conditions',constraint='expected_object')
        records=[dict(prompt_version=PROMPT,candidate_catalog_path='group1',validation_error=diag),dict(prompt_version=PROMPT,candidate_catalog_path='group1',validation_error=None)]
        for case in (2,3):
            self.assertIsNone(g(dict(variant='simple_v1',line='A',case=case),dict(execution_issues=[{'code':'MODEL_OUTPUT_ERROR','component':'power_domain_review'}],model_records=records)))
