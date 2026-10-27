from tests.temp_paths import ignored_temporary_directory
import asyncio,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from evaluation import fact_review_model_fit_v1 as m
from model_adapter.deepseek import DeepSeekAdapter
from model_adapter.contracts import ModelRequest,ModelMessage,ModelRequestError
from model_adapter.contracts import ModelTimeoutError,ModelConnectionError
from model_adapter.runtime import ModelBudget,model_scope
from model_adapter.strict_review_tool import specification,map_null,NAME
from tests.test_review_simple_v1 import response
from tests.test_fact_rereview_v3 import inputs
from agents.evidence_verification import ModelEvidenceVerificationAgent


def envelope(model,args,*,name=NAME,count=1,finish='tool_calls'):
    return json.dumps(dict(model=model,choices=[dict(finish_reason=finish,message=dict(content='',tool_calls=[dict(id=f'call-{i}',type='function',function=dict(name=name,arguments=args)) for i in range(count)]))],usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2))).encode()


class FitTests(unittest.IsolatedAsyncioTestCase):
    def test_default_production_gate_not_relaxed(self):
        model='deepseek-v4-pro';settings=replace(m.SETTINGS,model_id=model);request=ModelRequest(model,(ModelMessage('user','Unchanged task'),),8000,'test',result_tool=specification())
        a=DeepSeekAdapter(settings)
        try:
            with self.assertRaises(ModelRequestError):a.validate_request(request)
        finally:a.close()
        a=DeepSeekAdapter(settings,strict_model_id=model)
        try:a.validate_request(request)
        finally:a.close()

    async def test_pro_same_parser_partial_results_correction_and_envelopes(self):
        for kind in ('normal','missing','extra','duplicate','id','cross_scope','tool','multiple','length','reject'):
            posts=[]
            def exchange(body,*args):
                p=json.loads(body);posts.append(p);d=json.loads(p['messages'][1]['content']);v=map_null(response(d),encode=True)
                if kind=='reject':return 400,b'{"error":{"type":"invalid_request_error"}}'
                if d['review_object']!='original_citation':
                    row=v['judgments'][0]
                    if kind=='missing':row.pop('reason')
                    if kind=='extra':row['extra']='forbidden'
                    if kind=='id':row['basis_ids']=['illegal']
                    if kind=='cross_scope':row['conditions']['answer_ids']=['ANS:R0:0']
                text=json.dumps(v)
                if kind=='duplicate':text='{"judgments":[],"judgments":[]}'
                return 200,envelope(p['model'],text,name='wrong' if kind=='tool' else NAME,count=2 if kind=='multiple' else 1,finish='length' if kind=='length' else 'tool_calls')
            settings=replace(m.SETTINGS,model_id='deepseek-v4-pro');a=DeepSeekAdapter(settings,strict_model_id=settings.model_id,exchange=exchange);budget=ModelBudget(40)
            try:
                with model_scope(budget):out=await ModelEvidenceVerificationAgent(a,settings,schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1').run(inputs(True))
                self.assertLessEqual(sum(x.correction for x in budget.records),1)
                self.assertEqual(bool(out.execution_issues),kind!='normal')
                if kind=='reject':self.assertEqual(len(posts),1)
                for p in posts:self.assertEqual(p['tools'],[specification()]);self.assertEqual(p['thinking'],{'type':'disabled'});self.assertEqual(p['model'],'deepseek-v4-pro')
            finally:a.close()

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/materials.json').is_file(), 'Private historical archive unavailable')
    async def test_all16_wire_identity_freeze_no_factory_no_resume(self):
        posts=[]
        class HTTPResponse:
            status=200
            def __init__(self,data):self.data=data
            def read(self,n):return self.data
        class Connection:
            def __init__(self,*a,**kw):pass
            def connect(self):pass
            def request(self,method,path,body,headers):
                p=json.loads(body);posts.append((path,p));d=json.loads(p['messages'][1]['content']);self.data=envelope(p['model'],json.dumps(map_null(response(d),encode=True)))
            def getresponse(self):return HTTPResponse(self.data)
            def close(self):pass
        with ignored_temporary_directory(dir=m.ROOT/'data/retrieval_local') as tmp,patch.object(m,'LOCAL',Path(tmp)),patch('harness.deepseek_trial.load_project_env'),patch.object(m,'credential_from_environment',return_value='fixture-private'),patch('model_adapter.deepseek.credential_from_environment',return_value='fixture-private'),patch('http.client.HTTPSConnection',Connection),patch('backend.assembly.ComponentFactory.preflight',side_effect=AssertionError('No Factory')):
            m.save(Path(tmp)/'selection.json',dict(selected='deepseek-v4-pro'));f=m.freeze();r=await m.execute_async()
            self.assertEqual(len(r['controls']),16);self.assertFalse(r['unexecuted']);self.assertEqual(len(posts),32);self.assertTrue(all(not x['stop'] for x in r['controls']))
            for i in range(0,32,4):
                for a,b in ((posts[i],posts[i+2]),(posts[i+1],posts[i+3])):
                    self.assertEqual(a[0],'/beta/chat/completions');aa=dict(a[1]);bb=dict(b[1]);self.assertNotEqual(aa.pop('model'),bb.pop('model'));self.assertEqual(aa,bb)
            with self.assertRaises(FileExistsError):await m.execute_async()
            db=Path(tmp)/'runs.sqlite3';db.rename(db.with_suffix('.closed'))

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/materials.json').is_file(), 'Private historical archive unavailable')
    async def test_shared_failure_stops_both_models_and_preserves_received(self):
        posts=[]
        class HTTPResponse:
            def __init__(self,status,data):self.status,self.data=status,data
            def read(self,n):return self.data
        class Connection:
            def __init__(self,*a,**kw):pass
            def connect(self):pass
            def request(self,method,path,body,headers):
                p=json.loads(body);posts.append(p)
                if len(posts)>2:self.response=HTTPResponse(429,b'{"error":{"type":"rate_limit_error"}}')
                else:self.response=HTTPResponse(200,envelope(p['model'],json.dumps(map_null(response(json.loads(p['messages'][1]['content'])),encode=True))))
            def getresponse(self):return self.response
            def close(self):pass
        with ignored_temporary_directory(dir=m.ROOT/'data/retrieval_local') as tmp,patch.object(m,'LOCAL',Path(tmp)),patch('harness.deepseek_trial.load_project_env'),patch.object(m,'credential_from_environment',return_value='fixture-private'),patch('model_adapter.deepseek.credential_from_environment',return_value='fixture-private'),patch('http.client.HTTPSConnection',Connection):
            m.save(Path(tmp)/'selection.json',dict(selected='deepseek-v4-pro'));m.freeze();r=await m.execute_async();self.assertEqual(len(posts),3);self.assertEqual(len(r['results']),2);self.assertTrue(r['controls'][-1]['stop']);self.assertFalse(r['results']['A1-flash']['execution_issues'])

    async def test_unknown_acceptance_timeout_poison_prevents_second_post(self):
        calls=[]
        def timeout(*a):calls.append(1);raise ModelTimeoutError()
        a=m.ComparisonAdapter(m.SETTINGS,exchange=timeout);budget=ModelBudget(40)
        try:
            with model_scope(budget):out=await ModelEvidenceVerificationAgent(a,m.SETTINGS,schema_version=13,review_contract='simple_v1',review_result_transport='strict_tool_v1').run(inputs(True))
            self.assertEqual(len(calls),1);self.assertIsInstance(budget.fatal_error,ModelConnectionError);self.assertEqual(len(budget.records),1);self.assertEqual(out.execution_issues[0].code,'MODEL_CONNECTION_FAILED')
        finally:a.close()

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/review-contract-simple-v1/materials.json').is_file(), 'Private historical archive unavailable')
    async def test_budget_exhaustion_is_shared_stop_not_next_task(self):
        class HTTPResponse:
            status=200
            def __init__(self,data):self.data=data
            def read(self,n):return self.data
        posts=[]
        class Connection:
            def __init__(self,*a,**kw):pass
            def connect(self):pass
            def request(self,method,path,body,headers):
                p=json.loads(body);posts.append(p);self.data=envelope(p['model'],json.dumps(map_null(response(json.loads(p['messages'][1]['content'])),encode=True)))
            def getresponse(self):return HTTPResponse(self.data)
            def close(self):pass
        with ignored_temporary_directory(dir=m.ROOT/'data/retrieval_local') as tmp,patch.object(m,'LOCAL',Path(tmp)),patch('harness.deepseek_trial.load_project_env'),patch.object(m,'credential_from_environment',return_value='fixture-private'),patch('model_adapter.deepseek.credential_from_environment',return_value='fixture-private'),patch('http.client.HTTPSConnection',Connection),patch.object(m,'ModelBudget',side_effect=lambda *a,**kw:ModelBudget(1)):
            m.save(Path(tmp)/'selection.json',dict(selected='deepseek-v4-pro'));m.freeze();r=await m.execute_async();self.assertEqual(len(posts),1);self.assertEqual(len(r['results']),1);self.assertTrue(r['controls'][-1]['stop'])


if __name__=='__main__':unittest.main()
