"""Single frozen 16-branch development comparison. No resume or resends."""
import asyncio,json
from pathlib import Path
from dataclasses import asdict
from time import perf_counter
from evaluation.fact_internal_flow_trial_v1 import ROOT,SETTINGS,digest,message_hash,write,wire
from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
from services.fact_flow_protocol_v2 import create_agent as joint
from services.fact_two_stage_v1 import create_agent as split
from model_adapter.runtime import ModelBudget,model_scope,model_invocation_scope
PUBLIC=ROOT/'docs/evaluation/fact-two-stage-v1'
LOCAL=ROOT/'data/retrieval_local/fact-two-stage-v1'
def shared_failure(code):return code!='MODEL_OUTPUT_ERROR'
def order():return [(c,v) for i,c in enumerate(CASES) for v in (('v2','two_stage') if i%2==0 else ('two_stage','v2'))]
async def capture():
 rows=[]
 class Captured(BaseException):pass
 for c,v in order():
  seen=[]
  class Adapter:
   async def complete(self,r):seen.append(r);raise Captured()
  try:
   with model_scope(ModelBudget(40)):await (joint if v=='v2' else split)(Adapter(),SETTINGS).run(fixed_input(c))
  except Captured:pass
  if len(seen)!=1:raise ValueError('Initial boundary not captured')
  rows.append(dict(case=c['id'],variant=v,message_sha256=message_hash(seen[0].messages)))
 return rows
def freeze():
 if (LOCAL/'attempt.json').exists():raise ValueError('No rerun')
 rows=asyncio.run(capture())
 paths=[p for folder in ('agents','backend','core','harness','model_adapter','services','evaluation','tests','tools') for p in (ROOT/folder).glob('*.py')]
 write(PUBLIC/'freeze.json',dict(model=asdict(SETTINGS),order=rows,inputs=CASES,initial_calls=24,maximum_corrections=16,derived_maximum_calls=40,files=[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in paths],scoring='Seen development materials; F05 separate injected diagnosis; all planned branches retained; cost unknown; no production switch'))
async def batch(f,factory):
 results=[];stop=False;total=0
 for (case,v),entry in zip(order(),f['order']):
  ident=case['id']+'-'+v
  if stop:results.append(dict(id=ident,status='unexecuted'));continue
  branch=LOCAL/ident;sent=[];adapter=None;start=perf_counter();budget=ModelBudget(40,deadline=start+800)
  try:
   write(branch/'input.json',wire(fixed_input(case)));adapter=factory()
   class Guard:
    async def complete(self,r):
     nonlocal total
     n=len(sent)
     if not n and message_hash(r.messages)!=entry['message_sha256']:raise ValueError('Frozen input mismatch')
     if r.model_id!=SETTINGS.model_id or sum(x['correction'] for x in sent)+int(r.correction)>1 or sum(not x['correction'] for x in sent)+int(not r.correction)>(1 if v=='v2' else 2):raise ValueError('Budget ownership mismatch')
     write(branch/f'messages-{n+1}.json',wire(r));total+=1;sent.append(dict(correction=r.correction,sequence=total));response=await adapter.complete(r);write(branch/f'response-{n+1}.json',wire(response));return response
   with model_scope(budget),model_invocation_scope(ident,'evidence_verification',1):out=await asyncio.wait_for((joint if v=='v2' else split)(Guard(),SETTINGS,diagnostic_dir=branch/'diagnostics').run(fixed_input(case)),110)
   codes=[x.code for x in out.execution_issues];stop=any(shared_failure(x) for x in codes)
   row=dict(id=ident,status='execution_failed' if codes else 'complete',output=wire(out),codes=codes)
  except (Exception,asyncio.CancelledError) as exc:
   stop=shared_failure(getattr(exc,'code',None));row=dict(id=ident,status='execution_failed',exception_type=type(exc).__name__,code=getattr(exc,'code',None))
   if hasattr(exc,'partial_output'):row['partial_output']=wire(exc.partial_output)
  finally:
   if adapter is not None:adapter.close()
  row.update(seconds=perf_counter()-start,sent=sent,model_records=wire(budget.records));write(branch/'summary.json',row);results.append(row)
  write(LOCAL/(ident+'-checkpoint.json'),dict(total_sends=total,branches=results))
 return dict(total_sends=total,branches=results)
def execute():
 f=json.loads((PUBLIC/'freeze.json').read_text(encoding='utf-8'))
 if (LOCAL/'attempt.json').exists():raise ValueError('No resume')
 for r in f['files']:
  if digest(ROOT/r['path'])!=r['sha256']:raise ValueError('Frozen source changed')
 from harness.deepseek_trial import load_project_env
 from model_adapter.deepseek import create_adapter
 load_project_env();write(LOCAL/'attempt.json',dict(resume_allowed=False,freeze_sha256=digest(PUBLIC/'freeze.json')))
 s=asyncio.run(batch(f,lambda:create_adapter(SETTINGS)));write(PUBLIC/'results.json',s)
 predictions=[]
 for row in s['branches']:
  b=LOCAL/row['id'];predictions.append(dict(id=row['id'],attempts=[dict(messages=json.loads(p.read_text(encoding='utf-8')),response=json.loads((b/p.name.replace('messages','response')).read_text(encoding='utf-8')) if (b/p.name.replace('messages','response')).exists() else None) for p in sorted(b.glob('messages-*.json'))]))
 write(PUBLIC/'predictions.json',predictions)
 print(json.dumps(dict(total_sends=s['total_sends'],branches=[(r['id'],r['status']) for r in s['branches']])))
if __name__=='__main__':
 import sys
 if sys.argv[1:]==['freeze']:freeze()
 elif sys.argv[1:]==['execute']:execute()
 else:raise SystemExit('freeze | execute')
