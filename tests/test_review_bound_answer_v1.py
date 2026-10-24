import asyncio,json,unittest
from unittest.mock import patch
from dataclasses import replace
from services.review_bound_answer_v1 import BoundCatalog,specification,SYSTEM
from services.review_simple_tool_v1 import ToolCatalog
from model_adapter.strict_review_tool import map_null,VERSION,NAME
from model_adapter.contracts import ModelResponse,ModelSettings
from model_adapter.runtime import ModelBudget,model_scope
from agents.evidence_verification import ModelEvidenceVerificationAgent
from tests.test_fact_rereview_v3 import inputs
from tests.test_review_simple_v1 import response


def bound_response(d):
    v=response(d)
    for row in v['judgments']:row['conditions'].pop('answer_ids')
    return v


class BoundTests(unittest.TestCase):
    def exercise(self,mutate=None,inp=None):
        posts=[]
        class Adapter:
            async def complete(self,r):
                posts.append(r);d=json.loads(r.messages[1].content);v=bound_response(d)
                if mutate:mutate(v,d,r.correction)
                text=json.dumps(map_null(v,encode=True));return ModelResponse(text,r.model_id,finish_reason='tool_calls',result_transport=dict(version=VERSION,content='',tool_calls=[dict(id='bound-call',type='function',function=dict(name=NAME,arguments=text))]))
        b=ModelBudget(8)
        async def go():
            with model_scope(b):return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('fixture'),schema_version=13,review_contract='simple_bound_v1',review_result_transport='strict_tool_v1').run(inp or inputs(True))
        return asyncio.run(go()),posts,b

    def test_program_scope_only_removes_redundant_answer_locator(self):
        def mutate(v,d,c):
            for row,t in zip(v['judgments'],d['targets']):row['conditions'].update(applicability='present',expression='preserved',source_ids=t['source_unit_ids'][:1])
        out,posts,_=self.exercise(mutate);self.assertFalse(out.execution_issues);self.assertEqual(out.findings[0].status.value,'supported')
        self.assertIn('program_target_scope_not_semantic_condition_location',out.findings[0].component_reviews[0].rationale)
        c=specification()['function']['parameters']['properties']['judgments']['items']['properties']['conditions'];self.assertEqual(len(c['required']),5);self.assertNotIn('answer_ids',c['properties']);self.assertIn('gap_answer_ids',SYSTEM)

    def test_missing_misattached_extended_instance_unknown_and_conflicts_remain(self):
        for mode in ('missing','misattached','extended','instance','unknown','conflict','source','gap','objection'):
            def mutate(v,d,c):
                for row,t in zip(v['judgments'],d['targets']):
                    row['conditions'].update(applicability='present',expression='preserved',source_ids=t['source_unit_ids'][:1])
                    if mode in ('missing','misattached','extended'):row['conditions']['expression']=mode
                    elif mode=='instance':row['conditions']['instance']='missing'
                    elif mode=='unknown':row['conditions'].update(applicability='unknown',expression='uncertain')
                    elif mode=='conflict':row['conditions'].update(applicability='none',expression='preserved')
                    elif mode=='source':row['conditions']['source_ids']=[]
                    elif mode=='gap':row['gap_answer_ids']=t['answer_unit_ids'][:1]
                    else:row['objection']=dict(kind='uncertain',reason='Synthetic real semantic disagreement.')
            out,_,_=self.exercise(mutate);self.assertNotEqual(out.findings[0].status.value,'supported',mode)

    def test_old_binding_rule_and_new_illegal_field_not_silently_repaired(self):
        inp=inputs(False);old=ToolCatalog(inp);d=old.payload(['F0C0']);v=response(d);r=v['judgments'][0];r['conditions'].update(applicability='present',expression='preserved',source_ids=d['targets'][0]['source_unit_ids'][:1],answer_ids=[])
        parsed=old.parse_one(dict(r,target_id='F0C0'),old.targets['F0C0'],'$');self.assertIn('preservation_without_local_binding',parsed['projection_reasons'])
        out,_,b=self.exercise(lambda v,d,c:v['judgments'][0]['conditions'].update(answer_ids=[]));self.assertTrue(out.execution_issues);self.assertEqual(sum(r.correction for r in b.records),1)

    def test_factory_graph_policy_store_api_and_full_rereview(self):
        import tests.test_schema14_factory_flow as f
        original=f.SyntheticProvider.complete;config=f.ServiceConfig
        async def complete(provider,r):
            if r.result_tool is None:return await original(provider,r)
            provider.requests.append(r);d=json.loads(r.messages[1].content);v=bound_response(d)
            for row,t in zip(v['judgments'],d['targets']):
                if provider.revision and '9 kV' in t['proposition']:row['status']='contradicted';row['repair']=dict(basis_id=row['basis_ids'][0],replacement=f.GOOD)
            text=json.dumps(map_null(v,encode=True));return ModelResponse(text,r.model_id,finish_reason='tool_calls',result_transport=dict(version=VERSION,content='',tool_calls=[dict(id='factory-bound',type='function',function=dict(name=NAME,arguments=text))]))
        with patch.object(f,'ServiceConfig',side_effect=lambda **kw:config(**kw,fact_review_contract='simple_bound_v1',review_result_transport='strict_tool_v1',execution_path='langgraph_v1')),patch.object(f.SyntheticProvider,'complete',complete):
            for revision in (False,True):
                r,_,_=f.FactoryFlowTests().exercise(schema=13,existing=revision,revision=revision,concept=True);self.assertTrue(r['execution']['required_stages_complete']);self.assertEqual(len(r['answer']['versions']),2 if revision else 1)
        self.assertEqual(config().fact_review_contract,'production')


if __name__=='__main__':unittest.main()
