"""Public synthetic_fixture service wiring, no external model/data/network."""
import asyncio
from dataclasses import replace
from unittest.mock import patch
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory,ConfigurationError,Bundle,RetrieverLease
import unittest
from tests import test_semantic as fixtures
FixtureEncoder=fixtures.FixtureEncoder

class ServiceSemanticTests(unittest.TestCase):
    setUp=fixtures.SemanticTests.setUp
    tearDown=fixtures.SemanticTests.tearDown
    req=fixtures.SemanticTests.req
    def factory(self,mode='dense',strategy='aggregate'):
        return ComponentFactory(ServiceConfig(index_db=self.db,vector_db=self.vec,
            knowledge_version=self.kv,retrieval_mode=mode,fact_strategy=strategy))
    def test_three_modes_two_strategies(self):
        for mode in ('bm25','dense','hybrid'):
            for strategy in ('aggregate','per_claim_v1'):
                f=self.factory(mode,strategy);f.initialize_retrieval(self.encoder)
                manifest=f.manifest(self.kv)
                self.assertEqual((manifest['retrieval_mode'],manifest['fact_retrieval_strategy']),(mode,strategy))
                if mode!='bm25':
                    async def check():
                        r=await f.semantic_resource.retrieve(self.req('voltage'))
                        await f.semantic_resource.validate_result(self.req('voltage'),r)
                        self.assertTrue(r.evidence)
                        await f.close()
                    asyncio.run(check())
                else:self.assertIsNone(f.semantic_resource)
    def test_bad_profile_and_snapshot_fail_without_fallback(self):
        with self.assertRaises(ConfigurationError):self.factory().initialize_retrieval(FixtureEncoder('wrong'))
        f=self.factory();f.config=replace(f.config,knowledge_version='missing')
        with self.assertRaises(ConfigurationError):f.initialize_retrieval(self.encoder)
        self.assertIsNone(f.semantic_resource)
    def test_demo_never_loads_semantic(self):
        f=ComponentFactory(ServiceConfig(profile='synthetic_fixture',retrieval_mode='hybrid'))
        with patch('rag.embedding.E5ONNXEncoder',side_effect=AssertionError('must not load')):
            f.initialize_retrieval();self.assertIsNone(f.semantic_resource)
    def test_service_lifetime_and_lease(self):
        f=self.factory();f.initialize_retrieval(self.encoder);resource=f.semantic_resource
        f.initialize_retrieval(FixtureEncoder('wrong'))
        self.assertIs(resource,f.semantic_resource)
        Bundle(None,(RetrieverLease(resource),)).close();self.assertFalse(resource._closed)
        asyncio.run(f.close());self.assertTrue(resource._closed)
    def test_cancel_waits_before_encoder_close_and_rejects_overlap(self):
        import threading
        started=threading.Event();release=threading.Event();closed=[]
        f=self.factory();f.initialize_retrieval(self.encoder);r=f.semantic_resource
        original=self.encoder.encode
        def slow(texts,kind):
            started.set();release.wait(5);return original(texts,kind)
        self.encoder.encode=slow;self.encoder.close=lambda:closed.append(True)
        async def check():
            task=asyncio.create_task(r.retrieve(self.req()))
            await asyncio.to_thread(started.wait,2);task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            with self.assertRaisesRegex(RuntimeError,'busy'):await r.retrieve(self.req())
            closing=asyncio.create_task(f.close());await asyncio.sleep(.05)
            self.assertFalse(closed);self.assertFalse(closing.done())
            release.set();await closing;self.assertEqual(closed,[True])
        try:asyncio.run(check())
        finally:release.set()
    def test_per_component_scope_reuse_and_restart_in_all_modes(self):
        from core.models import AnswerDraft,TaskRequest,TaskMode,ObligationClaim,ClaimComponent
        from harness.contracts import RetrievalSettings,RunBudget
        from harness.retrieval import RetrievalSession
        from harness.fact_retrieval import retrieve_facts
        from rag.retriever import AsyncSQLiteBM25Retriever
        from services.fact_delivery import payload
        from services.scoped_candidates import CandidateScope
        from agents.contracts import ReliabilityVerificationInput
        from backend.store import RunStore
        from backend.serialization import wire
        from time import perf_counter
        a=AnswerDraft('answer',1,'Voltage. Reactive.')
        request=TaskRequest('task',TaskMode.ASSESS_EXISTING,'synthetic_fixture','Review.',existing_answer=a)
        claims=tuple(ObligationClaim('c'+str(i),'answer',1,text,offset,offset+len(text),'technical_fact',
            proposition=q,components=(ClaimComponent('p'+str(i),'technical_fact',q),),
            component_basis_targets=('technical_content',),component_obligations=('technical_truth',))
            for i,(text,offset,q) in enumerate((('Voltage.',0,'voltage'),('Reactive.',9,'reactive'))))
        async def check(mode):
            f=self.factory(mode,'per_claim_v1');f.initialize_retrieval(self.encoder)
            r=f.semantic_resource or AsyncSQLiteBM25Retriever(self.db)
            try:
                session=RetrievalSession(r,self.kv,RetrievalSettings(1,None,'per_claim_v1'),RunBudget(),perf_counter()+20,())
                d=await retrieve_facts(session,request,a,claims)
                i=ReliabilityVerificationInput(request,a,claims,d.evidence,knowledge_version=self.kv,fact_retrieval_bindings=d.record.fact_bindings)
                scope=CandidateScope(a,self.kv,'independent',d.evidence);p=payload(i,scope)
                catalog={q['quote_id']:q for q in scope.payload()['QUOTE_CANDIDATES']}
                for m in p['components']:
                    self.assertTrue(all(catalog[q]['evidence_id'] in m['delivered_evidence_ids'] for q in m['allowed_quote_ids']))
                repeated=replace(claims[1],components=(replace(claims[1].components[0],proposition='voltage'),))
                shared=await retrieve_facts(session,request,a,(claims[0],repeated))
                self.assertEqual(shared.record.fact_bindings[0].delivered_evidence_ids,shared.record.fact_bindings[1].delivered_evidence_ids)
                db=self.root/(mode+'-runs.sqlite3');s=RunStore(db);manifest=f.manifest(self.kv)
                s.create('run',request,manifest);s.mark('run','finished',result={'retrieval_records':wire((d.record,))});before=s.get('run');s.close()
                s=RunStore(db)
                try:self.assertEqual(s.get('run'),before)
                finally:s.close()
            finally:
                if f.semantic_resource:await f.close()
                else:r.close()
        for mode in ('bm25','dense','hybrid'):asyncio.run(check(mode))
    def test_public_fixed_comparison_driver(self):
        import json
        from dataclasses import asdict
        from evaluation.semantic_service_comparison import compare
        from core.models import AnswerDraft,ObligationClaim,ClaimComponent
        from harness.contracts import RetrievalSettings,RunBudget
        answer=AnswerDraft('a',1,'Voltage.')
        claim=ObligationClaim('c','a',1,'Voltage.',0,8,'technical_fact',proposition='voltage',
            components=(ClaimComponent('p','technical_fact','voltage'),),component_basis_targets=('technical_content',),
            component_obligations=('technical_truth',))
        case=json.loads(json.dumps({'case_id':0,'answer':asdict(answer),'shared_claims':[asdict(claim)],'targets':[]}))
        for mode in ('bm25','dense','hybrid'):
            result=asyncio.run(compare(self.factory(mode).config,(case,),RetrievalSettings(1,None),RunBudget(),encoder=self.encoder))
            self.assertEqual(result['paid_model_calls'],0)
            self.assertEqual(result['cases'][0]['retrieval_calls'],1)
            self.assertEqual(result['cases'][0]['query_encodings'],0 if mode=='bm25' else 2)
