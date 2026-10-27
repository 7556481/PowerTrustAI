from tests.temp_paths import ignored_temporary_directory
import asyncio,json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from evaluation import fact_internal_flow_trial_v1 as t
from model_adapter.contracts import ModelResponse
class Gates(unittest.TestCase):
 def test_failure_stops_after_one_correction(self):
  calls=[]
  class Bad:
   async def complete(self,r):calls.append(r);return ModelResponse('{bad',r.model_id,finish_reason='stop')
   def close(self):pass
  with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d:
   f={'order':t.read(t.PUBLIC/'preparation-v1.json')['order']}
   s=asyncio.run(t.batch(f,Path(d),Bad))
   self.assertEqual(len(calls),2);self.assertEqual(s['branches'][0]['status'],'execution_failed')
   self.assertTrue(all(r['status']=='unexecuted' for r in s['branches'][1:]))
 def test_presend_storage_failure_sends_zero(self):
  calls=[]
  class Bad:
   async def complete(self,r):calls.append(r);raise AssertionError()
   def close(self):pass
  original=t.write
  def fail(p,v):
   if Path(p).name.startswith('messages-'):raise OSError('synthetic')
   return original(p,v)
  with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d,patch.object(t,'write',side_effect=fail):
   s=asyncio.run(t.batch({'order':t.read(t.PUBLIC/'preparation-v1.json')['order']},Path(d),Bad))
   self.assertFalse(calls);self.assertEqual(s['branches'][0]['status'],'execution_failed')
 def test_known_precondition_continues(self):
  class Bad:
   async def complete(self,r):raise AssertionError('must not send')
   def close(self):pass
  order=[r for r in t.read(t.PUBLIC/'preparation-v1.json')['order'] if not r['initial_calls']]
  with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d:
   s=asyncio.run(t.batch({'order':order},Path(d),Bad))
   self.assertEqual([r['status'] for r in s['branches']],['known_precondition']*2)
 def test_attempt_rejected(self):
  with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d,patch.object(t,'LOCAL',Path(d)),patch.object(t,'read',return_value={'files':[]}):
   (Path(d)/'attempt.json').write_text('{}')
   with self.assertRaises(ValueError):t.preflight()
 def test_candidate_successes_persist_and_continue(self):
  from tests.test_fact_flow_v1 import case_response
  from evaluation.fact_internal_flow_materials_v1 import CASES
  class Good:
   async def complete(self,r):
    d=json.loads(r.messages[1].content);case=next(c for c in CASES if c['question']==d['question'])
    return ModelResponse(json.dumps(case_response(case,d)),r.model_id,finish_reason='stop')
   def close(self):pass
  order=[r for r in t.read(t.PUBLIC/'preparation-v1.json')['order'] if r['variant']=='candidate']
  with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d:
   s=asyncio.run(t.batch({'order':order},Path(d),Good))
   self.assertEqual([r['status'] for r in s['branches']],['complete']*8)
   self.assertEqual(s['total_sends'],8)
 def test_wrong_message_hash_sends_zero(self):
  class Bad:
   async def complete(self,r):raise AssertionError('never send')
   def close(self):pass
  order=t.read(t.PUBLIC/'preparation-v1.json')['order'];order[0]['message_sha256']='wrong'
  with ignored_temporary_directory(dir=t.ROOT/'data/retrieval_local') as d:
   s=asyncio.run(t.batch({'order':order},Path(d),Bad));self.assertEqual(s['total_sends'],0)
   self.assertEqual(s['branches'][0]['status'],'execution_failed')
