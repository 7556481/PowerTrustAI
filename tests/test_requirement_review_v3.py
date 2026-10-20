from copy import deepcopy
import unittest

from evaluation import requirement_review_v3 as probe


def fixture(answer='在给定条件下，设备提供信号。'):
    card={'question':'是否可用？说明相关条件。','source_pdf_sha256':'fixture-source',
          'requirements':[{'id':'R1','model_visible_task_requirement':'明确回答是否可用。','evaluator_only_expected_content':'SECRET_EXPECTED_1'},
                          {'id':'R2','model_visible_task_requirement':'说明适用条件。','evaluator_only_expected_content':'SECRET_EXPECTED_2'}],
          'evidence':[{'id':'E1','text':'在给定条件下提供信号。','printed_page':1,'pdf_page_1based':2,
                       'transcription_offsets':[0,12],'offset_basis':'fixture-transcription'}]}
    ex={'id':'S1','answer':answer,'expected_overall_coverage':'SECRET_LABEL','error_positions':'SECRET_POSITION'}
    return probe.model_input(card,ex,{'title':'fixture title','edition':'fixture edition'})


def prediction(task):
    uid=task['answer_units'][0]['unit_id']
    return {'sample_id':task['sample_id'],
            'requirements':[{'requirement_id':r['requirement_id'],'coverage':'covered','unit_ids':[uid],'rationale':'已回答'} for r in task['requirements']],
            'units':[{'unit_id':u['unit_id'],'composition':'single','judgments':[{'proposition':'在给定条件下提供信号',
                      'support':'supported','basis_ids':['E1'],'rationale':'证据支持'}],'rationale':'载体含一项判断'} for u in task['answer_units']],
            'rationale':'逐项覆盖独立于支持'}


class RequirementReviewTests(unittest.TestCase):
    def test_explicit_task_requirements_in_messages_without_truth_labels(self):
        t=fixture();wire=probe.canonical([m.content for m in probe.messages(t)])
        self.assertNotIn('SECRET',wire)
        self.assertEqual([r['requirement_id'] for r in t['requirements']],['R1','R2'])
        self.assertIn('明确回答是否可用。',wire);self.assertIn('说明适用条件。',wire)
        self.assertEqual(t['answer_units'][0]['text'],t['answer'])

    def test_missing_requirement_is_incomplete_despite_supported_assertions(self):
        t=fixture();v=prediction(t);v['requirements'][1].update(coverage='missing',unit_ids=[])
        r=probe.parse(v,t)
        self.assertEqual(r['program_coverage']['value'],'incomplete')
        self.assertEqual(r['units'][0]['judgments'][0]['support'],'supported')

    def test_coverage_can_be_complete_with_unsupported_extra_assertion(self):
        t=fixture();v=prediction(t);u=v['units'][0];u['composition']='multiple'
        u['judgments'].append({'proposition':'任何条件下均有保证','support':'insufficient_evidence','basis_ids':[],'rationale':'无该保证依据'})
        r=probe.parse(v,t);self.assertEqual(r['program_coverage']['value'],'complete')
        self.assertEqual(len(r['units'][0]['judgments']),2)

    def test_explicit_wrong_conclusion_can_be_addressed_but_contradicted(self):
        t=fixture();v=prediction(t);v['units'][0]['judgments'][0]['support']='contradicted'
        self.assertEqual(probe.parse(v,t)['program_coverage']['value'],'complete')

    def test_partial_and_uncertain_are_distinct(self):
        t=fixture()
        for state,overall,ids in [('partially_covered','incomplete',True),('uncertain','uncertain',False)]:
            v=prediction(t);v['requirements'][1].update(coverage=state,unit_ids=[t['answer_units'][0]['unit_id']] if ids else [])
            self.assertEqual(probe.parse(v,t)['program_coverage']['value'],overall)

    def test_all_requirement_ids_exact_and_valid_answer_unit_refs_required(self):
        t=fixture()
        for mutation in ('unknown','duplicate','missing','foreign_unit','missing_has_unit','covered_no_unit','extra_offsets','old_overall'):
            v=prediction(t);row=v['requirements'][0]
            if mutation=='unknown':row['requirement_id']='foreign'
            if mutation=='duplicate':v['requirements'][1]=deepcopy(row)
            if mutation=='missing':v['requirements'].pop()
            if mutation=='foreign_unit':row['unit_ids']=['foreign']
            if mutation=='missing_has_unit':row['coverage']='missing'
            if mutation=='covered_no_unit':row['unit_ids']=[]
            if mutation=='extra_offsets':row['start']=0
            if mutation=='old_overall':v['coverage']='complete'
            with self.subTest(mutation=mutation),self.assertRaises(probe.StructuredValidationError):probe.parse(v,t)

    def test_uncertain_unit_with_unassessable_judgment_valid(self):
        t=fixture();v=prediction(t);u=v['units'][0]
        u.update(composition='uncertain');u['judgments'][0].update(support='not_assessable',basis_ids=[])
        self.assertEqual(probe.parse(v,t)['units'][0]['composition'],'uncertain')

    def test_frozen_v2_unit_validator_still_strict(self):
        t=fixture()
        for mutation in ('wrong_unit','foreign_basis','missing_unit','extra_offset'):
            v=prediction(t);u=v['units'][0]
            if mutation=='wrong_unit':u['unit_id']='foreign'
            if mutation=='foreign_basis':u['judgments'][0]['basis_ids']=['foreign']
            if mutation=='missing_unit':v['units']=[]
            if mutation=='extra_offset':u['end']=999
            with self.subTest(mutation=mutation),self.assertRaises(probe.StructuredValidationError):probe.parse(v,t)


if __name__=='__main__':unittest.main()
