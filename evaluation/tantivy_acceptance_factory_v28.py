"""Explicit isolated Factory for v28; normal API/Harness and shared accounting."""
import json,time,threading
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from backend.assembly import ComponentFactory,RetrieverLease
from evaluation.tantivy_acceptance_v28 import CandidateRetriever,enable_v18
from evaluation.tantivy_accounting_v28 import AccountedFlash
from model_adapter.runtime import current_model_invocation
from backend.serialization import wire
from services.request_metrics import measure
enable_v18() # Windows spawn must resolve the archived worker module before unpickling.
HOME=Path('D:/PowerTrustAI/data/runtime_local/tantivy-acceptance-v28')
GROUP=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-shards-v16/accepted-shard-group.json')
SPOOL=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1/spool.sqlite3')
class Probe:
    def __init__(self,delegate,factory,rid):self.delegate=delegate;self.factory=factory;self.rid=rid;self.component=None
    @property
    def _active(self):return getattr(self.delegate,'_active',None)
    def close(self):return self.delegate.close()
    async def complete(self,request):
        owner=current_model_invocation();component=None if owner is None else owner[1];self.component=component
        row={'kind':'model_dispatch','component':component,'prompt':request.prompt_version,'correction':request.correction,'time':time.perf_counter(),'metrics':measure(request.messages),'message_chars':sum(len(m.content) for m in request.messages)}
        self.factory.emit(self.rid,row)
        self.factory.save_private(self.rid,dict(row,messages=wire(request.messages)))
        try:
            response=await self.delegate.complete(request)
            self.factory.emit(self.rid,{'kind':'model_return','component':component,'time':time.perf_counter(),'usage':wire(response.usage),'correction':request.correction})
            return response
        except BaseException as exc:
            self.factory.emit(self.rid,{'kind':'model_error','component':component,'time':time.perf_counter(),'error':type(exc).__name__});raise

class AcceptanceFactory(ComponentFactory):
    def __init__(self,config,candidate=False,gate=None):
        super().__init__(config);self.candidate=candidate;self.gate=gate;self.native=None;self.candidate_reader=None;self.lock=threading.Lock()
    def emit(self,rid,row):
        with self.lock:
            with (self.config.run_db.parent/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(run_id=rid,**row),ensure_ascii=False)+'\n')
    def save_private(self,rid,row):
        with self.lock:
            with (self.config.run_db.parent/'messages-private.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(run_id=rid,**row),ensure_ascii=False)+'\n')
    def prepare(self):
        if self.candidate and self.native is None:
            enable_v18();from rag.tantivy_global_rank_v18 import GlobalIDFRetriever
            group=json.loads(GROUP.read_text(encoding='utf-8'))
            # Use the frozen spool identity from the original v20 configuration.
            spool=SPOOL
            self.native=GlobalIDFRetriever(self.config.index_db,group['manifests'],self.config.knowledge_version,spool_path=spool,memory_limit=2*1024**3,diagnostic_path=self.config.run_db.parent/'native-events.jsonl',trim_owned_working_set=True)
            assert self.native.manifest['members']['total']==24620947
            self.candidate_reader=CandidateRetriever(self.native);warm=self.native.warm()
            (self.config.run_db.parent/'native-startup.json').write_text(json.dumps(dict(warm=warm,spool=str(spool),group=str(GROUP)),indent=2))
    def create(self,rid,observer,**kwargs):
        from model_adapter.deepseek import create_adapter as original_adapter
        def adapter(settings,**kw):
            base=original_adapter(settings,**kw);accounted=base if self.gate is None else AccountedFlash(base,self.gate,rid);probe=Probe(accounted,self,rid)
            if hasattr(base,'_exchange'):
                exchange=base._exchange
                def traced(*args,**opts):
                    self.emit(rid,{'kind':'http_worker_begin','component':probe.component,'time':time.perf_counter()});return exchange(*args,**opts)
                base._exchange=traced
            return probe
        def observe(snapshot):
            value=wire(snapshot);result=observer(snapshot) if observer is not None else None
            self.emit(rid,{'kind':'checkpoint_saved','time':time.perf_counter(),'event':value['event'],'state':value['state'],'has_output':value.get('stage_output') is not None});return result
        with patch('model_adapter.deepseek.create_adapter',adapter):bundle=super().create(rid,observe,**kwargs)
        bundle.harness.fact_domain_retrieval_overlap=True
        if self.candidate and bundle.harness.retriever is not None:
            if self.candidate_reader is None:raise RuntimeError('Candidate must be prepared before admission')
            old=bundle.harness.retriever;old.close();bundle.resources.remove(old);bundle.resources.append(RetrieverLease(self.candidate_reader));bundle.harness.retriever=self.candidate_reader
        reader=bundle.harness.retriever
        if reader is not None:
            # Per-bundle lease avoids retaining wrappers across tasks on the shared reader.
            class TraceReader:
                def __getattr__(inner,name):return getattr(reader,name)
                async def retrieve(inner,request):
                    self.emit(rid,{'kind':'retrieval_start','time':time.perf_counter(),'purpose':request.purpose.value})
                    try:
                        result=await reader.retrieve(request)
                        self.emit(rid,{'kind':'retrieval_return','time':time.perf_counter(),'purpose':request.purpose.value,'trace':getattr(reader,'last_trace',{}),'evidence_ids':[e.evidence_id for e in result.evidence]});return result
                    except BaseException as exc:
                        self.emit(rid,{'kind':'retrieval_error','time':time.perf_counter(),'purpose':request.purpose.value,'error':type(exc).__name__});raise
            bundle.harness.retriever=TraceReader()
        self.emit(rid,{'kind':'factory_created','time':time.perf_counter(),'candidate':self.candidate,'overlap':True,'fact_execution':self.config.fact_review_execution})
        return bundle
    async def close(self):
        if self.native is not None:self.native.close();self.native=None
        await super().close()
