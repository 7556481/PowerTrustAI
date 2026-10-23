import asyncio,json,unittest
from copy import deepcopy
from services.fact_flow_protocol_v2 import Catalog,create_agent,VERSION,PROMPT,FIELDS,response_schema
from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
from tests.test_fact_flow_v1 import case_response,response
from tests.test_fact_rereview_v3 import inputs
from model_adapter.contracts import ModelResponse,ModelSettings
from model_adapter.runtime import ModelBudget,model_scope
from core.validation import ContractError

class ContractTests(unittest.TestCase):
    def run_case(self,case=0,mutate=None,limit=4,inp=None):
        seen=[];given=inp or fixed_input(CASES[case])
        class Adapter:
            async def complete(self,r):
                d=json.loads(r.messages[1].content);seen.append(r)
                v=case_response(CASES[case],d) if inp is None else response(d)
                if mutate:mutate(v,d,r.correction)
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        async def go():
            with model_scope(ModelBudget(limit)):
                return await create_agent(Adapter(),ModelSettings('synthetic_fixture')).run(given)
        return asyncio.run(go()),seen

    def test_all_eight_and_protocol_identity(self):
        for i in range(8):
            with self.subTest(i=i):
                out,seen=self.run_case(i)
                self.assertFalse(out.execution_issues)
                self.assertEqual(out.flow_protocol,VERSION)
                self.assertEqual(out.prompt_version,PROMPT)
                self.assertEqual(len(seen),1)
                expected=['not_assessable' if CASES[i].get('diagnostic') else c[2] for c in CASES[i]['components']]
                self.assertEqual([c.status.value for c in out.findings[0].component_reviews],expected)
                self.assertEqual(out.flow_trace[0]['protocol'],VERSION)
                self.assertTrue(all(r['contract']==VERSION for r in out.object_reviews))

    def test_actual_initial_and_correction_have_identical_complete_schema(self):
        def mutate(v,d,c):
            if not c:v['judgments'][0].pop('repair')
        out,seen=self.run_case(2,mutate)
        self.assertFalse(out.execution_issues);self.assertEqual(len(seen),2)
        initial=json.loads(seen[0].messages[1].content)
        correction=json.loads(seen[1].messages[-1].content)
        self.assertEqual(initial['response_schema'],response_schema())
        self.assertEqual(correction['program_scope_guidance']['response_schema'],response_schema())
        self.assertEqual(set(initial['response_schema']['required_judgment_fields']),set(FIELDS))
        self.assertNotIn('conditions,objection,repair',seen[0].messages[0].content)
        self.assertNotIn('never copy text',correction['instruction'])
        self.assertIn('literal text is REQUIRED',correction['instruction'])
        self.assertTrue(initial['basis_catalog'])
        self.assertEqual(len(out.model_records),2)

    def test_missing_null_and_old_field_rejected(self):
        for change in ('repair','comparison','classification_objection','old'):
            def mutate(v,d,c):
                if change=='old':v['judgments'][0]['objection']=None
                else:v['judgments'][0].pop(change)
            out,seen=self.run_case(2,mutate)
            self.assertTrue(out.execution_issues);self.assertEqual(len(seen),2)

    def test_preservation_conflict_not_repaired_and_peer_retained(self):
        def mutate(v,d,c):
            v['judgments'][0]['conditions']=[dict(basis_id='S0B0',required=True,preserved=True,answer_quote='')]
        out,seen=self.run_case(0,mutate)
        self.assertTrue(out.execution_issues);self.assertEqual(len(seen),2)
        self.assertEqual(out.findings[0].component_reviews[1].status.value,'supported')
        self.assertEqual(out.findings[0].component_reviews[0].origin,'execution_incomplete')
        diagnostic=json.loads(seen[1].messages[-1].content)
        self.assertIn('preserved_requires_literal_carrier',json.dumps(diagnostic))

    def test_missing_condition_and_uncertainty_are_valid_not_success(self):
        for preserved,status in ((False,'insufficient_evidence'),(None,'not_assessable')):
            def mutate(v,d,c):v['judgments'][0]['conditions']=[dict(basis_id='S0B0',required=True,preserved=preserved,answer_quote='')]
            out,seen=self.run_case(3,mutate)
            self.assertFalse(out.execution_issues);self.assertEqual(len(seen),1)
            self.assertEqual(out.findings[0].status.value,status)

    def test_ordinary_cannot_bypass_technical_dependencies(self):
        def mutate(v,d,c):v['judgments'][0].update(object_kind='ordinary',dependencies=[])
        out,seen=self.run_case(2,mutate)
        self.assertTrue(out.execution_issues);self.assertEqual(len(seen),2)

    def test_ordinary_classification_objection_is_a_valid_review_result(self):
        def mutate(v,d,c):
            v['judgments'][0].update(object_kind='ordinary',dependencies=[],classification_objection='The extracted technical obligation is disputed; this is a recommendation.')
        out,seen=self.run_case(2,mutate)
        self.assertFalse(out.execution_issues);self.assertEqual(len(seen),1)
        self.assertEqual(out.findings[0].status.value,'not_assessable')
        self.assertEqual(out.object_reviews[0]['fidelity'],'faithful')

    def test_classification_and_fidelity_independent(self):
        out,_=self.run_case(4)
        self.assertEqual(out.object_reviews[0]['raw_model_status'],'supported')
        self.assertEqual(out.object_reviews[0]['fidelity'],'faithful')
        self.assertEqual(out.findings[0].status.value,'not_assessable')
        def mutate(v,d,c):v['judgments'][0]['fidelity']='disputed'
        out,_=self.run_case(2,mutate)
        self.assertIsNone(out.object_reviews[0]['classification_objection'])
        self.assertEqual(out.findings[0].status.value,'not_assessable')

    def test_original_citation_scope_and_budget(self):
        out,seen=self.run_case(inp=inputs(True))
        self.assertFalse(out.execution_issues);self.assertEqual(len(seen),2)
        def mutate(v,d,c):
            if d['targets'][0]['kind']=='citation':v['judgments'][0]['basis_ids']=['S0B0']
        out,_=self.run_case(inp=inputs(True),mutate=mutate)
        self.assertTrue(out.execution_issues)
        out,seen=self.run_case(inp=inputs(True),limit=1)
        self.assertTrue(out.execution_issues);self.assertEqual(len(seen),1)

    def test_previous_real_responses_are_audit_data_not_semantic_tests(self):
        from pathlib import Path
        prior=json.loads(Path('docs/evaluation/fact-internal-flow-v1/live-predictions-v1.json').read_text(encoding='utf8'))
        for cid in ('F03','F04','F05'):
            branch=next(b for b in prior['branches'] if b['id']==cid+'-candidate')
            cat=Catalog(fixed_input(next(c for c in CASES if c['id']==cid)))
            row=json.loads(branch['attempts'][0]['raw_response_text'])['judgments'][0]
            unchanged=deepcopy(row)
            with self.assertRaises(ContractError):cat.parse_one(row,cat.targets[row['target_id']],'$.judgments[0]')
            self.assertEqual(row,unchanged)

if __name__=='__main__':unittest.main()
