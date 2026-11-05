import tempfile,unittest
from types import SimpleNamespace as N
from evaluation.tantivy_full_budget_v1 import FullBudget,BudgetStop
class BudgetChecks(unittest.TestCase):
 def request(self):return N(model_id='deepseek-flash',max_output_tokens=8000,messages=[N(content='synthetic_fixture')])
 def test_usage_and_missing_retained_across_reopen(self):
  with tempfile.TemporaryDirectory() as t:
   g=FullBudget(t);i=g.reserve('a',self.request());g.received(i,None);held=g.held();g=FullBudget(t);self.assertEqual(g.held(),held);i=g.reserve('b',self.request());g.received(i,{'input_tokens':10,'output_tokens':5,'total_tokens':15});self.assertEqual(g.state['trusted_tokens'],15);self.assertEqual(g.held(),held)
 def test_call_cap_and_inflight_no_replay(self):
  with tempfile.TemporaryDirectory() as t:
   g=FullBudget(t,cap=1);i=g.reserve('a',self.request())
   with self.assertRaises(BudgetStop):FullBudget(t,cap=1).reserve('b',self.request())
   g.received(i,None)
   with self.assertRaises(BudgetStop):g.reserve('b',self.request())
 def test_original_fact_domain_pair_can_overlap_but_not_other_chain(self):
  with tempfile.TemporaryDirectory() as t:
   g=FullBudget(t);a=g.reserve('same',self.request());b=g.reserve('same',self.request())
   with self.assertRaises(BudgetStop):g.reserve('other',self.request())
   with self.assertRaises(BudgetStop):g.reserve('same',self.request())
   g.received(a,None);g.received(b,None);self.assertEqual(g.state['calls'],2)
 def test_threshold_and_flash(self):
  with tempfile.TemporaryDirectory() as t:
   g=FullBudget(t);i=g.reserve('a',self.request());g.received(i,{'input_tokens':4000000,'output_tokens':0,'total_tokens':4000000})
   with self.assertRaises(BudgetStop):g.reserve('b',self.request())
 def test_durable_journal_wins_over_stale_cache(self):
  import json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as t:
   g=FullBudget(t);i=g.reserve('a',self.request());stale=(Path(t)/'state.json').read_text();g.received(i,{'input_tokens':11,'output_tokens':4,'total_tokens':15});(Path(t)/'state.json').write_text(stale)
   reopened=FullBudget(t);self.assertEqual(reopened.state['trusted_tokens'],15);self.assertFalse(reopened.state['entries'][i]['inflight'])
 def test_other_model_rejected_before_admission(self):
  with tempfile.TemporaryDirectory() as t:
   g=FullBudget(t);r=self.request();r.model_id='other'
   with self.assertRaises(BudgetStop):g.reserve('a',r)
   self.assertEqual(g.state['calls'],0)
if __name__=='__main__':unittest.main()
