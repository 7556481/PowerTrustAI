"""Synthetic responses exercise contracts, not model reasoning or real equipment."""
import asyncio
from copy import deepcopy
import unittest

from evaluation import premise_bound_review_v6 as p
from evaluation import premise_bound_review_v5 as old
from evaluation.requirement_trial_v3 import execute
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from services.validation_diagnostics import StructuredValidationError, ValidationErrors
from tests.test_text_bound_review import Adapter


def card(question='按演示资料说明反序索引的排列方向。', premise_spans=None):
    return {'question':question,'premise_spans':premise_spans or [],
            'requirements':[{'id':'R1','model_visible_task_requirement':'说明索引排列方向'}],
            'expected':'SECRET_EXPECTED','evidence':[{'id':'L1',
                'text':'合成定义：反序索引按标签降序排列。',
                'url':'synthetic://index','locator':'definition','text_basis':'synthetic fixture'}]}


def task(answer='反序索引按标签降序排列。', source=None, ident='synthetic'):
    return p.model_input(source or card(),{'id':ident,'answer':answer,
                                         'role':'SECRET_ROLE','expected':'SECRET_LABEL'})


def prediction(t, *, support='supported', kind='literature_statement', basis=None):
    ids=basis if basis is not None else ['L1']
    uid=t['answer_units'][0]['unit_id']
    return {'sample_id':t['sample_id'],
            'requirements':[{'requirement_id':r['requirement_id'],'coverage':'covered',
                             'unit_ids':[uid],'rationale':'synthetic addressed aspect'}
                            for r in t['requirements']],
            'units':[{'unit_id':u['unit_id'],'judgments':[{
                'proposition':u['text'],'support':support,'claim_type':kind,
                'basis_ids':ids,'rationale':'synthetic supplied judgment, not model inference'}],
                'rationale':'synthetic unit'} for u in t['answer_units']],
            'rationale':'synthetic fixture only'}


class AddressednessTests(unittest.TestCase):
    def test_reverse_direction_can_be_covered_and_contradicted(self):
        t=task('反序索引按标签升序排列。')
        r=p.parse(prediction(t,support='contradicted'),t)
        self.assertEqual(r['requirements'][0]['coverage'],'covered')
        self.assertEqual(r['program_coverage']['value'],'complete')
        self.assertEqual(r['units'][0]['judgments'][0]['support'],'contradicted')

    def test_other_topic_wrong_operation_preserves_addressedness(self):
        c=card('根据合成盘点规则说明批次计数的运算。')
        c['requirements'][0]['model_visible_task_requirement']='说明计数采用哪种运算'
        c['evidence'][0]['text']='合成规则：批次计数取记录总数，不取分组平均数。'
        t=task('批次计数取分组平均数而非记录总数。',c)
        r=p.parse(prediction(t,support='contradicted'),t)
        self.assertEqual(r['program_coverage']['value'],'complete')

    def test_missing_scope_remains_partial_even_when_assertion_supported(self):
        c=card('按资料说明合成日志的事件范围和时间窗口。')
        c['requirements'][0]['model_visible_task_requirement']='说明时间窗口W内的事件范围'
        c['evidence'][0]['text']='合成日志描述窗口W内的连接事件。'
        t=task('日志描述连接事件。',c);v=prediction(t)
        v['requirements'][0].update(coverage='partially_covered',rationale='未说明窗口W')
        self.assertEqual(p.parse(v,t)['program_coverage']['value'],'incomplete')

    def test_substituted_scope_not_repaired_by_parser(self):
        c=card('按资料说明合成日志覆盖的时间范围。')
        c['evidence'][0]['text']='合成日志仅包含窗口W内的事件。'
        t=task('日志包含整个日期的事件。',c);v=prediction(t,support='insufficient_evidence')
        v['requirements'][0].update(coverage='partially_covered',rationale='将窗口W换成整个日期')
        before=deepcopy(v);r=p.parse(v,t)
        self.assertEqual(r['requirements'][0]['coverage'],'partially_covered')
        self.assertEqual(v,before)

    def test_absent_requirement_stays_missing_independently(self):
        c=card();c['requirements'].append({'id':'R2','model_visible_task_requirement':'说明标签字段'})
        t=task(source=c);v=prediction(t)
        v['requirements'][1].update(coverage='missing',unit_ids=[],rationale='未涉及字段')
        r=p.parse(v,t)
        self.assertEqual(r['requirements'][0]['coverage'],'covered')
        self.assertEqual(r['program_coverage']['value'],'incomplete')

    def test_semantic_mistake_is_not_silently_corrected(self):
        t=task('反序索引按标签升序排列。');v=prediction(t,support='contradicted')
        v['requirements'][0].update(coverage='partially_covered',rationale='fixture semantic mistake')
        self.assertEqual(p.parse(v,t)['requirements'][0]['coverage'],'partially_covered')


class ClaimTargetTests(unittest.TestCase):
    def test_literature_definition_needs_no_hypothetical_or_site_record(self):
        t=task();self.assertEqual(t['scenario_premises'],[])
        r=p.parse(prediction(t),t);j=r['units'][0]['judgments'][0]
        self.assertEqual(j['support'],'supported')
        self.assertEqual(j['program_support_scope'],'delivered_literature_only_not_site_verification')

    def test_actual_device_supported_or_contradicted_requires_record(self):
        t=task('试验台S此刻处于打开态。')
        for label in ('supported','contradicted'):
            with self.assertRaises(StructuredValidationError) as caught:
                p.parse(prediction(t,support=label,kind='external_claim'),t)
            self.assertEqual(caught.exception.diagnostic['constraint'],'actual_instance_record_required')

    def test_missing_actual_evidence_retains_insufficient_or_not_assessable(self):
        t=task('试验台S此刻处于打开态。')
        for label in ('insufficient_evidence','not_assessable'):
            r=p.parse(prediction(t,support=label,kind='external_claim',basis=[]),t)
            self.assertEqual(r['units'][0]['judgments'][0]['support'],label)
            self.assertIn('not_verified',r['units'][0]['judgments'][0]['program_support_scope'])

    def record_card(self):
        c=card('根据给定合成记录说明试验台S在记录时刻的状态。')
        c['evidence'].append({'id':'A1','text':'合成记录：试验台S在时刻T处于打开态。',
            'url':'synthetic://record','locator':'row 1','text_basis':'synthetic fixture',
            'source_role':'actual_record','record_context':{
                'subject':'试验台S','record_id':'synthetic-log-T','locator':'row 1'}})
        return c

    def test_supplied_actual_record_has_distinct_derived_identity_not_certification(self):
        t=task('试验台S在记录时刻处于打开态。',self.record_card())
        r=p.parse(prediction(t,kind='external_claim',basis=['A1']),t)
        j=r['units'][0]['judgments'][0]
        self.assertEqual(j['program_basis_bindings'][0]['basis_kind'],'actual_record')
        self.assertIn('not_independent_site_certification',j['program_support_scope'])

    def test_actual_record_cannot_replace_literature_basis_for_definition(self):
        t=task(source=self.record_card())
        with self.assertRaises(StructuredValidationError):p.parse(prediction(t,basis=['A1']),t)

    def test_incomplete_record_context_or_unknown_source_role_rejected(self):
        for edit in ('missing','empty','unknown'):
            c=self.record_card()
            if edit=='missing':del c['evidence'][1]['record_context']
            elif edit=='empty':c['evidence'][1]['record_context']['subject']=''
            else:c['evidence'][1]['source_role']='verified_by_model'
            with self.assertRaises(StructuredValidationError):task(source=c)

    def test_hypothetical_rule_application_never_becomes_site_verification(self):
        q='假设容器K处于打开态。请根据合成规则说明应有标记。'
        c=card(q,[{'start':2,'end':11}]);c['evidence'][0]['text']='合成规则：打开态对应标记Z。'
        t=task('该假定容器对应标记Z。',c);pid=t['scenario_premises'][0]['premise_id']
        r=p.parse(prediction(t,kind='scenario_application',basis=[pid,'L1']),t)
        self.assertEqual(r['units'][0]['judgments'][0]['program_support_scope'],'hypothetical_question_only')
        with self.assertRaises(StructuredValidationError):
            p.parse(prediction(t,kind='external_claim',basis=[pid,'L1']),t)


class WiringAndSafetyTests(unittest.TestCase):
    def test_model_messages_keep_task_and_old_schema_but_use_new_prompt(self):
        t=task();before=deepcopy(t);messages=p.messages(t)
        self.assertNotEqual(messages[0].content,old.PROMPT)
        self.assertEqual(json_safe(messages[1].content)['answer'],t['answer'])
        self.assertNotIn('SECRET',messages[1].content)
        self.assertIn('definite opposite answer',messages[0].content)
        self.assertIn('no real site observation',messages[0].content)
        self.assertEqual(t,before)

    def test_foreign_ids_extra_fields_and_missing_reasons_still_rejected(self):
        for edit in ('id','extra','reason'):
            t=task();v=prediction(t)
            if edit=='id':v['units'][0]['judgments'][0]['basis_ids']=['foreign']
            elif edit=='extra':v['units'][0]['composition']='single'
            else:del v['units'][0]['rationale']
            with self.assertRaises((StructuredValidationError,ValidationErrors)):p.parse(v,t)

    def test_program_composition_follows_count_not_semantic_certification(self):
        t=task();v=prediction(t);v['units'][0]['judgments'].append(deepcopy(v['units'][0]['judgments'][0]))
        r=p.parse(v,t)
        self.assertEqual(r['units'][0]['program_composition'],'multiple')
        self.assertIn('not_semantic_certification',r['units'][0]['program_composition_basis'])

    def test_fake_execution_receives_v6_messages_and_keeps_one_correction_stop(self):
        t=task();adapter=Adapter([{},{}]);saved={}
        result=asyncio.run(execute([t,task(ident='next')],
            ModelClient(adapter,ModelSettings('fixture')),None,
            lambda sid,kind,v:saved.update({(sid,kind):v}),protocol=p))
        self.assertEqual(adapter.requests[0].messages,p.messages(t))
        self.assertEqual(result['actual_calls'],2)
        self.assertTrue(result['controls'][0]['stop'])
        self.assertNotIn(('next','accepted'),saved)


def json_safe(value):
    import json
    return json.loads(value)
