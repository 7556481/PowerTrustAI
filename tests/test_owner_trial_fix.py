"""Different-topic synthetic regression; strict contracts and task constraints."""
import unittest,json
from types import SimpleNamespace
from services.task_requirements import prohibited_spans,INSTRUCTION
from services.review_isolation import WireIsolation,PartialReviewError
from core.validation import ContractError
from services.validation_diagnostics import ErrorCollector
from backend.presentation import explain
from services.bounded_repair import GAP_MARKER
from rag.topic_lanes import plan

class TrialFixTests(unittest.TestCase):
    def test_prohibition_is_constraint_not_positive_duty_multiple_topics(self):
        for question in ('解释电池效率，不要声称任何情况下无损耗。','解释保护范围，请勿说所有装置都可靠。'):
            spans=prohibited_spans(question);self.assertEqual(len(spans),1)
            self.assertEqual(spans[0]['kind'],'negative_output_constraint')
            self.assertNotIn('无损耗',str(plan(question)))
        self.assertIn('DOES assert',INSTRUCTION)
        self.assertEqual(prohibited_spans('所有装置都可靠。'),[])

    def test_strict_extra_source_fields_rejected_legal_sibling_kept(self):
        baseline={'rows':[{'id':0,'value':'pending'},{'id':1,'value':'pending'}]}
        def strict(value):
            ec=ErrorCollector('synthetic')
            for i,row in enumerate(value['rows']):ec.fields(row,{'id','value'},set(),f'$.rows[{i}]')
            ec.finish();return value
        iso=WireIsolation(baseline,strict,{'rows':'id'},lambda out,missing,errors:out)
        with self.assertRaises(PartialReviewError) as e:iso.parse({'rows':[{'id':0,'value':'legal'},{'id':1,'value':'bad','source_condition':'forbidden'}]})
        self.assertEqual(e.exception.partial_output['rows'][0]['value'],'legal')
        self.assertEqual(e.exception.partial_output['rows'][1]['value'],'pending')

    def test_scope_notes_not_rendered_as_required_gap(self):
        finding={'category':'analysis_scope','rationale':'synthetic'+GAP_MARKER+json.dumps([{'index':0,'applicability':'scope_note','reason':'unrequested guarantee'},{'index':1,'applicability':'required','reason':'needed condition'}])}
        result={'execution':{'status':'finished','execution_issues':[]},'findings':{'domain':[finding]},'answer':{'versions':[]},'decision':{'kind':'needs_information'}}
        output=explain(result)
        self.assertEqual(output['scope_note_indexes'],[0])
        self.assertEqual(output['missing_information_review'][1]['applicability'],'required')
