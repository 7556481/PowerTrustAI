import asyncio,json,unittest
from copy import deepcopy
from dataclasses import replace
from tests.test_fact_rereview_v3 import inputs
from agents.fact_flow_v1 import FactFlowAgent
from services.fact_flow_protocol_v1 import Catalog
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from core.models import VerificationStatus as V

def response(payload):
    rows=[]
    for t in payload['targets']:
        ids=t['allowed_basis_ids'][:1]
        rows.append(dict(target_id=t['target_id'],status='supported' if ids else 'insufficient_evidence',
            basis_ids=ids,reason='Synthetic full proposition review.',conditions=[],repair=None,
            requires_authoritative_source=False,object_kind='ordinary' if t['kind']=='citation' else 'external_fact',
            classification_objection=None,fidelity='faithful',fidelity_reason='Literal answer preserved.',
            dependencies=[] if t['kind']=='citation' else ids,comparison=None))
    return {'judgments':rows}

class FlowTests(unittest.TestCase):
    def exercise(self,mutate=None,inp=None,limit=8):
        seen=[];inp=inp or inputs(True)
        class Adapter:
            async def complete(self,r):
                d=json.loads(r.messages[1].content);v=response(d);seen.append((r,d))
                if mutate:mutate(v,d,r.correction)
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        async def go():
            with model_scope(ModelBudget(limit)):
                return await FactFlowAgent(Adapter(),ModelSettings('synthetic_fixture')).run(inp)
        return asyncio.run(go()),seen
    def test_graph_and_actual_messages(self):
        out,seen=self.exercise()
        self.assertFalse(out.execution_issues)
        self.assertEqual(out.findings[0].status,V.SUPPORTED)
        self.assertEqual(len(out.flow_trace),4)
        self.assertEqual(len(seen),2)
        self.assertIn('classification_objection',seen[0][0].messages[0].content)
        self.assertEqual(seen[0][1]['contract'],'fact-internal-flow-v1')
        self.assertTrue(seen[0][1]['basis_catalog'])
    def test_classification_separate_from_fidelity(self):
        def mutate(v,d,c):
            if d['targets'][0]['kind']=='fact':v['judgments'][0]['classification_objection']='Wrong frozen object category.'
        out,_=self.exercise(mutate)
        self.assertFalse(out.execution_issues)
        self.assertEqual(out.findings[0].component_reviews[0].fidelity_status,'faithful')
        self.assertEqual(out.findings[0].status,V.NOT_ASSESSABLE)
        self.assertTrue(out.object_reviews[0]['classification_objection'])
    def test_fidelity_not_classification(self):
        def mutate(v,d,c):
            if d['targets'][0]['kind']=='fact':v['judgments'][0]['fidelity']='disputed'
        out,_=self.exercise(mutate)
        self.assertFalse(out.execution_issues)
        self.assertIsNone(out.object_reviews[0]['classification_objection'])
        self.assertEqual(out.findings[0].status,V.NOT_ASSESSABLE)
    def test_illegal_id_peer_retention_finite_correction(self):
        def mutate(v,d,c):v['judgments'][0]['basis_ids']=['illegal']
        out,seen=self.exercise(mutate,inputs(False,True))
        self.assertTrue(out.execution_issues)
        self.assertEqual(len(seen),2)
        self.assertEqual(out.findings[1].status,V.SUPPORTED)
    def test_original_citation_isolation(self):
        def mutate(v,d,c):
            if d['targets'][0]['kind']=='citation':v['judgments'][0]['basis_ids']=['S0B0']
        out,_=self.exercise(mutate)
        self.assertTrue(out.execution_issues)
        self.assertEqual(out.findings[0].status,V.SUPPORTED)
    def test_budget(self):
        out,seen=self.exercise(limit=1)
        self.assertTrue(out.execution_issues)
        self.assertEqual(len(seen),1)

class FactoryFlowTests(unittest.TestCase):
    def test_actual_factory_worker_store_api_both_modes(self):
        from unittest.mock import patch
        import tests.test_schema14_factory_flow as fixture
        original=fixture.SyntheticProvider.complete
        config=fixture.ServiceConfig
        async def complete(provider,r):
            if r.prompt_version.startswith('evidence-verification-v9.30'):
                provider.requests.append(r);d=json.loads(r.messages[1].content);provider.payloads.append(d)
                return ModelResponse(json.dumps(response(d)),r.model_id,finish_reason='stop')
            return await original(provider,r)
        def candidate_config(**kwargs):
            kwargs.update(verification_schema=13,fact_internal_flow='langgraph_candidate_v1',execution_path='langgraph_v1')
            return config(**kwargs)
        for existing in (False,True):
            with self.subTest(existing=existing),patch.object(fixture,'ServiceConfig',candidate_config),patch.object(fixture.SyntheticProvider,'complete',complete):
                result,provider,events=fixture.FactoryFlowTests().exercise(schema=13,existing=existing,two=True,premises=True)
                self.assertEqual(result['fact_internal_flow']['protocol'],'fact-internal-flow-v1')
                self.assertEqual(len(result['fact_internal_flow']['trace']),4)
                self.assertTrue(result['fact_internal_flow']['object_reviews'])
                fact_payload=next(d for d in provider.payloads if d.get('contract')=='fact-internal-flow-v1')
                self.assertTrue(any(b['basis_type']=='task_premise_reference' for b in fact_payload['basis_catalog']))
                self.assertEqual(result['configuration']['fact_internal_flow'],'langgraph_candidate_v1')
                self.assertEqual(result['configuration']['prompts']['verification'],'evidence-verification-v9.30-fact-internal-flow-v1-dev')
                self.assertEqual(result['configuration']['contracts']['verification'],'fact-internal-flow-v1')

def case_response(case,payload):
    value=response(payload)
    bases={b['basis_id']:b for b in payload['basis_catalog']}
    for row,t in zip(value['judgments'],payload['targets']):
        if t['kind']=='citation':continue
        spec=case['components'][t['component_index']]
        row.update(object_kind=spec[1],status=spec[2],basis_ids=[],dependencies=[])
        if spec[2] in ('supported','contradicted'):
            if spec[1]!='premise_restatement':row['basis_ids'].append(next(b for b in t['allowed_basis_ids'] if bases[b]['basis_type']=='text_excerpt'))
            for n in spec[3]:row['basis_ids'].append('P'+str(n))
            row['dependencies']=list(row['basis_ids'])
        if case.get('diagnostic'):row['classification_objection']='Extracted input coverage misclassifies a literal literature rule.'
        if spec[1]=='numeric_comparison':row['comparison']=dict(deepcopy(case['comparison']),left_basis_id='P0',right_basis_id=next(b for b in row['basis_ids'] if b!='P0'))
    return value

class SemanticBoundaryTests(unittest.TestCase):
    exercise=FlowTests.exercise
    def test_all_fixed_synthetic_topics(self):
        from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
        for case in CASES:
            def mutate(v,d,c):v.update(case_response(case,d))
            with self.subTest(case=case['id']):
                out,seen=self.exercise(mutate,fixed_input(case))
                self.assertFalse(out.execution_issues)
                for part,spec in zip(out.findings[0].component_reviews,case['components']):
                    self.assertEqual(part.status.value,'not_assessable' if case.get('diagnostic') else spec[2])
                if case['id']=='F03':
                    self.assertEqual(out.object_reviews[0]['dependencies'],['S0B0','P0'])
                    self.assertNotIn('P1',out.object_reviews[0]['dependencies'])
                if case['id']=='F04':self.assertTrue(out.object_reviews[0]['scalar_result'])
    def test_missing_rule_is_contract_failure_not_silent_pass(self):
        from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
        case=CASES[2]
        def mutate(v,d,c):
            v.update(case_response(case,d));v['judgments'][0].update(basis_ids=['P0'],dependencies=['P0'])
        out,seen=self.exercise(mutate,fixed_input(case))
        self.assertTrue(out.execution_issues);self.assertEqual(len(seen),2)
    def test_wrong_scalar_relation_and_missing_operand_source(self):
        from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
        for change in ('operator','source'):
            def mutate(v,d,c):
                v.update(case_response(CASES[3],d));row=v['judgments'][0]
                if change=='operator':row['comparison']['operator']='<'
                else:row['comparison']['right_basis_id']='P1'
            out,_=self.exercise(mutate,fixed_input(CASES[3]));self.assertTrue(out.execution_issues)
    def test_cancel_no_graph_resend(self):
        count=[]
        class Adapter:
            async def complete(self,r):count.append(r);raise asyncio.CancelledError()
        async def go():
            with model_scope(ModelBudget(8)):
                await FactFlowAgent(Adapter(),ModelSettings('synthetic_fixture')).run(inputs(False))
        with self.assertRaises(asyncio.CancelledError):asyncio.run(go())
        self.assertEqual(len(count),1)
    def test_timeout_no_graph_retry(self):
        count=[]
        class Adapter:
            async def complete(self,r):count.append(r);raise asyncio.TimeoutError()
        async def go():
            with model_scope(ModelBudget(8)):
                return await FactFlowAgent(Adapter(),ModelSettings('synthetic_fixture')).run(inputs(False))
        out=asyncio.run(go());self.assertTrue(out.execution_issues);self.assertEqual(len(count),1)

class RevisionAndToolsTests(unittest.TestCase):
    def test_revision_reextract_full_review_and_store_versions(self):
        from unittest.mock import patch
        import tests.test_schema14_factory_flow as fixture
        original=fixture.SyntheticProvider.complete;config=fixture.ServiceConfig
        async def complete(provider,r):
            if r.prompt_version.startswith('evidence-verification-v9.30'):
                provider.requests.append(r);d=json.loads(r.messages[1].content);provider.payloads.append(d);v=response(d)
                for row,t in zip(v['judgments'],d['targets']):
                    if fixture.BAD in t['proposition']:
                        row['status']='contradicted'
                        row['repair']={'basis_id':row['basis_ids'][0],'replacement':fixture.GOOD}
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
            return await original(provider,r)
        def candidate_config(**kwargs):
            kwargs.update(verification_schema=13,fact_internal_flow='langgraph_candidate_v1',execution_path='langgraph_v1');return config(**kwargs)
        with patch.object(fixture,'ServiceConfig',candidate_config),patch.object(fixture.SyntheticProvider,'complete',complete):
            result,provider,events=fixture.FactoryFlowTests().exercise(schema=13,existing=True,revision=True)
        self.assertEqual(len(result['answer']['versions']),2)
        self.assertEqual(len(result['review_rounds']),2)
        self.assertEqual(result['answer']['final']['text'],fixture.GOOD)
        self.assertEqual(sum(r.prompt_version.startswith('atomic-claims') for r in provider.requests),2)
        seen=[d for d in provider.payloads if d.get('contract')=='fact-internal-flow-v1']
        self.assertEqual({d['answer_version'] for d in seen},{1,2})
    def test_scalar_tool_failure_is_not_a_legal_basis(self):
        from tools.contracts import ToolResult
        from core.models import ExecutionStatus
        from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
        inp=fixed_input(CASES[-1]);cat=Catalog(inp)
        self.assertFalse(any(b.startswith('CALC') for b in cat.bases))
        self.assertEqual(cat.payload(cat.targets)['available_tools'],[])
        failed=ToolResult('failed','call','unit_conversion','scalar-si-conversion-v2',ExecutionStatus.FAILED,{})
        cat=Catalog(replace(inp,tool_results=(failed,)))
        self.assertFalse(any(b.startswith('CALC') for b in cat.bases))
        # Failed results never enter the catalog, even when delivered as diagnostics.
