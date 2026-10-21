from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from evaluation.eia_nrc_input_preparation_v1 import build_task, prepare
from evaluation.text_bound_review_v2 import build_units


def fixture(cid='H-EIA-001'):
    return {'card_id':cid,'source_group':'fixture','question':'fixture question',
        'scenario_premises':[],
        'requirements':[{'id':'R1','description':'task','reference':'SECRET_REQUIREMENT'}],
        'evidence':{'selected_definition':'official definition.',
            'paragraph_context':'official definition. official context.',
            'url':'fixture','title':'fixture','version':'fixture',
            'snapshot_sha256':'fixture','locator':'fixture'},
        'expected_support':'SECRET_LABEL','reference_units':['SECRET_SPLIT'],
        'sample_role':'SECRET_ROLE','rationale':'SECRET_REASON'}


class PreparationTests(unittest.TestCase):
    def test_whitelist_no_reference_payload_and_program_units_only(self):
        card=fixture();answer={'question_id':'H-EIA-001','candidate_id':'case','answer':'第一句。第二句。'}
        before=deepcopy(card);task=build_task(card,answer)
        self.assertNotIn('SECRET',json.dumps(task))
        self.assertEqual(card,before)
        self.assertEqual(task['answer_units'],build_units('case',answer['answer']))
        self.assertEqual(task['evidence'][0]['scope_context'][0]['text'],'official context.')

    def test_wrong_binding_extra_label_and_new_premise_rejected(self):
        answer={'question_id':'H-EIA-001','candidate_id':'case','answer':'fixture'}
        with self.assertRaises(ValueError):build_task(fixture('H-NRC-001'),answer)
        with self.assertRaises(ValueError):build_task(fixture(),dict(answer,expected='SECRET'))
        card=fixture();card['scenario_premises']=[{'text':'extra'}]
        with self.assertRaises(ValueError):build_task(card,answer)

    def test_prepare_does_not_read_poisoned_evaluator_file_or_overwrite(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);cards=root/'cards';cards.mkdir()
            for cid in ('H-EIA-001','H-NRC-001'):
                (cards/(cid+'.json')).write_text(json.dumps(fixture(cid)),encoding='utf-8')
            (root/'evaluator-only').mkdir()
            (root/'evaluator-only/expected-labels.json').write_text('NOT JSON SECRET',encoding='utf-8')
            answers=[{'question_id':cid,'candidate_id':cid+str(i),'answer':'fixture。'}
                     for cid in ('H-EIA-001','H-NRC-001') for i in range(4)]
            path=root/'answers.json';path.write_text(json.dumps({'answers':answers}),encoding='utf-8')
            output=root/'prepared';prepare(cards,path,output)
            self.assertNotIn('SECRET',(output/'messages-preview.json').read_text(encoding='utf-8'))
            with self.assertRaises(FileExistsError):prepare(cards,path,output)
