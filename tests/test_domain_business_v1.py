import asyncio,json,unittest
from evaluation.domain_business_materials_v1 import CASES,fixed_input
from services.domain_business_v1 import create_agent
from agents.power_domain_review import MODEL_KEYS
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
class DomainBusinessTests(unittest.TestCase):
 def test_actual_messages_six_categories(self):
  for c in CASES:
   seen=[]
   class Adapter:
    async def complete(self,r):
     p=json.loads(r.messages[1].content);seen.append(p)
     checks=[dict(check_id=k,status='not_applicable',claim_ids=[],quote_ids=[],basis_kind='engineering_rule',rationale='合成开发检查',missing_prerequisites=[]) for k in MODEL_KEYS]
     next(x for x in checks if x['check_id']=='analysis_scope')['task_scope']=c[3]
     a=dict(scope=dict(kind=c[3],reason='实际范围'),input_requirements=[],analysis_capability=dict(status=c[4],reason='实际能力'),constraints=dict(applicable=c[5]=='dangerous',reason='来源有界'),summary='开发判断')
     next(x for x in checks if x['check_id']=='analysis_scope')['business_assessment']=a
     v=dict(checks=checks,missing_information_review=[],safety_reviews=[dict(claim_id=fixed_input(c).claims[0].claim_id,verdict='not_applicable',reason='合成测试不验证危险语义',source_ids=[])])
     return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
   async def go():
    with model_scope(ModelBudget(40)):return await create_agent(Adapter(),ModelSettings('synthetic_fixture')).run(fixed_input(c))
   out=asyncio.run(go());self.assertFalse(out.execution_issues);self.assertEqual(len(seen),1);self.assertFalse(seen[0]['ACTUAL_CAPABILITIES']['engineering_simulation']);self.assertEqual(out.business_assessment['scope']['kind'],c[3]);self.assertEqual(len(out.business_trace),3)

class BatchTests(unittest.TestCase):
 def test_local_failure_continue_shared_stop(self):
  from tempfile import TemporaryDirectory
  from pathlib import Path
  from unittest.mock import patch
  import evaluation.domain_business_trial_v1 as t
  from model_adapter.contracts import ModelConnectionError
  for shared in (False,True):
   class Adapter:
    async def complete(self,r):
     if shared:raise ModelConnectionError()
     return ModelResponse('{}',r.model_id,finish_reason='stop')
    def close(self):pass
   async def go():return await t.batch({'order':await t.capture()},Adapter)
   with TemporaryDirectory(dir='data/retrieval_local') as d,patch.object(t,'LOCAL',Path(d)):s=asyncio.run(go())
   self.assertEqual(sum(r['status']=='unexecuted' for r in s['branches']),11 if shared else 0)
   self.assertEqual(s['total_sends'],1 if shared else 24)
 def test_factory_store_api_qa_and_revision(self):
  from unittest.mock import patch
  import tests.test_schema14_factory_flow as f
  original=f.SyntheticProvider.complete;config=f.ServiceConfig
  async def complete(provider,r):
   if r.prompt_version=='power-domain-review-v3.6-business-v1':
    from dataclasses import replace
    out=await original(provider,replace(r,prompt_version='power-domain-review-v3.5-task-obligations'))
    v=json.loads(out.text);scope=next(x for x in v['checks'] if x['check_id']=='analysis_scope')
    scope['business_assessment']=dict(scope=dict(kind=scope['task_scope'],reason='实际范围'),input_requirements=[],analysis_capability=dict(status='not_needed',reason='仅概念'),constraints=dict(applicable=False,reason='无操作建议'),summary='开发集成检查')
    return replace(out,text=json.dumps(v))
   return await original(provider,r)
  with patch.object(f,'ServiceConfig',side_effect=lambda **kw:config(**kw,domain_internal_flow='business_v1',execution_path='langgraph_v1')),patch.object(f.SyntheticProvider,'complete',complete):
   for revision in (False,True):
    result=f.FactoryFlowTests().exercise(schema=13,existing=revision,revision=revision,concept=True)[0]
    self.assertTrue(result['execution']['required_stages_complete']);self.assertIsNotNone(result['domain_internal_flow']['assessment'])


class ServiceFreezeTests(unittest.TestCase):
 def test_collector_filename_matches_independent_freeze(self):
  from pathlib import Path
  from tempfile import TemporaryDirectory
  from unittest.mock import patch,MagicMock
  from backend.config import ServiceConfig
  import evaluation.domain_business_service_v1 as s
  factory=MagicMock();factory.preflight.return_value=None;factory.manifest.return_value={}
  with TemporaryDirectory(dir='data/retrieval_local') as d,patch.object(s,'PUBLIC',Path(d)/'public'),patch.object(s,'LOCAL',Path(d)/'local'),patch.object(s,'config',return_value=ServiceConfig(domain_internal_flow='business_v1')),patch.object(s.shared,'ComponentFactory',return_value=factory):
   s.freeze()
   self.assertEqual((Path(d)/'public/service-freeze.json').read_bytes(),(Path(d)/'public/execution-freeze-v1.json').read_bytes())
   self.assertFalse((Path(d)/'local/service/attempt.json').exists())
