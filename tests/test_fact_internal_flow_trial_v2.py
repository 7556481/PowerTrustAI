from tests.temp_paths import ignored_temporary_directory
import asyncio,json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from evaluation import fact_internal_flow_trial_v2 as t
from evaluation.fact_internal_flow_materials_v1 import CASES
from model_adapter.contracts import ModelResponse
from tests.test_fact_flow_v1 import case_response

class Gates(unittest.TestCase):
    def run_batch(self,behavior=None,fail_file=None):
        seen=[];closed=[];plan=t.shared.read(t.PLAN)
        class Adapter:
            async def complete(self,r):
                seen.append(r)
                d=json.loads(r.messages[1].content);case=next(c for c in CASES if c['question']==d['question'])
                value=case_response(case,d)
                if behavior:return behavior(r,value)
                return ModelResponse(json.dumps(value),r.model_id,finish_reason='stop')
            def close(self):closed.append(True)
        original=t.shared.write
        def write(p,v):
            if fail_file and Path(p).name==fail_file:raise OSError('synthetic storage failure')
            original(p,v)
        with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d,patch.object(t.shared,'write',side_effect=write):
            result=asyncio.run(t.batch(plan,Path(d),Adapter))
            if not fail_file:self.assertTrue((Path(d)/'summary.json').exists())
        return result,seen,closed

    def test_all_six_complete_fixed_order_v2_only(self):
        out,seen,closed=self.run_batch()
        self.assertEqual([r['id'] for r in out['branches']],[c+'-v2' for c in t.CASE_IDS])
        self.assertEqual([r['status'] for r in out['branches']],['complete']*6)
        self.assertEqual(len(seen),6);self.assertEqual(len(closed),6)
        self.assertTrue(all(r.prompt_version==t.PROMPT for r in seen))
        f05=out['branches'][4]['output']['object_reviews'][0]
        self.assertEqual(f05['raw_model_status'],'supported')
        self.assertEqual(f05['effective_support_status'],'not_assessable')
        self.assertTrue(f05['classification_objection'])

    def test_final_structure_failure_stops_and_preserves_valid_peer(self):
        def behavior(r,v):
            v['judgments'][0]['basis_ids']=['illegal']
            return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        out,seen,_=self.run_batch(behavior)
        self.assertEqual(len(seen),2)
        self.assertEqual(out['branches'][0]['status'],'execution_failed')
        self.assertTrue(all(r['status']=='unexecuted' for r in out['branches'][1:]))
        parts=out['branches'][0]['output']['findings'][0]['component_reviews']
        self.assertEqual(parts[1]['status'],'supported')
        self.assertEqual(parts[0]['origin'],'execution_incomplete')

    def test_single_correction_then_continue_not_rerun(self):
        def behavior(r,v):
            if not r.correction:v['judgments'][0].pop('repair')
            return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        out,seen,_=self.run_batch(behavior)
        self.assertEqual(len(seen),12)
        self.assertEqual(sum(r.correction for r in seen),6)
        self.assertTrue(all(r['status']=='complete' for r in out['branches']))

    def test_storage_failure_before_send_and_after_response_stop(self):
        for filename,count in (('messages-1.json',0),('response-1.json',1),('output.json',1)):
            with self.subTest(filename=filename):
                out,seen,_=self.run_batch(fail_file=filename)
                self.assertEqual(len(seen),count)
                self.assertEqual(out['branches'][0]['status'],'execution_failed')
                self.assertTrue(all(r['status']=='unexecuted' for r in out['branches'][1:]))

    def test_timeout_and_cancel_stop_without_correction(self):
        for error in (asyncio.TimeoutError,asyncio.CancelledError):
            def behavior(r,v):raise error()
            with self.subTest(error=error):
                out,seen,_=self.run_batch(behavior)
                self.assertEqual(len(seen),1)
                self.assertEqual(out['branches'][0]['status'],'execution_failed')
                self.assertTrue(all(r['status']=='unexecuted' for r in out['branches'][1:]))

    def test_plan_v1_wrong_order_and_hash_rejected(self):
        for mutation in ('variant','order','hash'):
            plan=t.shared.read(t.PLAN)
            if mutation=='variant':plan['order'][0]['variant']='v1'
            elif mutation=='order':plan['order'].reverse()
            else:plan['order'][0]['message_sha256']='wrong'
            with self.assertRaises(ValueError):t.validate_plan(plan)

    def test_attempt_exclusive_and_frozen_source_rejected(self):
        with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d,patch.object(t,'LOCAL',Path(d)):
            (Path(d)/'attempt.json').write_text('{}')
            with self.assertRaises(ValueError):t.preflight()
        with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d,patch.object(t,'LOCAL',Path(d)),patch.object(t.shared,'read',return_value={'plan':{},'files':[{'path':'evaluation/fact_internal_flow_trial_v2.py','sha256':'wrong'}]}),patch.object(t,'validate_plan'):
            with self.assertRaises(ValueError):t.preflight()

if __name__=='__main__':unittest.main()
