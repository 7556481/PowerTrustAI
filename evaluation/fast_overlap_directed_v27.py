"""Directed ISO control at the genuine generation request boundary, no model."""
import asyncio,hashlib,json,time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from evaluation.fast_overlap_v27 import HOME,select
from evaluation.fast_overlap_replay_v27 import SourceCatalog,read
from evaluation.fast_overlap_boundary_v27 import Recorder,OneFrozenRequest
from evaluation.archive_replay import restore
from backend.config import ServiceConfig
from backend.managed import ManagedFactory
from backend.serialization import wire
from core.models import TaskRequest,TaskMode
from rag.contracts import RetrievalPurpose,RetrievalResult,RetrievalHit,ContextOptions
from rag.context import read_adjacent_context
from harness.retrieval import RetrievalSession
from agents.contracts import GenerationInput
from model_adapter.runtime import model_scope,ModelBudget
from model_adapter.contracts import ModelOutputError

def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,list):
        for v in value:yield from strings(v)
    elif isinstance(value,dict):
        for v in value.values():yield from strings(v)

async def run():
    root=Path('D:/PowerTrustAI/data/retrieval_local');materials=read(root/'tantivy-shards-v16/review-materials-v17.json');case=next(c for c in materials['cases'] if c['id']=='Q10');catalog=SourceCatalog();pool=next(r for r in read(root/'tantivy-query-repair-v18/delivery-replay.json')['results'] if r['query']=='Q10');question=case['query'];k=pool['roots'][0]['provenance']['knowledge_version'];from core.models import Evidence
    full=tuple(restore(v,Evidence) for v in pool['roots']);baseline=tuple(catalog.evidence(materials['documents'][eid]['provenance']['fragment_id'],k) for eid in case['baseline']['roots']);candidate,_=select(question,full)
    configurations={'sqlite_existing':baseline,'mechanical_first3_control':full[:3],'six_roots_control':full,'candidate':candidate};rec=Recorder();summary=[]
    try:
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=rec):
            for name,roots in configurations.items():
                context=read_adjacent_context(catalog,roots,k,ContextOptions());hits=tuple(RetrievalHit(e.evidence_id,e.provenance.fragment_id,i+1,1.0,'frozen-directed-control') for i,e in enumerate(roots));result=RetrievalResult(roots,k,(),hits,context)
                c=replace(ServiceConfig(),run_db=HOME/'directed'/name/'runs.sqlite3',knowledge_version=k);c.run_db.parent.mkdir(parents=True,exist_ok=True);factory=ManagedFactory(c,'overlap');bundle=factory.create('v27-directed-'+name,None,fixed_evidence_only=True)
                reader=OneFrozenRequest();item={'query_sha256':hashlib.sha256(question.encode()).hexdigest(),'purpose':'generation'};reader.set(item,result)
                session=RetrievalSession(reader,k,replace(bundle.harness.retrieval_settings,max_results=len(roots)),c.budget,time.perf_counter()+60,())
                task=TaskRequest('v27-iso-directed',TaskMode.QUESTION_ANSWER,'voltage_stability_reactive_support',question)
                delivery=await session.retrieve(RetrievalPurpose.GENERATION,task,None,());assert delivery.issue is None,(name,delivery.issue,delivery.record.reason)
                rec.tag={'batch':'offline24-v18','case':'Q10','route':name,'question_sha256':item['query_sha256']}
                before=len(rec.rows)
                with model_scope(ModelBudget(c.budget.max_model_calls)):
                    try:await bundle.harness.generation.run(GenerationInput(task,delivery.evidence,delivery.bindings,k))
                    except ModelOutputError:pass
                assert len(rec.rows)==before+1;row=rec.rows[-1];literal=[]
                for message in row['messages']:
                    try:payload=json.loads(message['content'])
                    except ValueError:continue
                    literal.extend(strings(payload))
                target=next(e for e in full if '1.05' in e.text)
                summary.append(dict(route=name,roots=len(roots),root_chars=sum(len(e.text) for e in roots),context_chars=context.char_count,evidence_chars=row['metrics']['evidence_chars_delivered'],message_chars=sum(len(m['content']) for m in row['messages']),iso_literal105_at_final_boundary=any('1.05' in s for s in literal),exact_expected_body_at_final_boundary=target.text in literal,expected_evidence_id=target.evidence_id,same_production_budget=wire(c.budget)))
                bundle.close();await factory.close()
        (HOME/'directed-boundary-private.json').write_text(json.dumps(rec.rows,ensure_ascii=False,indent=2),encoding='utf-8');(HOME/'directed-boundary-summary.json').write_text(json.dumps({'rows':summary,'model_requests_real':0,'controls_not_new_candidates':True,'interpretation':'SQLite and mechanical3 also omit this known source; not claimed as a newly induced SQLite-relative semantic error. Candidate broad pool has it but selector discards it within budget.'},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps([{k:v for k,v in r.items() if k!='same_production_budget'} for r in summary],ensure_ascii=False))
    finally:catalog.close()
if __name__=='__main__':asyncio.run(run())
