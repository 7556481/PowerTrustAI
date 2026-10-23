"""Offline authorized-entry gates; no credentials or network."""
import json,tempfile,socket,unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import asdict
from evaluation import public_review_object_trial_v1 as trial
from evaluation.public_review_object_materials_v1 import build_inputs,identities,read,check
from model_adapter.contracts import ModelResponse,ModelRequest,ModelMessage
from tests.test_public_review_object_v2 import Adapter
from agents.generation import messages_for
from agents.fakes import make_fake_harness,FakeConfig
from core.models import VerificationStatus

class Bad:
    calls=0
    async def complete(self,request):self.calls+=1;return ModelResponse('{bad')
    def close(self):pass

def freeze():return {'order':identities(build_inputs(read('inputs-r1.json'))[0])[0]}
class Gates(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.guard=patch.object(socket.socket,'connect',side_effect=AssertionError('offline'));self.guard.start();self.addCleanup(self.guard.stop)
        t=tempfile.TemporaryDirectory(dir=trial.ROOT/'data/retrieval_local',prefix='object-entry-');self.addCleanup(t.cleanup);self.root=Path(t.name)
    async def test_lengths_and_prepared_hashes(self):
        # Old authorization is not reusable after source evolution.
        with self.assertRaisesRegex(ValueError,'Approved materials/source unchanged'):check()
        from evaluation import public_review_object_materials_v1 as materials
        original=materials.read
        def fixture_read(name):
            value=original(name)
            if name=='freeze-plan-v1.json':value={**value,'bound_files':[]}
            return value
        # Independently retain all literal length/input/message/injection assertions.
        with patch.object(materials,'read',side_effect=fixture_read):check()
    async def test_final_generation_failure_stops_all_later(self):
        adapters=[]
        def factory():a=Bad();adapters.append(a);return a
        s=await trial.run_batch(freeze(),self.root/'batch',self.root/'responses',factory)
        self.assertEqual([b['status'] for b in s['branches']],['execution_failed','unexecuted','unexecuted'])
        self.assertEqual(sum(a.calls for a in adapters),2)
    async def test_presend_storage_or_identity_failure_never_calls_delegate(self):
        from time import perf_counter
        v=build_inputs(read('inputs-r1.json'))[0]['OB2-01'];case=freeze()['order'][0]
        for storage in (True,False):
            a=Bad();state={'started':perf_counter(),'request':v.request,'send_sequence':0,'sent':[]}
            guard=trial.GuardedAdapter(a,case,v,state,self.root)
            req=ModelRequest('deepseek-flash',messages_for(v,3,product_guidance=True) if storage else (ModelMessage('user','wrong'),),8000,trial.GENERATION_PROMPT)
            with patch.object(trial,'write',side_effect=OSError('offline fixture')):
                with self.assertRaises(trial.PreSendStorageFailure if storage else trial.PreSendFailure):await guard.complete(req)
            self.assertEqual(a.calls,0)
    async def test_full_candidate_three_branches_injection_has_no_extraction_call(self):
        class Model(Adapter):
            def close(self):pass
            async def complete(self,request):
                if request.prompt_version==trial.GENERATION_PROMPT:
                    return ModelResponse(json.dumps({'answer_units':[
                        {'kind':'technical','text':'样品得分为71分。','evidence_ids':[]},
                        {'kind':'technical','text':'达到64分允许省略Q。','evidence_ids':['OB2-E1']},
                        {'kind':'technical','text':'本题71分故允许省略Q。','evidence_ids':[]}],
                        'assumptions':[],'missing_information':[],'evidence_sufficient':True},ensure_ascii=False))
                return await super().complete(request)
        s=await trial.run_batch(freeze(),self.root/'batch',self.root/'responses',Model)
        self.assertEqual([b['status'] for b in s['branches']],['complete']*3)
        third=s['branches'][2]
        self.assertEqual(len(third['sent']),2)
        self.assertFalse(any(x['prompt_version'] in (trial.GENERATION_PROMPT,trial.EXTRACTION_PROMPT) for x in third['sent']))
        self.assertIsNone(third['result']['generation_output'])
        self.assertIsNone(third['result']['verification_output']['generation_snapshot'])
        self.assertEqual(third['result']['extraction_output']['claims'][0]['component_objects'],['scenario_application'])
    async def test_semantic_review_continues_storage_failure_stops(self):
        def factory(c,v,o,s,a,d):
            h=make_fake_harness(FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)));h.observer=o;return h
        s=await trial.run_batch(freeze(),self.root/'ok',self.root/'responses',Bad,factory)
        self.assertEqual([b['status'] for b in s['branches']],['complete']*3)
        write=trial.write
        def fail(p,v):
            if Path(p).name=='final-result.json':raise OSError('fixture')
            return write(p,v)
        with patch.object(trial,'write',side_effect=fail):
            s=await trial.run_batch(freeze(),self.root/'fail',self.root/'r2',Bad,factory)
        self.assertEqual([b['status'] for b in s['branches']],['execution_failed','unexecuted','unexecuted'])
    async def test_attempt_is_not_resumable(self):
        f={'owner_authorized':True,'per_branch_model_calls':40,'batch_call_cap':None,'bound_files':[]}
        p=self.root/'freeze.json';d=self.root/'batch';trial.write(p,f);trial.write(d/'freeze.json',f)
        with patch.object(trial,'FREEZE',p),patch.object(trial,'DIRECTORY',d):
            self.assertEqual(trial.preflight(),f);trial.write(d/'attempt.json',{})
            with self.assertRaises(ValueError):trial.preflight()
if __name__=='__main__':unittest.main()
