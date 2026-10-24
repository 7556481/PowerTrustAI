"""Synthetic program-boundary checks, never semantic model scores."""
import asyncio,json,unittest
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
from tests.test_fact_rereview_v3 import inputs
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from services.review_scope_v2 import ScopeCatalog,PROMPT,SYSTEM
from core.models import VerificationStatus as V


def response(d):
    return {'judgments':[dict(status='supported' if t['allowed_basis_ids'] else 'insufficient_evidence',basis_ids=t['allowed_basis_ids'][:1],reason='Synthetic selected basis supports the full local target.',gaps=[],conditions=[],inference='preserved',objection=None,repair=None,requires_authoritative_source=False) for t in d['targets']]}


class ScopeTests(unittest.TestCase):
    def exercise(self,mutate=None,inp=None,budget_limit=8):
        seen=[];inp=inp or inputs(True)
        class Adapter:
            async def complete(self,r):
                d=json.loads(r.messages[1].content);v=response(d);seen.append((r,d))
                if mutate:mutate(v,d,r.correction)
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        budget=ModelBudget(budget_limit)
        async def go():
            with model_scope(budget):return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13,review_contract='scope_v2').run(inp)
        return asyncio.run(go()),seen,budget

    def test_default_and_ordered_contract_boundaries(self):
        out,seen,_=self.exercise();self.assertFalse(out.execution_issues)
        self.assertEqual(out.findings[0].status,V.SUPPORTED)
        for r,d in seen:
            self.assertEqual(r.prompt_version,PROMPT)
            self.assertIn('CONTEXT ONLY',r.messages[0].content)
            self.assertNotIn('target_id',response(d)['judgments'][0])
        self.assertEqual(seen[1][1]['review_object'],'original_citation')

    def test_gap_cannot_describe_other_unit_or_full_question(self):
        def mutate(v,d,c):v['judgments'][0]['gaps']=['unanswered unrelated subquestion']
        out,seen,_=self.exercise(mutate);self.assertTrue(out.execution_issues)
        self.assertEqual(sum(r.correction for r,d in seen),1)
        self.assertIn('SAME nine-field',seen[1][0].messages[-1].content)

    def test_unsupported_literal_gap_not_auto_supported(self):
        def mutate(v,d,c):v['judgments'][0]['gaps']=[d['targets'][0]['evaluated_text']]
        out,_,_=self.exercise(mutate);self.assertFalse(out.execution_issues)
        self.assertEqual(out.findings[0].component_reviews[0].raw_support_status,'supported')
        self.assertEqual(out.findings[0].status,V.INSUFFICIENT_EVIDENCE)

    def test_illegal_fields_ids_count_partial_and_budget(self):
        for kind in ('identity','field','basis','count'):
            def mutate(v,d,c):
                if d['review_object']!='independent_fact':return
                if kind=='identity':v['judgments'][0]['target_id']='invented'
                elif kind=='field':v['judgments'][0]['source_kind']='invented'
                elif kind=='basis':v['judgments'][0]['basis_ids']=['S1B0']
                else:v['judgments'].pop()
            out,seen,budget=self.exercise(mutate,inputs(False,True),budget_limit=2)
            self.assertTrue(out.execution_issues);self.assertEqual(budget.used,2)
            if kind!='count':self.assertEqual(out.findings[1].status,V.SUPPORTED)

    def test_conditions_preserved_missing_misattached_extended_uncertain(self):
        inp=inputs(False)
        for relationship,expected in [('preserved',V.SUPPORTED),('missing',V.INSUFFICIENT_EVIDENCE),('misattached',V.INSUFFICIENT_EVIDENCE),('extended',V.INSUFFICIENT_EVIDENCE),('uncertain',V.NOT_ASSESSABLE)]:
            def mutate(v,d,c):
                t=d['targets'][0];r=v['judgments'][0];b=r['basis_ids'][0];source=next(x for x in d['basis_catalog'] if x['basis_id']==b)['text'];answer=t['answer_text']
                r['conditions']=[dict(basis_id=b,required=True,source_subject=source,source_condition=source,source_conclusion=source,answer_subject=answer,answer_condition=answer if relationship!='missing' else '',answer_conclusion=answer,relationship=relationship,reason='Synthetic explicit object/condition/conclusion relation')]
            out,_,_=self.exercise(mutate,inp)
            self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status,expected)

    def test_condition_cannot_be_borrowed_from_neighbor_or_other_source(self):
        def mutate(v,d,c):
            r=v['judgments'][0];r['conditions']=[dict(basis_id=r['basis_ids'][0],required=True,source_subject='invented source',source_condition='',source_conclusion='invented source',answer_subject='neighbor text',answer_condition='',answer_conclusion='neighbor text',relationship='preserved',reason='Invalid local literal bindings')]
        out,_,_=self.exercise(mutate);self.assertTrue(out.execution_issues)

    def test_objection_and_uncertain_inference_keep_raw_and_require_review(self):
        def mutate(v,d,c):v['judgments'][0]['objection']=dict(kind='fidelity',reason='Synthetic extraction lost the answer condition')
        out,_,_=self.exercise(mutate);self.assertFalse(out.execution_issues)
        cr=out.findings[0].component_reviews[0];self.assertEqual(cr.raw_support_status,'supported');self.assertEqual(cr.status,V.NOT_ASSESSABLE)

    def test_cancel_and_timeout_partial_lifecycle(self):
        inp=inputs(True);count=0
        class Cancel:
            async def complete(self,r):
                nonlocal count
                count+=1
                if count>1:raise asyncio.CancelledError()
                return ModelResponse(json.dumps(response(json.loads(r.messages[1].content))),r.model_id,finish_reason='stop')
        async def go():
            with model_scope(ModelBudget(4)):
                try:await ModelEvidenceVerificationAgent(Cancel(),ModelSettings('synthetic_fixture'),schema_version=13,review_contract='scope_v2').run(inp)
                except asyncio.CancelledError as e:return e.partial_output
        out=asyncio.run(go());self.assertEqual(out.findings[0].status,V.SUPPORTED)
        class Slow:
            async def complete(self,r):await asyncio.sleep(.05)
        async def timeout():
            with model_scope(ModelBudget(4)):return await ModelEvidenceVerificationAgent(Slow(),ModelSettings('synthetic_fixture',timeout_seconds=.001),schema_version=13,review_contract='scope_v2').run(inputs(False))
        self.assertTrue(asyncio.run(timeout()).execution_issues)


class FactoryTests(unittest.TestCase):
    def test_actual_factory_graph_api_store_revision_and_failure(self):
        from harness.graph_runtime_v1 import validate_versions,build_graph
        validate_versions();build_graph()
        import tests.test_schema14_factory_flow as f
        original=f.SyntheticProvider.complete;config=f.ServiceConfig
        async def complete(provider,r):
            if r.prompt_version==PROMPT:
                provider.requests.append(r);d=json.loads(r.messages[1].content);v=response(d)
                for row,t in zip(v['judgments'],d['targets']):
                    if provider.revision and '9 kV' in t['proposition']:
                        row['status']='contradicted';row['repair']=dict(basis_id=row['basis_ids'][0],replacement=f.GOOD)
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
            return await original(provider,r)
        with patch.object(f,'ServiceConfig',side_effect=lambda **kw:config(**kw,fact_review_contract='scope_v2',execution_path='langgraph_v1')),patch.object(f.SyntheticProvider,'complete',complete):
            for revise in (False,True):
                r,_,_=f.FactoryFlowTests().exercise(schema=13,existing=revise,revision=revise,concept=True)
                self.assertTrue(r['execution']['required_stages_complete'])
                self.assertEqual(len(r['answer']['versions']),2 if revise else 1)
        self.assertEqual(config().fact_review_contract,'production')
        with self.assertRaises(ValueError):config(fact_review_contract='scope_v2',verification_schema=14)
