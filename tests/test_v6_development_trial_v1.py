import copy
import unittest
from unittest.mock import patch
from evaluation import premise_bound_review_v6 as protocol
from evaluation.eia_nrc_trial_v1 import ORDER
from evaluation.text_bound_review import canonical, sha
from evaluation.v6_development_trial_v1 import prepare_tasks, run
from tests.test_premise_bound_review_v4 import fixture


class V6TrialTests(unittest.TestCase):
    def fixture(self):
        tasks = [fixture(s) for s in ORDER]
        items = []
        for task in tasks:
            new = copy.deepcopy(task)
            for evidence in new['evidence']:
                evidence['source_role'] = 'literature'
            messages = [{'role':m.role, 'content':m.content} for m in protocol.messages(new)]
            items.append({'sample_id':task['sample_id'],
                'original_task_sha256_utf8':sha(canonical(task).encode()),
                'candidate_task_sha256_utf8':sha(canonical(new).encode()),
                'candidate_messages_sha256_utf8':sha(canonical(messages).encode())})
        return tasks, {'items':items}

    def test_only_explicit_role_added_without_mutation(self):
        tasks, plan = self.fixture()
        before = copy.deepcopy(tasks)
        new = prepare_tasks(tasks, plan)
        self.assertEqual(tasks, before)
        for task in new:
            for e in task['evidence']:
                self.assertEqual(e.pop('source_role'), 'literature')
        self.assertEqual(new, tasks)

    def test_order_and_reference_injection_rejected(self):
        tasks, plan = self.fixture()
        with self.assertRaises(ValueError):prepare_tasks(tasks[::-1], plan)
        tasks[0]['expected'] = 'not transmitted'
        with self.assertRaises(ValueError):prepare_tasks(tasks, plan)

    def test_task_and_message_tampering_rejected(self):
        tasks, plan = self.fixture()
        for key in ['original_task_sha256_utf8','candidate_task_sha256_utf8','candidate_messages_sha256_utf8']:
            wrong = copy.deepcopy(plan)
            wrong['items'][0][key] = 'wrong'
            with self.assertRaises(ValueError):prepare_tasks(tasks, wrong)

    def test_existing_attempt_blocks_before_adapter_import(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            (directory/'attempt.json').write_text('already attempted')
            with patch('evaluation.v6_development_trial_v1.preflight', return_value=({}, {'order':ORDER}, [])):
                with self.assertRaises(FileExistsError):run(directory)
