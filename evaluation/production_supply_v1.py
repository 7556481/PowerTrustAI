"""One fixed existing-component comparison, no alternate scheduler."""
import asyncio,json,os,subprocess,time,hashlib
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from backend.config import ServiceConfig,ROOT
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation.archive_replay import restore
from evaluation.natural_draft_audit_v1 import save,sha
from evaluation.source_first_live_v2 import inputs,Accounted,OWNER,UsageGate
from evaluation.answer_review_net_benefit_v1 import batch as fixed_batch
from core.models import TaskRequest,TaskMode,ClaimExtractionOutput,GenerationEvidenceSnapshot,EngineeringContext
from harness.contracts import RunBudget
from harness.execution import RunExecution
from harness.states import RunState
DATA=Path('D:/PowerTrustAI/data')
LOCAL=DATA/'maintenance_local/production-evidence-decoupling-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def config():
 f=read(DATA/'runtime_local/stable-product-ten-v1/freeze.json')['configuration']
 return ServiceConfig(index_db=Path(f['index_db']),knowledge_version=f['knowledge_version'],execution_path=f['execution_path'],run_db=LOCAL/'runs.sqlite3',token_file=LOCAL/'token')
def freeze():
 assert not (LOCAL/'freeze.json').exists(),'No overwrite'
 old=read(DATA/'retrieval_local/source-first-modality-release-v6/materials.json');cases=[]
 for i in (0,4,5,1,2,6,3):cases.append(old['cases'][i])
 raw=read(DATA/'runtime_local/stable-product-ten-v1/Q7-stored.json');req=raw['request'];result=raw['result'];snapshot=result['generation_output']['evidence_snapshot']
 req=dict(req,mode='assess_existing',existing_answer=result['answer'],provided_evidence=snapshot['evidence'])
 cases.append(dict(id='outside-source-gap',request=req,snapshot=snapshot,extraction=result['extraction_output'],expected='Must seek boundary modeling body outside organizational/CIP original sources or preserve insufficiency; never invent MW/Mvar locations.',required_reference=old['cases'][0]['request']['provided_evidence']))
 for i,x in enumerate(cases):x['slot']='S'+str(i+1);x['protection']='correct' if i<3 else 'key_defect' if i<6 else 'gap'
 materials=dict(cases=cases);c=config();sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ('agents','backend','core','harness','rag','services','model_adapter','evaluation') for p in (ROOT/d).glob('*.py')}
 questions=read(DATA/'runtime_local/stable-product-ten-v1/freeze.json')['cases'];f=dict(version='production-evidence-reuse-v1',commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),sources=sources,configuration=wire(c),materials_sha=sha(materials),scope='explicit conceptual goal, no typed quantities, valid bounded source delivery; otherwise original domain query',input_changes='unchanged production prompts/contracts; mandatory independent fact query preserved; domain uses original full snapshot + <=2400 chars/6 neighbors/depth1 + fact search supply. Domain full search at most once per review round after model not_assessable or adverse literature check. Existing fact semantic-gap subject supplement retained; no count/lexical sufficiency heuristic.',budget=dict(calls=240,trusted_usage_stop=4000000,per_chain=c.budget.max_model_calls,unknown='preserve pending and stop if no reliable conservative continuation'),order=[dict(id='S'+str(i+1)+'-'+v,input=dict(line='B',case=i,variant=v)) for i in range(8) for v in (('baseline','candidate') if i%2==0 else ('candidate','baseline'))],timing='8 materials x 2 paths x 3 alternating rounds; fresh adapter/session, OS cache unchanged; process seal separate; source/gap costs included',thresholds='>=6 complete pairs; candidate completeness >= baseline; paired comparable median wall time >=30% and >=5s lower; no candidate-only critical acceptance/edit/omission/counterevidence loss; failures never count as speedup',product_questions=[questions[3]['question'],questions[4]['question']],smoke_question=questions[3]['question'],labels='seen development; AI-assisted user-supervised review, not expert gold/holdout')
 save(LOCAL/'materials.json',materials);save(LOCAL/'freeze.json',f);print('8 materials, 16 chains and 2 product questions frozen; no sends',flush=True)
def verify():
 f=read(LOCAL/'freeze.json');assert sha(read(LOCAL/'materials.json'))==f['materials_sha']
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in f['sources'].items()),'Frozen code changed'
 return f
async def offline():
 f=verify();m=read(LOCAL/'materials.json');c=config();assert not (LOCAL/'timing').exists(),'No timing repeat'
 assert RunState.EXTRACTING_CLAIMS.value=='extracting_claims'
 for item in m['cases']:
  req=replace(restore(item['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING)
  from core.validation import validate_request,validate_extraction
  from services.evidence_scope import validate_snapshot
  validate_request(req,c.budget);validate_snapshot(restore(item['snapshot'],GenerationEvidenceSnapshot),req.existing_answer);validate_extraction(restore(item['extraction'],ClaimExtractionOutput),req.existing_answer)
 start=time.monotonic();factory=ComponentFactory(c);await asyncio.to_thread(factory.warm_corpus_index);save(LOCAL/'seal.json',dict(seconds=time.monotonic()-start))
 records=[]
 class NoModel:
  def close(self):pass
  async def complete(self,r):raise AssertionError('Offline model request prohibited')
 for round in range(3):
  for i,row in enumerate(m['cases']):
   for v in (('baseline','candidate') if round%2==0 else ('candidate','baseline')):
    cfg=replace(c,audit_evidence_profile='deferred_subject_v1' if v=='candidate' else 'baseline_v1');factory=ComponentFactory(cfg);bundle=None;start=time.monotonic()
    with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash','DEEPSEEK_API_KEY':'offline-fixture'}),patch('model_adapter.deepseek.create_adapter',return_value=NoModel()):bundle=factory.create('offline-'+str(i),None)
    try:
     req=replace(restore(row['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING);snapshot=restore(row['snapshot'],GenerationEvidenceSnapshot);ex=RunExecution(bundle.harness,req,cfg.budget,knowledge_version=cfg.knowledge_version,indexed_reference_ids=tuple(e.evidence_id for e in req.provided_evidence),generation_snapshot=snapshot);fixed=restore(row['extraction'],ClaimExtractionOutput)
     class FrozenExtractor:
      async def extract(self,a):return fixed
     bundle.harness.extractor=FrozenExtractor()
     await ex.validate_saved_inputs();await ex.extract_and_tools();await ex.prepare_review()
     rec=dict(slot=row['slot'],round=round,path=v,seconds=time.monotonic()-start,records=wire(tuple(ex.retrieval.records)),fact_input=wire(ex.v_input),domain_input=wire(ex.d_input))
     records.append(rec);save(LOCAL/'timing'/f'{len(records):02d}.json',rec);print(row['slot'],round,v,round_time(rec['seconds']),flush=True)
    finally:await bundle.drain();bundle.close();await factory.close()
 save(LOCAL/'timing-summary.json',records)
def round_time(n):return float(format(n,'.3f'))
class Gate(UsageGate):
 def __init__(self,root):super().__init__(root,threshold=4000000,cap=240)
 def __call__(self,spec,r,n):
  with self.lock:
   key=str(spec['case'])+'-'+spec['variant']
   if self.stopped or self.calls>=self.cap or self.tokens>=self.threshold:raise RuntimeError('Shared budget stopped')
   assert r.model_id=='deepseek-flash' and r.max_output_tokens==8000
   assert self.chains.get(key,0)<40
   idx=self.calls+1;self.event('send',dict(id=idx,chain=key,usage_before=self.tokens,message_utf8_bytes=sum(len(m.content.encode()) for m in r.messages),max_output_tokens=r.max_output_tokens,estimate='bytes warning only; no billing upper-bound claim'));self.calls=idx;self.chains[key]=self.chains.get(key,0)+1;self.pending.add(idx);OWNER.set(idx)
async def live():
 f=verify();assert not (LOCAL/'live-attempt.json').exists(),'No resume or replacement slots';assert (LOCAL/'timing-summary.json').exists(),'Offline timing required'
 from harness.deepseek_trial import load_project_env
 load_project_env(DATA.parent/'.env');assert os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash'
 c=config();factory=ComponentFactory(c);factory.preflight();m=read(LOCAL/'materials.json');gate=Gate(LOCAL/'live');save(LOCAL/'live-attempt.json',dict(freeze_sha=sha(f),resume=False))
 from model_adapter.deepseek import create_adapter
 async def runner(h,req,budget,**kw):
  if req.mode==TaskMode.QUESTION_ANSWER:kw['knowledge_version']=c.knowledge_version
  return await h.run(req,budget,indexed_reference_ids=tuple(e.evidence_id for e in req.provided_evidence),**kw)
 async def admission(spec,outputs):
  if gate.stopped or gate.pending:raise RuntimeError('No next slot after global budget/pending failure')
 def totals(phase):save(LOCAL/'live-totals.json',dict(phase=phase,calls=gate.calls,tokens=gate.tokens,pending=sorted(gate.pending),stopped=gate.stopped,cost=None))
 try:
  s=await fixed_batch(c,m,LOCAL/'live',lambda settings,**kw:Accounted(create_adapter(settings,**kw),gate),rows=f['order'],request_builder=lambda m,i,**kw:replace(restore(m['cases'][i]['request'],TaskRequest),mode=TaskMode.ASSESS_EXISTING),variant_config=lambda cfg,v:replace(cfg,audit_evidence_profile='deferred_subject_v1' if v=='candidate' else 'baseline_v1'),task_runner=runner,initial_generated=inputs(m),fixed_audit_delivery=False,independent_audit_budget=True,send_guard=gate,before_submit=admission)
  totals('comparison-finished')
  from evaluation.production_supply_read import check
  check(LOCAL/'live',c)
  print('Comparison archived; awaiting comparison-review.json; no new sends',flush=True)
  decision=LOCAL/'comparison-review.json'
  while not decision.exists():await asyncio.sleep(1)
  if not read(decision).get('passed') or gate.stopped or gate.pending:return
  rows=[dict(id='P'+str(i+1)+'-'+v,input=dict(line='P',case=8+i,variant=v)) for i in range(2) for v in (('baseline','candidate') if i==0 else ('candidate','baseline'))]
  def question(m,i,**kw):return TaskRequest('product-'+str(i),TaskMode.QUESTION_ANSWER,'voltage_stability_reactive_support',f['product_questions'][i-8],engineering_context=EngineeringContext(goal='conceptual'))
  await fixed_batch(c,m,LOCAL/'products',lambda settings,**kw:Accounted(create_adapter(settings,**kw),gate),rows=rows,request_builder=question,variant_config=lambda cfg,v:replace(cfg,audit_evidence_profile='deferred_subject_v1' if v=='candidate' else 'baseline_v1'),task_runner=runner,fixed_audit_delivery=False,send_guard=gate,before_submit=admission)
  check(LOCAL/'products',c);totals('products-finished')
  print('Products archived; awaiting product-review.json; no new sends',flush=True)
  decision=LOCAL/'product-review.json'
  while not decision.exists():await asyncio.sleep(1)
  if not read(decision).get('passed') or gate.stopped or gate.pending:return
  save(LOCAL/'smoke-budget.json',dict(version='production-supply-smoke-budget-v1',calls=gate.calls,tokens=gate.tokens,pending=[],cap=240,threshold=4000000))
  print('Budget handed off for one frozen managed-service smoke; no evaluator sends',flush=True)
  totals('handoff-to-managed-smoke')
 finally:await factory.close()
if __name__=='__main__':
 import sys
 if sys.argv[1]=='freeze':freeze()
 elif sys.argv[1]=='offline':asyncio.run(offline())
 elif sys.argv[1]=='live':asyncio.run(live())
