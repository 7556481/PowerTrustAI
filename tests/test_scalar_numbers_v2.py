"""Offline development regressions; not engineering validation."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
import unittest
from tools.scalar_numbers import parse_number, quantities
from tools.unit_conversion import UnitConversionTool,requests_for,validate_result,validate_claim_conversion,PAIRS
from tools.contracts import ToolRequest
from core.models import VerificationStatus

class ScalarNumberTests(unittest.TestCase):
    def result(self):
        tool=UnitConversionTool(version='scalar-si-conversion-v2')
        payload=requests_for((SimpleNamespace(proposition='230 kV = 230,000 V',text='',claim_id='c'),),version=tool.spec.version)[0]
        return asyncio.run(tool.execute(ToolRequest('call','task',tool.spec.name,'evidence_verification',payload,1)))

    def test_explicit_format(self):
        for raw in ('230000','230,000','230,000.0'):
            self.assertEqual(parse_number(raw)['value'],230000)
        for raw in ('23,00','230,00','230,000,0','230.000,0','1,234.5.6','+230','１２０'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_number(raw)

    def test_no_suffix_extraction(self):
        for raw in ('230,00 V','230,000,0 V','230.000,0 V'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):quantities(raw,PAIRS)
        parsed=quantities('230,000 V',PAIRS)[0]
        self.assertEqual(parsed['value'],230000)
        self.assertEqual('230,000 V'[parsed['start_offset']:parsed['end_offset']],parsed['raw'])

    def test_real_tool_truth_and_binding(self):
        result=self.result();validate_result(result)
        for raw in ('230000','230,000','230,000.0'):
            validate_claim_conversion('230 kV = '+raw+' V','c',result,VerificationStatus.SUPPORTED)
        validate_claim_conversion('230 kV = 230 V','c',result,VerificationStatus.CONTRADICTED)
        for prop in ('230 kV = 230 V','230 kV = 230,00 V','230 kV proves stability'):
            with self.subTest(prop=prop),self.assertRaises(ValueError):
                validate_claim_conversion(prop,'c',result,VerificationStatus.SUPPORTED)
        with self.assertRaises(ValueError):validate_claim_conversion('230 kV = 230000 V','wrong',result,VerificationStatus.SUPPORTED)

    def test_trace_tampering_and_category(self):
        result=self.result();payload={**result.payload,'numeric_trace':{**result.payload['numeric_trace'],'raw':'230,000'}}
        with self.assertRaises(ValueError):validate_result(replace(result,payload=payload))
        with self.assertRaises(ValueError):validate_claim_conversion('230 kV = 230000 Mvar','c',result,VerificationStatus.SUPPORTED)

    def test_legacy_still_rejects_grouped_relation(self):
        from tests.test_review_reliability import tool
        with self.assertRaises(ValueError):validate_claim_conversion('230 kV = 230,000 V','c',tool('c'),VerificationStatus.SUPPORTED)
