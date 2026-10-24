"""New independent domain batch; historical fact controllers are not modified."""
import asyncio,json
from dataclasses import asdict
from time import perf_counter
from pathlib import Path
from evaluation.fact_internal_flow_trial_v1 import ROOT,SETTINGS,digest,message_hash,write,wire
from evaluation.domain_business_materials_v1 import CASES,fixed_input
from agents.power_domain_review import ModelPowerDomainReviewAgent
from services.domain_business_v1 import create_agent
from model_adapter.runtime import ModelBudget,model_scope,model_invocation_scope
PUBLIC=ROOT/'docs/evaluation/domain-business-v1'
LOCAL=ROOT/'data/retrieval_local/domain-business-v1'
def build(adapter,variant,diagnostics=None):
 if variant=='candidate':return create_agent(adapter,SETTINGS,diagnostic_dir=diagnostics)
 return ModelPowerDomainReviewAgent(adapter,SETTINGS,diagnostic_dir=diagnostics,protocol_version=5,safety_review=True,task_applicability=True)
def order():return [(c,v) for i,c in enumerate(CASES) for v in (('baseline','candidate') if i%2==0 else ('candidate','baseline'))]
def shared_failure(code):return code!='MODEL_OUTPUT_ERROR'
async def capture():
 rows=[]
 class Captured(BaseException):pass
 for c,v in order():
  seen=[]
  class Adapter:
   async def complete(self,r):seen.append(r);raise Captured()
  try:
   with model_scope(ModelBudget(40)):await build(Adapter(),v).run(fixed_input(c))
  except Captured:pass
  if len(seen)!=1:raise ValueError('Expected one initial domain request')
  rows.append(dict(case=c[0],variant=v,message_sha256=message_hash(seen[0].messages)))
 return rows
def freeze():
 if (LOCAL/'attempt.json').exists():raise ValueError('No rerun')
 rows=asyncio.run(capture());paths=[p for folder in ('agents','backend','core','harness','model_adapter','services','evaluation','tests','tools') for p in (ROOT/folder).glob('*.py')]
 write(PUBLIC/'freeze.json',dict(model=asdict(SETTINGS),order=rows,inputs=CASES,initial_calls=12,corrections_per_branch=1,derived_maximum=24,budget=40,timeout=110,files=[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in paths]))
async def batch(f,factory):
 rows=[];stop=False;total=0
 for (c,v),entry in zip(order(),f['order']):
  ident=c[0]+'-'+v;branch=LOCAL/ident
  if stop:rows.append(dict(id=ident,status='unexecuted'));continue
  sent=[];adapter=None;start=perf_counter();budget=ModelBudget(40,deadline=start+800)
  try:
   write(branch/'input.json',wire(fixed_input(c)));adapter=factory()
   class Guard:
    async def complete(self,r):
     nonlocal total
     n=len(sent)
     if (n==0 and (r.correction or message_hash(r.messages)!=entry['message_sha256'])) or (n==1 and not r.correction) or n>=2 or r.model_id!=SETTINGS.model_id:raise ValueError('Frozen identity or correction ownership mismatch')
     write(branch/f'messages-{n+1}.json',wire(r));total+=1;sent.append(dict(sequence=total,correction=r.correction));out=await adapter.complete(r);write(branch/f'response-{n+1}.json',wire(out));return out
   with model_scope(budget),model_invocation_scope(ident,'power_domain_review',1):out=await asyncio.wait_for(build(Guard(),v,branch/'diagnostics').run(fixed_input(c)),110)
   codes=[x.code for x in out.execution_issues];stop=any(shared_failure(x) for x in codes)
   row=dict(id=ident,status='execution_failed' if codes else 'complete',output=wire(out),codes=codes)
  except (Exception,asyncio.CancelledError) as exc:
   stop=shared_failure(getattr(exc,'code',None));row=dict(id=ident,status='execution_failed',exception_type=type(exc).__name__,code=getattr(exc,'code',None))
   if hasattr(exc,'partial_output'):row['partial_output']=wire(exc.partial_output)
  finally:
   if adapter is not None:adapter.close()
  row.update(sent=sent,seconds=perf_counter()-start,model_records=wire(budget.records));write(branch/'summary.json',row);rows.append(row)
 return dict(total_sends=total,branches=rows,shared_stop=stop)
def execute():
 f=json.loads((PUBLIC/'freeze.json').read_text(encoding='utf-8'))
 if (LOCAL/'attempt.json').exists():raise ValueError('No resume')
 for r in f['files']:
  if digest(ROOT/r['path'])!=r['sha256']:raise ValueError('Frozen identity changed')
 from harness.deepseek_trial import load_project_env
 from model_adapter.deepseek import create_adapter
 load_project_env();write(LOCAL/'attempt.json',dict(resume_allowed=False,freeze_sha256=digest(PUBLIC/'freeze.json')))
 s=asyncio.run(batch(f,lambda:create_adapter(SETTINGS)));write(PUBLIC/'results.json',s)
 predictions=[]
 for row in s['branches']:
  b=LOCAL/row['id'];predictions.append(dict(id=row['id'],attempts=[dict(messages=json.loads(p.read_text(encoding='utf-8')),response=json.loads((b/p.name.replace('messages','response')).read_text(encoding='utf-8')) if (b/p.name.replace('messages','response')).exists() else None) for p in sorted(b.glob('messages-*.json'))]))
 write(PUBLIC/'predictions.json',predictions);print(json.dumps({'total_sends':s['total_sends'],'shared_stop':s['shared_stop'],'branches':[(r['id'],r['status']) for r in s['branches']]}))
if __name__=='__main__':
 import sys
 if sys.argv[1:]==['freeze']:freeze()
 elif sys.argv[1:]==['execute']:execute()
 else:raise SystemExit('freeze | execute')
