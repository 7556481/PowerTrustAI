"""Offline application integration, no .env or network/paid model requests."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from backend.config import ServiceConfig
from backend.assembly import Bundle,ComponentFactory,ConfigurationError
from backend.service import ApplicationService,QueueFullError,ServiceUnavailable
from backend.store import RunStore,StorageError,BindingError
from backend.serialization import wire,safe
from backend.local_access import ProcessLease
from agents.fakes import make_fake_harness,FakeConfig
from core.models import TaskRequest,TaskMode,AnswerDraft,VerificationStatus

class FixtureFactory(ComponentFactory):
    def __init__(self,config,fake_config=FakeConfig()):super().__init__(config);self.fake_config=fake_config;self.created=[]
    def create(self,rid,observer):
        h=make_fake_harness(self.fake_config);h.observer=observer;self.created.append(h)
        return Bundle(h)

def task(existing=False):
    from uuid import uuid4
    t=uuid4().hex
    return TaskRequest(t,TaskMode.ASSESS_EXISTING if existing else TaskMode.QUESTION_ANSWER,
        'voltage_stability_reactive_support','synthetic_fixture: explain voltage',
        existing_answer=AnswerDraft(t+'-answer',1,'Reactive power affects voltage.') if existing else None)

async def terminal(service,rid):
    for _ in range(150):
        state=service.state(rid)
        if state['status'] not in ('queued','running'):return state
        await asyncio.sleep(.01)
    raise AssertionError('Run did not terminate')

class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        self.config=ServiceConfig(profile='synthetic_fixture',run_db=p/'runs.sqlite3',token_file=p/'token',queue_capacity=1)
        self.store=RunStore(self.config.run_db);self.factory=FixtureFactory(self.config)
        self.service=ApplicationService(self.config,self.store,self.factory)
    async def asyncTearDown(self):
        await self.service.stop();self.store.close();self.tmp.cleanup()

    async def test_two_modes_same_harness_and_durable_trace(self):
        await self.service.start()
        for existing in (False,True):
            rid=await self.service.submit(task(existing));state=await terminal(self.service,rid)
            result=self.service.result(rid)
            self.assertEqual(state['status'],'finished');self.assertEqual(result['execution']['required_stages_complete'],True)
            self.assertTrue(self.store.events(rid));self.assertTrue(self.store.objects(rid,'answer'))
            self.assertEqual(self.store.get(rid)['result']['run_id'],rid)
        self.assertEqual(len(self.factory.created),2)

    async def test_queue_full_persisted_and_cancel_frees_slot(self):
        rid=await self.service.submit(task())
        with self.assertRaises(QueueFullError):await self.service.submit(task())
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],1)
        await self.service.cancel(rid);self.assertEqual(self.service.state(rid)['status'],'cancelled')
        second=await self.service.submit(task());self.assertNotEqual(rid,second)

    async def test_active_cancel_keeps_valid_partial(self):
        self.factory.fake_config=FakeConfig(verification_delay=.5,domain_delay=.5)
        await self.service.start();rid=await self.service.submit(task())
        for _ in range(100):
            if self.service.state(rid)['harness_state']=='verifying':break
            await asyncio.sleep(.01)
        cancel=await self.service.cancel(rid);self.assertFalse(cancel['termination_guaranteed'])
        state=await terminal(self.service,rid);self.assertEqual(state['status'],'cancelled')
        self.assertTrue(self.store.objects(rid,'answer'));self.assertTrue(self.store.objects(rid,'claim'))
        self.assertEqual(self.service.result(rid)['execution']['required_stages_complete'],False)

    async def test_restart_marks_queued_and_running_interrupted_no_replay(self):
        a=await self.service.submit(task());b='saved-running';self.store.create(b,task(),self.factory.manifest(None));self.store.mark(b,'running')
        await self.service.start()
        self.assertEqual(self.service.state(a)['status'],'interrupted');self.assertEqual(self.service.state(b)['status'],'interrupted')
        self.assertFalse(self.factory.created)

    async def test_peer_review_survives_failure(self):
        self.factory.fake_config=FakeConfig(verification_error=True)
        await self.service.start();rid=await self.service.submit(task());await terminal(self.service,rid)
        result=self.service.result(rid)
        self.assertFalse(result['execution']['required_stages_complete']);self.assertTrue(result['findings']['domain'])
        self.assertEqual(result['decision']['kind'],'review_required')

    async def test_revision_versions_and_feedback_binding(self):
        self.factory.fake_config=FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,VerificationStatus.SUPPORTED))
        await self.service.start();rid=await self.service.submit(task(True));await terminal(self.service,rid)
        result=self.service.result(rid);answers=result['answer']['versions'];self.assertEqual([a['version'] for a in answers],[1,2])
        orig=json.dumps(self.store.get(rid)['result'],sort_keys=True)
        fid=result['findings']['model_fact'][0]['finding_id'];a=result['answer']['final']
        feedback={'answer_id':a['answer_id'],'answer_version':a['version'],'finding_id':fid,'action':'pending','source':'ai_assisted_user_supervised','reviewer_id':'local','note':'synthetic_fixture'}
        self.store.add_review(rid,feedback)
        with self.assertRaises(BindingError):self.store.add_review(rid,dict(feedback,answer_version=1))
        self.store.add_review(rid,dict(feedback,action='note'))
        self.assertEqual(len(self.store.reviews(rid)),2);self.assertEqual(orig,json.dumps(self.store.get(rid)['result'],sort_keys=True))

    async def test_checkpoint_failure_stops_and_reports_not_durable(self):
        await self.service.start()
        with patch.object(self.store,'checkpoint',side_effect=StorageError('synthetic storage failure')):
            rid=await self.service.submit(task());state=await terminal(self.service,rid)
        self.assertEqual(state['error_code'],'RUN_STORAGE_FAILED');self.assertFalse(state['persistence_confirmed'])
        self.assertFalse(self.factory.created[0].generation.inputs)
        with self.assertRaises(ServiceUnavailable):await self.service.submit(task())

    async def test_create_transaction_failure_no_acceptance(self):
        self.store.db.execute("CREATE TRIGGER fail_input BEFORE INSERT ON runs BEGIN SELECT RAISE(ABORT,'synthetic_fixture'); END")
        with self.assertRaises(StorageError):await self.service.submit(task())
        self.assertTrue(self.service.queue.empty());self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],0)

    async def test_evidence_run_scope(self):
        await self.service.start();rid=await self.service.submit(task());await terminal(self.service,rid)
        e=self.store.objects(rid,'evidence')[0]
        other='other-run';self.store.create(other,task(),self.factory.manifest(None))
        self.assertEqual(self.store.evidence(rid,e['evidence_id'])['text'],e['text'])
        with self.assertRaises(KeyError):self.store.evidence(other,e['evidence_id'])

    async def test_real_scalar_tool_results_persist_without_paid_models(self):
        from tools.unit_conversion import UnitConversionTool
        self.factory.fake_config=FakeConfig(text='230 kV equals 230000 V.')
        make=self.factory.create
        def create(rid,observer):
            bundle=make(rid,observer);bundle.harness.unit_tool=UnitConversionTool(version='scalar-si-conversion-v2');return bundle
        self.factory.create=create
        await self.service.start();rid=await self.service.submit(task());await terminal(self.service,rid)
        result=self.service.result(rid)
        self.assertEqual(result['budget_usage']['actual_model_request_records'],0)
        self.assertGreater(result['budget_usage']['tool_calls'],0)
        self.assertEqual(len(result['findings']['tools']),len(self.store.objects(rid,'tool')))
        self.assertTrue(any(t['payload']['output_value']==230000 for t in result['findings']['tools']))

    async def test_completed_sibling_visible_while_other_review_pending(self):
        self.factory.fake_config=FakeConfig(verification_delay=.4,domain_delay=.01)
        await self.service.start();rid=await self.service.submit(task())
        for _ in range(100):
            stages=self.store.events(rid)
            if any(s['event']['component']=='power_domain_review' and s['stage_output'] for s in stages):break
            await asyncio.sleep(.01)
        partial=self.service.result(rid)
        self.assertEqual(partial['execution']['status'],'running');self.assertTrue(partial['execution']['partial_only'])
        self.assertTrue(partial['findings']['domain']);await terminal(self.service,rid)

class AssemblyTests(unittest.TestCase):
    def test_real_assembly_explicit_schema13_and_no_model_fallback(self):
        from rag.storage import KnowledgeStore
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);md=p/'fixture.md';md.write_text('# synthetic_fixture\n\nVoltage evidence.',encoding='utf-8')
            with KnowledgeStore(p/'knowledge.sqlite3') as index:k=index.ingest(md,'synthetic_fixture').knowledge_version
            config=ServiceConfig(index_db=p/'knowledge.sqlite3',knowledge_version=k,verification_schema=13)
            factory=ComponentFactory(config)
            with patch.dict('os.environ',{},clear=True):
                with self.assertRaises(ConfigurationError):factory.preflight()
            with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fictional-key-not-real','DEEPSEEK_MODEL_ID':'deepseek-flash'},clear=True),patch('model_adapter.deepseek.create_adapter',side_effect=lambda s:MagicMock()) as adapter:
                self.assertEqual(factory.preflight(),k);bundle=factory.create('fixture',lambda s:None)
                h=bundle.harness
                self.assertEqual(h.verification.schema_version,13);self.assertEqual(h.extractor.protocol_version,7)
                self.assertEqual(h.generation.schema_version,3);self.assertEqual(h.domain_review.protocol_version,5)
                self.assertEqual(h.revision.protocol_version,2);self.assertIsNotNone(h.unit_tool)
                self.assertEqual(adapter.call_count,2);bundle.close()

    def test_exclusive_process_lease(self):
        with tempfile.TemporaryDirectory() as d:
            a=ProcessLease(Path(d)/'lock');b=ProcessLease(Path(d)/'lock')
            a.acquire()
            try:
                with self.assertRaises(RuntimeError):b.acquire()
            finally:a.close()

    def test_public_projection_preserves_original_and_hides_archive_paths(self):
        source={'text':'exact evidence original','diagnostic_path':'D:/private/raw.json','detail':json.dumps({'input_snapshot_path':'D:/private/input.json'}),'message':'Failure D:/private/file.db'}
        projected=safe(source)
        self.assertEqual(projected['text'],source['text']);self.assertNotIn('D:/',json.dumps(projected));self.assertNotIn('diagnostic_path',projected)

