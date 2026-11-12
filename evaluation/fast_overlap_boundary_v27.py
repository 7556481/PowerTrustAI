"""Current Factory -> agents -> review_transport -> final offline adapter boundary."""
import asyncio,hashlib,json,sqlite3,time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from backend.assembly import ComponentFactory
from backend.managed import ManagedFactory
from backend.config import ServiceConfig
from backend.serialization import wire
from evaluation.archive_replay import restore
from evaluation.fast_overlap_v27 import HOME
from harness.evidence_review_demo import restore_answer,restore_snapshot
from core.models import TaskRequest,TaskMode,ClaimExtractionOutput,EvidenceBinding
from agents.contracts import ReliabilityVerificationInput,ReliabilityDomainInput,GenerationInput
from rag.contracts import RetrievalResult,RetrievalPurpose
from harness.retrieval import RetrievalSession
from model_adapter.runtime import model_scope,ModelBudget
from model_adapter.contracts import ModelOutputError
from services.request_metrics import measure

PRIOR=HOME.parent/'tantivy-product-v19';FROZEN=HOME.parent/'tantivy-delivery-replay-v20'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))

class Recorder:
    def __init__(self):self.rows=[];self.tag={}
    def close(self):pass
    async def complete(self,request):
        payloads=[]
        for message in request.messages:
            try:payloads.append(json.loads(message.content))
            except (ValueError,TypeError):pass
        category='generation' if request.prompt_version.startswith('evidence-bound-generation') else 'domain' if request.prompt_version.startswith('power-domain') else 'original_citation' if any('ORIGINAL_CITATION_SCOPES' in p for p in payloads if isinstance(p,dict)) else 'independent'
        self.rows.append(dict(self.tag,category=category,correction=request.correction,prompt=request.prompt_version,metrics=measure(request.messages),messages=wire(request.messages),system_sha256=hashlib.sha256(''.join(m.content for m in request.messages if m.role=='system').encode()).hexdigest()))
        raise ModelOutputError()

class OneFrozenRequest:
    def set(self,item,result):self.item=item;self.result=result
    async def retrieve(self,request):
        assert hashlib.sha256(request.query.encode()).hexdigest()==self.item['query_sha256'] and request.purpose.value==self.item['purpose']
        return self.result
    async def validate_result(self,request,result):assert result==self.result

async def run():
    directory=HOME/'boundary-v2';directory.mkdir(exist_ok=False)
    freeze=read(FROZEN/'freeze.json');baseline=[json.loads(line) for line in (FROZEN/'measurements.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(line)['route']=='sqlite'];bymap={r['slot']:r for r in baseline};candidate={r['slot']:r for r in read(HOME/'frozen56-candidate-results.json')};recorder=Recorder();states=[]
    c=replace(ServiceConfig(),run_db=directory/'runs.sqlite3',index_db=Path('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3'),knowledge_version=freeze['requests'][0]['knowledge_version'],execution_path='langgraph_v1')
    with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=recorder):
        for case,origin in dict.fromkeys((r['case'],r['origin']) for r in freeze['requests']):
            published=read(PRIOR/(case+'-'+origin+'-result.json'));rid=published['execution']['run_id'];db=sqlite3.connect((PRIOR/origin/'runs.sqlite3').as_uri()+'?mode=ro',uri=True)
            raw,original_request=db.execute('select result,request from runs where id=?',(rid,)).fetchone();db.close();raw=json.loads(raw);original_task=restore(json.loads(original_request),TaskRequest)
            answer=restore_answer(raw['generation_output']['answer']);snapshot=restore_snapshot(raw['generation_output']['evidence_snapshot']);extraction=restore(raw['extraction_output'],ClaimExtractionOutput)
            assert wire(answer)==published['answer']['versions'][0] and snapshot.snapshot_id==published['snapshots']['generation']['evidence_snapshot']['snapshot_id']
            task=replace(original_task,mode=TaskMode.ASSESS_EXISTING,existing_answer=answer,provided_evidence=snapshot.evidence)
            selected=[r for r in freeze['requests'] if (r['case'],r['origin'])==(case,origin)]
            for route in ('sqlite','candidate'):
                factory=ManagedFactory(c,'overlap');bundle=factory.create('v27-boundary-'+case+'-'+origin+'-'+route,None,fixed_evidence_only=True);assert bundle.harness.fact_domain_retrieval_overlap
                reader=OneFrozenRequest();session=RetrievalSession(reader,snapshot.knowledge_version,bundle.harness.retrieval_settings,c.budget,time.perf_counter()+300,snapshot.evidence,tuple(e.evidence_id for e in snapshot.evidence));accumulated=();bindings=()
                generation_items=[item for item in selected if item['purpose']=='generation']
                # Final saved generation delivery is a conditional historical state.
                # An actual candidate can skip a historical fallback if its first lookup is nonempty.
                for item in generation_items:
                    output=restore((bymap if route=='sqlite' else candidate)[item['slot']]['result'],RetrievalResult);reader.set(item,output)
                    delivery=await session.retrieve(RetrievalPurpose.GENERATION,original_task,None,(),query_override=item['query']);assert delivery.issue is None
                recorder.tag=dict(case=case,origin=origin,route=route,slot=generation_items[-1]['slot'],question_sha256=hashlib.sha256(task.question.encode()).hexdigest(),answer_id=answer.answer_id,snapshot_id=snapshot.snapshot_id,conditional_historical_fallback=len(generation_items)>1)
                with model_scope(ModelBudget(c.budget.max_model_calls)):
                    try:await bundle.harness.generation.run(GenerationInput(original_task,delivery.evidence,delivery.bindings,snapshot.knowledge_version,snapshot.answer_requirements))
                    except ModelOutputError:pass
                for item in [v for v in selected if v['purpose']!='generation']:
                    purpose=RetrievalPurpose(item['purpose']);output=restore((bymap if route=='sqlite' else candidate)[item['slot']]['result'],RetrievalResult);reader.set(item,output)
                    delivery=await session.retrieve(purpose,task,answer,extraction.claims,query_override=item['query']);assert delivery.issue is None,(case,origin,item['slot'])
                    recorder.tag=dict(case=case,origin=origin,route=route,slot=item['slot'],question_sha256=hashlib.sha256(task.question.encode()).hexdigest(),answer_id=answer.answer_id,snapshot_id=snapshot.snapshot_id,conditional_subject_supplement=sum(v['purpose']=='verification' and v['slot']<=item['slot'] for v in selected)>1 if purpose==RetrievalPurpose.VERIFICATION else False)
                    before=len(recorder.rows)
                    if purpose==RetrievalPurpose.VERIFICATION:
                        from core.validation import merge_evidence
                        accumulated=merge_evidence(accumulated,delivery.evidence);bindings+=delivery.bindings
                        inputs=ReliabilityVerificationInput(task,answer,extraction.claims,accumulated,bindings,snapshot.knowledge_version,tuple(e for e in snapshot.evidence if e.evidence_id in {i for citation in answer.citations for i in citation.evidence_ids}),snapshot,tuple(restore(t,__import__('core.models',fromlist=['ToolResult']).ToolResult) for t in raw.get('tool_results',[])),json.dumps(wire(delivery.record)))
                        agent=bundle.harness.verification
                    else:
                        inputs=ReliabilityDomainInput(task,answer,extraction.claims,delivery.evidence,bundle.harness.domain_review.rule_set_version,delivery.bindings,snapshot.knowledge_version,(),json.dumps(wire(delivery.record)));agent=bundle.harness.domain_review
                    with model_scope(ModelBudget(c.budget.max_model_calls)):await agent.run(inputs)
                    assert len(recorder.rows)>before
                    states.append(dict(recorder.tag,requests=len(recorder.rows)-before))
                bundle.close();await factory.close()
    # All literal messages are private; public summary keeps counts/identities only.
    (directory/'requests-private.json').write_text(json.dumps(recorder.rows,ensure_ascii=False,indent=2),encoding='utf-8')
    summary=dict(requests=[{k:v for k,v in row.items() if k!='messages'} for row in recorder.rows],states=states,real_model_requests=0,budget=wire(c.budget),correction_note='Recorder raises provider output error at final boundary, not a formatting response. No fake correction. Historical corrections remain conditional and unpaired where candidate scope differs.',generation_note='16 per route saved final delivery states;4 fallback cases are conditional, not predictions of actual candidate conversion calls.')
    (directory/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    import collections
    totals=collections.defaultdict(lambda:collections.Counter())
    for row in recorder.rows:
        t=totals[(row['route'],row['category'])];t['requests']+=1;t['evidence_chars']+=row['metrics']['evidence_chars_delivered'];t['message_chars']+=sum(len(m['content']) for m in row['messages'])
    print(json.dumps({str(k):dict(v) for k,v in totals.items()},ensure_ascii=False))
if __name__=='__main__':asyncio.run(run())
