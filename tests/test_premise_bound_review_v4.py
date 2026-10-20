from copy import deepcopy
import unittest

from evaluation import premise_bound_review_v4 as p
from evaluation import requirement_review_v3 as old
from tests.test_requirement_review_v3 import fixture as old_fixture, prediction as old_prediction
from services.validation_diagnostics import StructuredValidationError


def fixture(sample='sample-A'):
    question='设设备属于本题范围，其导电部件外露。请说明入口要求。'
    card={'question':question,'premise_spans':[{'start':1,'end':9},{'start':10,'end':17}],
          'requirements':[{'id':'R1','model_visible_task_requirement':'只评分定义映射'},
                          {'id':'R2','model_visible_task_requirement':'只评分入口标志，不因R1缺失降分'}],
          'candidate_reference':'SECRET_REFERENCE',
          'evidence':[{'id':'E1','text':'definition','url':'fixture','locator':'def','text_basis':'fixture'},
                      {'id':'E2','text':'rule','url':'fixture','locator':'rule','text_basis':'fixture',
                       'scope_context':[{'text':'scope','url':'fixture','locator':'parent','text_basis':'fixture'}]}]}
    return p.model_input(card,{'id':sample,'answer':'题设说明部件外露。','expected':'SECRET_LABEL'})


def prediction(task):
    uid=task['answer_units'][0]['unit_id'];pid=task['scenario_premises'][1]['premise_id']
    return {'sample_id':task['sample_id'],
        'requirements':[{'requirement_id':r['requirement_id'],'coverage':'covered',
                          'unit_ids':[uid],'rationale':'fixture judgment'} for r in task['requirements']],
        'units':[{'unit_id':uid,'judgments':[{'proposition':'题设说明部件外露',
                  'claim_type':'premise_restatement','support':'supported','basis_ids':[pid],
                  'rationale':'题设假定，非现场核验'}],'rationale':'fixture decomposition'}],
        'rationale':'fixture only, not a model prediction'}


class PremiseBoundTests(unittest.TestCase):
    def test_B_independent_R2_kept_when_R1_missing(self):
        task=fixture();v=prediction(task)
        v['requirements'][0].update(coverage='missing',unit_ids=[],rationale='映射未说出')
        v['units'][0]['judgments'][0].update(claim_type='scenario_application',
            proposition='题设房间入口应设标志',basis_ids=[task['scenario_premises'][1]['premise_id'],'E1','E2'])
        result=p.parse(v,task)
        self.assertEqual(result['requirements'][1]['coverage'],'covered')
        self.assertEqual(result['program_coverage']['value'],'incomplete')
        self.assertEqual(result['requirements'][0]['unit_ids'],[])

    def test_wrong_mapping_can_address_R1_but_be_contradicted(self):
        task=fixture();v=prediction(task)
        v['units'][0]['judgments'][0].update(claim_type='scenario_application',
            support='contradicted',basis_ids=[task['scenario_premises'][1]['premise_id'],'E1'],
            proposition='故意错误连接的合成断言',rationale='fixture conflict, not a real new sample')
        self.assertEqual(p.parse(v,task)['program_coverage']['value'],'complete')

    def test_A_C_identical_premise_has_same_identity_and_support_semantics(self):
        results=[]
        for sample in ('sample-A','sample-C'):
            task=fixture(sample);result=p.parse(prediction(task),task)
            j=result['units'][0]['judgments'][0]
            self.assertEqual(j['support'],'supported')
            self.assertEqual(j['program_support_scope'],'hypothetical_question_only')
            results.append(j['program_basis_bindings'])
        self.assertEqual(results[0],results[1])

    def test_premise_restatement_cannot_borrow_literature_id(self):
        task=fixture();v=prediction(task);v['units'][0]['judgments'][0]['basis_ids']=['E2']
        with self.assertRaises(StructuredValidationError):p.parse(v,task)

    def test_premise_cannot_verify_external_claim_or_general_rule(self):
        for typ in ('external_claim','literature_statement'):
            task=fixture();v=prediction(task);v['units'][0]['judgments'][0]['claim_type']=typ
            with self.assertRaises(StructuredValidationError):p.parse(v,task)

    def test_application_needs_both_kinds_for_supported_or_conflict(self):
        for support in ('supported','contradicted'):
            for ids in (['E2'],[]):
                task=fixture();v=prediction(task);v['units'][0]['judgments'][0].update(
                    claim_type='scenario_application',support=support,basis_ids=ids)
                with self.assertRaises(StructuredValidationError):p.parse(v,task)

    def test_literature_statement_supported_by_literature_only(self):
        task=fixture();v=prediction(task);v['units'][0]['judgments'][0].update(
            claim_type='literature_statement',basis_ids=['E2'])
        self.assertEqual(p.parse(v,task)['units'][0]['judgments'][0]['program_basis_bindings'][0]['basis_kind'],
                         'literature_evidence')

    def test_lifespan_insufficient_does_not_erase_coverage(self):
        task=fixture();v=prediction(task);v['units'][0]['judgments'].append({
            'proposition':'寿命十年','claim_type':'external_claim','support':'insufficient_evidence',
            'basis_ids':[],'rationale':'未交付寿命资料'})
        r=p.parse(v,task)
        self.assertEqual(r['program_coverage']['value'],'complete')
        self.assertEqual(r['units'][0]['program_composition'],'multiple')

    def test_single_multiple_derived_for_one_two_three_judgments(self):
        for n in (1,2,3):
            task=fixture();v=prediction(task)
            v['units'][0]['judgments']=[deepcopy(v['units'][0]['judgments'][0]) for _ in range(n)]
            r=p.parse(v,task)
            self.assertEqual(r['units'][0]['program_composition'],'single' if n==1 else 'multiple')
            self.assertNotIn('composition',v['units'][0])

    def test_empty_judgments_and_model_count_or_composition_rejected(self):
        for mutation in ('empty','composition','judgment_count'):
            task=fixture();v=prediction(task)
            if mutation=='empty':v['units'][0]['judgments']=[]
            else:v['units'][0][mutation]='single'
            with self.assertRaises(StructuredValidationError):p.parse(v,task)

    def test_uncertainty_is_preserved_without_uncertain_count(self):
        task=fixture();v=prediction(task);v['units'][0]['judgments'][0].update(
            claim_type='external_claim',support='not_assessable',basis_ids=[],rationale='无法可靠评估')
        r=p.parse(v,task)
        self.assertEqual(r['units'][0]['program_composition'],'single')
        self.assertEqual(r['units'][0]['judgments'][0]['support'],'not_assessable')

    def test_invalid_basis_and_requirement_ids_rejected(self):
        for mutation in ('basis','requirement','unit'):
            task=fixture();v=prediction(task)
            if mutation=='basis':v['units'][0]['judgments'][0]['basis_ids']=['R1']
            elif mutation=='requirement':v['requirements'][0]['requirement_id']='foreign'
            else:v['units'][0]['unit_id']='foreign'
            with self.assertRaises(StructuredValidationError):p.parse(v,task)

    def test_foreign_question_premise_id_rejected(self):
        task=fixture();v=prediction(task)
        other=p.bind_premise('另一题的前提',0,6)
        v['units'][0]['judgments'][0]['basis_ids']=[other['premise_id']]
        with self.assertRaises(StructuredValidationError):p.parse(v,task)

    def test_premise_tamper_and_type_collision_rejected(self):
        for mutation in ('text','collision'):
            task=fixture()
            if mutation=='text':task['scenario_premises'][0]['text']='偷偷改变前提'
            else:task['evidence'][0]['evidence_id']=task['scenario_premises'][0]['premise_id']
            with self.assertRaises(StructuredValidationError):p.parse(prediction(task),task)

    def test_no_labels_in_messages_and_parent_scope_preserved(self):
        task=fixture();wire=p.canonical([m.content for m in p.messages(task)])
        self.assertNotIn('SECRET',wire)
        self.assertEqual(task['evidence'][1]['scope_context'][0]['text'],'scope')
        self.assertTrue(all(not x['site_verified'] for x in task['scenario_premises']))
        self.assertIn('Do not lower one requirement',p.PROMPT)

    def test_old_multiple_with_one_judgment_still_fails(self):
        task=old_fixture();v=old_prediction(task);v['units'][0]['composition']='multiple'
        with self.assertRaises(StructuredValidationError):old.parse(v,task)


if __name__=='__main__':unittest.main()
