import asyncio
from copy import deepcopy
import unittest

from evaluation import premise_bound_review_v4 as old
from evaluation import premise_bound_review_v5 as new
from evaluation.requirement_trial_v3 import execute
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelClient
from services.validation_diagnostics import StructuredValidationError, ValidationErrors
from tests.test_premise_bound_review_v4 import fixture, prediction
from tests.test_text_bound_review import Adapter


class FieldDiagnosticsTests(unittest.TestCase):
    def test_valid_prediction_unchanged_and_no_mutation(self):
        task=fixture();value=prediction(task);before=deepcopy(value)
        self.assertEqual(new.parse(value,task),old.parse(value,task))
        self.assertEqual(value,before)
        self.assertEqual(new.messages(task),old.messages(task))
        self.assertEqual(new.PROMPT,old.PROMPT)

    def test_missing_reasons_all_located_without_inventing_text(self):
        task=fixture();value=prediction(task);value['units'][0].pop('rationale')
        with self.assertRaises(ValidationErrors) as caught:new.parse(value,task)
        self.assertEqual(caught.exception.diagnostics[0]['field_path'],'$.units[0].rationale')
        self.assertEqual(caught.exception.diagnostics[0]['constraint'],'required_field_missing')
        self.assertNotIn('rationale',value['units'][0])
        with self.assertRaises(StructuredValidationError):old.parse(value,task)

    def test_empty_or_wrong_reason_type_rejected(self):
        for reason in ('', ' ', None, 1, []):
            task=fixture();value=prediction(task);value['units'][0]['rationale']=reason
            with self.assertRaises(ValidationErrors):new.parse(value,task)

    def test_extra_fields_still_rejected_without_echoing_payload(self):
        task=fixture();value=prediction(task)
        value['units'][0]['SECRET_FIELD']='SECRET_VALUE'
        with self.assertRaises(ValidationErrors) as caught:new.parse(value,task)
        self.assertNotIn('SECRET',str(caught.exception.diagnostic))

    def test_foreign_ids_and_judgment_reason_still_strict(self):
        for edit in ('id','reason'):
            task=fixture();value=prediction(task)
            if edit=='id':value['units'][0]['judgments'][0]['basis_ids']=['foreign']
            else:value['units'][0]['judgments'][0]['rationale']=''
            with self.assertRaises(StructuredValidationError):new.parse(value,task)

    def test_correction_receives_precise_path_and_can_succeed(self):
        task=fixture();bad=prediction(task);bad['units'][0].pop('rationale')
        adapter=Adapter([bad,prediction(task)]);saved={}
        result=asyncio.run(execute([task],ModelClient(adapter,ModelSettings('fixture')),None,
            lambda sid,kind,v:saved.update({kind:v}),protocol=new))
        self.assertEqual(result['actual_calls'],2)
        correction=adapter.requests[1].messages[-1].content
        self.assertIn('$.units[0].rationale',correction)
        self.assertIn('required_field_missing',correction)
        self.assertEqual(saved['result']['status'],'complete')

    def test_second_failure_stops_without_retry_or_next_item(self):
        task=fixture();bad=prediction(task);bad['units'][0].pop('rationale')
        adapter=Adapter([bad,bad]);saved={}
        result=asyncio.run(execute([task,fixture('next')],
            ModelClient(adapter,ModelSettings('fixture')),None,
            lambda sid,kind,v:saved.update({(sid,kind):v}),protocol=new))
        self.assertEqual(result['actual_calls'],2)
        self.assertTrue(result['controls'][0]['stop'])
        self.assertNotIn(('next','accepted'),saved)
