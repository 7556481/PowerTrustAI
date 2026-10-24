"""Actual official adapter with offline HTTP substitutes, never credentials/network."""
import asyncio,json,unittest
from dataclasses import asdict
from model_adapter.contracts import *
from model_adapter.deepseek import DeepSeekAdapter,json_mode_preflight
from model_adapter.runtime import ModelClient,ModelBudget,model_scope
from services.structured_model import structured_request


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_messages_preflight_not_only_a_prompt_constant(self):
        posts=[];a=DeepSeekAdapter(ModelSettings('synthetic'),exchange=lambda *x:posts.append(x))
        try:
            with self.assertRaises(ModelRequestError) as e:
                await a.complete(ModelRequest('synthetic',(ModelMessage('system','Return an object.'),),20,'synthetic'))
            self.assertFalse(posts);self.assertIsNone(e.exception.diagnostic['http_status'])
            from services.review_simple_v1 import PROMPT,SYSTEM
            req=ModelRequest('synthetic',(ModelMessage('system',SYSTEM),ModelMessage('user','{"targets":[]}')),20,PROMPT)
            json_mode_preflight(req)
            from dataclasses import replace
            with self.assertRaises(ModelRequestError):json_mode_preflight(replace(req,messages=(ModelMessage('system','Return JSON.'),)))
        finally:a.close()

    async def test_rejection_poison_shared_run_and_preserve_previous_record(self):
        posts=[]
        def exchange(*args):
            posts.append(1)
            if len(posts)==1:return 200,json.dumps({'model':'synthetic','choices':[{'message':{'content':'{}'},'finish_reason':'stop'}]}).encode()
            return 400,json.dumps({'error':{'type':'invalid_request_error','message':'Authorization: Bearer secret-input-credential'},'request_id':'req-1234567890abcdef'}).encode()
        a=DeepSeekAdapter(ModelSettings('synthetic'),exchange=exchange);b=ModelBudget(10);c=ModelClient(a,ModelSettings('synthetic'));msg=(ModelMessage('system','Return JSON {}.'),)
        try:
            with model_scope(b):
                await c.complete(msg,'initial',b)
                with self.assertRaises(ModelRequestError):await c.complete(msg,'citation',b)
                for version in ('correction','later-citation','revision','domain-downstream'):
                    with self.assertRaises(ModelRequestError):await c.complete(msg,version,b,True)
            self.assertEqual(len(posts),2);self.assertEqual(len(b.records),2)
            self.assertEqual(b.records[0].returned_model_id,'synthetic')
            d=b.records[1].network_diagnostic;self.assertEqual(d['http_status'],400);self.assertTrue(d['provider_request_id'].startswith('sha256:'))
            self.assertNotIn('secret-input-credential',json.dumps(asdict(b.records[1])))
            self.assertIn('withheld',d['diagnostic_gap']);self.assertTrue(d['request_id'])
        finally:a.close()

    async def test_output_contract_failure_still_one_correction_initial_and_citation(self):
        posts=[]
        def exchange(body,*args):
            request=json.loads(body);self.assertTrue(any('json' in m['content'].lower() for m in request['messages']));posts.append(request)
            text='bad JSON' if len(posts)%2 else '{}'
            return 200,json.dumps({'model':'synthetic','choices':[{'message':{'content':text},'finish_reason':'stop'}]}).encode()
        a=DeepSeekAdapter(ModelSettings('synthetic'),exchange=exchange);b=ModelBudget(4);c=ModelClient(a,ModelSettings('synthetic'))
        try:
            with model_scope(b):
                for name in ('initial','original-citation'):
                    await structured_request(c,(ModelMessage('system','Return JSON {}.'),),name,lambda x:x)
            self.assertEqual(len(posts),4);self.assertEqual(sum(r.correction for r in b.records),2);self.assertIsNone(b.fatal_error)
        finally:a.close()

    async def test_rejection_has_no_format_correction(self):
        posts=[]
        def exchange(*args):posts.append(1);return 422,b'private error'
        a=DeepSeekAdapter(ModelSettings('synthetic'),exchange=exchange);b=ModelBudget(8)
        try:
            with model_scope(b):
                with self.assertRaises(ModelRequestError):await structured_request(ModelClient(a,ModelSettings('synthetic')),(ModelMessage('system','Return JSON {}.'),),'test',lambda x:x)
            self.assertEqual(len(posts),1);self.assertFalse(b.records[0].correction)
        finally:a.close()
