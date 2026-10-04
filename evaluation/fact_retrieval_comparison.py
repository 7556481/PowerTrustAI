"""Compare frozen answers/claims with the same indexed BM25; zero model calls."""
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter
from core.models import AnswerDraft, ObligationClaim, TaskRequest, TaskMode
from evaluation.archive_replay import restore
from harness.contracts import RetrievalSettings, RunBudget
from harness.fact_retrieval import retrieve_facts
from harness.retrieval import RetrievalSession
from rag.contracts import RetrievalPurpose
from rag.retriever import AsyncSQLiteBM25Retriever


async def compare(index_db, knowledge_version, cases, settings, budget):
    retriever=AsyncSQLiteBM25Retriever(index_db); output=[]
    try:
        for case in cases:
            answer=restore(case['answer'],AnswerDraft)
            claims=tuple(restore(c,ObligationClaim) for c in case['shared_claims'])
            request=TaskRequest('comparison-'+str(case['case_id']),TaskMode.ASSESS_EXISTING,'fixed-real-material',
                                'Review these statements.',existing_answer=answer)
            sides={}
            for strategy in ('aggregate','per_claim_v1'):
                from dataclasses import replace
                started=perf_counter();s=RetrievalSession(retriever,knowledge_version,replace(settings,fact_strategy=strategy),budget,started+budget.max_duration_seconds,())
                d=await retrieve_facts(s,request,answer,claims) if strategy=='per_claim_v1' else await s.retrieve(RetrievalPurpose.VERIFICATION,request,answer,claims)
                hits={h.fragment_id for r in s.records for h in r.hits}
                delivered={e.provenance.fragment_id for e in d.evidence}
                sides[strategy]={'retrieval_calls':s.calls,'delivered_chars':s.chars,'seconds':perf_counter()-started,
                    'required_hits':[t['expected_fragment_id'] in hits for t in case['targets']],
                    'required_delivered':[t['expected_fragment_id'] in delivered for t in case['targets']],
                    'records':[asdict(r) for r in s.records],'issue':None if d.issue is None else asdict(d.issue)}
            output.append(dict(case,sides=sides))
    finally:retriever.close()
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',required=True);p.add_argument('--plan',required=True)
    p.add_argument('--cases',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();plan_path=Path(a.plan);plan=json.loads(plan_path.read_text(encoding='utf8'))
    cases=json.loads(Path(a.cases).read_text(encoding='utf8'))['cases']
    settings=restore(plan['settings'],RetrievalSettings);budget=restore(plan['limits'],RunBudget)
    result=asyncio.run(compare(a.index,plan['knowledge_version'],cases,settings,budget))
    root=Path(__file__).resolve().parents[1]
    hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
            ('harness/retrieval.py','harness/fact_retrieval.py','rag/bm25.py','rag/retriever.py','rag/context.py')}
    with Path(a.output).open('x',encoding='utf8') as f:json.dump({'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        'source_sha256':hashes,'knowledge_version':plan['knowledge_version'],'cases':result,'model_calls':0},f,ensure_ascii=False,indent=2)
    print(json.dumps([{'case':c['case_id'],**{s:{k:v for k,v in x.items() if k not in ('records','issue')} for s,x in c['sides'].items()}} for c in result]))


if __name__=='__main__':main()
