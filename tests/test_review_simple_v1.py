"""Synthetic behavior checks; none of these substitute for semantic model scores."""
import asyncio,json,unittest
from dataclasses import replace
from unittest.mock import patch
from tests.test_fact_rereview_v3 import inputs
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from services.review_simple_v1 import SimpleCatalog,PROMPT,SYSTEM
from core.models import VerificationStatus as V


def response(d):
    return {'judgments':[dict(status='supported' if t['allowed_basis_ids'] else 'insufficient_evidence',basis_ids=t['allowed_basis_ids'][:1],reason='Synthetic complete local proposition support judgment.',gap_answer_ids=[],conditions=dict(applicability='none',expression='not_applicable',instance='not_claimed',source_ids=[],answer_ids=[],reason='Synthetic explicit no extra condition, no expression obligation and no instance claim.'),inference='preserved',objection=None,repair=None,requires_authoritative_source=False) for t in d['targets']]}


class SimpleTests(unittest.TestCase):
    def exercise(self,mutate=None,inp=None,limit=8):
        seen=[];inp=inp or inputs(True)
        class Adapter:
            async def complete(self,r):
                d=json.loads(r.messages[1].content);v=response(d);seen.append((r,d))
                if mutate:mutate(v,d,r.correction)
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        budget=ModelBudget(limit)
        async def go():
            with model_scope(budget):return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13,review_contract='simple_v1').run(inp)
        return asyncio.run(go()),seen,budget

    def test_none_is_explicit_and_no_old_empty_quote_projection(self):
        out,seen,_=self.exercise();self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status,V.SUPPORTED)
        self.assertEqual(out.findings[0].component_reviews[0].review_projection_version,'simple-condition-projection-v1.1')
        self.assertEqual(seen[1][1]['review_object'],'original_citation')
        self.assertIn('CONTEXT ONLY',SYSTEM);self.assertNotIn('source_subject',SYSTEM)
        self.assertIn('json',SYSTEM.lower())

    def test_no_extra_condition_and_instance_data_missing_are_independent(self):
        def mutate(v,d,c):v['judgments'][0]['conditions']['instance']='missing'
        out,_,_=self.exercise(mutate)
        self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status,V.INSUFFICIENT_EVIDENCE)

    def test_request_rejection_stops_before_next_scope_no_correction(self):
        from model_adapter.contracts import ModelRequestError
        calls=[]
        class Rejected:
            async def complete(self,r):calls.append(r);raise ModelRequestError()
        async def go():
            with model_scope(ModelBudget(8)):
                return await ModelEvidenceVerificationAgent(Rejected(),ModelSettings('synthetic_fixture'),schema_version=13,review_contract='simple_v1').run(inputs(True))
        out=asyncio.run(go());self.assertEqual(len(calls),1);self.assertEqual(out.execution_issues[0].code,'MODEL_REQUEST_REJECTED')

    def test_three_dimensions_preservation_missing_and_instance(self):
        cases=[('present','preserved','not_claimed',V.SUPPORTED),('present','missing','not_claimed',V.INSUFFICIENT_EVIDENCE),('present','misattached','not_claimed',V.INSUFFICIENT_EVIDENCE),('present','extended','not_claimed',V.INSUFFICIENT_EVIDENCE),('present','preserved','missing',V.INSUFFICIENT_EVIDENCE),('present','preserved','uncertain',V.NOT_ASSESSABLE),('unknown','uncertain','not_claimed',V.NOT_ASSESSABLE),('none','missing','not_claimed',V.NOT_ASSESSABLE)]
        for ap,ex,inst,expect in cases:
            def mutate(v,d,c):
                for row,t in zip(v['judgments'],d['targets']):row['conditions'].update(applicability=ap,expression=ex,instance=inst,source_ids=[t['source_unit_ids'][0]],answer_ids=[t['answer_units'][0]['unit_id']])
            out,_,_=self.exercise(mutate);self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status,expect)
            self.assertEqual(out.findings[0].component_reviews[0].raw_support_status,'supported')

    def test_no_empty_arrays_waive_unknown_or_unbound_preservation(self):
        for condition in ({'applicability':'unknown','expression':'uncertain'},{'applicability':'present','expression':'preserved'}):
            def mutate(v,d,c):v['judgments'][0]['conditions'].update(condition)
            out,_,_=self.exercise(mutate);self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status,V.NOT_ASSESSABLE)

    def test_ids_not_quotes_partial_peers_budget_and_correction(self):
        for kind in ('source','answer','identity','fields'):
            def mutate(v,d,c):
                if d['review_object']!='independent_fact':return
                row=v['judgments'][0]
                if kind=='source':row['conditions']['source_ids']=['ANS:F0C0:0']
                elif kind=='answer':row['gap_answer_ids']=['ANS:F1C0:0']
                elif kind=='identity':row['target_id']='F0C0'
                else:row['conditions'].pop('instance')
            out,seen,budget=self.exercise(mutate,inputs(False,True),limit=2)
            self.assertTrue(out.execution_issues);self.assertEqual(out.findings[1].status,V.SUPPORTED);self.assertEqual(budget.used,2)
            self.assertIn('SAME nine-field',seen[1][0].messages[-1].content)

    def test_missing_gap_inference_and_objection_remain_adverse(self):
        for key,value in [('gap_answer_ids',True),('inference','unsupported'),('objection',dict(kind='classification',reason='Synthetic legitimate obligation objection'))]:
            def mutate(v,d,c):v['judgments'][0][key]=[d['targets'][0]['answer_units'][0]['unit_id']] if value is True else value
            out,_,_=self.exercise(mutate);self.assertFalse(out.execution_issues);self.assertNotEqual(out.findings[0].status,V.SUPPORTED)

    def test_literal_pdf_bytes_repeated_terms_and_scope_isolation(self):
        inp=inputs(True,True);e=replace(inp.seed_evidence[0],text='N-1 c ontinuous\ncontrol; N-2 c ontinuous\ncontrol.\n\nCross sentence condition.');inp=replace(inp,seed_evidence=(e,),original_evidence=tuple(replace(x,text=e.text) for x in inp.original_evidence))
        cat=SimpleCatalog(inp)
        for unit in cat.source_units.values():self.assertEqual(unit['text'],e.text);self.assertEqual(unit['source_sha256'],__import__('hashlib').sha256(e.text.encode()).hexdigest())
        for t in cat.targets.values():
            for uid in t['answer_unit_ids']:
                u=cat.answer_units[uid];self.assertEqual(inp.answer.text[u['start_offset']:u['end_offset']],u['text'])
        self.assertTrue(set(cat.source_units).isdisjoint(cat.answer_units))
        t=cat.targets['R0'];self.assertTrue(all(cat.bases[u['basis_id']]['scope_index']==t['scope_index'] for u in cat.payload(['R0'])['source_units']))

    def test_cancel_timeout_keep_partial_and_single_correction(self):
        count=0
        class Cancel:
            async def complete(self,r):
                nonlocal count
                count+=1
                if count>1:raise asyncio.CancelledError()
                return ModelResponse(json.dumps(response(json.loads(r.messages[1].content))),r.model_id,finish_reason='stop')
        async def go():
            with model_scope(ModelBudget(4)):
                try:await ModelEvidenceVerificationAgent(Cancel(),ModelSettings('synthetic_fixture'),schema_version=13,review_contract='simple_v1').run(inputs(True))
                except asyncio.CancelledError as e:return e.partial_output
        self.assertEqual(asyncio.run(go()).findings[0].status,V.SUPPORTED)
        class Slow:
            async def complete(self,r):await asyncio.sleep(.05)
        async def slow():
            with model_scope(ModelBudget(4)):return await ModelEvidenceVerificationAgent(Slow(),ModelSettings('synthetic_fixture',timeout_seconds=.001),schema_version=13,review_contract='simple_v1').run(inputs(False))
        self.assertTrue(asyncio.run(slow()).execution_issues)


class FactoryTests(unittest.TestCase):
    def test_service_factory_graph_domain_policy_store_api_revision_and_history(self):
        import tests.test_schema14_factory_flow as f
        original=f.SyntheticProvider.complete;config=f.ServiceConfig
        async def complete(provider,r):
            if r.prompt_version==PROMPT:
                provider.requests.append(r);d=json.loads(r.messages[1].content);v=response(d)
                for row,t in zip(v['judgments'],d['targets']):
                    if provider.revision and '9 kV' in t['proposition']:row['status']='contradicted';row['repair']=dict(basis_id=row['basis_ids'][0],replacement=f.GOOD)
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
            return await original(provider,r)
        with patch.object(f,'ServiceConfig',side_effect=lambda **kw:config(**kw,fact_review_contract='simple_v1',execution_path='langgraph_v1')),patch.object(f.SyntheticProvider,'complete',complete):
            for revise in (False,True):
                r,_,_=f.FactoryFlowTests().exercise(schema=13,existing=revise,revision=revise,concept=True)
                self.assertTrue(r['execution']['required_stages_complete']);self.assertEqual(len(r['answer']['versions']),2 if revise else 1)
        self.assertEqual(config().fact_review_contract,'production')
        with self.assertRaises(ValueError):config(fact_review_contract='simple_v1',verification_schema=14)
