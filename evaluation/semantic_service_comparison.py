"""Fixed-answer retrieval comparison; no model calls or environment loading."""
import argparse
import asyncio
from dataclasses import asdict,replace
import json
from pathlib import Path
from time import perf_counter
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from evaluation.archive_replay import restore
from core.models import AnswerDraft,ObligationClaim,TaskRequest,TaskMode
from harness.contracts import RetrievalSettings,RunBudget
from harness.retrieval import RetrievalSession
from harness.fact_retrieval import retrieve_facts
from rag.retriever import AsyncSQLiteBM25Retriever

async def compare(config,cases,settings,budget,*,encoder=None):
    factory=ComponentFactory(config);started=perf_counter()
    factory.initialize_retrieval(encoder)
    retriever=factory.semantic_resource or AsyncSQLiteBM25Retriever(config.index_db)
    cold=perf_counter()-started;rows=[]
    try:
        for case in cases:
            answer=restore(case['answer'],AnswerDraft)
            claims=tuple(restore(c,ObligationClaim) for c in case['shared_claims'])
            request=TaskRequest('fixed-comparison',TaskMode.ASSESS_EXISTING,'fixed-real-material','Review.',existing_answer=answer)
            before=getattr(retriever,'query_encodings',0);started=perf_counter()
            session=RetrievalSession(retriever,config.knowledge_version,replace(settings,fact_strategy='per_claim_v1'),budget,
                                    started+budget.max_duration_seconds,())
            delivery=await retrieve_facts(session,request,answer,claims)
            hits={h.fragment_id for r in session.records for h in r.hits}
            delivered={e.provenance.fragment_id for e in delivery.evidence}
            core_ids={h.evidence_id for r in session.records for h in r.hits}
            rows.append({'case_id':case['case_id'],'seconds':perf_counter()-started,'retrieval_calls':session.calls,
                'query_encodings':getattr(retriever,'query_encodings',0)-before,
                'core_chars':sum(len(e.text) for e in delivery.evidence if e.evidence_id in core_ids),
                'context_chars':sum(len(e.text) for e in delivery.evidence if e.evidence_id not in core_ids),
                'delivered_chars':session.chars,'required_hits':[t['expected_fragment_id'] in hits for t in case['targets']],
                'required_delivered':[t['expected_fragment_id'] in delivered for t in case['targets']],
                'records':[asdict(r) for r in session.records]})
        return {'mode':config.retrieval_mode,'fact_strategy':'per_claim_v1','knowledge_version':config.knowledge_version,
                'cold_seconds':cold,'embedding_profile':None if factory.semantic_resource is None else retriever.encoder.profile,
                'settings':asdict(settings),'budget':asdict(budget),'cases':rows,'paid_model_calls':0}
    finally:
        if factory.semantic_resource:await factory.close()
        else:retriever.close()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('index','vectors','model-dir','plan','cases','output'):p.add_argument('--'+flag,required=True)
    p.add_argument('--mode',choices=('bm25','dense','hybrid'),required=True);a=p.parse_args()
    plan=json.loads(Path(a.plan).read_text(encoding='utf8'));cases=json.loads(Path(a.cases).read_text(encoding='utf8'))['cases']
    config=ServiceConfig(index_db=Path(a.index),vector_db=Path(a.vectors),embedding_model_dir=Path(a.model_dir),
        knowledge_version=plan['knowledge_version'],retrieval_mode=a.mode,fact_strategy='per_claim_v1')
    result=asyncio.run(compare(config,cases,restore(plan['settings'],RetrievalSettings),restore(plan['limits'],RunBudget)))
    with Path(a.output).open('x',encoding='utf8') as handle:json.dump(result,handle,ensure_ascii=False,indent=2)
    print(json.dumps({'mode':a.mode,'cases':len(cases),'paid_model_calls':0}))
if __name__=='__main__':main()
