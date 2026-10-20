import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from evaluation import single_scoped_trial_v1 as single
from evaluation import requirement_trial_v3 as trial
from evaluation.text_bound_review import sha, write
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from tests.test_requirement_review_v3 import fixture, prediction
from tests.test_text_bound_review import Adapter


class SingleScopedTests(unittest.TestCase):
    def test_freeze_single_has_two_call_ceiling_and_default_still_rejects(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); prepared=root/'prepared';prepared.mkdir()
            task=fixture();task['sample_id']='SW-001-D'
            write(prepared/'input.json',[task]);write(prepared/'expectations-private.json',{})
            write(prepared/'messages-preview.json',[[{'role':m.role,'content':m.content}
                for m in single.protocol.messages(task)]])
            manifest={'version':single.protocol.VERSION,'working_tree_hashes':{}}
            for filename,key in [('input.json','input_sha256'),
                ('expectations-private.json','expectations_sha256'),
                ('messages-preview.json','messages_preview_sha256')]:
                manifest[key]=sha((prepared/filename).read_bytes())
            write(prepared/'offline-manifest.json',manifest)
            with self.assertRaises(AssertionError):
                trial.freeze(prepared,root/'wrong',protocol=single.protocol)
            frozen=trial.freeze(prepared,root/'single',protocol=single.protocol,expected_items=1)
            self.assertEqual(frozen['planned_items'],1)
            self.assertEqual(frozen['maximum_calls'],2)
            single.verify_single(root/'single')

    def test_single_execution_one_request_no_other_samples(self):
        task=fixture();task['sample_id']='SW-001-D'
        adapter=Adapter([prediction(task)]); saved=[]
        result=asyncio.run(trial.execute([task],ModelClient(adapter,ModelSettings('fixture')),
            None,lambda sid,kind,value:saved.append((sid,kind)),protocol=single.protocol))
        self.assertEqual(result['actual_calls'],1)
        self.assertEqual(len(result['controls']),1)
        self.assertEqual({sid for sid,kind in saved},{'SW-001-D'})
        self.assertEqual(adapter.requests[0].messages[0].content,single.protocol.PROMPT)

    def test_single_gate_rejects_old_sample(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);write(p/'input.json',[{'sample_id':'SW-001-A'}])
            with self.assertRaises(AssertionError):single.verify_single(p)


if __name__=='__main__':unittest.main()
