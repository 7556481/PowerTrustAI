"""Offline: actual saved inputs at adapter boundary; not semantic scores."""
import asyncio
import json
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from backend.config import ServiceConfig
from backend.serialization import wire
from services.claim_message_v1 import system,contract,VERSION
from services.claim_obligations import parse,DAILY_SYSTEM
from services.claim_extractor import ModelClaimExtractor
from services.answer_anchors import anchors
from services.structured_model import strict_json
from core.models import AnswerDraft
from model_adapter.contracts import ModelResponse,ModelSettings,ModelOutputError
from model_adapter.runtime import ModelBudget,model_scope
from evaluation import natural_review_seam_v1 as t


class Script:
    def __init__(self,texts):self.texts=iter(texts);self.requests=[]
    async def complete(self,r):
        self.requests.append(r)
        return ModelResponse(next(self.texts),r.model_id,finish_reason='stop')


class SeamTests(unittest.TestCase):
    def test_example_is_current_parser_valid_and_shapes_unambiguous(self):
        text=system();v=json.loads(contract().split('not a classification of this answer:\n')[1])
        a=AnswerDraft('fixture',1,'The supplied input states Q=30 MW.')
        v['claims'][0]['anchor_id']=anchors(a)[0]['anchor_id'];parse(v,a)
        self.assertNotIn('CURRENT V6',text);self.assertNotIn('EXACT {category,proposition}',text)
        self.assertNotIn('Full legal example:',text);self.assertEqual(text.count('Example is synthetic'),1)
        self.assertLess(len(text),len(DAILY_SYSTEM))
        for phrase in ('Each independently checkable assertion','Do not repair it while extracting',
                       'Do NOT turn endorsed X','Keep every actually asserted compound clause',
                       'Each component preserves the original answer'):
            self.assertIn(phrase,text)

    def test_no_semantic_field_fill_and_one_correction_same_contract(self):
        a=AnswerDraft('fixture',1,'Only under C, a device may operate.')
        v=dict(claims=[dict(anchor_id=anchors(a)[0]['anchor_id'],proposition=a.text,
            claim_type='technical_fact',assertion_role='conditional',semantic_qualifiers=['Only under C','may'],
            components=[dict(category='technical_fact',proposition=a.text,basis_target='technical_content',verification_obligation='technical_truth')])],non_claims=[])
        missing=deepcopy(v);missing.pop('non_claims')
        adapter=Script([json.dumps(missing),json.dumps(v)])
        async def run():
            b=ModelBudget(2)
            with model_scope(b):out=await ModelClaimExtractor(adapter,ModelSettings('synthetic-fixture'),protocol_version=7,daily_guidance=True,message_profile='unified_v1').extract(a)
            return out,b
        out,b=asyncio.run(run());self.assertEqual(out.claims[0].components[0].proposition,a.text)
        self.assertEqual(len(b.records),2);self.assertTrue(b.records[1].correction)
        for r in adapter.requests:self.assertEqual(r.messages[0].content,system())
        self.assertIn(contract(),json.loads(adapter.requests[1].messages[-1].content)['instruction'])
        self.assertEqual(b.records[0].validation_error['errors'][0]['constraint'],'required_field_missing')
        with self.assertRaises(ValueError):ServiceConfig(extraction_message_profile='silent_fill')

    @unittest.skipUnless((t.OLD/'summary.json').exists(),'Private historical archive unavailable')
    def test_all_real_natural_drafts_and_actual_correction_at_boundary(self):
        gs=t.generations();self.assertEqual(len(gs),3)
        messages=[t.load(p) for p in sorted((t.OLD/'messages').glob('*.json'))]
        for i in range(3):
            selected=[m for m in messages if m['task']==dict(line='B',case=i,variant='bound') and m['prompt_version'].startswith('atomic-claims')]
            texts=[t.load(t.OLD/'responses'/f"{m['sequence']:04d}.json")['text'] for m in selected]
            expected=parse(strict_json(texts[-1]),gs[i].answer)
            adapter=Script(texts)
            result=asyncio.run(ModelClaimExtractor(adapter,ModelSettings('synthetic-fixture'),protocol_version=7,daily_guidance=True,message_profile='unified_v1').extract(gs[i].answer))
            self.assertEqual(wire(result),wire(expected)) # Old outputs are not new predictions.
            for r in adapter.requests:
                p=json.loads(r.messages[1].content)
                self.assertEqual(p['ANSWER_ANCHORS'],list(anchors(gs[i].answer)))
                self.assertEqual(p['missing_information'],list(gs[i].answer.missing_information))
                self.assertEqual(p['answer_version'],gs[i].answer.version)
            self.assertEqual(len(adapter.requests),len(texts))

    def test_factory_full_revision_reextract_and_old_path(self):
        from tests.test_schema14_factory_flow import FactoryFlowTests
        case=FactoryFlowTests()
        def config(**kw):return ServiceConfig(**kw,extraction_message_profile='unified_v1')
        with patch('tests.test_schema14_factory_flow.ServiceConfig',side_effect=config):
            case.exercise(schema=13,revision=True,two=True)
            case.exercise(schema=13,objection=True)

    def test_shared_controller_real_seed_and_independent_quota_view(self):
        if not (t.OLD/'summary.json').exists():self.skipTest('Private archive unavailable')
        gs=t.generations();c=ServiceConfig();self.assertEqual(len(t.order()),12)
        for g in gs.values():
            charged=g.retrieval_records[-1]
            self.assertGreater(c.budget.max_model_calls-len(g.model_records),0)
            self.assertEqual(c.budget.max_retrieval_calls-charged.calls_used,11)
            self.assertGreater(c.budget.max_retrieval_chars_total-charged.cumulative_chars,0)
        self.assertEqual(t.variants(c,'before').fact_review_contract,'simple_bound_v1')
        self.assertEqual(t.variants(c,'seam').fact_review_contract,'simple_bound_v1')
        self.assertEqual(t.variants(c,'before').budget,t.variants(c,'seam').budget)

    def test_existing_full_batch_rehearsal_candidate_and_stop_paths(self):
        from tests.test_review_delivery_unblock_v1 import DeliveryTests
        from evaluation import review_delivery_unblock_v1 as old
        original=old.variants
        def variants(c,v):
            cfg=original(c,v)
            return replace(cfg,extraction_message_profile='unified_v1') if v=='bound' else cfg
        with patch.object(old,'variants',side_effect=variants):
            DeliveryTests().test_full_rehearsal_factory_same_draft_budget_and_response_storage_stop()


if __name__=='__main__':unittest.main()
