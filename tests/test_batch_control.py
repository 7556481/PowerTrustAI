"""Synthetic evidence of shared stop, local isolation, and persistence order."""
import asyncio,unittest
from evaluation.batch_control import classify,run_fixed

class BatchControlTests(unittest.TestCase):
 def test_actual_historical_missing_input_is_shared_not_model_failure(self):
  v={'execution':{'execution_issues':[{'component':'evidence_verification','code':'EXECUTION_FAILURE','message':"AttributeError: 'EvidenceVerificationInput' object has no attribute 'tool_results'"}]}}
  d=classify(v);self.assertTrue(d['shared']);self.assertEqual(d['evidence'][0]['exception_type'],'AttributeError')
 def test_contract_response_failure_and_case_timeout_remain_local(self):
  for code,name in [('MODEL_OUTPUT_ERROR','ModelOutputError'),('TIMEOUT','TimeoutError')]:
   self.assertFalse(classify({'execution_issues':[{'component':'evidence_verification','code':code,'message':name+': synthetic single case'}]})['shared'])
 def test_shared_dependency_and_configuration(self):
  self.assertTrue(classify({},configuration_matches=False)['shared'])
  self.assertTrue(classify({'execution_issues':[{'component':'claim_extraction','code':'EXECUTION_FAILURE','message':'ImportError: synthetic dependency missing'}]})['shared'])
 def test_local_failure_continues_then_shared_stops_before_next_submit(self):
  sent=[];saved=[]
  async def submit(v):sent.append(v);return {'run_id':len(sent)}
  async def collect(a):return {'execution_issues':[{'component':'evidence_verification','code':'MODEL_OUTPUT_ERROR','message':'single JSON failure'}]} if a['run_id']==1 else {'execution_issues':[{'component':'harness','code':'EXECUTION_FAILURE','message':'ReviewInputContractError: shared input contract mismatch'}]}
  result=asyncio.run(run_fixed([{'id':str(i),'input':{'n':i}} for i in range(4)],submit=submit,collect=collect,persist=lambda i,k,v:saved.append((i,k))))
  self.assertEqual(len(sent),2);self.assertEqual(len(result),2);self.assertEqual(saved[-2:], [('1','result'),('1','control')]);self.assertTrue(result[-1]['stop'])
 def test_unknown_submit_state_never_retried(self):
  sent=[]
  async def submit(v):sent.append(v);raise OSError('synthetic disconnect')
  async def collect(a):raise AssertionError('No accepted run known')
  asyncio.run(run_fixed([{'id':'a','input':{}},{'id':'b','input':{}}],submit=submit,collect=collect,persist=lambda *x:None))
  self.assertEqual(len(sent),1)

class PersistenceBoundaryTests(unittest.TestCase):
 def test_acceptance_persistence_failure_returns_identity_and_stops(self):
  async def submit(body):return {'run_id':'accepted-synthetic'}
  async def collect(a):raise AssertionError('Never collect after failed persistence')
  def fail(i,k,v):raise TypeError('synthetic callback fault')
  rows=asyncio.run(run_fixed([{'id':'one','input':{}},{'id':'two','input':{}}],submit=submit,collect=collect,persist=fail))
  self.assertEqual(len(rows),1);self.assertTrue(rows[0]['stop']);self.assertEqual(rows[0]['accepted']['run_id'],'accepted-synthetic')
 def test_result_persistence_failure_retains_partial_and_never_resubmits(self):
  submitted=[]
  async def submit(body):submitted.append(body);return {'run_id':'accepted-synthetic'}
  async def collect(a):return {'execution':{'required_stages_complete':True}}
  def persist(i,k,v):
   if k=='result':raise TypeError('synthetic callback fault')
  rows=asyncio.run(run_fixed([{'id':'one','input':{}},{'id':'two','input':{}}],submit=submit,collect=collect,persist=persist))
  self.assertEqual(len(submitted),1);self.assertTrue(rows[0]['partial_result']['execution']['required_stages_complete'])
