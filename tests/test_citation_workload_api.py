"""Real API wiring with synthetic model/knowledge components, no paid calls."""
import json
from pathlib import Path
import tempfile
import time
import unittest
try:
    from fastapi.testclient import TestClient
    from backend.api import create_app
except ImportError:
    TestClient=None
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory,Bundle
from agents.fakes import make_fake_harness
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings,ModelResponse
from rag.storage import KnowledgeStore
from rag.retriever import AsyncSQLiteBM25Retriever
from services.citation_workload import CitationWorkload
from services.claim_obligations import parse
from services.answer_anchors import anchors
from tests.test_fact_rereview_v3 import response

class Extractor:
    uses_model_adapter=True
    async def extract(self,answer):
        return parse({'claims':[{'anchor_id':anchors(answer)[0]['anchor_id'],
            'proposition':answer.text,'claim_type':'technical_fact','assertion_role':'asserted',
            'semantic_qualifiers':[],'components':[{'category':'technical_fact','proposition':answer.text,
                'basis_target':'technical_content','verification_obligation':'technical_truth'}]}], 'non_claims':[]},answer)

class Factory(ComponentFactory):
    def preflight(self):return self.config.knowledge_version
    def create(self,rid,observer):
        class Adapter:
            async def complete(self,r):
                d=json.loads(r.messages[1].content)
                if 'ORIGINAL_CITATION_SCOPES' not in d:v=response(d)
                else:v={'citation_reviews':[{'citation_index':s['citation_index'],'status':'supported',
                    'rationale':'synthetic_fixture support','applicability_conditions':[],
                    'bases':[{'type':'text_excerpt','quote_id':s['QUOTE_CANDIDATES'][0]['quote_id']}]} for s in d['ORIGINAL_CITATION_SCOPES']]}
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        h=make_fake_harness();h.observer=observer;h.extractor=Extractor()
        retriever=AsyncSQLiteBM25Retriever(self.config.index_db);h.retriever=retriever
        h.verification=ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture',max_output_tokens=8000),
            schema_version=13,citation_workload=self.config.citation_workload)
        return Bundle(h,(retriever,))

@unittest.skipUnless(TestClient is not None,'Optional API test dependencies unavailable; install requirements-api.lock.txt')
class WorkloadAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        md=p/'source.md';md.write_text('# synthetic_fixture\n\nReactive power affects voltage.',encoding='utf-8')
        with KnowledgeStore(p/'index.db') as s:
            k=s.ingest(md,'synthetic_fixture').knowledge_version;self.fragment=s.rows(k)[0]['fragment_id']
        self.config=ServiceConfig(index_db=p/'index.db',knowledge_version=k,run_db=p/'runs.db',token_file=p/'token')
        self.headers={'Authorization':'Bearer fictional-test-token-not-a-secret'}
        self.client=TestClient(create_app(self.config,factory=Factory(self.config),access_token='fictional-test-token-not-a-secret'))
        self.client.__enter__()
        self.body={'mode':'assess_existing','question':'Reactive power voltage','existing_answer':'Reactive power affects voltage.',
            'existing_citations':[{'start_offset':0,'end_offset':30,'fragment_ids':[self.fragment]} for _ in range(3)]}
    def tearDown(self):
        self.client.__exit__(None,None,None);self.tmp.cleanup()
    def test_bindings_api_scopes_results_and_restart_persistence(self):
        r=self.client.post('/runs',headers=self.headers,json=self.body)
        self.assertEqual(r.status_code,202,r.text);rid=r.json()['run_id'];base='/runs/'+rid
        for _ in range(300):
            if self.client.get(base,headers=self.headers).json()['status'] not in ('queued','running'):break
            time.sleep(.01)
        result=self.client.get(base+'/result',headers=self.headers).json()
        citations=result['findings']['original_citations']
        self.assertEqual(len(citations),3,result);self.assertTrue(all(c['status']=='supported' for c in citations),result)
        self.assertEqual(sum(r['prompt_version']=='evidence-verification-v9.6-explicit-frozen-stance' for r in result['model_usage']),2)
        for e in result['evidence']:
            self.assertEqual(self.client.get(base+'/evidence/'+e['evidence_id'],headers=self.headers).json()['text'],e['text'])
        self.client.__exit__(None,None,None)
        self.client=TestClient(create_app(self.config,factory=Factory(self.config),access_token='fictional-test-token-not-a-secret'));self.client.__enter__()
        self.assertEqual(self.client.get(base+'/result',headers=self.headers).json(),result)
    def test_bad_fragment_span_and_mode_rejected_before_run(self):
        for body in (dict(self.body,existing_citations=[{'start_offset':0,'end_offset':999,'fragment_ids':[self.fragment]}]),
                     dict(self.body,existing_citations=[{'start_offset':0,'end_offset':10,'fragment_ids':['unknown']}]),
                     dict(self.body,mode='question_answer',existing_answer=None)):
            self.assertEqual(self.client.post('/runs',headers=self.headers,json=body).status_code,422)
        self.assertEqual(self.client.get('/runs/page/0',headers=self.headers).json()['items'],[])
    def test_known_capacity_rejected_before_queue(self):
        self.client.__exit__(None,None,None)
        from dataclasses import replace
        self.config=replace(self.config,citation_workload=CitationWorkload(32,100,200))
        self.client=TestClient(create_app(self.config,factory=Factory(self.config),access_token='fictional-test-token-not-a-secret'));self.client.__enter__()
        r=self.client.post('/runs',headers=self.headers,json=self.body)
        self.assertEqual(r.status_code,422)
        self.assertEqual(r.json()['detail']['code'],'REVIEW_MESSAGE_CAPACITY_EXCEEDED')
