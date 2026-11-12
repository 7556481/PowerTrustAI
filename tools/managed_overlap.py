"""Managed explicit Factory selector. Default ordinary; no environment feature switch."""
import argparse,threading,json,time
from pathlib import Path
from dataclasses import replace
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from evaluation.fact_domain_overlap_v23 import OverlapFactory
from backend.api import create_app
from backend.launcher import open_local,stop_local,health_at
class ManagedFactory(OverlapFactory):
 def __init__(self,config,selection):super().__init__(config);self.selection=selection
 def manifest(self,*a,**kw):
  v=super().manifest(*a,**kw);v['managed_factory']={'selection':self.selection,'overlap_requested':self.selection=='overlap','version':'explicit-factory-v24'};return v
 def create(self,rid,observer,**kw):
  b=OverlapFactory.create(self,rid,observer,**kw) if self.selection=='overlap' else ComponentFactory.create(self,rid,observer,**kw)
  trace=self.config.run_db.parent/'managed-overlap-events.jsonl';lock=threading.Lock()
  def emit(kind,**details):
   with lock:
    with trace.open('a',encoding='utf8') as f:f.write(json.dumps(dict(run_id=rid,kind=kind,wall=time.time(),**details))+'\n')
  emit('factory_created',selection=self.selection,enabled=getattr(b.harness,'fact_domain_retrieval_overlap',False))
  retriever=b.harness.retriever
  if retriever is not None:
   original=retriever.retrieve
   async def retrieve(r):
    emit('retrieval_start',purpose=r.purpose.value)
    try:return await original(r)
    finally:emit('retrieval_return',purpose=r.purpose.value)
   retriever.retrieve=retrieve
  from model_adapter.runtime import current_model_invocation
  def tag(client):
   previous=client.complete;adapter=client.adapter;target=getattr(adapter,'delegate',adapter)
   async def complete(*a,**kw):
    owner=current_model_invocation();target._managed_role=None if owner is None else owner[1]
    try:return await previous(*a,**kw)
    finally:target._managed_role=None
   client.complete=complete
  for agent in (b.harness.generation,b.harness.extractor,b.harness.verification,b.harness.revision):tag(agent.client)
  model=b.harness.verification.client.adapter;delegate=getattr(model,'delegate',model)
  if hasattr(delegate,'_exchange'):
   original_exchange=delegate._exchange
   def exchange(*a,**kw):
    if getattr(delegate,'_managed_role',None)=='evidence_verification':emit('fact_http_worker_begin')
    return original_exchange(*a,**kw)
   delegate._exchange=exchange
  return b

def main():
 import uvicorn
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--factory',choices=('component','overlap'),default='component')
 parser.add_argument('--port',type=int,default=8778)
 parser.add_argument('--store',type=Path)
 parser.add_argument('--budget-dir',type=Path)
 parser.add_argument('--model-cap',type=int,default=16);parser.add_argument('--token-cap',type=int,default=300000)
 parser.add_argument('--open',action='store_true');parser.add_argument('--stop',action='store_true');args=parser.parse_args()
 if not 1024<=args.port<=65535:parser.error('Unprivileged local port required')
 c=ServiceConfig.from_environment()
 if args.store:c=replace(c,run_db=args.store.resolve(),token_file=args.store.resolve().parent/'access-token')
 if args.budget_dir:
  from model_adapter.call_budget_v1 import FullBudget,_GATES
  if not 1<=args.model_cap<=16 or not 1<=args.token_cap<=300000:parser.error('Limited release allowance may not exceed16 calls/300000 tokens')
  root=args.budget_dir.resolve();gate=FullBudget(root,cap=args.model_cap,threshold=args.token_cap);_GATES[str(root)]=gate;gate.save();c=replace(c,model_budget_dir=root)
 origin=f'http://127.0.0.1:{args.port}'
 if args.stop:stop_local(c,origin);return
 if args.open:
  if health_at(origin):open_local(c,origin);return
  threading.Thread(target=open_local,args=(c,origin),daemon=True).start()
 server=None
 def shutdown():server.should_exit=True
 server=uvicorn.Server(uvicorn.Config(create_app(c,factory=ManagedFactory(c,args.factory),shutdown=shutdown),host='127.0.0.1',port=args.port,workers=1,access_log=False));server.run()
if __name__=='__main__':main()
