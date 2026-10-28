import asyncio,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from evaluation.source_first_live_budget_v1 import Ledger,BudgetStop,GuardedAdapter,live_bound_unavailable
from model_adapter.contracts import ModelRequest,ModelMessage

class BudgetTests(unittest.TestCase):
    def ledger(self,root,**kw):return Ledger(Path(root)/'attempt',**kw)
    def test_contention_and_global_stop(self):
        with tempfile.TemporaryDirectory() as root:
            l=self.ledger(root,limit=100,chain_calls=100)
            def call(i):
                try:return l.reserve('A',10,10)
                except BudgetStop:return None
            with ThreadPoolExecutor(max_workers=8) as pool:r=list(pool.map(call,range(20)))
            self.assertEqual(sum(x is not None for x in r),5);self.assertEqual(l.charged,100)
    def test_usage_release_cache_not_double_counted_and_unknown_retained(self):
        with tempfile.TemporaryDirectory() as root:
            l=self.ledger(root);a=l.reserve('A',100,80)
            l.settle(a,dict(input_tokens=60,output_tokens=10,total_tokens=70,cache_hit_tokens=20,cache_miss_tokens=40))
            self.assertEqual(l.charged,70)
            b=l.reserve('B',100,80)
            for u in (None,{},dict(input_tokens=1,output_tokens=2,total_tokens=8)):
                l.settle(b,u);self.assertEqual(l.charged,250)
            with self.assertRaises(FileExistsError):Ledger(l.path)
    def test_underestimate_and_persistence_failure_stop(self):
        with tempfile.TemporaryDirectory() as root:
            l=self.ledger(root);k=l.reserve('A',10,10)
            with self.assertRaises(BudgetStop):l.settle(k,dict(input_tokens=11,output_tokens=1,total_tokens=12))
            self.assertTrue(l.stopped);self.assertEqual(l.charged,20)
        with tempfile.TemporaryDirectory() as root:
            l=self.ledger(root)
            with patch.object(l,'persist',side_effect=OSError):
                with self.assertRaises(OSError):l.reserve('A',10,10)
            self.assertTrue(l.stopped);self.assertFalse(l.entries)
    def test_real_bound_gate_prevents_delegate_and_unknown_send_retains_reservation(self):
        class Delegate:
            calls=0
            async def complete(self,r):self.calls+=1;raise TimeoutError()
        r=ModelRequest('deepseek-flash',(ModelMessage('user','fixture'),),8000,'synthetic')
        with tempfile.TemporaryDirectory() as root:
            l=self.ledger(root);d=Delegate();a=GuardedAdapter(d,l,'A',live_bound_unavailable)
            with self.assertRaises(BudgetStop):asyncio.run(a.complete(r))
            self.assertEqual(d.calls,0);self.assertEqual(l.charged,0)
            a.bound=lambda r:10
            with self.assertRaises(TimeoutError):asyncio.run(a.complete(r))
            self.assertEqual(d.calls,1);self.assertEqual(l.charged,8010);self.assertTrue(l.stopped)
