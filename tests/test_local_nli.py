"""Public synthetic sidecar scope/lifecycle/storage tests; no paid calls."""
import asyncio,json,tempfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
import unittest
from backend.config import ServiceConfig
from backend.store import RunStore,BindingError
from backend.service import ApplicationService
from backend.serialization import wire
from services.local_nli import LocalNLI,production_frames_v1 as production_frames,frame
from tests import test_support_nli as fixtures
from tests.test_local_service import task,terminal


def frozen_raw():
    text='Only when connected, 5 MW is not 5 MVA.'
    claim={'claim_id':'c','answer_id':'a','answer_version':1,'text':'5 MW is not 5 MVA when connected.',
        'assertion_role':'asserted','qualifiers':['Only when connected'],'components':[{'component_id':'p','category':'fixture','proposition':'5 MW is not 5 MVA when connected.'}],'component_basis_targets':['document_body']}
    evidence={'evidence_id':'e','source_id':'fixture-doc','source_version':'v1','text':text,'applicability':['fixture-scope'],'provenance':{'document_title':'Fixture'}}
    verification={'answer_id':'a','answer_version':1,'input_body_delivered':True,'claims':[claim],'evidence':[evidence,dict(evidence,evidence_id='unrelated',text='NOT_DELIVERED')],
        'quote_candidates':[{'quote_id':'q','evidence_id':'e','method':'whole_fragment','text':text,'start_offset':0,'end_offset':len(text)}],
        'findings':[{'claim_id':'c','status':'supported','component_reviews':[{'component_id':'p','status':'supported'}]}]}
    mapping={'answer_id':'a','answer_version':1,'claim_id':'c','component_id':'p','basis_target':'document_body','knowledge_version':'k-fixture','outcome':'hits','delivered_evidence_ids':['e']}
    verification['delivery_summary']=json.dumps({'fact_bindings':[mapping]})
    return {'run_id':'r','answer':{'answer_id':'a','version':1,'text':'fixture answer'},'extraction_output':{'claims':[claim]},'verification_output':verification,'retrieval_records':[{'fact_bindings':[mapping]}]}

class ScopeTests(unittest.TestCase):
    def test_worker_protocol_preserves_utf8_body_exactly(self):
        from backend.nli_worker import decode_request
        original={'pair':{'premise':'500 MVA / 100 MW = 5; curly ’ and ≥; 条件不删除',
                          'hypothesis':'Only if supplied by power electronics.'}}
        self.assertEqual(decode_request(json.dumps(original,ensure_ascii=False).encode('utf-8')),original)
    def test_only_explicit_delivery_not_pool_or_model_basis(self):
        raw=frozen_raw();a=production_frames(raw)[0]
        self.assertEqual(len(a['sample']['task']['evidence']),1)
        self.assertNotIn('NOT_DELIVERED',str(a['sample']))
        raw['verification_output']['findings'][0]['evidence_ids']=['unrelated']
        self.assertEqual(a['sample']['task'],production_frames(raw)[0]['sample']['task'])
        self.assertIn('Only when connected',a['sample']['task']['claim']['qualifiers'])
    def test_version_body_mapping_and_type_fail_closed(self):
        for mode in ('version','mapping','type','stance','candidate','snapshot','not_assessable'):
            r=frozen_raw()
            if mode=='version':r['extraction_output']['claims'][0]['answer_version']=2
            elif mode=='mapping':r['retrieval_records']=[]
            elif mode=='type':r['extraction_output']['claims'][0]['component_basis_targets']=['metadata']
            elif mode=='stance':r['extraction_output']['claims'][0]['assertion_role']='reported_not_asserted'
            elif mode=='candidate':r['verification_output']['quote_candidates']=[]
            elif mode=='snapshot':r['verification_output']['delivery_summary']=''
            else:r['verification_output']['findings'][0]['component_reviews'][0]['status']='not_assessable'
            self.assertIn('skip_reason',production_frames(r)[0])

class FakeProcess:
    def __init__(self,result=None,fail=False):
        self.stdin=self;self.stdout=self;self.returncode=None;self.result=result;self.fail=fail;self.requests=0
    def write(self,value):self.requests+=1
    async def drain(self):pass
    async def readline(self):
        if self.fail:raise RuntimeError('fixture failure')
        return json.dumps(self.result).encode()
    def kill(self):self.returncode=-1
    async def wait(self):return self.returncode

class SidecarTests(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_task_does_not_send_a_model_request(self):
        engine=LocalNLI(ServiceConfig());engine.process=FakeProcess()
        sample=fixtures.NLIBoundaries().fixture();sample['task']['task_type']='scalar_calculation'
        item=frame(sample,run_id='r',answer_id='a',answer_version=1,claim_id='c',component_id='p')
        self.assertEqual((await engine.diagnose(item))['reason'],'unsupported_task_type')
        self.assertEqual(engine.process.requests,0)

    async def test_enabled_diagnostic_exception_leaves_finished_decision_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            config=ServiceConfig(profile='synthetic_fixture',run_db=Path(directory)/'runs.sqlite3',nli_enabled=True)
            store=RunStore(config.run_db);service=ApplicationService(config,store)
            with patch('services.local_nli.LocalNLI.start',new=AsyncMock()):
                await service.start()
            service.nli.diagnose=AsyncMock(side_effect=RuntimeError('fixture diagnostic failure'))
            rid=await service.submit(task());await terminal(service,rid)
            if service.nli_tasks:await asyncio.gather(*list(service.nli_tasks))
            self.assertEqual(store.get(rid)['status'],'finished')
            self.assertEqual(store.get(rid)['result']['report']['decision']['kind'],'pass')
            self.assertEqual(service.nli_result(rid)['error_code'],'diagnostic_conversion_or_storage_failed')
            await service.stop();store.close()
    async def test_skips_without_inference_and_failure_is_diagnostic_only(self):
        engine=LocalNLI(ServiceConfig());item=production_frames(frozen_raw())[0]
        engine.process=FakeProcess(fail=True);engine.identity={'fixture':True}
        r=await engine.diagnose(item);self.assertEqual(r['status'],'failed');self.assertFalse(r['affects_decision'])
        self.assertEqual(item['production_status'],'supported')
        skipped=await engine.diagnose(dict(item,skip_reason='unsupported_basis_target'))
        self.assertEqual(skipped['status'],'skipped')
    async def test_overlong_skip_and_disagreement_are_separate(self):
        item=production_frames(frozen_raw())[0];engine=LocalNLI(ServiceConfig())
        engine.process=FakeProcess({'status':'skipped','reason':'over_context_no_truncation','tokens':513,'context_limit':512})
        r=await engine.diagnose(item);self.assertEqual(r['tokens'],513);self.assertIsNone(r['nli_three_class_result'])
        engine.process=FakeProcess({'status':'complete','nli_three_class_result':'contradicted','logits':[2.,0.,-1.],'tokens':20})
        r=await engine.diagnose(item);self.assertTrue(r['disagreement']);self.assertFalse(r['affects_decision'])
    async def test_concurrency_busy_and_timeout_kill_only_owned_worker(self):
        engine=LocalNLI(replace(ServiceConfig(),nli_timeout_seconds=.01));item=production_frames(frozen_raw())[0]
        process=FakeProcess();engine.process=process
        await engine.lock.acquire()
        self.assertEqual((await engine.diagnose(item))['reason'],'local_concurrency_busy');engine.lock.release()
        async def blocked():await asyncio.sleep(10)
        process.readline=blocked
        r=await engine.diagnose(item);self.assertEqual(r['reason'],'local_inference_timeout');self.assertEqual(process.returncode,-1)
        other=LocalNLI(replace(ServiceConfig(),nli_timeout_seconds=.01));process=FakeProcess();other.process=process
        process.drain=blocked
        self.assertEqual((await other.diagnose(item))['reason'],'local_inference_timeout')
        self.assertEqual(process.returncode,-1)
    async def test_default_off_run_decision_unchanged_and_no_model_load(self):
        with tempfile.TemporaryDirectory() as directory:
            config=ServiceConfig(profile='synthetic_fixture',run_db=Path(directory)/'runs.sqlite3')
            store=RunStore(config.run_db);service=ApplicationService(config,store)
            with patch('services.local_nli.LocalNLI.start',side_effect=AssertionError('No default loading')):
                await service.start();rid=await service.submit(task());await terminal(service,rid)
                before=deepcopy(store.get(rid)['result']);self.assertIsNone(service.nli)
                diag=service.nli_result(rid);self.assertFalse(diag['enabled']);self.assertEqual(diag['records'],[])
                self.assertEqual(store.get(rid)['result'],before)
                await service.stop();store.close()
    async def test_append_binding_persist_restart_and_immutable_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runs.sqlite3';store=RunStore(path);raw=frozen_raw()
            store.create('r',{},{});store.mark('r','finished',result=raw)
            before=store.get('r')['result']
            engine=LocalNLI(ServiceConfig());engine.process=FakeProcess({'status':'complete','nli_three_class_result':'supported','logits':[0.,1.,0.]})
            record=await engine.diagnose(production_frames(raw)[0]);store.add_nli_diagnostic('r',record)
            with self.assertRaises(BindingError):store.add_nli_diagnostic('r',dict(record,answer_version=2))
            with self.assertRaises(BindingError):store.add_nli_diagnostic('r',dict(record,affects_decision=True))
            self.assertEqual(store.get('r')['result'],before);store.close();store=RunStore(path)
            self.assertEqual(store.objects('r','nli_diagnostic')[0]['input_id'],record['input_id']);store.close()

if __name__=='__main__':unittest.main()
