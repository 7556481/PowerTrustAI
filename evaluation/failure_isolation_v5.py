"""Experiment-only one-unknown policy. Admission waits for actual resource release."""
import asyncio,time,json,threading
from uuid import uuid4
from evaluation.source_first_quality_v4 import Gate as PriorGate
from evaluation.source_first_live_v2 import OWNER
from evaluation.natural_draft_audit_v1 import save

class Gate(PriorGate):
    def __init__(self,root):
        super().__init__(root);self.unknown={};self.suspended=False;self.call_chains={};self.release_records=[]
    def __call__(self,spec,r,n):
        if self.suspended:raise RuntimeError('Physical release not yet certified; no next send')
        super().__call__(spec,r,n)
        self.call_chains[OWNER.get()]=(spec['case'],spec['variant'])
    def ambiguous(self,index,exc):
        with self.lock:
            self.unknown.setdefault(index,dict(kind=type(exc).__name__,released=False))
            self.suspended=True
            if len(self.unknown)>1 or not isinstance(exc,(asyncio.CancelledError,TimeoutError)):self.stopped=True
            self.event('unknown',dict(id=index,kind=type(exc).__name__,pending=sorted(self.pending),unknown_count=len(self.unknown),stopped=self.stopped))

class Accounted:
    def __init__(self,delegate,gate):self.delegate,self.gate=delegate,gate
    @property
    def _active(self):return getattr(self.delegate,'_active',None)
    def validate_request(self,r):
        fn=getattr(self.delegate,'validate_request',None)
        if fn:fn(r)
    def close(self):self.delegate.close()
    async def complete(self,r):
        index=OWNER.get()
        if index not in self.gate.pending:raise RuntimeError('No atomic send admission')
        self.delegate._v5_call_id=index
        try:
            response=await self.delegate.complete(r);self.gate.received(index,response);return response
        except BaseException as exc:
            self.gate.ambiguous(index,exc);raise

class Isolation:
    def __init__(self,gate,release_timeout=110):
        self.gate=gate;self.release_timeout=release_timeout;self.storage_failed=False;self.monitors={}
    def storage_failure(self):self.storage_failed=True;self.gate.stopped=True
    def pre_send_failure(self,exc):
        import sqlite3
        from backend.store import StorageError
        self.gate.stopped=True
        self.storage_failed=isinstance(exc,(OSError,sqlite3.Error,StorageError))
    async def finish(self,rid):
        monitor=self.monitors.pop(rid,None)
        if monitor:
            monitor.cancel();results=await asyncio.gather(monitor,return_exceptions=True)
            if any(isinstance(x,BaseException) and not isinstance(x,asyncio.CancelledError) for x in results):
                self.storage_failure();raise RuntimeError('Timing persistence failed')
    def begin(self,rid,spec):
        async def monitor():
            last=time.monotonic();maximum=0
            try:
                while True:
                    await asyncio.sleep(.1);now=time.monotonic();maximum=max(maximum,now-last-.1);last=now
            finally:save(self.gate.root/rid/'event-loop-lag.json',dict(max_lag_seconds=maximum,sample_seconds=.1))
        self.monitors[rid]=asyncio.create_task(monitor())
    def on_exception(self,spec,exc):
        allowed=isinstance(exc,(asyncio.CancelledError,TimeoutError)) and not self.gate.stopped
        if not allowed:self.gate.stopped=True
        return not allowed
    async def finalize(self,rid,spec,raw,bundle,store):
        await self.finish(rid)
        indices=[i for i in self.gate.unknown if self.gate.call_chains.get(i)==(spec['case'],spec['variant'])]
        if not indices:return
        started=time.monotonic();active_before=sum(getattr(r,'_active',None) is not None and not r._active.done() for r in bundle.resources)
        codes={x['code'] for x in raw['execution_issues']}
        safe=False;failure=None;work_done=closed=writable=False
        try:
            if not codes or not codes<= {'TIMEOUT','MODEL_TIMEOUT'} or self.storage_failed:raise RuntimeError('Not a classified local timeout')
            await asyncio.wait_for(bundle.drain(),self.release_timeout)
            if any(getattr(r,'_active',None) is not None and not r._active.done() for r in bundle.resources):raise RuntimeError('Physical work remains')
            work_done=True
            bundle.close() # Actual adapter close must succeed before new Factory.
            closed=True
            with store.tx():store.db.execute('UPDATE runs SET harness_state=harness_state WHERE id=?',(rid,))
            writable=True
            safe=True
        except BaseException as exc:
            failure=type(exc).__name__;self.gate.stopped=True
            if isinstance(exc,asyncio.CancelledError):raise
        receipt=dict(run_id=rid,call_ids=indices,active_before=active_before,physical_work_done=work_done,adapter_closed=closed,store_write_verified=writable,release_seconds=time.monotonic()-started,failure_type=failure)
        self.gate.release_records.append(receipt);self.gate.event('release',receipt)
        for i in indices:self.gate.unknown[i]['released']=safe
        if safe and len(self.gate.unknown)==1 and not self.gate.stopped:self.gate.suspended=False
        else:self.gate.stopped=True
        if self.gate.stopped:raw['execution_issues'].append(dict(component='service',code='SERVICE_EXECUTION_FAILED',message='v5 unreleased/shared fault or second unresolved call; stop'))

def observed_provider(gate,create_adapter):
    def provider(settings,**options):
        adapter=create_adapter(settings,**options);exchange=adapter._exchange
        def timed(body,timeout,limit,**kwargs):
            started=time.monotonic();status='succeeded';kind=None
            try:return exchange(body,timeout,limit,**kwargs)
            except BaseException as exc:status='failed';kind=type(exc).__name__;raise
            finally:
                save(gate.root/'transport'/(uuid4().hex+'.json'),dict(call_id=getattr(adapter,'_v5_call_id',None),thread_id=threading.get_ident(),start_monotonic=started,end_monotonic=time.monotonic(),status=status,exception_type=kind,socket_timeout=timeout,body_utf8_bytes=len(body),physical_exchange_exited=True))
        adapter._exchange=timed
        return adapter
    return provider
