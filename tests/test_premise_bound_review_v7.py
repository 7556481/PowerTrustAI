"""Preset synthetic responses test wiring/contracts, not model reliability."""
import asyncio
from copy import deepcopy
import json
import unittest

from core.validation import ContractError
from evaluation import premise_bound_review_v6 as old
from evaluation import premise_bound_review_v7 as p
from evaluation.requirement_trial_v3 import execute
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from tests.test_text_bound_review import Adapter


def fixture(answer='演示队列按票号升序处理，仅在窗口W内启用。', ident='queue'):
    card = {'question':'按给定合成约定说明演示队列的处理次序与启用范围。',
        'premise_spans':[], 'expected':'DO_NOT_SEND_REFERENCE',
        'requirements':[
            {'id':'R1','model_visible_task_requirement':'说明票号处理次序'},
            {'id':'R2','model_visible_task_requirement':'保留启用窗口限定'}],
        'evidence':[{'id':'L-Q','text':'合成约定：队列按票号升序处理，仅在窗口W内启用。',
            'url':'synthetic://queue','locator':'rule-1','text_basis':'synthetic'}]}
    return p.model_input(card, {'id':ident,'answer':answer,'expected':'DO_NOT_SEND_LABEL'})


def prediction(task):
    ids = [u['unit_id'] for u in task['answer_units']]
    return {'sample_id':task['sample_id'],
        'requirements':[{'requirement_id':r['requirement_id'],'coverage':'covered',
            'unit_ids':ids,'rationale':'Synthetic addressedness reason'}
            for r in task['requirements']],
        'units':[{'unit_id':u['unit_id'],
            'rationale':'One scoped assertion retains the stated window and order.',
            'judgments':[{'proposition':u['text'],'claim_type':'literature_statement',
                'support':'supported','basis_ids':['L-Q'],
                'rationale':'The supplied synthetic rule states this scope and order.'}]}
            for u in task['answer_units']],
        'rationale':'Synthetic contract fixture, not a model prediction.'}


class RationaleLayoutTests(unittest.TestCase):
    def test_one_final_shape_and_explicit_sibling_reason(self):
        self.assertEqual(p.PROMPT.count('Return ONLY JSON with exact fields:'), 1)
        example = json.loads(p.PROMPT.split('Return ONLY JSON with exact fields:')[-1])
        self.assertEqual(example, p.OUTPUT_SHAPE)
        self.assertEqual(list(example['units'][0]), ['unit_id','rationale','judgments'])
        for path in ['requirements[i].rationale','units[i].rationale',
                     'units[i].judgments[j].rationale','Top-level rationale']:
            self.assertIn(path, p.PROMPT)

    def test_input_whitelist_unchanged_new_prompt_sent(self):
        task = fixture(); before = deepcopy(task)
        messages = p.messages(task)
        self.assertNotEqual(messages[0].content, old.PROMPT)
        self.assertEqual(messages[1].content, old.messages(task)[1].content)
        self.assertNotIn('DO_NOT_SEND', messages[1].content)
        self.assertEqual(task, before)

    def test_valid_prediction_acceptance_and_derivations_equal_v6(self):
        task = fixture(); value = prediction(task); before = deepcopy(value)
        self.assertEqual(p.parse(value, task), old.parse(value, task))
        self.assertEqual(value, before)

    def test_every_reason_location_rejects_missing_empty_null(self):
        task = fixture()
        for location in ['root','requirement','unit','judgment']:
            for malformed in ['missing','', '   ', None]:
                with self.subTest(location=location, malformed=malformed):
                    value = prediction(task)
                    obj = {'root':value,'requirement':value['requirements'][0],
                           'unit':value['units'][0],
                           'judgment':value['units'][0]['judgments'][0]}[location]
                    if malformed == 'missing': del obj['rationale']
                    else: obj['rationale'] = malformed
                    with self.assertRaises(ContractError): p.parse(value, task)
                    self.assertEqual('rationale' in obj, malformed != 'missing')

    def test_multiple_judgments_still_need_separate_unit_reason(self):
        task = fixture(); value = prediction(task)
        value['units'][0]['judgments'].append(deepcopy(value['units'][0]['judgments'][0]))
        self.assertEqual(p.parse(value, task)['units'][0]['program_composition'], 'multiple')
        del value['units'][0]['rationale']
        with self.assertRaises(ContractError): p.parse(value, task)

    def test_second_topic_multiple_units_no_silent_unit_reason_repair(self):
        task = fixture('档案标签用字母代码。保留时间限定为窗口T。', ident='archive')
        task['question'] = '按合成档案约定说明标签和保留时间。'
        task['evidence'][0]['text'] = '合成约定：标签用字母代码，记录仅在窗口T内保留。'
        task['requirements'][0]['description'] = '说明标签表示'
        task['requirements'][1]['description'] = '说明保留窗口'
        value = prediction(task); self.assertEqual(len(value['units']), 2)
        self.assertEqual(len(p.parse(value, task)['units']), 2)
        del value['units'][1]['rationale']
        with self.assertRaises(ContractError) as caught: p.parse(value, task)
        self.assertEqual(caught.exception.diagnostic['field_path'], '$.units[1].rationale')

    def test_json_object_order_not_a_new_rejection_rule(self):
        task = fixture(); value = prediction(task)
        value['units'][0] = dict(reversed(list(value['units'][0].items())))
        self.assertEqual(p.parse(value, task), old.parse(value, task))

    def test_wrong_ids_and_model_derived_fields_still_rejected(self):
        task = fixture()
        for edit in ['id','extra']:
            value = prediction(task)
            if edit == 'id': value['units'][0]['judgments'][0]['basis_ids'] = ['FOREIGN']
            else: value['units'][0]['program_composition'] = 'single'
            with self.assertRaises(ContractError): p.parse(value, task)

    def test_actual_instance_gate_not_waived_by_well_formed_reasons(self):
        task = fixture('试验台Q此刻已打开。'); value = prediction(task)
        value['units'][0]['judgments'][0]['claim_type'] = 'external_claim'
        with self.assertRaises(ContractError): p.parse(value, task)

    def test_semantically_poor_reason_is_not_mechanically_certified(self):
        task = fixture(); value = prediction(task)
        value['units'][0]['rationale'] = 'A generic filler explanation.'
        self.assertEqual(p.parse(value, task)['units'][0]['rationale'],
                         'A generic filler explanation.')

    def test_mock_correction_uses_exact_path_and_retains_model_reason(self):
        task = fixture(); good = prediction(task); bad = deepcopy(good)
        del bad['units'][0]['rationale']
        adapter = Adapter([bad, good]); saved = {}
        result = asyncio.run(execute([task], ModelClient(adapter, ModelSettings('fixture')),
            None, lambda sid,kind,v:saved.update({(sid,kind):v}), protocol=p))
        self.assertEqual(result['actual_calls'], 2)
        self.assertEqual(adapter.requests[0].messages, p.messages(task))
        correction = json.loads(adapter.requests[1].messages[-1].content)
        self.assertEqual(correction['validation_error']['field_path'], '$.units[0].rationale')
        self.assertEqual(json.loads(correction['invalid_output']), bad)
        self.assertEqual(saved[(task['sample_id'],'result')]['prediction']['units'][0]['rationale'],
                         good['units'][0]['rationale'])

    def test_mock_final_failure_stops_next_item_no_reason_fabricated(self):
        task = fixture(); bad = prediction(task); del bad['units'][0]['rationale']
        adapter = Adapter([bad, bad]); saved = {}
        result = asyncio.run(execute([task, fixture(ident='not-executed')],
            ModelClient(adapter, ModelSettings('fixture')), None,
            lambda sid,kind,v:saved.update({(sid,kind):v}), protocol=p))
        self.assertEqual(result['actual_calls'], 2)
        self.assertTrue(result['controls'][0]['stop'])
        self.assertNotIn(('not-executed','accepted'), saved)
        self.assertNotIn('prediction', saved[(task['sample_id'],'result')])
