import asyncio
from copy import deepcopy
import json
import unittest

from evaluation import text_bound_review as probe
from model_adapter.contracts import ModelResponse, ModelSettings, ModelConnectionError
from model_adapter.runtime import ModelClient


def fixture():
    card = {'question':'Describe its use, without wiring.', 'evidence_id':'E1',
            'support_span':{'text':'In this application it scales current for measuring and protection.', 'start':12,'end':81},
            'source_version':'version1','provenance':{'knowledge_version':'knowledge1'},
            'required_points':['SECRET_EXPECTED_POINT']}
    example = {'id':'S1','answer':'In this application it scales current.',
               'assessment':{'coverage':'SECRET_LABEL'},'reason':'SECRET_REASON'}
    return probe.model_input(card,example)


def prediction(task):
    return {'sample_id':task['sample_id'],'coverage':'incomplete','missing_content':['use'],
            'claims':[{'start':0,'end':len(task['answer']),'support':'supported',
                       'basis_ids':['E1'],'rationale':'provided text'}], 'rationale':'Missing requested use.'}


class Adapter:
    def __init__(self,items):self.items=iter(items);self.requests=[]
    async def complete(self,request):
        self.requests.append(request);value=next(self.items)
        if isinstance(value,Exception):raise value
        return ModelResponse(json.dumps(value),'synthetic_fixture',finish_reason='stop')


class TextBoundTests(unittest.TestCase):
    def test_allowlist_keeps_complete_selected_text_but_no_labels(self):
        task=fixture();wire=probe.canonical(task)
        self.assertNotIn('SECRET',wire)
        self.assertEqual(task['evidence'][0]['text'],'In this application it scales current for measuring and protection.')
        self.assertEqual(set(task),{'sample_id','question','answer','evidence'})

    def test_incomplete_can_have_supported_stated_content(self):
        task=fixture();self.assertEqual(probe.parse(prediction(task),task)['coverage'],'incomplete')

    def test_wrong_ids_offsets_and_omitted_tail_strictly_rejected(self):
        task=fixture()
        for mutation in ('foreign','wrong_sample','tail','bool_offset','extra_field'):
            value=prediction(task)
            if mutation=='foreign':value['claims'][0]['basis_ids']=['foreign']
            if mutation=='wrong_sample':value['sample_id']='other'
            if mutation=='tail':value['claims'][0]['end']-=3
            if mutation=='bool_offset':value['claims'][0]['start']=False
            if mutation=='extra_field':value['expected_label']='supported'
            with self.subTest(mutation=mutation),self.assertRaises(probe.StructuredValidationError):
                probe.parse(value,task)

    def test_no_support_does_not_require_contradiction(self):
        task=fixture();value=prediction(task)
        value['claims'][0].update(support='insufficient_evidence',basis_ids=[])
        self.assertEqual(probe.parse(value,task)['claims'][0]['support'],'insufficient_evidence')

    def test_one_correction_and_then_stop_retains_failure(self):
        task=fixture();other=deepcopy(task);other['sample_id']='S2'
        adapter=Adapter([{},{}]);saved={}
        result=asyncio.run(probe.execute([task,other],ModelClient(adapter,ModelSettings('synthetic_fixture')),
            None,lambda sid,kind,value:saved.update({(sid,kind):value})))
        self.assertEqual(result['actual_calls'],2)
        self.assertEqual([r['correction'] for r in result['records']],[False,True])
        self.assertEqual(saved[('S1','result')]['status'],'failed')
        self.assertNotIn(('S2','accepted'),saved)

    def test_service_failure_stops_without_retry(self):
        task=fixture();adapter=Adapter([ModelConnectionError()])
        result=asyncio.run(probe.execute([task],ModelClient(adapter,ModelSettings('synthetic_fixture')),
            None,lambda *args:None))
        self.assertEqual(result['actual_calls'],1);self.assertTrue(result['controls'][0]['stop'])

    def test_three_predictions_continue_without_expected_label_scoring(self):
        tasks=[dict(fixture(),sample_id='S'+str(i)) for i in range(3)]
        adapter=Adapter([prediction(t) for t in tasks]);saved={}
        result=asyncio.run(probe.execute(tasks,ModelClient(adapter,ModelSettings('synthetic_fixture')),
            None,lambda sid,kind,value:saved.update({(sid,kind):value})))
        self.assertEqual(result['actual_calls'],3)
        self.assertEqual(len([1 for sid,kind in saved if kind=='result']),3)


if __name__=='__main__':unittest.main()
