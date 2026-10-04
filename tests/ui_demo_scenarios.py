"""Manual offline UI scenarios in the existing run store; server must be stopped.

No .env, model transport, production configuration changes or second database.
Reuses the tested service, Harness, fake components and process lease.
"""
import asyncio
import json
from backend.config import ServiceConfig,ROOT
from backend.store import RunStore
from backend.service import ApplicationService
from backend.local_access import ProcessLease
from tests.test_local_service import FixtureFactory,task,terminal
from agents.fakes import FakeConfig
from core.models import VerificationStatus

async def build():
    config=ServiceConfig(profile='synthetic_fixture')
    with_lease=ProcessLease(config.run_db.with_suffix('.process-lock'));with_lease.acquire()
    store=RunStore(config.run_db);factory=FixtureFactory(config);service=ApplicationService(config,store,factory)
    scenarios={}
    try:
        await service.start()
        factory.fake_config=FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED,VerificationStatus.SUPPORTED))
        rid=await service.submit(task(True));await terminal(service,rid);scenarios['revision_v1_v2']=rid
        factory.fake_config=FakeConfig(verification_error=True)
        rid=await service.submit(task());await terminal(service,rid);scenarios['partial_peer_review']=rid
        factory.fake_config=FakeConfig(verification_delay=.8,domain_delay=.01)
        rid=await service.submit(task())
        while service.state(rid)['harness_state']!='verifying':await asyncio.sleep(.01)
        await service.cancel(rid);await terminal(service,rid);scenarios['cancelled_partial']=rid
        original=factory.create
        def fail(*args):raise RuntimeError('synthetic_fixture execution failure')
        factory.create=fail
        rid=await service.submit(task());await terminal(service,rid);scenarios['failed']=rid
        factory.create=original;factory.fake_config=FakeConfig(text='<script>alert(1)</script><style>body{display:none}</style><img src=x onerror=alert(2)>')
        rid=await service.submit(task());await terminal(service,rid);scenarios['hostile_text']=rid
        factory.fake_config=FakeConfig(verification_delay=2,domain_delay=2)
        rid=await service.submit(task())
        while service.state(rid)['harness_state']!='verifying':await asyncio.sleep(.01)
        scenarios['interrupted_partial']=rid
        queued=await service.submit(task(True));scenarios['interrupted_queued']=queued
        await service.stop()
        rows={label:{'run_id':rid,'state':service.state(rid),'result':service.result(rid)} for label,rid in scenarios.items()}
        target=ROOT/'data/runtime_local/ui-v1-demo-scenarios.json'
        with target.open('x',encoding='utf-8') as f:json.dump({'profile':'synthetic_fixture','paid_calls':0,'scenarios':rows},f,ensure_ascii=False,indent=2)
        print(json.dumps({label:{'run_id':rid,'status':service.state(rid)['status']} for label,rid in scenarios.items()}))
    finally:
        if not service.closing:await service.stop()
        store.close();with_lease.close()

if __name__=='__main__':asyncio.run(build())
