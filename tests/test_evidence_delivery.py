"""Delivery plumbing tests; synthetic fixtures, no semantic quality labels/API."""
import asyncio
import importlib.util
from pathlib import Path
import tempfile
import unittest

from core.validation import InputError
from evaluation.evidence_delivery_trial import FrozenExtraction, review_worst, settings_for
from harness.retrieval import validate_settings
from rag.context import read_adjacent_context
from rag.contracts import ContextOptions
from rag.storage import KnowledgeStore, SourceMetadata
from tests.pdf_fixtures import make_pdf


class DeliveryTests(unittest.TestCase):
    def test_live_components_can_be_constructed_without_credentials(self):
        from agents.generation import EvidenceGenerationAgent
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from agents.power_domain_review import ModelPowerDomainReviewAgent
        from agents.revision import ModelRevisionAgent
        from model_adapter.contracts import ModelSettings
        settings=ModelSettings('synthetic-model')
        adapter=object()
        self.assertEqual(EvidenceGenerationAgent(adapter,settings,schema_version=3).schema_version,3)
        ModelEvidenceVerificationAgent(adapter,settings,schema_version=8)
        ModelPowerDomainReviewAgent(adapter,settings,protocol_version=2)
        ModelRevisionAgent(adapter,settings,protocol_version=2)

    def test_unknown_priority_rejected_before_execution(self):
        with self.assertRaises(InputError):
            validate_settings(settings_for('invented'))

    def test_frozen_extraction_rejects_other_answer(self):
        service=FrozenExtraction('answer-v1', ('extracted-real',))
        self.assertEqual(asyncio.run(service.extract('answer-v1')), ('extracted-real',))
        with self.assertRaises(ValueError):
            asyncio.run(service.extract('answer-v2'))

    def test_worst_budget_counts_corrections_and_shared_extraction(self):
        class Answer:
            citations=(1,2)
        self.assertEqual(review_worst(Answer()),10)
        self.assertEqual(review_worst(Answer(),True),8)
        Answer.citations=(1,2,3,4)
        self.assertEqual(review_worst(Answer()),14)
        self.assertEqual(6*(2+10+8+2*2+2*14),312)

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'optional pypdf absent')
    def test_priority_changes_budget_selection_not_core_or_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic_fixture.pdf'
            path.write_bytes(make_pdf(['previous condition', 'core condition', 'next condition']))
            with KnowledgeStore(Path(tmp)/'index.sqlite3') as store:
                old=store.ingest(path,'synthetic_fixture',SourceMetadata(source_type='synthetic_fixture'))
                new=store.derive_pdf('synthetic_fixture',old.knowledge_version,max_chars=200)
                roots=[store.evidence(r['fragment_id'],new.knowledge_version) for r in store.rows(new.knowledge_version)]
                core=next(e for e in roots if e.provenance.file_page==2)
                baseline=read_adjacent_context(store,(core,),new.knowledge_version,ContextOptions(200,1,1,True))
                revised=read_adjacent_context(store,(core,),new.knowledge_version,ContextOptions(200,1,1,True,'cross_page_next_first'))
                self.assertEqual(baseline.items[0].evidence.provenance.file_page,1)
                self.assertEqual(revised.items[0].evidence.provenance.file_page,3)
                self.assertTrue(revised.omitted)
                self.assertEqual(revised.char_count,len(revised.items[0].evidence.text))
                self.assertEqual(store.verify_evidence(core),core)
                self.assertEqual(store.verify_evidence(revised.items[0].evidence),revised.items[0].evidence)
                no_cross=read_adjacent_context(store,(core,),new.knowledge_version,ContextOptions(200,1,1,False,'cross_page_next_first'))
                self.assertFalse(no_cross.items)
