"""Offline preparation checks; no model construction, response replay or .env."""
from copy import deepcopy
from dataclasses import asdict
import json
import socket
import unittest
from unittest.mock import patch

from evaluation import public_review_validation_materials_v1 as materials
from agents.generation import messages_for
from core.models import TaskMode
from core.validation import ContractError, validate_request
from harness.contracts import RunBudget
from services.task_premises_v1 import catalog


class PreparationTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket.socket, 'connect', side_effect=AssertionError('offline preparation only'))
        guard.start(); self.addCleanup(guard.stop)
        self.document = materials.read(materials.PUBLIC / 'tasks-v1.json')

    def test_four_original_generation_inputs_and_five_fixed_branches(self):
        with patch('model_adapter.runtime.ModelClient', side_effect=AssertionError('no model client')):
            values, diagnostic = materials.build_inputs(self.document)
            rows, private = materials.identities(values, diagnostic)
        self.assertEqual(tuple(r['request_id'] for r in rows), materials.ORDER)
        self.assertEqual(sum(r['initial_generation_messages_sha256'] is not None for r in rows), 4)
        self.assertEqual(sum(r['mode'] == TaskMode.ASSESS_EXISTING.value for r in rows), 1)
        self.assertEqual(len(private), 5)
        self.assertEqual(sum(len(c['requirements']) for c in self.document['cases']), 12)
        for inp in values.values():
            validate_request(inp.request, RunBudget(max_model_calls=40, max_revision_rounds=0, max_transient_retries=0,
                             max_retrieval_calls=0, max_duration_seconds=800, step_timeout_seconds=110))

    def test_diagnostic_is_fixed_incorrect_text_without_fake_original_citations_or_snapshot(self):
        values, diagnostic = materials.build_inputs(self.document)
        self.assertIn('74', diagnostic.user_context)
        self.assertIn('88', diagnostic.existing_answer.text)
        self.assertEqual(diagnostic.existing_answer.citations, ())
        self.assertEqual(catalog(values['BTV-02'].request), catalog(diagnostic))
        rows, _ = materials.identities(values, diagnostic)
        row = rows[2]
        self.assertEqual(row['generation_snapshot'], 'must_remain_none')
        self.assertIsNone(row['generation_input_sha256'])
        self.assertIsNone(row['initial_generation_messages_sha256'])

    def test_missing_rule_case_delivers_only_its_own_unrelated_body(self):
        values, _ = materials.build_inputs(self.document)
        value = values['BTV-03']
        self.assertEqual(len(value.evidence), 1)
        self.assertEqual(value.evidence[0].source_id, 'BTV-S2')
        body = json.dumps([asdict(m) for m in messages_for(value, 3, product_guidance=True)], ensure_ascii=False)
        self.assertNotIn(self.document['sources'][0]['text'], body)
        self.assertIn(self.document['sources'][1]['text'], body)

    def test_scoring_labels_and_diagnostic_answer_do_not_leak_into_generation(self):
        values, _ = materials.build_inputs(self.document)
        for inp in values.values():
            messages = json.dumps([asdict(m) for m in messages_for(inp, 3, product_guidance=True)], ensure_ascii=False)
            self.assertNotIn('diagnostic_reference_clauses', messages)
            self.assertNotIn('coverage_components', messages)
            self.assertNotIn('expected', messages)
            self.assertNotIn(self.document['diagnostic']['text'], messages)
            self.assertNotIn('diagnostic_map', messages)

    def test_whitelist_rejects_new_hidden_fields_instead_of_forwarding_them(self):
        for location in ('root', 'case', 'source', 'requirement', 'diagnostic'):
            doc = deepcopy(self.document)
            target = {'root': doc, 'case': doc['cases'][0], 'source': doc['sources'][0],
                      'requirement': doc['cases'][0]['requirements'][0], 'diagnostic': doc['diagnostic']}[location]
            target['expected_labels'] = ['supported']
            with self.assertRaises(ContractError): materials.build_inputs(doc)

    def test_model_visible_common_requirements_are_not_used_to_register_premises(self):
        values, diagnostic = materials.build_inputs(self.document)
        for request in [v.request for v in values.values()] + [diagnostic]:
            p, = catalog(request)
            self.assertEqual(p.source_field, 'user_context')
            self.assertEqual(p.text, request.user_context[p.start_offset:p.end_offset])
            self.assertEqual(p.kind, 'stipulated')
            self.assertNotIn('88', p.text)


if __name__ == '__main__': unittest.main()
