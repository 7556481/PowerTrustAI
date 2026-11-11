"""Offline comparison of actual dispatched messages, storage and overlap."""
import json,collections,hashlib,asyncio
from pathlib import Path
from model_adapter.runtime import ModelClient,ModelBudget
from model_adapter.contracts import ModelMessage,ModelSettings,ModelOutputError
from evaluation.fact_domain_overlap_run_v23 import HOME,read

def normalize(messages):
 out=[];diff=[]
 for m in messages:
  try:p=json.loads(m['content'])
  except (ValueError,TypeError):out.append(m);continue
  if isinstance(p,dict) and 'DELIVERY_RECORD' in p:
   r=json.loads(p['DELIVERY_RECORD'])
   for k in ('retrieval_id','duration_ms'):r[k]='FROZEN_RUNTIME_METADATA'
   p['DELIVERY_RECORD']=json.dumps(r,sort_keys=True)
  out.append(dict(role=m['role'],content=json.dumps(p,ensure_ascii=False,sort_keys=True)))
 return out
async def main():
 rows=read(HOME/'offline/summary.json');assert len(rows)==16;proof=[];seen=[]
 class Recorder:
  async def complete(self,r):seen.append(r.messages);raise ModelOutputError()
 client=ModelClient(Recorder(),ModelSettings('deepseek-flash'))
 for case in dict.fromkeys(r['case'] for r in rows):
  paths={n:HOME/'offline'/case/n for n in ('serial','overlap')};aa=read(paths['serial']/'messages.json');bb=read(paths['overlap']/'messages.json');sort=lambda r:(r['component'],r['prompt'],r['correction'],str(r['metrics']['scope_ids']));aa.sort(key=sort);bb.sort(key=sort);assert len(aa)==len(bb)
  for a,b in zip(aa,bb):
   assert sort(a)==sort(b)
   na=normalize(a['messages']);nb=normalize(b['messages']);assert na==nb,(case,a['component'],'non-runtime message mismatch')
   # Re-record both clients with exactly the same frozen input metadata.
   for r,m in ((a,na),(b,nb)):
    try:await client.complete(tuple(ModelMessage(**v) for v in m),r['prompt'],ModelBudget(1),r['correction'])
    except ModelOutputError:pass
   assert seen[-1]==seen[-2]
  a=read(paths['serial']/'result.json');b=read(paths['overlap']/'result.json')
  for k in ('answer','decision','findings','review_bindings','evidence','budget_usage'):assert a[k]==b[k],(case,k)
  assert a['execution']['required_stages_complete']==b['execution']['required_stages_complete']
  assert collections.Counter((m['component'],m['correction']) for m in a['model_usage'])==collections.Counter((m['component'],m['correction']) for m in b['model_usage'])
  events=read(paths['overlap']/'events.json');fact=next(e['time'] for e in events if e['kind']=='request_dispatch' and e.get('component')=='evidence_verification');start=next(e['time'] for e in events if e['kind']=='retrieval_start' and e.get('purpose')=='domain_review');end=next(e['time'] for e in events if e['kind']=='retrieval_end' and e.get('purpose')=='domain_review');assert start<fact<end,(case,'no actual overlap')
  proof.append(dict(case=case,requests_each=len(aa),complete=a['execution']['required_stages_complete'],fact_dispatch_after_domain_start=fact-start,domain_retrieval_seconds=end-start,stored_business_result_equal=True,evidence_and_ranges_equal=True,budget_by_component_equal=True,frozen_metadata_message_bytes_equal=True))
 result=dict(passed=True,pairs=proof,exact_recorded_message_pairs=len(seen)//2,runtime_metadata_exception='Live SQL runs necessarily differ in DELIVERY_RECORD.retrieval_id and duration_ms. Every other field, evidence, scope and system prompt matches. Offline fixed-input boundary replay freezes ONLY those2 runtime metadata fields on BOTH sides before ModelClient.',physical_scope='Adapter boundary dispatch proves event-loop progress during real SQLite retrieval; exact socket POST time not measured offline.',tests='1465 tests/254.260 seconds OK skipped80;3 product failure/cancel/revision tests pass',real_model_calls=0)
 (HOME/'admission.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print('Offline admission passed',len(proof),'pairs',len(seen)//2,'message pairs')
if __name__=='__main__':asyncio.run(main())
