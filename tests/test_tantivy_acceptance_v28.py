import unittest
from dataclasses import replace
from unittest.mock import patch
from core.models import Evidence,EvidenceProvenance
from evaluation.tantivy_acceptance_v28 import make_span,verify_span,select_span,CandidateRetriever
class SpanTests(unittest.TestCase):
 def fixture(self,text):return Evidence('e-old','doc','v','chars[0:1000)',text,'industry_corpus_unverified',provenance=EvidenceProvenance('doc','v','f'*64,'fragment','k',100,100+len(text),5,20,text_basis='dataset_record_original_text'))
 def test_contiguous_paragraph_context_and_original_binding(self):
  text='Unrelated first.\n\nBackground follows.\n\nAnother background.\n\nElectric alpha works.\n\nFurther background.\n\nLast unrelated.';parent=self.fixture(text)
  with patch('evaluation.tantivy_acceptance_v28.query_tokens',return_value={'alpha'}):excerpt,row=select_span('alpha',parent)
  self.assertLess(len(excerpt.text),len(text));self.assertIn('Another background.',excerpt.text);self.assertIn('Further background.',excerpt.text);self.assertEqual(verify_span(excerpt,parent),excerpt)
  for invalid in (replace(excerpt,text=excerpt.text+'x'),replace(excerpt,source_version='changed'),replace(excerpt,provenance=replace(excerpt.provenance,start_offset=0))):
   with self.assertRaises(ValueError):verify_span(invalid,parent)
 def test_scope_numeric_pdf_and_unknown_boundaries_remain_whole(self):
  for text in ('If operation is allowed, except local conditions.','Never omit the exception.','A device has a rating of 5 kV.','无功功率的定义及例外。'):
   p=self.fixture(text);self.assertEqual(select_span('device',p)[0],p)
  p=self.fixture('Alpha.\n\nBeta.');p=replace(p,provenance=replace(p.provenance,text_basis='pdf_extracted_page_text'));self.assertEqual(select_span('alpha',p)[0],p)
 def test_normal_factory_source_bound_revision_full_reaudit_and_store(self):
  from backend.managed import OverlapFactory
  from tests import test_schema14_factory_flow as fixture
  class Factory(OverlapFactory):
   def create(self,*args,**kwargs):
    bundle=super().create(*args,**kwargs)
    if bundle.harness.retriever is not None:bundle.harness.retriever=CandidateRetriever(bundle.harness.retriever)
    return bundle
  with patch('tests.test_schema14_factory_flow.ComponentFactory',Factory):result,provider,trace=fixture.FactoryFlowTests().exercise(schema=13,subject=True)
  self.assertTrue(result['execution']['required_stages_complete']);self.assertEqual(len(result['answer']['versions']),2);self.assertEqual(len(result['review_rounds']),2)
if __name__=='__main__':unittest.main()
