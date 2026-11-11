"""Normal Factory/auditors/transport -> offline final adapter boundary; no network."""
import asyncio,json,sqlite3,time,hashlib
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from backend.assembly import ComponentFactory
from backend.serialization import wire
from evaluation.audit_tantivy_v21 import AuditFactory
from evaluation.tantivy_product_v19 import configs
from evaluation.archive_replay import restore
from harness.evidence_review_demo import restore_answer,restore_snapshot,restore_evidence
from core.models import TaskRequest,TaskMode,ClaimExtractionOutput,EvidenceBinding
from agents.contracts import ReliabilityVerificationInput,ReliabilityDomainInput
from rag.contracts import RetrievalResult,RetrievalPurpose
from harness.retrieval import RetrievalSession
from model_adapter.runtime import model_scope,ModelBudget
from model_adapter.contracts import ModelOutputError,ModelMessage
from services.request_metrics import measure
HOME=Path('D:/PowerTrustAI/data/runtime_local/audit-tantivy-v21/boundary-v3')
OLD=HOME.parent.parent/'tantivy-delivery-replay-v20'
PRIOR=HOME.parent.parent/'tantivy-product-v19'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Recorder:
 def __init__(self):self.rows=[];self.tag={}
 def close(self):pass
 async def complete(self,r):
  payloads=[]
  for m in r.messages:
   try:payloads.append(json.loads(m.content))
   except (ValueError,TypeError):pass
  category='domain' if r.prompt_version.startswith('power-domain') else 'original_citation' if any('ORIGINAL_CITATION_SCOPES' in p for p in payloads if isinstance(p,dict)) else 'independent'
  self.rows.append(dict(self.tag,category=category,correction=r.correction,prompt=r.prompt_version,metrics=measure(r.messages),messages=wire(r.messages)))
  # Record a built request, not a semantic prediction; avoid artificial format correction.
  raise ModelOutputError()

class FrozenReader:
 def __init__(self,records):self.records=records;self.seen=[]
 async def retrieve(self,r):
  found=[x for x in self.records if x['query_sha256']==hashlib.sha256(r.query.encode()).hexdigest() and x['purpose']==r.purpose.value]
  assert len(found)==1,'Frozen request identity ambiguous'
  x=found[0];self.seen.append(x['slot']);return restore(x['result'],RetrievalResult)
 async def validate_result(self,r,result):
  assert result==restore(next(x for x in self.records if x['slot']==self.seen[-1])['result'],RetrievalResult)
 def close(self):pass

async def run():
 HOME.mkdir(parents=True,exist_ok=False)
 f=read(OLD/'freeze.json');allrows=[json.loads(l) for l in (OLD/'measurements.jsonl').read_text(encoding='utf8').splitlines()]
 assert all(sha(Path(p))==h for p,h in f['inputs'].items())
 assert sha(Path('D:/PowerTrustAI/data/retrieval_local/tantivy-shards-v16/accepted-shard-group.json'))==f['group_sha256']
 requests=[x for x in f['requests'] if x['purpose']!='generation'];rec=Recorder();summary=[];hist=[]
 cs=configs(HOME)
 with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=rec):
  for case,origin in dict.fromkeys((r['case'],r['origin']) for r in requests):
   published=read(PRIOR/(case+'-'+origin+'-result.json'));rid=published['execution']['run_id']
   db=sqlite3.connect('file:'+str(PRIOR/origin/'runs.sqlite3')+'?mode=ro',uri=True)
   raw,req=db.execute('select result,request from runs where id=?',(rid,)).fetchone();db.close();raw=json.loads(raw)
   answer=restore_answer(raw['generation_output']['answer']);snapshot=restore_snapshot(raw['generation_output']['evidence_snapshot']);extraction=restore(raw['extraction_output'],ClaimExtractionOutput)
   assert wire(answer)==published['answer']['versions'][0]
   assert snapshot.snapshot_id==published['snapshots']['generation']['evidence_snapshot']['snapshot_id']
   assert [(e.evidence_id,e.source_version,e.text) for e in snapshot.evidence]==[(e['evidence_id'],e['source_version'],e['text']) for e in published['snapshots']['generation']['evidence_snapshot']['evidence']]
   task=replace(restore(json.loads(req),TaskRequest),mode=TaskMode.ASSESS_EXISTING,existing_answer=answer,provided_evidence=snapshot.evidence)
   selected=[r for r in requests if (r['case'],r['origin'])==(case,origin)]
   for route in ('sqlite','candidate'):
    c=cs['baseline' if route=='sqlite' else 'fast'];factory=ComponentFactory(c) if route=='sqlite' else AuditFactory(c)
    bundle=factory.create('v21-boundary-'+case+'-'+origin+'-'+route,None,fixed_evidence_only=True)
    records=[x for x in allrows if x['slot'] in {r['slot'] for r in selected} and x['route']==('sqlite' if route=='sqlite' else 'v18')]
    reader=FrozenReader(records)
    if route=='candidate':
     bundle.harness.retriever.sqlite.close();bundle.harness.retriever.sqlite=reader;bundle.harness.retriever.tantivy=reader;retriever=bundle.harness.retriever
    else:retriever=reader
    session=RetrievalSession(retriever,snapshot.knowledge_version,bundle.harness.retrieval_settings,c.budget,time.perf_counter()+300,snapshot.evidence,tuple(e.evidence_id for e in snapshot.evidence))
    accumulated=();bindings=()
    for item in selected:
     purpose=RetrievalPurpose(item['purpose']);delivery=await session.retrieve(purpose,task,answer,extraction.claims,query_override=item['query'])
     assert delivery.issue is None,(item['slot'],delivery.issue)
     assert reader.seen[-1]==item['slot']
     rec.tag=dict(case=case,origin=origin,route=route,slot=item['slot'],question=task.question,answer_id=answer.answer_id,snapshot_id=snapshot.snapshot_id,conditional_supplement=len([x for x in selected if x['purpose']=='verification' and x['slot']<=item['slot']])>1 if purpose==RetrievalPurpose.VERIFICATION else False)
     before=len(rec.rows)
     if purpose==RetrievalPurpose.VERIFICATION:
      from core.validation import merge_evidence
      accumulated=merge_evidence(accumulated,delivery.evidence);bindings+=delivery.bindings
      inp=ReliabilityVerificationInput(task,answer,extraction.claims,accumulated,bindings,snapshot.knowledge_version,tuple(e for e in snapshot.evidence if e.evidence_id in {i for cit in answer.citations for i in cit.evidence_ids}),snapshot,tuple(restore(t,__import__('core.models',fromlist=['ToolResult']).ToolResult) for t in raw.get('tool_results',[])),json.dumps(wire(delivery.record)))
      agent=bundle.harness.verification
     else:
      inp=ReliabilityDomainInput(task,answer,extraction.claims,delivery.evidence,bundle.harness.domain_review.rule_set_version,delivery.bindings,snapshot.knowledge_version,(),json.dumps(wire(delivery.record)));agent=bundle.harness.domain_review
     # The normal agent constructs scopes, original groups, transport, and ModelClient request.
     with model_scope(ModelBudget(80)):await agent.run(inp)
     assert len(rec.rows)>before,(item['slot'],'no boundary request')
     summary.append(dict(rec.tag,requests=len(rec.rows)-before,retrieval_slots=reader.seen[:]))
    bundle.close();await factory.close()
   # Historical corrections are saved final messages. They are conditional on old output.
   for response in (Path('data/retrieval_local/service_private')/rid).glob('response-*.json'):
    d=read(response)
    if d.get('correction') and d.get('request_messages_path'):
     p=Path(d['request_messages_path']);v=read(p)
     if v['prompt_version'].startswith(('evidence-verification','power-domain')):
      from model_adapter.runtime import ModelClient
      from model_adapter.contracts import ModelSettings
      hr=Recorder();hr.tag=dict(case=case,origin=origin,route='historical_only')
      hc=ModelClient(hr,ModelSettings('deepseek-flash'))
      try:await hc.complete(tuple(ModelMessage(**m) for m in v['messages']),v['prompt_version'],ModelBudget(1),True)
      except ModelOutputError:pass
      assert len(hr.rows)==1
      hist.append(dict(case=case,origin=origin,correction=True,metrics=hr.rows[0]['metrics'],messages_sha256=sha(p),boundary_recorded=True,reason='Historical output and original scope IDs only; altered candidate scopes cannot faithfully replay this old correction as a paired prediction.'))
 (HOME/'boundary-requests.json').write_text(json.dumps(rec.rows,ensure_ascii=False,indent=2),encoding='utf8')
 (HOME/'summary.json').write_text(json.dumps(dict(invocations=summary,requests=[{k:v for k,v in x.items() if k!='messages'} for x in rec.rows],historical_corrections=hist,inputs={str(OLD/'freeze.json'):sha(OLD/'freeze.json'),str(OLD/'measurements.jsonl'):sha(OLD/'measurements.jsonl')},models_real=0),ensure_ascii=False,indent=2),encoding='utf8')
 print('Boundary requests',len(rec.rows),'historical corrections',len(hist),flush=True)
if __name__=='__main__':asyncio.run(run())
