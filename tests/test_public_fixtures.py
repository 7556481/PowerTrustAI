"""Public synthetic_fixture regressions replacing reliance on private examples."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agents.generation import parse_answer
from core.validation import ContractError
from evaluation.acceptance_preparation import baseline
from tests.fixture_paths import synthetic_diagnostics
from tests.test_generation import inputs


class PublicFixtureTests(unittest.TestCase):
    def test_diagnostics_creates_its_parent_without_a_preexisting_data_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / 'not-created' / 'retrieval_local'
            with patch('tests.fixture_paths.LOCAL_ROOT', parent):
                with synthetic_diagnostics() as child:
                    self.assertEqual(Path(child).parent, parent)
                    self.assertTrue(Path(child).is_dir())
                self.assertFalse(Path(child).exists())

    def test_public_baseline_never_reads_private_history_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('evaluation.acceptance_preparation.PRIVATE', Path(directory) / 'absent'):
                value = baseline()
                self.assertTrue(value['source_files'])
                # Explicit opt-in also tolerates undistributed historical files.
                opted = baseline(include_private_history=True)
                self.assertEqual(value['source_files'], opted['source_files'])

    def test_legacy_quote_not_in_answer_stays_a_contract_failure(self):
        value = {'answer_id': 'synthetic-answer', 'version': 1,
                 'text': 'Voltage stability needs assessment.',
                 'citations': [{'quote': 'Not present in the answer.', 'evidence_ids': ['synthetic-e1']}],
                 'assumptions': [], 'missing_information': [], 'evidence_sufficient': True}
        with self.assertRaises(ContractError) as caught:
            parse_answer(json.dumps(value), inputs())
        self.assertIn('$.citations[0].quote', str(caught.exception))
