import asyncio
import json
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation import strict_interface_probe_v1 as p
from model_adapter.contracts import ModelMessage,ModelRequest,ModelRequestError
from model_adapter.deepseek import DeepSeekAdapter
from model_adapter.runtime import ModelBudget,ModelClient,model_scope
from model_adapter.wire_observation import response_view
from evaluation.batch_control import run_fixed


def envelope(arguments='{"name":"alpha","enabled":false,"kind":"sample"}',**changes):
    v=dict(model='deepseek-flash',choices=[dict(finish_reason='tool_calls',message=dict(content='',tool_calls=[dict(id='call-1',type='function',function=dict(name=p.NAME,arguments=arguments))]))],usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2))
    v.update(changes);return json.dumps(v).encode()


class ProbeTests(unittest.IsolatedAsyncioTestCase):
    def test_static_subset_and_values(self):
        for s,v in p.schemas():p.check_schema(s);self.assertTrue(p.conforms(v,s))
        p.check_schema(p.specification()['function']['parameters'])
        with self.assertRaises(AssertionError):p.check_schema(dict(type='string',minLength=1))
        self.assertFalse(p.conforms(0,dict(type='boolean')))

    def test_null_roundtrip(self):
        v={'judgments':[dict(objection=None,repair=None),dict(objection=dict(kind='uncertain',reason='x'),repair=dict(basis_id='r',replacement='y'))]}
        self.assertEqual(p.map_null(p.map_null(v,encode=True)),v)

    def test_raw_arguments_and_invalid_payloads(self):
        for args,syntax,duplicate in [(' {"name":"a","name":"b"}',True,True),('{} }',False,False)]:
            t=response_view(200,envelope(args));self.assertEqual(t['tool_calls'][0]['function']['arguments'],args)
            r=p.evaluate(t,*p.schemas()[0]);self.assertEqual(r['json_syntax'],syntax);self.assertEqual(r['duplicate_keys'],duplicate);self.assertIsNone(r['schema_valid']);self.assertFalse(r['valid'])
        t=response_view(200,envelope());self.assertTrue(p.evaluate(t,*p.schemas()[0])['valid'])
        for change in ('none','wrong','multiple','finish','text','id'):
            value=json.loads(envelope());c=value['choices'][0];calls=c['message']['tool_calls']
            if change=='none':c['message']['tool_calls']=[]
            if change=='wrong':calls[0]['function']['name']='wrong'
            if change=='multiple':calls.append(calls[0])
            if change=='finish':c['finish_reason']='length'
            if change=='text':c['message']['content']='conflict'
            if change=='id':calls[0]['id']=''
            self.assertFalse(p.evaluate(response_view(200,json.dumps(value).encode()),*p.schemas()[0])['valid'])

    async def test_exact_serialized_boundary_for_all_pairs(self):
        class Response:
            status=200
            def read(self,n):return envelope()
        captured=[]
        class Connection:
            def __init__(self,host,**kw):self.context=kw['context'];self.host=host
            def connect(self):pass
            def request(self,method,path,body,headers):captured.append((self.host,path,body,self.context.check_hostname,int(self.context.verify_mode)))
            def getresponse(self):return Response()
            def close(self):pass
        with tempfile.TemporaryDirectory() as tmp,patch('model_adapter.deepseek.credential_from_environment',return_value='private-test'),patch.object(p,'credential_from_environment',return_value='private-test'),patch('http.client.HTTPSConnection',Connection):
            for n,case in enumerate(p.minimal_cases()):
                spec=case['input'];body=json.dumps(spec['payload'],ensure_ascii=False).encode();rec=p.Recorder(Path(tmp)/str(n),p.digest(body))
                adapter=DeepSeekAdapter(p.SETTINGS,diagnostic_tool=p.tool(spec['schema']),wire_observer=rec) if spec['path']=='adapter' else p.DirectHTTP(p.SETTINGS,body,rec)
                req=ModelRequest(p.SETTINGS.model_id,tuple(ModelMessage(**m) for m in spec['payload']['messages']),1024,p.VERSION,result_tool=p.tool(spec['schema']))
                out=await adapter.complete(req)
                if hasattr(adapter,'close'):adapter.close()
                host,path,actual,hostname,verify=captured[-1]
                self.assertEqual(actual,body);self.assertEqual(host,'api.deepseek.com');self.assertEqual(path,p.PATH);self.assertTrue(hostname);self.assertEqual(verify,int(ssl.CERT_REQUIRED));self.assertEqual(out.text,json.loads(envelope())['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
            for i in range(0,8,2):self.assertEqual(captured[i][2],captured[i+1][2])

    async def test_shared_rejection_retains_previous_and_stops(self):
        count=[];persisted=[]
        async def submit(v):count.append(v);return v
        async def collect(v):return {'error_code':'MODEL_REQUEST_REJECTED'} if v==2 else {'ok':True}
        controls=await run_fixed([dict(id=str(i),input=i) for i in (1,2,3)],submit=submit,collect=collect,persist=lambda *v:persisted.append(v))
        self.assertEqual(count,[1,2]);self.assertTrue(controls[-1]['stop']);self.assertTrue(any(x[0]=='1' and x[1]=='result' for x in persisted))

    async def test_unknown_acceptance_no_resubmit_and_storage_failure(self):
        for failure in ('submit','store'):
            count=[]
            async def submit(v):
                count.append(v)
                if failure=='submit':raise TimeoutError()
                return v
            async def collect(v):return {'ok':True}
            def persist(cid,phase,data):
                if failure=='store' and phase=='accepted':raise OSError()
            controls=await run_fixed([dict(id=str(i),input=i) for i in (1,2)],submit=submit,collect=collect,persist=persist)
            self.assertEqual(count,[1]);self.assertTrue(controls[-1]['stop'])

    async def test_fatal_budget_blocks_later_clients(self):
        calls=[]
        def reject(*a):calls.append(1);return 400,b'{"error":{"type":"invalid_request_error"}}'
        adapter=DeepSeekAdapter(p.SETTINGS,exchange=reject,diagnostic_tool=p.tool(p.schemas()[0][0]));budget=ModelBudget(limit=8)
        messages=tuple(ModelMessage(**m) for m in p.minimal_cases()[0]['input']['payload']['messages'])
        try:
            with model_scope(budget):
                for _ in range(2):
                    with self.assertRaises(ModelRequestError):await ModelClient(adapter,p.SETTINGS).complete(messages,p.VERSION,budget,result_tool=p.tool(p.schemas()[0][0]))
            self.assertEqual(len(calls),1);self.assertEqual(budget.used,1)
        finally:adapter.close()

    def test_gate_and_request_identity_storage(self):
        rows={x['id']:dict(layers=dict(valid=True),arguments_unchanged=True) for x in p.minimal_cases()}
        self.assertTrue(p.admission(rows,[]));rows['S4-adapter']['arguments_unchanged']=False;self.assertFalse(p.admission(rows,[]))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'runs.sqlite3';store=p.RunStore(path);store.create('1',{},{});store.mark('1','completed',result={'ok':True});self.assertEqual(store.get('1')['result'],{'ok':True});store.close();path.rename(path.with_suffix('.moved'))
            rec=p.Recorder(Path(tmp)/'audit','incorrect')
            with self.assertRaises(ValueError):rec('request',dict(url='https://api.deepseek.com'+p.PATH,body_sha256='actual'))
            self.assertTrue(rec.failed)

    async def test_full_lightweight_collection_gate_and_no_resume(self):
        from agents.contracts import ReliabilityVerificationOutput
        class Response:
            status=200
            def __init__(self,body):self.body=body
            def read(self,n):return self.body
        class Connection:
            def __init__(self,*a,**kw):pass
            def connect(self):pass
            def request(self,method,path,body,headers):
                v=json.loads(body);self.body=envelope(v['messages'][1]['content'])
            def getresponse(self):return Response(self.body)
            def close(self):pass
        async def regression(agent,inp):return ReliabilityVerificationOutput(inp.answer.answer_id,1,inp.claims,(),inp.seed_evidence)
        with tempfile.TemporaryDirectory(dir=p.ROOT/'data/retrieval_local') as tmp,patch.object(p,'LOCAL',Path(tmp)),patch('harness.deepseek_trial.load_project_env'),patch('model_adapter.deepseek.credential_from_environment',return_value='private-test'),patch.object(p,'credential_from_environment',return_value='private-test'),patch('http.client.HTTPSConnection',Connection),patch('backend.assembly.ComponentFactory.preflight',side_effect=AssertionError('No Factory')),patch('agents.evidence_verification.ModelEvidenceVerificationAgent.run',regression):
            p.freeze();r=await p.execute_async()
            self.assertTrue(r['admission']);self.assertEqual(len(r['minimal_controls']),8);self.assertEqual(len(r['regression_controls']),4)
            self.assertTrue(all(not x['stop'] for x in r['regression_controls']))
            with self.assertRaises(FileExistsError):await p.execute_async()


if __name__=='__main__':unittest.main()
