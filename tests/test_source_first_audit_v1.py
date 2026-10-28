"""Synthetic evidence/semantic responses test wiring, not measured model quality."""
import asyncio,json,os,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from tests.temp_paths import ignored_temporary_directory
from tests.test_literal_review_v1 import Provider,response,fixture
from tests.test_schema14_factory_flow import GOOD
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory
from backend.store import RunStore
from backend.serialization import wire
from services.evidence_scope import make_snapshot
from services.source_first_audit_v1 import VERSION
from core.validation import ContractError

class CandidateProvider(Provider):
    def __init__(self,mode='repair'):super().__init__();self.mode=mode;self.fact_count=0
    async def complete(self,r):
        if r.prompt_version==VERSION:
            self.fact_count+=1;self.requests.append(r)
            d=json.loads(r.messages[1].content);self.payloads.append(d);v=response(d)
            if self.mode in ('gap','missing') and self.fact_count==1 or self.mode=='missing':
                v['defects']=[]
                for row in v['units']:row.update(status='insufficient_evidence',quote_ids=[])
            if self.mode=='supported':
                v['defects']=[]
                for row in v['units']:row.update(status='supported')
            from model_adapter.contracts import ModelResponse
            return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        return await super().complete(r)

def exercise(mode='repair',*,execution_path='sequential',bad_snapshot=False,wrong_source=False):
    from rag.storage import KnowledgeStore,SourceMetadata
    with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
        root=Path(tmp).resolve();doc=root/'fixture.md'
        from tests.test_schema14_factory_flow import BAD
        doc.write_text((BAD if wrong_source else GOOD)+' The synthetic setting applies under condition C.',encoding='utf-8')
        with KnowledgeStore(root/'index.sqlite3') as store:
            k=store.ingest(doc,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            fid=store.rows(k)[0]['fragment_id']
            if wrong_source:
                other=root/'counterevidence.md';other.write_text(GOOD,encoding='utf-8')
                k=store.ingest(other,'counterevidence',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            e=store.evidence(fid,k)
        inp=fixture();a=replace(inp.answer,citations=tuple(replace(c,evidence_ids=(e.evidence_id,)) for c in inp.answer.citations))
        req=replace(inp.request,existing_answer=a,provided_evidence=(e,))
        snapshot=make_snapshot(a,(e,),k)
        if bad_snapshot:snapshot=replace(snapshot,knowledge_version='wrong')
        c=ServiceConfig(index_db=root/'index.sqlite3',knowledge_version=k,run_db=root/'runs.sqlite3',
            fact_review_contract='literal_v1',audit_strategy=VERSION,execution_path=execution_path,
            local_revision_interface='source_actions_v2')
        class P(CandidateProvider):
            async def complete(self,r):
                from services.local_revision_v2 import VERSION as RV
                if r.prompt_version==RV:
                    from model_adapter.contracts import ModelResponse
                    d=json.loads(r.messages[1].content);self.requests.append(r)
                    auth=d['authorizations'][0]
                    v=dict(context_id=d['context_id'],edits=[dict(unit_ref=auth['unit_ref'],authorization_refs=[auth['authorization_ref']],text=GOOD,
                        support_refs=[auth['source_spans'][0]['source_ref']],dependencies=[])],
                        opinion_actions=[dict(opinion_ref=o['opinion_ref'],action='modified' if o['origin']=='source_bound_fact_defect' else 'retained',
                        edit_indices=[0] if o['origin']=='source_bound_fact_defect' else [],explanation='Synthetic action.') for o in d['opinions']])
                    if mode=='revision_failure':v['context_id']='wrong'
                    return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
                return await super().complete(r)
        p=P(mode);store=RunStore(c.run_db);store.create('fixture',req,{})
        async def run():
            f=ComponentFactory(c);b=None
            try:
                b=f.create('fixture',lambda v:store.checkpoint('fixture',v))
                return await b.harness.run(req,c.budget,knowledge_version=k,generation_snapshot=snapshot,run_id='fixture')
            finally:
                if b:await b.drain();b.close()
                await f.close()
        try:
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'synthetic','DEEPSEEK_API_KEY':'fixture'}),patch('model_adapter.deepseek.create_adapter',return_value=p),patch('backend.assembly.ROOT',root):
                result=asyncio.run(run())
            raw=wire(result);store.mark('fixture','finished',result=raw)
            assert store.get('fixture')['result']==raw
            from evaluation.archive_replay import restore
            from harness.contracts import HarnessResult
            assert wire(restore(raw,HarnessResult))==raw
            return result,p
        finally:store.close()

class SourceFirstTests(unittest.TestCase):
    def test_faithful_wrong_source_with_other_document_counterevidence_is_not_truth_checked(self):
        r,p=exercise('supported',wrong_source=True)
        self.assertFalse(r.execution_issues,r.execution_issues)
        self.assertFalse(r.revision_outputs)
        self.assertTrue(all(x.calls_used==0 for x in r.retrieval_records))
        self.assertEqual(r.report.decision.kind.value,'pass')
        self.assertIn('independent external truth',r.report.decision.reasons[-1])

    def test_five_gap_queries_cap_and_duplicate_objects_are_explicit(self):
        from types import SimpleNamespace as NS
        from core.models import Claim
        from core.literal_review import LiteralUnitReview
        from harness.source_first_audit_v1 import supplement
        from harness.contracts import RetrievalRecord
        from harness.retrieval import Delivery
        from core.models import ExecutionStatus
        from agents.contracts import LiteralVerificationOutput
        claims=tuple(Claim(str(i),'a',1,f'topic{i}',i*10,i*10+6,'technical_fact',proposition=f'topic{i}') for i in range(5))
        claims+=(replace(claims[0],claim_id='duplicate'),)
        units=tuple(LiteralUnitReview(str(i),f'topic{i}',i*10,i*10+6,'insufficient_evidence','Synthetic missing body.','adequate',()) for i in range(5))
        class Session:
            def __init__(self):self.calls=0;self.chars=0;self.records=[]
            async def retrieve(self,*args,**kw):
                self.calls+=1
                r=RetrievalRecord(str(self.calls),'verification',kw['query_override'],'fixture',1,'k',ExecutionStatus.SUCCEEDED,'empty')
                return Delivery((),(),None,r)
        ex=NS(v_issue=None,verification=LiteralVerificationOutput('a',1,claims,(),(),literal_reviews=units),
            claims=claims,v_evidence=(),request=None,answer=NS(answer_id='a',version=1),knowledge_version='k',
            retrieval=Session(),record=lambda *a:None)
        asyncio.run(supplement(ex))
        self.assertEqual(ex.retrieval.calls,3)
        gaps=json.loads(ex.retrieval.records[-1].reason)['gaps']
        self.assertEqual(sum(g['outcome']=='query_limit' for g in gaps),2)
        self.assertEqual(gaps[0]['retrieval_id'],gaps[1]['retrieval_id'])
        self.assertEqual(ex.verification.literal_reviews,units)

    def test_atomic_global_token_and_chain_budget_is_reserved_before_send(self):
        from evaluation.source_first_audit_redesign_v1 import SendLimit
        from model_adapter.contracts import ModelRequest,ModelMessage
        from concurrent.futures import ThreadPoolExecutor
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            guard=SendLimit(Path(tmp));r=ModelRequest('deepseek-flash',(ModelMessage('user','x'),),8000,'fixture')
            spec={'case':0,'variant':'candidate'}
            def reserve(_):
                try:guard(spec,r,1);return True
                except RuntimeError:return False
            with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(reserve,range(20)))
            self.assertEqual(sum(values),12);self.assertEqual(guard.calls,12)
            self.assertEqual(len(list((Path(tmp)/'reservations').glob('*.json'))),12)
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            guard=SendLimit(Path(tmp));guard.tokens=1199999
            with self.assertRaises(RuntimeError):guard(spec,r,1)
            self.assertEqual(guard.calls,0)

    def test_source_context_wrong_version_and_cancellation_never_fall_back_to_match(self):
        from rag.retriever import AsyncSQLiteBM25Retriever
        from rag.storage import KnowledgeStore
        from rag.contracts import ContextOptions
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            root=Path(tmp);p=root/'x.md';p.write_text('Synthetic first fragment.\n\nSynthetic second fragment.',encoding='utf-8')
            with KnowledgeStore(root/'k.sqlite3') as s:
                k=s.ingest(p,'fixture').knowledge_version;e=s.evidence(s.rows(k)[0]['fragment_id'],k)
            async def run():
                r=AsyncSQLiteBM25Retriever(root/'k.sqlite3')
                try:
                    with self.assertRaises(ContractError):await r.source_context((e,),'wrong',ContextOptions())
                    ctx=await r.source_context((e,),k,ContextOptions(max_chars=0))
                    self.assertFalse(ctx.items)
                    from threading import Event
                    entered=Event();release=Event();original=r._work
                    def slow(*a):entered.set();release.wait(2);return original(*a)
                    r._work=slow
                    task=asyncio.create_task(r.source_context((e,),k,ContextOptions()))
                    while not entered.is_set():await asyncio.sleep(.005)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):await task
                    with self.assertRaises(RuntimeError):await r.source_context((e,),k,ContextOptions())
                    release.set()
                    while not r._active.done():await asyncio.sleep(.005)
                finally:r.close()
            asyncio.run(run())

    def test_fixed_sources_repair_and_full_reaudit_both_drivers_store(self):
        for driver in ('sequential','langgraph_v1'):
            r,p=exercise(execution_path=driver)
            self.assertFalse(r.execution_issues,r.execution_issues)
            self.assertEqual(r.answer.version,2);self.assertEqual(len(r.review_rounds),2)
            self.assertEqual(p.fact_count,2)
            self.assertEqual(sum(x.prompt_version.startswith('power-domain') for x in p.requests),2)
            self.assertTrue(all(x.query_method==VERSION for x in r.retrieval_records))
            self.assertTrue(all(x.calls_used==0 for x in r.retrieval_records))

    def test_supported_first_round_is_not_external_truth_proof(self):
        r,p=exercise('supported')
        self.assertEqual(r.answer.version,1);self.assertFalse(r.revision_outputs)
        scope=json.loads(r.retrieval_records[0].reason)
        self.assertFalse(scope['source_truth_verified']);self.assertEqual(scope['external_cross_check'],'not_executed')
        # Deliberately wrong source-faithful/supported judgment survives: expose the
        # first-round miss, do not reinterpret a synthetic pass as truth.

    def test_missing_basis_bounded_search_never_becomes_pass(self):
        r,p=exercise('missing');self.assertNotEqual(r.report.decision.kind.value,'pass')
        self.assertLessEqual(max(x.calls_used for x in r.retrieval_records),3)
        self.assertFalse(r.revision_outputs)

    def test_gap_delivery_second_review_and_revision(self):
        r,p=exercise('gap');self.assertFalse(r.execution_issues,r.execution_issues)
        self.assertEqual(r.answer.version,2);self.assertEqual(p.fact_count,3)

    def test_revision_failure_no_false_success(self):
        r,p=exercise('revision_failure');self.assertTrue(r.execution_issues)
        self.assertEqual(r.answer.version,1);self.assertFalse(r.revision_outputs)

    def test_wrong_snapshot_rejected_before_model(self):
        with self.assertRaises(ContractError):exercise(bad_snapshot=True)

    def test_default_and_incompatible_candidate_rejected(self):
        self.assertEqual(ServiceConfig().audit_strategy,'baseline')
        with self.assertRaises(ValueError):ServiceConfig(audit_strategy=VERSION)

if __name__=='__main__':unittest.main()
