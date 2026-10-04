"""Public synthetic_fixture: indexed delivery, scopes and restart, no network."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import importlib.util
from unittest.mock import patch
from agents.fakes import make_fake_harness
from core.models import *
from core.validation import ContractError
from harness.contracts import RetrievalSettings, RunBudget
from harness.fact_retrieval import retrieve_facts
from harness.retrieval import RetrievalSession
from rag.contracts import ContextOptions, RetrievalPurpose
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.storage import KnowledgeStore, SourceMetadata
from services.fact_delivery import payload, validate_result
from services.scoped_candidates import CandidateScope
from tests.test_harness_retrieval import HookRetriever

class FactRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);md=root/'synthetic_fixture.md'
        md.write_text('# Alpha\n\nalpha generator winding.\n\n# Beta\n\nbeta voltage support.\n',encoding='utf8')
        self.db=root/'knowledge.sqlite3'
        with KnowledgeStore(self.db) as store:self.k=store.ingest(md,'synthetic_fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
        self.actual=AsyncSQLiteBM25Retriever(self.db);self.addCleanup(self.actual.close)
        self.retriever=HookRetriever(self.actual)
        self.answer=AnswerDraft('a',1,'alpha generator. beta voltage.')
        self.request=TaskRequest('t',TaskMode.ASSESS_EXISTING,'synthetic_fixture','Explain.',existing_answer=self.answer)
        self.claims=tuple(ObligationClaim('c'+str(i),'a',1,text,start,start+len(text),'technical_fact',proposition=word,
            components=(ClaimComponent('p'+str(i),'technical_fact',word),),component_basis_targets=('technical_content',),component_obligations=('technical_truth',))
            for i,(text,start,word) in enumerate((('alpha generator.',0,'alpha'),('beta voltage.',17,'beta'))))
    def session(self,**limits):
        from time import perf_counter
        return RetrievalSession(self.retriever,self.k,RetrievalSettings(1,None,'per_claim_v1'),RunBudget(**limits),perf_counter()+30,())

    async def test_keyword_competition_and_shared_evidence_explicit(self):
        s=self.session();out=await retrieve_facts(s,self.request,self.answer,self.claims)
        self.assertEqual(s.calls,2);self.assertEqual(len(out.evidence),2)
        maps=out.record.fact_bindings
        self.assertNotEqual(maps[0].delivered_evidence_ids,maps[1].delivered_evidence_ids)
        aggregate=await self.session().retrieve(RetrievalPurpose.VERIFICATION,self.request,self.answer,self.claims)
        self.assertEqual(len(aggregate.evidence),1)
        # Separate queries can intentionally deliver the same frozen Evidence.
        c=replace(self.claims[1],components=(replace(self.claims[1].components[0],proposition='alpha generator'),))
        shared=await retrieve_facts(self.session(),self.request,self.answer,(self.claims[0],c))
        self.assertEqual(shared.record.fact_bindings[0].delivered_evidence_ids,shared.record.fact_bindings[1].delivered_evidence_ids)
        self.assertEqual(len(shared.evidence),1)

    async def test_identical_query_reused_with_stable_mapping_order(self):
        s=self.session();c=replace(self.claims[1],components=(replace(self.claims[1].components[0],proposition='alpha'),))
        out=await retrieve_facts(s,self.request,self.answer,(self.claims[0],c))
        self.assertEqual(s.calls,1);self.assertEqual(len(self.retriever.requests),1)
        m=out.record.fact_bindings;self.assertEqual([x.claim_id for x in m],['c0','c1'])
        self.assertEqual(m[1].reused_from_retrieval_id,m[0].retrieval_id)

    async def test_no_hit_is_not_contradiction(self):
        c=replace(self.claims[0],components=(replace(self.claims[0].components[0],proposition='zzzzzz'),))
        out=await retrieve_facts(self.session(),self.request,self.answer,(c,))
        self.assertIsNone(out.issue);self.assertEqual(out.record.fact_bindings[0].outcome,'empty')

    async def test_failure_preserves_valid_peer_and_capacity_is_separate(self):
        async def fail(r):
            if r.query=='beta':raise RuntimeError('synthetic_fixture failure')
        self.retriever.hook=fail
        out=await retrieve_facts(self.session(),self.request,self.answer,self.claims)
        self.assertTrue(out.evidence);self.assertIsNotNone(out.issue)
        self.assertEqual([m.outcome for m in out.record.fact_bindings],['hits','failed'])
        self.retriever.hook=None
        out=await retrieve_facts(self.session(max_retrieval_chars_per_call=1),self.request,self.answer,self.claims)
        self.assertFalse(out.evidence);self.assertTrue(out.record.fact_bindings[0].core_hit_ids)
        self.assertEqual(out.record.fact_bindings[0].outcome,'budget_exhausted')
        self.assertTrue(out.record.fact_bindings[0].omissions)

    async def test_metadata_scope_recommendation_and_scalar_are_not_body_queries(self):
        for target in ('index_metadata','input_snapshot','answer_text','recommendation','mathematical_relation','unknown'):
            c=replace(self.claims[0],component_basis_targets=(target,))
            s=self.session();out=await retrieve_facts(s,self.request,self.answer,(c,))
            self.assertEqual(s.calls,0)
            self.assertEqual(out.record.fact_bindings[0].basis_target,target)

    async def test_revision_rebinds_same_query_to_new_version(self):
        s=self.session();one=await retrieve_facts(s,self.request,self.answer,self.claims)
        two=await retrieve_facts(s,self.request,replace(self.answer,version=2),tuple(replace(c,answer_version=2) for c in self.claims))
        self.assertEqual(s.calls,2)
        self.assertTrue(all(m.answer_version==2 and m.reused_from_retrieval_id for m in two.record.fact_bindings))
        self.assertNotEqual(one.record.fact_bindings[0].retrieval_id,two.record.fact_bindings[0].retrieval_id)

    async def test_wrong_scope_version_and_cross_component_basis_rejected(self):
        from agents.contracts import ReliabilityVerificationInput,EvidenceVerificationOutput
        out=await retrieve_facts(self.session(),self.request,self.answer,self.claims)
        i=ReliabilityVerificationInput(self.request,self.answer,self.claims,out.evidence,knowledge_version=self.k,fact_retrieval_bindings=out.record.fact_bindings)
        scope=CandidateScope(self.answer,self.k,'independent',out.evidence)
        self.assertEqual(len(payload(i,scope)['components']),2)
        for wrong in (replace(i.fact_retrieval_bindings[0],answer_version=2),replace(i.fact_retrieval_bindings[0],delivered_evidence_ids=('wrong',))):
            with self.assertRaises(ContractError):payload(replace(i,fact_retrieval_bindings=(wrong,i.fact_retrieval_bindings[1])),scope)
        f=VerificationFinding('f','c0',VerificationStatus.SUPPORTED,(),'synthetic_fixture','synthetic_fixture',
            bases=(TypedBasis('text_excerpt',evidence_id=i.fact_retrieval_bindings[1].delivered_evidence_ids[0]),),
            component_reviews=(ComponentReview('p0',VerificationStatus.SUPPORTED,(0,),'synthetic_fixture'),))
        with self.assertRaises(ContractError):validate_result(EvidenceVerificationOutput('a',1,self.claims,(f,),out.evidence),i)

    async def test_index_wrong_id_fails_not_a_fact_verdict(self):
        async def tamper(r):
            output=await self.actual.retrieve(r)
            return replace(output,evidence=tuple(replace(e,evidence_id='wrong') for e in output.evidence))
        self.retriever.hook=tamper
        out=await retrieve_facts(self.session(),self.request,self.answer,self.claims)
        self.assertFalse(out.evidence);self.assertEqual(out.issue.code,'RETRIEVAL_CONTRACT_ERROR')

    async def test_checkpoint_mapping_restart_persisted(self):
        from backend.store import RunStore
        from backend.serialization import wire
        out=await retrieve_facts(self.session(),self.request,self.answer,self.claims)
        path=Path(self.tmp.name)/'runs.sqlite3';store=RunStore(path)
        store.create('r',self.request,{'profile':'synthetic_fixture'})
        store.mark('r','finished',result={'retrieval_records':wire(tuple(self.session().records)+(out.record,))})
        original=store.get('r')['result'];store.close();store=RunStore(path)
        try:self.assertEqual(store.get('r')['result'],original)
        finally:store.close()

    async def test_harness_partial_retrieval_keeps_reviews_and_cannot_pass(self):
        from agents.fakes import FakeConfig
        h=make_fake_harness(FakeConfig(text=self.answer.text,reference_input_evidence=True))
        h.retriever=self.retriever;h.retrieval_settings=RetrievalSettings(1,None,'per_claim_v1')
        h.verification.schema_version=13
        class Extractor:
            async def extract(_,answer):return tuple(replace(c,answer_id=answer.answer_id,answer_version=answer.version) for c in self.claims)
        h.extractor=Extractor()
        async def fail(r):
            if r.query=='beta':raise RuntimeError('synthetic_fixture beta failed')
        self.retriever.hook=fail
        result=await h.run(self.request,RunBudget(max_revision_rounds=0),knowledge_version=self.k)
        self.assertTrue(result.verification_output.findings)
        self.assertIsNotNone(result.domain_output)
        self.assertTrue(result.execution_issues)
        self.assertNotEqual(result.report.decision.kind,DecisionKind.PASS)

    async def test_frozen_comparison_driver_preserves_shared_answer_and_claims(self):
        from dataclasses import asdict
        from evaluation.fact_retrieval_comparison import compare
        out=await retrieve_facts(self.session(),self.request,self.answer,self.claims)
        case={'case_id':0,'answer':asdict(self.answer),'shared_claims':[asdict(c) for c in self.claims],
              'targets':[{'expected_fragment_id':e.provenance.fragment_id} for e in out.evidence]}
        case=json.loads(json.dumps(case)) # frozen JSON, not Python dataclass tuples
        result=(await compare(self.db,self.k,(case,),RetrievalSettings(1,None),RunBudget()))[0]
        self.assertEqual(result['answer'],case['answer']);self.assertEqual(result['shared_claims'],case['shared_claims'])
        self.assertEqual(result['sides']['aggregate']['retrieval_calls'],1)
        self.assertEqual(result['sides']['per_claim_v1']['retrieval_calls'],2)

    @unittest.skipUnless(importlib.util.find_spec('fastapi') and importlib.util.find_spec('httpx'), 'Optional API dependencies: requirements-api.lock.txt')
    def test_http_mapping_projection_and_restart_preserve_version_and_query(self):
        import time
        from fastapi.testclient import TestClient
        from backend.api import create_app
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory,Bundle
        from agents.fakes import FakeConfig
        outer=self
        class Factory(ComponentFactory):
            def preflight(self):return outer.k
            def create(self,rid,observer):
                h=make_fake_harness(FakeConfig(reference_input_evidence=True));h.retriever=outer.retriever
                h.retrieval_settings=RetrievalSettings(1,None,'per_claim_v1');h.observer=observer;h.verification.schema_version=13
                class Extractor:
                    async def extract(_,answer):return tuple(replace(c,answer_id=answer.answer_id,answer_version=answer.version) for c in outer.claims)
                h.extractor=Extractor();return Bundle(h)
        config=ServiceConfig(profile='synthetic_fixture',fact_strategy='per_claim_v1',run_db=Path(self.tmp.name)/'api.sqlite3',token_file=Path(self.tmp.name)/'synthetic-token')
        headers={'Authorization':'Bearer fictional-fixture-only'}
        def app():return create_app(config,factory=Factory(config),access_token='fictional-fixture-only')
        with TestClient(app()) as client:
            r=client.post('/runs',headers=headers,json={'mode':'assess_existing','question':'synthetic_fixture','existing_answer':self.answer.text})
            self.assertEqual(r.status_code,202);rid=r.json()['run_id']
            for _ in range(150):
                if client.get('/runs/'+rid,headers=headers).json()['status'] not in ('queued','running'):break
                time.sleep(.01)
            result=client.get('/runs/'+rid+'/result',headers=headers).json()
            mappings=[m for record in result['retrieval'] for m in record.get('fact_bindings',[])]
            self.assertEqual(len(mappings),2);self.assertTrue(all(m['answer_version']==1 for m in mappings))
            self.assertEqual(result['budget_usage']['retrieval_calls'],3) # two facts + domain
        with TestClient(app()) as client:
            self.assertEqual(client.get('/runs/'+rid+'/result',headers=headers).json(),result)

class FactModelScopeTests(unittest.TestCase):
    def test_one_request_scoped_components_and_original_citation_remain_isolated(self):
        from tests.test_citation_workload import invoke
        from tests.test_fact_rereview_v3 import inputs
        i=inputs(two=True)
        other=replace(i.seed_evidence[0],evidence_id='other-independent')
        i=replace(i,seed_evidence=i.seed_evidence+(other,),knowledge_version='synthetic-k',generation_snapshot=None)
        maps=tuple(FactRetrievalBinding(i.answer.answer_id,i.answer.version,c.claim_id,c.components[0].component_id,
            'technical_fact','technical_content',c.components[0].proposition,'synthetic_fixture','r'+str(n),
            'synthetic-k','hits',delivered_evidence_ids=(i.seed_evidence[n].evidence_id,)) for n,c in enumerate(i.claims))
        i=replace(i,fact_retrieval_bindings=maps)
        out,b,seen=invoke(i)
        self.assertEqual(b.used,3) # independent + one correction + original group
        self.assertTrue(out.execution_issues)
        self.assertEqual(out.findings[0].status,VerificationStatus.SUPPORTED)
        self.assertEqual(out.findings[1].status,VerificationStatus.NOT_ASSESSABLE)
        self.assertEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)
        independent=json.loads(seen[0].messages[1].content)
        original=json.loads(seen[-1].messages[1].content)
        self.assertEqual(independent['FACT_EVIDENCE_DELIVERY']['contract_version'],'fact-evidence-delivery-v1')
        self.assertNotIn('FACT_EVIDENCE_DELIVERY',original)
        self.assertEqual({q['evidence_id'] for q in original['ORIGINAL_CITATION_SCOPES'][0]['QUOTE_CANDIDATES']},{'original'})
