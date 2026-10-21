import asyncio
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from evaluation import reviewer_baseline_trial_v1 as trial
from model_adapter.contracts import ModelSettings,ModelConnectionError
from model_adapter.runtime import ModelClient
from tests.test_text_bound_review import Adapter
from tests.test_format_stability_trial_v1 import prediction


class BaselineTests(unittest.TestCase):
    def test_order_whitelist_and_complete_context(self):
        cards=json.loads(trial.CARDS.read_text(encoding='utf-8'))
        answers=json.loads(trial.ANSWERS.read_text(encoding='utf-8'))
        original=trial.build_tasks(cards,answers)
        for c in cards['cards']:
            c['evaluator_secret']='DO_NOT_SEND_REFERENCE'
            for r in c['requirements']:r['expected_label']='DO_NOT_SEND_REFERENCE'
        for a in answers['answers']:a['role']='DO_NOT_SEND_REFERENCE'
        tasks=trial.build_tasks(cards,answers)
        self.assertEqual(tasks,original)
        self.assertEqual(len(tasks),24)
        self.assertEqual([t['sample_id'] for t in tasks[:4]],
                         ['H-BL-'+s+'-01-A01' for s in ('NWS','USGS','NASA','CDC')])
        self.assertNotIn('DO_NOT_SEND_REFERENCE',json.dumps(tasks))
        lookup={c['card_id']:c for c in cards['cards']}
        for t in tasks:
            for e,src in zip(t['evidence'],lookup[t['sample_id'].rsplit('-A',1)[0]]['evidence']):
                self.assertEqual(e['text'],src['text'])
                self.assertEqual(e['scope_context'],src['scope_context'])

    def test_all24_shared_budget_contract_and_prompt(self):
        tasks=trial.prepare_tasks();adapter=Adapter([prediction(t) for t in tasks])
        r=asyncio.run(trial.execute(tasks,ModelClient(adapter,ModelSettings('fixture')),None,lambda *a:None))
        self.assertEqual(r['actual_calls'],24)
        self.assertEqual(len(r['controls']),24)
        self.assertTrue(all(x['response_contract_version']==trial.v6.VERSION for x in r['records']))
        self.assertTrue(all(x['prompt_version']==trial.v7.VERSION for x in r['records']))

    def test_final_contract_failure_stops_after_one_correction(self):
        adapter=Adapter([{},{}]);tasks=trial.prepare_tasks();saved={}
        r=asyncio.run(trial.execute(tasks,ModelClient(adapter,ModelSettings('fixture')),None,
            lambda sid,k,v:saved.update({(sid,k):v})))
        self.assertEqual(r['actual_calls'],2);self.assertEqual(len(r['controls']),1)
        self.assertTrue(r['controls'][0]['stop'])
        self.assertNotIn((tasks[1]['sample_id'],'accepted'),saved)

    def test_all24_one_correction_each_uses_shared48(self):
        tasks=trial.prepare_tasks();adapter=Adapter([x for t in tasks for x in ({},prediction(t))])
        r=asyncio.run(trial.execute(tasks,ModelClient(adapter,ModelSettings('fixture')),None,lambda *a:None))
        self.assertEqual(r['actual_calls'],48)
        self.assertEqual(len(r['controls']),24)
        self.assertEqual([x['call_number'] for x in r['records']],list(range(1,49)))
        self.assertEqual(sum(x['correction'] for x in r['records']),24)

    def test_changed_bound_file_refused_before_credentials(self):
        f={'owner_authorized':True,'maximum_calls':48,'planned_items':24,'order':[{}]*24,
           'budget_deadline_seconds':4320,'model_settings':{'model_id':'deepseek-flash',
           'endpoint':'https://api.deepseek.com','timeout_seconds':90,'max_output_tokens':2000,
           'max_response_chars':24000},'prompt_sha256_utf8':trial.sha(trial.v7.PROMPT.encode()),
           'bound_file_hashes':{str(trial.CARDS):'not-the-real-hash'}}
        with patch.object(trial.Path,'read_text',return_value=json.dumps(f)):
            with self.assertRaisesRegex(ValueError,'Frozen file changed'):
                trial.preflight(trial.DIRECTORY)

    def test_transport_failure_no_retry(self):
        adapter=Adapter([ModelConnectionError()])
        r=asyncio.run(trial.execute(trial.prepare_tasks(),ModelClient(adapter,ModelSettings('fixture')),None,lambda *a:None))
        self.assertEqual(r['actual_calls'],1);self.assertEqual(len(adapter.requests),1)
        self.assertTrue(r['controls'][0]['stop'])

    def test_persistence_failure_before_call(self):
        def fail(*a):raise OSError('fixture')
        r=asyncio.run(trial.execute(trial.prepare_tasks(),ModelClient(Adapter([]),ModelSettings('fixture')),None,fail))
        self.assertEqual(r['actual_calls'],0);self.assertTrue(r['controls'][0]['stop'])

    def test_exact_identity_and_nested_whitelist(self):
        cards=json.loads(trial.CARDS.read_text(encoding='utf-8'));answers=json.loads(trial.ANSWERS.read_text(encoding='utf-8'))
        answers['answers'][0]['id']='foreign'
        with self.assertRaises(ValueError):trial.build_tasks(cards,answers)
        task=trial.prepare_tasks()[0];task['evidence'][0]['expected']='illegal'
        with self.assertRaises(ValueError):trial.validate_task(task)

    def test_attempt_marker_blocks_before_credentials(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir='data/evaluation_local') as name:
            p=Path(name);(p/'attempt.json').write_text('fixture')
            with patch.object(trial,'preflight',return_value=({},[])):
                with self.assertRaises(FileExistsError):trial.run(p)
