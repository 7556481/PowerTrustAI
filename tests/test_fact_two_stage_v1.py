import asyncio,json,unittest
from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
from tests.test_fact_flow_v1 import case_response
from services.fact_two_stage_v1 import create_agent,STAGE1
from model_adapter.contracts import ModelResponse,ModelSettings
from model_adapter.runtime import ModelBudget,model_scope
class TwoStageTests(unittest.TestCase):
 def test_adapter_boundary_all_cases(self):
  for case in CASES:
   seen=[]
   class Adapter:
    async def complete(self,r):
     p=json.loads(r.messages[1].content);seen.append(r)
     rows=case_response(case,p)['judgments']
     if r.messages[0].content==STAGE1:
      v={'objects':[dict(target_id=x['target_id'],object_kind=x['object_kind'],dependencies=x['dependencies'],classification_objection=x['classification_objection'],uncertainty=None,reason='独立对象判断') for x in rows]}
     else:
      assert p['stage_one'] and p['basis_catalog']
      for x in rows:x.update(stage_one_agreement=True,stage_one_reason='独立核对一致',condition_expression='not_applicable',instance_satisfaction='not_applicable',complete_conclusion='yes')
      v={'judgments':rows}
     return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
   async def run():
    with model_scope(ModelBudget(40)):return await create_agent(Adapter(),ModelSettings('synthetic_fixture')).run(fixed_input(case))
   out=asyncio.run(run());self.assertFalse(out.execution_issues,(case['id'],out.execution_issues));self.assertEqual(len(seen),2)

class StopTests(unittest.TestCase):
 def test_local_failure_continues_shared_stops(self):
  from evaluation.fact_two_stage_trial_v1 import shared_failure
  self.assertFalse(shared_failure('MODEL_OUTPUT_ERROR'))
  for code in (None,'MODEL_CONNECTION_FAILED','MODEL_CALL_BUDGET_EXHAUSTED','STORAGE_FAILED','MODEL_TIMEOUT'):self.assertTrue(shared_failure(code))
 def test_batch_isolation_and_shared_stop(self):
  from unittest.mock import patch
  from tempfile import TemporaryDirectory
  from pathlib import Path
  import evaluation.fact_two_stage_trial_v1 as trial
  from model_adapter.contracts import ModelConnectionError
  for shared in (False,True):
   class Adapter:
    async def complete(self,r):
     if shared:raise ModelConnectionError()
     return ModelResponse('{}',r.model_id,finish_reason='stop')
    def close(self):pass
   async def run():
    f={'order':await trial.capture()}
    return await trial.batch(f,Adapter)
   with TemporaryDirectory(dir='data/retrieval_local') as d,patch.object(trial,'LOCAL',Path(d)):
    s=asyncio.run(run())
   self.assertEqual(sum(r['status']=='unexecuted' for r in s['branches']),15 if shared else 0)
   self.assertEqual(s['total_sends'],1 if shared else 32)
