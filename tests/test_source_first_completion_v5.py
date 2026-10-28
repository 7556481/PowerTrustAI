"""Actual adapter thread + Factory/Harness/Store; no paid model requests."""
import asyncio,json,unittest,tempfile,time,threading
from pathlib import Path
from dataclasses import replace
from copy import deepcopy
from unittest.mock import patch
from model_adapter.contracts import ModelResponse,ModelSettings,ModelRequest,ModelMessage
from tests.test_source_first_quality_v4 import RelationSubstitute
from evaluation.source_first_quality_v4 import LOCAL as V4

class ArchivedThenSynthetic(RelationSubstitute):
    def __init__(self):
        super().__init__();self.archive=V4/'live/provider-responses'
    async def complete(self,r):
        d=json.loads(r.messages[1].content);answer=d.get('answer',{});aid=answer.get('answer_id','');version=answer.get('version')
        n=None
        if version==1 and 'N1' in aid:n=5 if r.prompt_version=='source_first_audit_v2' else 6 if r.prompt_version.startswith('power-domain-review') else None
        if version==1 and 'N2' in aid:n=(9 if r.correction else 7) if r.prompt_version=='source_first_audit_v2' else 8 if r.prompt_version.startswith('power-domain-review') else None
        if n:
            from evaluation.archive_replay import restore
            return restore(json.loads((self.archive/f'{n:04d}.json').read_text()),ModelResponse)
        return await super().complete(r)

class IsolationEntryTests(unittest.TestCase):
    def exercise(self,two_unknown=False,unsafe=False,shared=False):
        from rag.storage import KnowledgeStore,SourceMetadata
        from tests.pdf_fixtures import make_pdf
        from tests.test_schema14_factory_flow import GOOD
        from tests.test_literal_review_v1 import fixture
        from services.evidence_scope import make_snapshot
        from services.claim_extractor import ModelClaimExtractor
        from backend.serialization import wire
        from backend.config import ServiceConfig
        from core.validation import validate_extraction
        from model_adapter.runtime import ModelBudget,model_scope
        from model_adapter.deepseek import DeepSeekAdapter
        from evaluation.source_first_completion_v5 import execute
        from evaluation.failure_isolation_v5 import Gate,Isolation
        async def go(root):
            pdf=root/'fixture.pdf';pdf.write_bytes(make_pdf([GOOD+' The synthetic setting applies under condition C.','A nonempty real adjacent page.']))
            with KnowledgeStore(root/'index.sqlite3') as store:
                version=store.ingest(pdf,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
                e=next(store.evidence(x['fragment_id'],version) for x in store.rows(version) if GOOD in x['raw_text'])
            original=fixture();a=replace(original.answer,text=GOOD,citations=tuple())
            request=replace(original.request,existing_answer=a,provided_evidence=(e,))
            with model_scope(ModelBudget(2)):
                extraction=await ModelClaimExtractor(RelationSubstitute(),ModelSettings('deepseek-flash',90,8000,96000),typed_components=True,protocol_version=7,daily_guidance=True).extract(a)
            cases=[]
            for i in range(3):
                answer=replace(a,answer_id='isolation-'+str(i))
                ex=replace(extraction,answer_id=answer.answer_id,claims=tuple(replace(cl,answer_id=answer.answer_id) for cl in extraction.claims))
                cases.append(dict(request=wire(replace(request,existing_answer=answer)),snapshot=wire(make_snapshot(answer,(e,),version)),extraction=wire(ex)))
            m=dict(cases=cases);c=ServiceConfig(index_db=root/'index.sqlite3',knowledge_version=version,execution_path='langgraph_v1')
            gate=Gate(root/'batch');policy=Isolation(gate,release_timeout=.01 if unsafe else 2);created=[];work_ended=[]
            def provider(settings,**options):
                channel=len(created);created.append(time.monotonic());delegate=RelationSubstitute()
                def exchange(body,timeout,limit):
                    if shared and channel==0:return 429,b'{}'
                    payload=json.loads(body);messages=tuple(ModelMessage(x['role'],x['content']) for x in payload['messages'])
                    version='source_first_audit_v2' if 'relation_check' in messages[0].content else 'power-domain-review-v3.5-task-obligations'
                    if channel==0 or two_unknown and channel==2:time.sleep(.8)
                    out=asyncio.run(delegate.complete(ModelRequest('deepseek-flash',messages,8000,version)))
                    work_ended.append((channel,time.monotonic()))
                    return 200,json.dumps(dict(model='deepseek-flash',choices=[dict(message=dict(content=out.text),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=10))).encode()
                return DeepSeekAdapter(settings,exchange=exchange)
            rows=[dict(id=f'T{i}',input=dict(line='B',case=i,variant='candidate')) for i in range(3)]
            with patch.dict('os.environ',{'DEEPSEEK_MODEL_ID':'deepseek-flash'}):
                result=await execute(c,m,root/'batch',provider,selected=rows,gate=gate,policy=policy,budget_for=lambda spec,b:replace(b,max_model_calls=20,step_timeout_seconds=.4,max_revision_rounds=1))
            if unsafe or shared:
                self.assertEqual(len(result['control']),1);self.assertTrue(gate.stopped);self.assertEqual(len(created),2)
                self.assertFalse(any(x['code']=='DIAGNOSTIC_STORAGE_FAILED' for v in result['outputs'].values() for x in v['execution_issues']))
                if unsafe:self.assertFalse(gate.release_records[0]['physical_work_done'])
                else:self.assertTrue(any(x['code']=='MODEL_RATE_LIMITED' for v in result['outputs'].values() for x in v['execution_issues']))
                return
            self.assertEqual(len(gate.unknown),2 if two_unknown else 1,(result['control'],result['outputs']))
            self.assertEqual(len(result['control']),2 if two_unknown else 3)
            self.assertTrue(gate.release_records[0]['active_before']>0)
            self.assertTrue(all(gate.release_records[0][k] for k in ('physical_work_done','adapter_closed','store_write_verified')))
            self.assertGreaterEqual(created[2],next(t for ch,t in work_ended if ch==0))
            self.assertTrue(gate.pending);self.assertEqual(gate.stopped,two_unknown)
            self.assertFalse(any(x['code']=='DIAGNOSTIC_STORAGE_FAILED' for v in result['outputs'].values() for x in v['execution_issues']))
            if not two_unknown:self.assertTrue(all(not v['execution_issues'] for v in list(result['outputs'].values())[1:]))
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:asyncio.run(go(Path(tmp).resolve()))

    def test_real_entry_no_next_chain_before_physical_release_then_continue(self):self.exercise()
    def test_real_entry_second_unknown_stops_without_third_chain(self):self.exercise(True)
    def test_real_entry_unreleased_work_stops_without_closing_active_adapter(self):self.exercise(unsafe=True)
    def test_real_entry_429_is_shared_not_an_allowed_unknown(self):self.exercise(shared=True)

    def test_shared_classification_not_swallowed(self):
        from evaluation.failure_isolation_v5 import Gate,Isolation
        from model_adapter.contracts import ModelRateLimitError,ModelAuthenticationError,ModelConnectionError
        with tempfile.TemporaryDirectory() as tmp:
            for error in (ModelRateLimitError(),ModelAuthenticationError(),ModelConnectionError(),TypeError()):
                g=Gate(Path(tmp));p=Isolation(g);self.assertTrue(p.on_exception({},error));self.assertTrue(g.stopped)
