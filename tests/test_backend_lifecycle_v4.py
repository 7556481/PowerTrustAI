"""Bounded synthetic lifecycle faults; no environment, models or production DB."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agents.fakes import make_fake_harness, FakeConfig
from backend.assembly import Bundle, ComponentFactory, ResourceCleanupError
from backend.config import ServiceConfig
from backend.service import ApplicationService, ServiceUnavailable
from backend.store import RunStore, StorageError
from tests.test_local_service import task


class LifecycleFactory(ComponentFactory):
    def __init__(self,config,mode='normal'):
        super().__init__(config);self.mode=mode;self.created=[]
        self.cleanup_entered=asyncio.Event();self.cleanup_release=asyncio.Event()
        self.before_cleanup=None;self.close_calls=0

    def create(self,rid,observer):
        h=make_fake_harness(FakeConfig(verification_error=self.mode=='component_error'))
        h.observer=observer;h.execution_path=self.config.execution_path;self.created.append(rid)
        if self.mode=='no_answer':
            original=h.generation.run
            async def generate(inputs):
                value=await original(inputs)
                return replace(value,substantive_answer=False,answer=replace(value.answer,
                    text='synthetic_fixture: required evidence unavailable.',missing_information=('Required source missing',)))
            h.generation.run=generate
        bundle=Bundle(h)
        if self.mode in ('close_error','drain_error'):
            async def drain():
                self.cleanup_entered.set();await self.cleanup_release.wait()
                if self.mode=='drain_error':raise RuntimeError('synthetic drain fault; do not expose this message')
            def close():
                self.close_calls+=1
                if self.mode=='close_error':raise RuntimeError('synthetic close fault; do not expose this message')
            bundle.drain=drain;bundle.close=close
        return bundle


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();p=Path(self.temp.name)
        self.config=ServiceConfig(profile='synthetic_fixture',run_db=p/'runs.sqlite3',token_file=p/'unused',queue_capacity=2)
        self.store=RunStore(self.config.run_db);self.factory=LifecycleFactory(self.config)
        self.service=ApplicationService(self.config,self.store,self.factory)

    async def asyncTearDown(self):
        self.factory.cleanup_release.set()
        await self.service.stop();self.store.close();self.temp.cleanup()

    async def finish_worker(self):
        await asyncio.wait_for(asyncio.shield(self.service.worker),2)

    async def test_close_fault_rejects_new_and_retires_waiting_without_changing_saved_result(self):
        self.factory.mode='close_error';await self.service.start()
        first=await self.service.submit(task());await asyncio.wait_for(self.factory.cleanup_entered.wait(),2)
        saved=json.dumps(self.store.get(first)['result'],sort_keys=True)
        waiting=await self.service.submit(task());self.factory.cleanup_release.set()
        try:await self.finish_worker()
        except RuntimeError:pass  # Baseline worker actually raises; assertions below must fail before repair.
        print(json.dumps(dict(case='close_fault',worker_done=self.service.worker.done(),active_stale=self.service.active is not None,
                              storage_fault=self.service.storage_fault,queued=self.service.queue.qsize()),sort_keys=True))
        with self.assertRaises(ServiceUnavailable):await self.service.submit(task())
        self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        self.assertEqual(json.dumps(self.store.get(first)['result'],sort_keys=True),saved)
        self.assertEqual(self.service.state(first)['status'],'finished')
        self.assertIsNone(self.service.active);self.assertIsNone(self.service.active_bundle)
        await asyncio.wait_for(self.service.queue.join(),1)
        self.assertEqual(self.factory.created,[first]);self.assertFalse(self.service.storage_fault)

    async def gated_pair(self,mode):
        self.factory.mode=mode;await self.service.start();first=await self.service.submit(task())
        await asyncio.wait_for(self.factory.cleanup_entered.wait(),2)
        saved=json.dumps(self.store.get(first)['result'],sort_keys=True)
        waiting=await self.service.submit(task())
        return first,waiting,saved

    async def test_drain_fault_defers_close_and_retires_waiting(self):
        first,waiting,saved=await self.gated_pair('drain_error')
        self.factory.cleanup_release.set();await self.finish_worker()
        self.assertEqual(self.factory.close_calls,0)
        self.assertEqual(self.service.lifecycle_fault,'RESOURCE_DRAIN_FAILED')
        self.assertEqual(len(self.service.undrained_bundles),1)
        self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        self.assertEqual(json.dumps(self.store.get(first)['result'],sort_keys=True),saved)
        self.assertIsNone(self.service.active_bundle);await asyncio.wait_for(self.service.queue.join(),1)
        self.factory.mode='normal';await self.service.stop();await self.service.stop()
        self.assertEqual(self.factory.close_calls,1);self.assertFalse(self.service.undrained_bundles)

    async def test_timing_storage_fault_preserves_result_and_stops_next_task(self):
        first,waiting,saved=await self.gated_pair('close_error');self.factory.mode='normal'
        with patch.object(self.store,'add_retrieval_timing',side_effect=StorageError('synthetic timing storage')):
            self.factory.cleanup_release.set();await self.finish_worker()
        self.assertTrue(self.service.storage_fault);self.assertIsNone(self.service.lifecycle_fault)
        self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        self.assertEqual(self.service.state(waiting)['error_code'],'RUN_STORAGE_FAILED')
        self.assertEqual(json.dumps(self.store.get(first)['result'],sort_keys=True),saved)
        self.assertTrue(self.service.state(first)['persisted_result_available'])
        with self.assertRaises(ServiceUnavailable):await self.service.submit(task())
        await asyncio.wait_for(self.service.queue.join(),1)

    async def test_unwritable_waiting_terminal_reports_unconfirmed_then_explicit_reopen_recovers(self):
        first,waiting,saved=await self.gated_pair('close_error');original=self.store.mark
        def mark(rid,*a,**kw):
            if rid==waiting:raise StorageError('synthetic unavailable write')
            return original(rid,*a,**kw)
        with patch.object(self.store,'mark',side_effect=mark):
            self.factory.cleanup_release.set();await self.finish_worker()
        state=self.service.state(waiting)
        self.assertEqual(state['status'],'queued');self.assertFalse(state['persistence_confirmed'])
        self.assertEqual(state['pending_terminal_status'],'interrupted')
        self.assertEqual(self.factory.created,[first]);await asyncio.wait_for(self.service.queue.join(),1)
        await self.service.stop();self.store.close();self.store=RunStore(self.config.run_db)
        self.factory=LifecycleFactory(self.config);self.service=ApplicationService(self.config,self.store,self.factory)
        await self.service.start();self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        self.assertEqual(self.factory.created,[])
        self.assertEqual(json.dumps(self.store.get(first)['result'],sort_keys=True),saved)

    async def test_unexpected_worker_exit_and_unstarted_service_reject_before_preflight(self):
        with patch.object(self.factory,'preflight',side_effect=AssertionError('must reject before preflight')):
            with self.assertRaises(ServiceUnavailable):await self.service.submit(task())
        release=asyncio.Event()
        async def unexpected():await release.wait();raise RuntimeError('private synthetic worker failure')
        self.service._worker=unexpected;await self.service.start();waiting=await self.service.submit(task())
        release.set()
        await asyncio.gather(self.service.worker,return_exceptions=True);await asyncio.sleep(0)
        self.assertEqual(self.service.lifecycle_fault,'WORKER_UNEXPECTED_EXIT')
        self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        with patch.object(self.factory,'preflight',side_effect=AssertionError('must reject early')):
            with self.assertRaises(ServiceUnavailable):await self.service.submit(task())
        await asyncio.wait_for(self.service.queue.join(),1)

    async def test_component_failure_does_not_disable_next_run(self):
        self.factory.mode='component_error';await self.service.start();first=await self.service.submit(task())
        await asyncio.wait_for(self.service.queue.join(),2)
        self.assertFalse(self.service.result(first)['execution']['required_stages_complete'])
        self.factory.mode='normal';second=await self.service.submit(task());await asyncio.wait_for(self.service.queue.join(),2)
        self.assertTrue(self.service.result(second)['execution']['required_stages_complete'])
        self.assertIsNone(self.service.lifecycle_fault);self.assertTrue(self.service.lifecycle_status()['accepting_work'])

    async def test_cleanup_exits_timing_in_same_task_exactly_once(self):
        from contextlib import contextmanager
        import rag.timing as timing
        original=timing.capture_timing;owners=[]
        @contextmanager
        def capture(**kw):
            owner=asyncio.current_task();owners.append(('enter',owner))
            try:
                with original(**kw) as log:yield log
            finally:owners.append(('exit',asyncio.current_task(),timing._log.get()))
        with patch.object(timing,'capture_timing',capture):
            first,waiting,saved=await self.gated_pair('close_error')
            self.factory.cleanup_release.set();await self.finish_worker()
        self.assertEqual(len(owners),2);self.assertIs(owners[0][1],owners[1][1]);self.assertIsNone(owners[1][2])
        self.assertEqual(len(self.store.objects(first,'retrieval_timing')),1)

    async def test_bundle_and_factory_close_try_all_resources_once(self):
        from types import SimpleNamespace
        attempts=[]
        def bad():attempts.append('bad');raise RuntimeError('do not leak details')
        good=SimpleNamespace(close=lambda:attempts.append('good'))
        bundle=Bundle(None,(SimpleNamespace(close=bad),good))
        with self.assertRaises(ResourceCleanupError) as error:bundle.close()
        bundle.close();self.assertEqual(attempts,['bad','good'])
        self.assertEqual(error.exception.failures,('RuntimeError',))
        encoder=SimpleNamespace(encoding_seconds=0,close=lambda:attempts.append('encoder'))
        self.factory.semantic_resource=SimpleNamespace(_active=None,query_encodings=0,validation_replays=0,encoder=encoder,close=bad)
        with self.assertRaises(ResourceCleanupError):await self.factory.close()
        self.assertEqual(attempts[-2:],['bad','encoder']);self.assertIsNone(self.factory.semantic_resource)

    async def test_start_failure_closes_factory_and_no_worker_is_admitted(self):
        closed=[]
        async def close():closed.append(True)
        with patch.object(self.factory,'initialize_retrieval',side_effect=RuntimeError('synthetic init')),patch.object(self.factory,'close',close):
            with self.assertRaises(RuntimeError):await self.service.start()
            await self.service.stop()
        self.assertEqual(closed,[True]);self.assertIsNone(self.service.worker)
        self.assertEqual(self.service.lifecycle_fault,'SERVICE_START_FAILED')

    async def test_admission_rechecks_after_awaited_preparation(self):
        entered=asyncio.Event();release=asyncio.Event()
        async def prepare():entered.set();await release.wait()
        await self.service.start()
        with patch.object(self.service,'nli_capability',return_value={'available':True}),patch.object(self.service,'ensure_nli',prepare):
            submitting=asyncio.create_task(self.service.submit(task(),nli_enabled=True));await entered.wait()
            self.service.worker.cancel();await asyncio.gather(self.service.worker,return_exceptions=True)
            release.set()
            with self.assertRaises(ServiceUnavailable):await submitting
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],0)

    async def active_pair(self):
        entered=asyncio.Event();release=asyncio.Event();original=self.factory.create
        def create(rid,observer):
            bundle=original(rid,observer);verify=bundle.harness.verification.run
            async def held(inputs):entered.set();await release.wait();return await verify(inputs)
            bundle.harness.verification.run=held;return bundle
        self.factory.create=create;await self.service.start();first=await self.service.submit(task())
        await asyncio.wait_for(entered.wait(),2);waiting=await self.service.submit(task())
        return first,waiting,release

    async def test_explicit_running_and_queued_cancel_remain_usable(self):
        first,waiting,release=await self.active_pair()
        await self.service.cancel(waiting);await self.service.cancel(first)
        await asyncio.wait_for(self.service.queue.join(),2)
        self.assertEqual(self.service.state(waiting)['status'],'cancelled')
        self.assertEqual(self.service.state(first)['status'],'cancelled')
        self.assertTrue(self.store.objects(first,'answer'));self.assertIsNone(self.service.lifecycle_fault)
        release.set();another=await self.service.submit(task());await asyncio.wait_for(self.service.queue.join(),2)
        self.assertTrue(self.service.result(another)['execution']['required_stages_complete'])

    async def test_stop_active_and_waiting_is_not_a_worker_crash_and_is_idempotent(self):
        first,waiting,release=await self.active_pair();closed=[]
        async def close():closed.append(True)
        with patch.object(self.factory,'close',close):
            await asyncio.wait_for(self.service.stop(),2);await self.service.stop()
        self.assertEqual(closed,[True]);self.assertIsNone(self.service.lifecycle_fault)
        self.assertEqual(self.service.state(first)['status'],'interrupted')
        self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        self.assertTrue(self.store.objects(first,'answer'));await asyncio.wait_for(self.service.queue.join(),1)

    async def test_unexpected_active_worker_cancellation_cannot_be_swallowed_by_harness(self):
        first,waiting,release=await self.active_pair();self.service.worker.cancel()
        await self.finish_worker()
        self.assertEqual(self.service.lifecycle_fault,'WORKER_UNEXPECTED_EXIT')
        self.assertEqual(self.service.state(waiting)['status'],'interrupted')
        self.assertTrue(self.store.objects(first,'answer'));self.assertEqual(self.factory.created,[first])
