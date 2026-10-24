"""Official HTTP adapter substitutes plus normal Factory; no paid requests."""
import asyncio,json,unittest
from copy import deepcopy
from dataclasses import replace,asdict
from unittest.mock import patch
from model_adapter.contracts import *
from model_adapter.deepseek import DeepSeekAdapter
from model_adapter.runtime import ModelBudget,model_scope,ModelClient
from model_adapter.strict_review_tool import *
from services.review_simple_tool_v1 import ToolCatalog,PROMPT,SYSTEM
from services.structured_model import structured_request
from tests.test_review_simple_v1 import response
from tests.test_fact_rereview_v3 import inputs


def envelope(args,*,content=None,name=NAME,count=1,finish='tool_calls'):
    return json.dumps(dict(id='completion-fixture',model='deepseek-flash',choices=[dict(message=dict(content=content,tool_calls=[dict(id='call-'+str(i),type='function',function=dict(name=name,arguments=args)) for i in range(count)]),finish_reason=finish)],usage=dict(prompt_tokens=20,completion_tokens=10,total_tokens=30))).encode()


class ToolTests(unittest.IsolatedAsyncioTestCase):
    async def run_review(self,mutate=None,inp=None):
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        posts=[]
        def exchange(body,*args):
            r=json.loads(body);posts.append(r);self.assertEqual(r['tools'],[specification()]);self.assertEqual(r['tool_choice']['function']['name'],NAME);self.assertNotIn('response_format',r);self.assertEqual(r['thinking'],{'type':'disabled'})
            d=json.loads(r['messages'][1]['content']);v=map_null(response(d),encode=True)
            if mutate:return mutate(v,d,len(posts))
            return 200,envelope(json.dumps(v))
        a=DeepSeekAdapter(ModelSettings('deepseek-flash'),exchange=exchange);b=ModelBudget(8)
        try:
            with model_scope(b):out=await ModelEvidenceVerificationAgent(a,ModelSettings('deepseek-flash'),schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1').run(inp or inputs(True))
            return out,posts,b
        finally:a.close()

    async def test_normal_raw_arguments_ids_usage_and_no_followup_summary(self):
        out,posts,b=await self.run_review();self.assertFalse(out.execution_issues);self.assertEqual(len(posts),2)
        self.assertEqual(b.records[0].finish_reason,'tool_calls');t=b.records[0].result_transport;self.assertEqual(t['tool_calls'][0]['id'],'call-0');self.assertIn('__NULL__',t['tool_calls'][0]['function']['arguments']);self.assertEqual(b.records[0].usage.total_tokens,30)

    async def test_null_unknown_and_objects_roundtrip_no_semantic_change(self):
        d=ToolCatalog(inputs(False)).payload(['F0C0']);v=response(d)
        for objection,repair in [(None,None),({'kind':'uncertain','reason':'Uncertain classification'},None),(None,{'basis_id':'S0B0','replacement':'A corrected answer.'})]:
            v['judgments'][0].update(objection=objection,repair=repair);v['judgments'][0]['conditions'].update(applicability='unknown',expression='uncertain')
            self.assertEqual(map_null(map_null(v,encode=True)),v)

    async def test_duplicate_keys_missing_enum_illegal_id_partial_and_one_correction(self):
        for kind in ('duplicate','missing','enum','id','native_null'):
            def mutate(v,d,n):
                if d['review_object']=='original_citation':return 200,envelope(json.dumps(v))
                if kind=='duplicate':return 200,envelope('{"judgments":[],"judgments":[]}')
                row=v['judgments'][0]
                if kind=='missing':row.pop('reason')
                elif kind=='enum':row['status']='invented'
                elif kind=='id':row['basis_ids']=['SRC:S9B0']
                else:row['objection']=None
                return 200,envelope(json.dumps(v))
            out,posts,b=await self.run_review(mutate,inputs(False,True));self.assertTrue(out.execution_issues);self.assertEqual(sum(r.correction for r in b.records),1)
            if kind!='duplicate':self.assertEqual(out.findings[1].status.value,'supported')
            self.assertEqual(posts[0]['tools'],posts[1]['tools'])

    async def test_wrong_missing_multiple_tools_text_conflict_and_truncated(self):
        for kind in ('missing','wrong','multiple','text','length','aborted'):
            def mutate(v,d,n):return 200,envelope(json.dumps(v),count=0 if kind=='missing' else 2 if kind=='multiple' else 1,name='another' if kind=='wrong' else NAME,content='{"competing":"result"}' if kind=='text' else None,finish=kind if kind in ('length','aborted') else 'tool_calls')
            out,posts,b=await self.run_review(mutate,inputs(False));self.assertTrue(out.execution_issues)
            self.assertEqual(len(posts),1 if kind=='length' else 2);self.assertTrue(b.records[0].result_transport)

    async def test_http_rejection_blocks_citation_and_correction(self):
        def mutate(v,d,n):return 400,b'withheld private HTTP diagnostic'
        out,posts,b=await self.run_review(mutate);self.assertEqual(len(posts),1);self.assertEqual(b.records[0].network_diagnostic['http_status'],400);self.assertTrue(b.fatal_error)

    async def test_undecodable_envelope_has_unknown_identity_and_explicit_gap(self):
        from model_adapter.deepseek import parse_response
        r=parse_response(200,b'not-an-envelope','deepseek-flash',result_tool=specification())
        self.assertIsNone(r.model_id);self.assertIn('withheld',r.result_transport['diagnostic_gap'])
        self.assertNotIn('not-an-envelope',json.dumps(r.result_transport))

    async def test_actual_beta_path_and_legacy_path(self):
        paths=[]
        class Response:
            status=200
            def read(self,*x):return envelope('{"judgments":[]}')
        class Connection:
            def __init__(self,*args,**kwargs):pass
            def connect(self):pass
            def request(self,method,path,**kwargs):paths.append(path)
            def getresponse(self):return Response()
            def close(self):pass
        with patch('model_adapter.deepseek.credential_from_environment',return_value='fixture'),patch('model_adapter.deepseek.http.client.HTTPSConnection',Connection):
            a=DeepSeekAdapter(ModelSettings('deepseek-flash'))
            try:await a.complete(ModelRequest('deepseek-flash',(ModelMessage('system',SYSTEM),),8000,PROMPT,result_tool=specification()))
            finally:a.close()
        self.assertEqual(paths,['/beta/chat/completions'])

    async def test_cancel_and_timeout_do_not_create_extra_posts(self):
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        class Cancel:
            async def complete(self,r):raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            with model_scope(ModelBudget(3)):await ModelEvidenceVerificationAgent(Cancel(),ModelSettings('fixture'),schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1').run(inputs(False))
        class Slow:
            async def complete(self,r):await asyncio.sleep(.05)
        b=ModelBudget(3)
        with model_scope(b):out=await ModelEvidenceVerificationAgent(Slow(),ModelSettings('fixture',timeout_seconds=.001),schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1').run(inputs(False))
        self.assertTrue(out.execution_issues);self.assertEqual(b.used,1)


class SchemaFactoryTests(unittest.TestCase):
    def test_supported_schema_subset_and_all_properties_required(self):
        def visit(s):
            self.assertNotIn('minLength',s);self.assertNotIn('maxLength',s);self.assertNotIn('minItems',s);self.assertNotIn('maxItems',s)
            if 'anyOf' in s:
                for x in s['anyOf']:visit(x)
                return
            self.assertIn(s['type'],('object','array','string','boolean'))
            if s['type']=='object':
                self.assertEqual(set(s['required']),set(s['properties']));self.assertIs(s['additionalProperties'],False)
                for x in s['properties'].values():visit(x)
            if s['type']=='array':visit(s['items'])
        visit(schema());self.assertEqual(len(schema()['properties']['judgments']['items']['required']),9)

    def test_factory_graph_service_store_api_revision_and_reextract(self):
        import tests.test_schema14_factory_flow as f
        original=f.SyntheticProvider.complete;config=f.ServiceConfig
        async def complete(provider,r):
            if r.result_tool is not None:
                provider.requests.append(r);d=json.loads(r.messages[1].content);v=response(d)
                for row,t in zip(v['judgments'],d['targets']):
                    if provider.revision and '9 kV' in t['proposition']:row['status']='contradicted';row['repair']=dict(basis_id=row['basis_ids'][0],replacement=f.GOOD)
                args=json.dumps(map_null(v,encode=True));return ModelResponse(args,r.model_id,finish_reason='tool_calls',result_transport=dict(version=VERSION,tool_calls=[dict(id='factory-call',type='function',function=dict(name=NAME,arguments=args))],content=None))
            return await original(provider,r)
        with patch.object(f,'ServiceConfig',side_effect=lambda **kw:config(**kw,fact_review_contract='simple_v1',review_result_transport='strict_tool_v1',execution_path='langgraph_v1')),patch.object(f.SyntheticProvider,'complete',complete):
            for revision in (False,True):
                r,_,_=f.FactoryFlowTests().exercise(schema=13,existing=revision,revision=revision,concept=True);self.assertTrue(r['execution']['required_stages_complete']);self.assertEqual(len(r['answer']['versions']),2 if revision else 1)
        self.assertEqual(config().review_result_transport,'json')
