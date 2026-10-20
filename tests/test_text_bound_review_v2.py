import asyncio
from copy import deepcopy
import unittest

from evaluation import text_bound_review_v2 as probe
from model_adapter.contracts import ModelSettings, ModelConnectionError
from model_adapter.runtime import ModelClient
from tests.test_text_bound_review import Adapter


def task(answer='在所述条件下，传感器提供测量信号，但保证所有设备永不失效。'):
    card={'question':'说明资料中的用途，不写操作步骤。','evidence_id':'E1',
          'support_span':{'text':'在该条件下传感器提供测量信号。','start':10,'end':27},
          'source_version':'v1','provenance':{'knowledge_version':'k1'},
          'required_points':['SECRET_POINT'],'candidate_answer':'SECRET_REFERENCE'}
    example={'id':'fixture-1','answer':answer,'assessment':'SECRET_LABEL','bindings':'SECRET_POSITION'}
    return probe.model_input(card,example)


def judgment(label='supported'):
    return {'proposition':'在所述条件下提供测量信号','support':label,
            'basis_ids':['E1'] if label in ('supported','contradicted') else [],'rationale':'依据指定文本'}


def prediction(t):
    return {'sample_id':t['sample_id'],'coverage':'complete','missing_content':[],
            'units':[{'unit_id':u['unit_id'],'composition':'single','judgments':[judgment()],
                      'rationale':'单元判断'} for u in t['answer_units']], 'rationale':'用途已覆盖'}


class TextBoundV2Tests(unittest.TestCase):
    def test_lossless_program_units_and_positions_across_topics(self):
        for answer in ['变压器关系只适用于给定条件。保护另有要求！','P=UI；需说明工况。\n不可无条件推广。',
                       '单句包含多个判断，不能按标点认定原子性。','😊e\u0301。\n\n第二句？','  温度测量\n尾部无句号  ']:
            units=probe.build_units('S1',answer)
            self.assertEqual(''.join(u['text'] for u in units),answer)
            for u in units:self.assertEqual(answer[u['start']:u['end']],u['text'])
            self.assertEqual(units,probe.build_units('S1',answer))
            self.assertNotEqual(units[0]['unit_id'],probe.build_units('S2',answer)[0]['unit_id'])

    def test_no_labels_or_expected_positions_leak(self):
        t=task();self.assertNotIn('SECRET',probe.canonical(t))
        self.assertEqual(t['answer_units'][0]['text'],t['answer'])
        self.assertIn('start',t['answer_units'][0])

    def test_same_unit_accepts_mixed_support_without_forced_aggregate(self):
        t=task();v=prediction(t);u=v['units'][0]
        u['composition']='multiple';u['judgments'].append(dict(judgment('insufficient_evidence'),proposition='保证所有设备永不失效'))
        result=probe.parse(v,t)
        self.assertEqual([j['support'] for j in result['units'][0]['judgments']],['supported','insufficient_evidence'])

    def test_uncertain_and_unassessable_are_valid(self):
        t=task();v=prediction(t);v['coverage']='uncertain'
        v['units'][0].update(composition='uncertain',judgments=[judgment('not_assessable')])
        self.assertEqual(probe.parse(v,t)['coverage'],'uncertain')

    def test_incomplete_but_supported_and_complete_with_unsupported(self):
        t=task();v=prediction(t);v.update(coverage='incomplete',missing_content=['用途'])
        self.assertEqual(probe.parse(v,t)['units'][0]['judgments'][0]['support'],'supported')
        v=prediction(t);v['units'][0]['judgments']=[judgment('insufficient_evidence')]
        self.assertEqual(probe.parse(v,t)['coverage'],'complete')

    def test_wrong_missing_duplicate_ids_and_extra_offsets_rejected(self):
        t=task()
        for mutation in ('unit','sample','missing','duplicate','offset','basis','missing_basis','multi_one','uncertain_supported'):
            v=prediction(t);u=v['units'][0]
            if mutation=='unit':u['unit_id']='foreign'
            if mutation=='sample':v['sample_id']='foreign'
            if mutation=='missing':v['units']=[]
            if mutation=='duplicate':v['units'].append(deepcopy(u))
            if mutation=='offset':u['start']=0
            if mutation=='basis':u['judgments'][0]['basis_ids']=['foreign']
            if mutation=='missing_basis':u['judgments'][0]['basis_ids']=[]
            if mutation=='multi_one':u['composition']='multiple'
            if mutation=='uncertain_supported':u['composition']='uncertain'
            with self.subTest(mutation=mutation),self.assertRaises(probe.StructuredValidationError):probe.parse(v,t)

    def test_one_correction_keeps_all_carriers_then_success(self):
        t=task();adapter=Adapter([{},prediction(t)]);saved={}
        r=asyncio.run(probe.execute([t],ModelClient(adapter,ModelSettings('synthetic_fixture')),None,
            lambda sid,kind,value:saved.update({kind:value})))
        self.assertEqual(r['actual_calls'],2)
        self.assertEqual(saved['result']['program_answer_units'],t['answer_units'])
        self.assertEqual([x['correction'] for x in r['records']],[False,True])

    def test_second_invalid_stops_without_third_call_or_second_item(self):
        t=task();other=deepcopy(t);other['sample_id']='fixture-2';saved={};adapter=Adapter([{},{}])
        r=asyncio.run(probe.execute([t,other],ModelClient(adapter,ModelSettings('synthetic_fixture')),None,
            lambda sid,kind,value:saved.update({(sid,kind):value})))
        self.assertEqual(r['actual_calls'],2)
        self.assertEqual(saved[(t['sample_id'],'result')]['status'],'failed')
        self.assertNotIn((other['sample_id'],'accepted'),saved)

    def test_shared_failure_stops_without_retry(self):
        t=task();adapter=Adapter([ModelConnectionError()])
        r=asyncio.run(probe.execute([t,t],ModelClient(adapter,ModelSettings('synthetic_fixture')),None,lambda *x:None))
        self.assertEqual(r['actual_calls'],1);self.assertTrue(r['controls'][0]['stop'])

    def test_timeout_stops_and_preserves_call_record(self):
        class Slow:
            async def complete(self,request):await asyncio.sleep(1)
        r=asyncio.run(probe.execute([task()],ModelClient(Slow(),ModelSettings('synthetic_fixture',timeout_seconds=.01)),None,lambda *x:None))
        self.assertEqual(r['actual_calls'],1);self.assertTrue(r['controls'][0]['stop'])
        self.assertEqual(r['records'][0]['error_code'],'MODEL_TIMEOUT')


if __name__=='__main__':unittest.main()
