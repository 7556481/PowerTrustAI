import asyncio
from pathlib import Path
import tempfile
import unittest

from evaluation import premise_bound_trial_v4 as entry
from evaluation import requirement_trial_v3 as trial
from evaluation.text_bound_review import sha, write
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from tests.test_premise_bound_review_v4 import fixture,prediction
from tests.test_text_bound_review import Adapter


class PremiseBoundTrialTests(unittest.TestCase):
    def tasks(self):
        return [fixture(s) for s in ('RC-001-A','RC-001-B','RC-001-C-v2')]

    def test_exact_three_gate_rejects_old_C_or_extra_sample(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            for tasks in (self.tasks()[:2], self.tasks()+[fixture('other')],
                          [fixture('RC-001-A'),fixture('RC-001-B'),fixture('RC-001-C')]):
                write(path/'input.json',tasks)
                with self.assertRaises(AssertionError):entry.verify_items(path)
            write(path/'input.json',self.tasks());entry.verify_items(path)

    def test_three_once_derived_composition_and_no_expected_messages(self):
        tasks=self.tasks();adapter=Adapter([prediction(t) for t in tasks]);saved={}
        result=asyncio.run(trial.execute(tasks,ModelClient(adapter,ModelSettings('fixture')),None,
            lambda sid,kind,v:saved.update({(sid,kind):v}),protocol=entry.protocol))
        self.assertEqual(result['actual_calls'],3)
        self.assertEqual({sid for sid,kind in saved},{t['sample_id'] for t in tasks})
        for t,request in zip(tasks,adapter.requests):
            self.assertEqual(request.messages,entry.protocol.messages(t))
            self.assertNotIn('SECRET',request.messages[1].content)
            self.assertEqual(saved[(t['sample_id'],'result')]['prediction']['units'][0]['program_composition'],'single')

    def test_one_correction_then_failure_stops_batch(self):
        tasks=self.tasks();adapter=Adapter([{},{}]);saved={}
        result=asyncio.run(trial.execute(tasks,ModelClient(adapter,ModelSettings('fixture')),None,
            lambda sid,kind,v:saved.update({(sid,kind):v}),protocol=entry.protocol))
        self.assertEqual(result['actual_calls'],2)
        self.assertTrue(result['controls'][0]['stop'])
        self.assertEqual(saved[('RC-001-A','result')]['status'],'failed')
        self.assertNotIn(('RC-001-B','accepted'),saved)

    def test_freeze_keeps_six_call_budget_and_once_marker_control(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepared=root/'prepared';prepared.mkdir();tasks=self.tasks()
            write(prepared/'input.json',tasks);write(prepared/'expectations-private.json',{'SECRET':'labels'})
            write(prepared/'messages-preview.json',[[{'role':m.role,'content':m.content}
                for m in entry.protocol.messages(t)] for t in tasks])
            manifest={'version':entry.protocol.VERSION,'working_tree_hashes':{}}
            for filename,key in [('input.json','input_sha256'),('expectations-private.json','expectations_sha256'),
                                  ('messages-preview.json','messages_preview_sha256')]:
                manifest[key]=sha((prepared/filename).read_bytes())
            write(prepared/'offline-manifest.json',manifest)
            frozen=trial.freeze(prepared,root/'out',protocol=entry.protocol)
            self.assertEqual(frozen['maximum_calls'],6)
            self.assertEqual(frozen['max_corrections_per_item'],1)
            with self.assertRaises(FileExistsError):trial.freeze(prepared,root/'out',protocol=entry.protocol)


if __name__=='__main__':unittest.main()
