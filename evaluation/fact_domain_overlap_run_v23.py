"""Frozen same-draft API experiment. Offline archive first; real mode separately gated."""
import asyncio,json,time,sqlite3,hashlib,os,contextlib
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation.fact_domain_overlap_v23 import OverlapFactory
from evaluation.tantivy_product_v19 import configs,LOCAL as PRIOR
from evaluation.archive_replay import restore
from harness.evidence_review_demo import restore_answer,restore_snapshot
from core.models import TaskRequest,TaskMode
from model_adapter.contracts import ModelResponse,ModelMessage
from model_adapter.runtime import current_model_invocation
from services.request_metrics import measure
HOME=PRIOR.parent/'fact-domain-overlap-v23'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def key(messages,prompt,correction):
 scopes=measure(messages)['scope_ids']
 return (prompt,correction,tuple(scopes))
class ArchiveProvider:
 def __init__(self,catalog):self.catalog=catalog;self.used={}
 def close(self):pass
 async def complete(self,r):
  k=key(r.messages,r.prompt_version,r.correction);items=self.catalog[k];n=self.used.get(k,0);self.used[k]=n+1
  return ModelResponse(items[min(n,len(items)-1)],r.model_id,finish_reason='stop')
class Probe:
 def __init__(self,inner,events,messages):self.inner=inner;self.events=events;self.messages=messages
 async def complete(self,r):
  owner=current_model_invocation();self.events.append(dict(kind='request_dispatch',component=None if owner is None else owner[1],time=time.monotonic(),correction=r.correction))
  self.messages.append(dict(component=None if owner is None else owner[1],prompt=r.prompt_version,correction=r.correction,messages=wire(r.messages),metrics=measure(r.messages)))
  base=getattr(self.inner,'delegate',self.inner)
  base._v23_component=None if owner is None else owner[1]
  try:return await self.inner.complete(r)
  finally:self.events.append(dict(kind='request_settled',component=None if owner is None else owner[1],time=time.monotonic(),correction=r.correction))
 def close(self):return self.inner.close()
def materials():
 out={}
 for pair in read(PRIOR/'summary.json')['pairs']:
  case=pair['case'];pub=read(PRIOR/(case+'-baseline-result.json'));rid=pub['execution']['run_id'];db=sqlite3.connect('file:'+str(PRIOR/'baseline/runs.sqlite3')+'?mode=ro',uri=True);raw,request=db.execute('select result,request from runs where id=?',(rid,)).fetchone();db.close();raw=json.loads(raw)
  gen=raw['generation_output'];answer=restore_answer(gen['answer']);snapshot=restore_snapshot(gen['evidence_snapshot']);assert wire(answer)==pub['answer']['versions'][0]
  task=replace(restore(json.loads(request),TaskRequest),mode=TaskMode.ASSESS_EXISTING,existing_answer=answer,provided_evidence=snapshot.evidence)
  catalog={}
  for p in (Path('data/retrieval_local/service_private')/rid).glob('response-*.json'):
   d=read(p)
   if not d.get('request_messages_path'):continue
   req=read(d['request_messages_path']);messages=tuple(ModelMessage(**m) for m in req['messages']);catalog.setdefault(key(messages,d['prompt_version'],d['correction']),[]).append((d.get('call_number',0),d['response_text']))
  catalog={k:[v for _,v in sorted(vs)] for k,vs in catalog.items()}
  out[task.question]=dict(case=case,task=task,snapshot=snapshot,catalog=catalog)
 return out
def physical_probe(adapter,events):
 base=getattr(adapter,'delegate',adapter)
 if hasattr(base,'_exchange') and not getattr(base,'_v23_probed',False):
  old=base._exchange
  def exchange(*a,**kw):
   events.append(dict(kind='http_worker_begin',component=getattr(base,'_v23_component',None),time=time.monotonic()))
   return old(*a,**kw)
  base._exchange=exchange;base._v23_probed=True

class ExperimentFactory(ComponentFactory):
 def __init__(self,config,items,overlap):super().__init__(config);self.items=items;self.overlap=overlap;self.events={};self.messages={};self.entered={}
 def create(self,rid,observer,**kw):
  events=self.events[rid]=[];messages=self.messages[rid]=[]
  def observe(snapshot):
   event=snapshot['event'];component=getattr(event,'component',None)
   if component in ('evidence_verification','power_domain_review'):events.append(dict(kind='review_complete',component=component,time=time.monotonic()))
   return observer(snapshot)
  b=super().create(rid,observe,**kw);b.harness.fact_domain_retrieval_overlap=self.overlap
  for agent in (b.harness.verification,b.harness.domain_review):physical_probe(agent.client.adapter,events)
  retriever=b.harness.retriever;original_retrieve=retriever.retrieve
  async def retrieve(r):
   events.append(dict(kind='retrieval_start',purpose=r.purpose.value,time=time.monotonic()))
   try:return await original_retrieve(r)
   finally:events.append(dict(kind='retrieval_end',purpose=r.purpose.value,time=time.monotonic()))
  retriever.retrieve=retrieve
  for agent in (b.harness.verification,b.harness.domain_review,b.harness.extractor,b.harness.revision):agent.client.adapter=Probe(agent.client.adapter,events,messages)
  original_run=b.harness.run
  async def run(request,budget,**kwargs):
   item=self.items[request.question];self.entered[rid]=time.monotonic();events.append(dict(kind='draft_entered',time=self.entered[rid]))
   kwargs.update(generation_snapshot=item['snapshot'],indexed_reference_ids=tuple(e.evidence_id for e in item['snapshot'].evidence))
   return await original_run(item['task'],budget,**kwargs)
  b.harness.run=run;return b

def main(mode='offline'):
 items=materials();dest=HOME/mode;dest.mkdir(parents=True,exist_ok=False);real=mode=='real'
 if real:
  admission=read(HOME/'admission.json');assert admission['passed']
 cs=configs(dest,load_real=real);c=cs['baseline'];records=[]
 if real:
  frozen={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('harness/execution.py'),Path(__file__),Path('backend/assembly.py'),Path('agents/verification_contract_v10_batched.py')]}
  (dest/'freeze.json').write_text(json.dumps({'sources':frozen,'cases':[{'case':v['case'],'answer':wire(v['task'].existing_answer),'snapshot_id':v['snapshot'].snapshot_id} for v in items.values()],'max_calls':240,'max_trusted_tokens':4000000,'model':'deepseek-flash'},ensure_ascii=False,indent=2),encoding='utf8')
 if real:(dest/'attempt.json').write_text(json.dumps({'started':time.time(),'max_calls':240,'max_tokens':4000000}),encoding='utf8')
 for i,item in enumerate(items.values()):
  for route in (('serial','overlap') if i%2==0 else ('overlap','serial')):
   if real:assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
   runhome=dest/item['case']/route;runhome.mkdir(parents=True)
   config=replace(c,run_db=runhome/'runs.sqlite3',token_file=runhome/'token');factory=ExperimentFactory(config,items,route=='overlap')
   provider=ArchiveProvider(item['catalog'])
   with contextlib.ExitStack() as stack:
    if not real:
     stack.enter_context(patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}));stack.enter_context(patch('model_adapter.deepseek.create_adapter',return_value=provider))
    with TestClient(create_app(config,factory=factory,access_token='fixture')) as client:
     h={'Authorization':'Bearer fixture'};a=client.post('/runs',headers=h,json={'mode':'question_answer','question':item['task'].question,'engineering_context':{'goal':'conceptual'}});assert a.status_code==202,a.text;rid=a.json()['run_id'];deadline=time.monotonic()+850
     while time.monotonic()<deadline:
      state=client.get('/runs/'+rid,headers=h).json()
      if state['status'] not in ('queued','running'):break
      time.sleep(.05)
     result=client.get('/runs/'+rid+'/result',headers=h).json();readable=time.monotonic();trace=client.get('/runs/'+rid+'/trace',headers=h).json();events=factory.events[rid];events.append(dict(kind='answer_readable',time=readable))
     for name,value in [('result',result),('trace',trace),('events',events),('messages',factory.messages[rid])]:
      (runhome/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
     record=dict(case=item['case'],route=route,run_id=rid,post_draft_seconds=readable-factory.entered[rid],complete=result['execution']['required_stages_complete'],issues=result['execution']['execution_issues']);records.append(record);print(record,flush=True)
   (dest/'summary.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
   if real:
    if result['execution'].get('service_fault_code') or result['execution'].get('error_code'):raise RuntimeError('Shared service/storage failure')
    from model_adapter.call_budget_v1 import shared_gate
    gate=shared_gate(dest/'accounting')
    if any(not e.get('finished') or e.get('usage') is None for e in gate.state['entries'].values()):raise RuntimeError('Unknown shared accounting; stop batch')
if __name__=='__main__':
 import sys
 main(sys.argv[1] if len(sys.argv)>1 else 'offline')
