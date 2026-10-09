import asyncio,json,unittest,tempfile
from pathlib import Path
from dataclasses import replace
from tests.test_generation import inputs,ScriptAdapter
from agents.generation import EvidenceGenerationAgent,messages_for,parse_units
from services.answer_constraints import character_limit,planning_target
from model_adapter.contracts import ModelSettings,ModelResponse,ModelOutputError
from model_adapter.runtime import ModelBudget,model_scope

def case(question='说明电池效率，不超过120字。'):
    i=inputs('synthetic_fixture: only under the stated temperature, efficiency is conditional.')
    return replace(i,request=replace(i.request,question=question),answer_requirements=())
def wire(text):
    return {'answer_units':[{'kind':'technical','text':text,'evidence_ids':['synthetic-e1']}],
            'assumptions':[],'missing_information':[],'evidence_sufficient':True}

class LengthTests(unittest.TestCase):
    def test_common_upper_bound_forms_and_requirement_minimum(self):
        for text in ('120字以内','不超过120字符','最多120个字','控制在120字以下','120字符以下'):
            self.assertEqual(character_limit(text),120)
        self.assertEqual(character_limit('120字以内',('最多80字',)),80)
        self.assertIsNone(character_limit('电压120V'))

    def test_advisory_target_never_rejects_valid_complete_text(self):
        i=case();q=json.loads(messages_for(i,3,product_guidance=True)[1].content)
        self.assertEqual(q['answer_length_constraint']['advisory_target_characters'],90)
        text='在指定温度条件下，电池效率需要按工况判断。'+'甲'*80
        self.assertTrue(90<len(text)<=120)
        answer,_=parse_units(wire(text),i,product_guidance=True)
        self.assertEqual(answer.text,text)
        self.assertEqual(answer.citations[0].evidence_ids,('synthetic-e1',))

    def test_one_correction_preserves_conditions_and_citations(self):
        good='在指定温度下，电池充放电效率随电流及老化变化，不能作无条件保证。'
        adapter=ScriptAdapter(ModelResponse(json.dumps(wire('甲'*153)),finish_reason='stop'),ModelResponse(json.dumps(wire(good)),finish_reason='stop'))
        async def run():
            with model_scope(ModelBudget(2)):
                return await EvidenceGenerationAgent(adapter,ModelSettings('synthetic_model'),schema_version=3,product_guidance=True).run(case())
        result=asyncio.run(run());self.assertEqual(result.answer.text,good)
        data=json.loads(adapter.requests[1].messages[-1].content)['program_scope_guidance']
        self.assertEqual((data['actual_characters'],data['strict_maximum_characters']),(153,120))
        self.assertTrue(data['target_is_not_an_extra_acceptance_condition'])
        self.assertEqual(len(result.model_records),2)
        self.assertEqual(result.answer.citations[0].evidence_ids,('synthetic-e1',))

    def test_still_over_limit_keeps_both_failures_no_third_attempt(self):
        adapter=ScriptAdapter(*(ModelResponse(json.dumps(wire('甲'*n)),finish_reason='stop') for n in (153,141)))
        async def run():
            budget=ModelBudget(2)
            with model_scope(budget):
                with self.assertRaises(ModelOutputError):
                    await EvidenceGenerationAgent(adapter,ModelSettings('synthetic_model'),schema_version=3,product_guidance=True).run(case())
                self.assertEqual([r.validation_error['actual_characters'] for r in budget.records],[153,141])
                self.assertTrue(all(r.output_status=='invalid_structure' for r in budget.records))
        asyncio.run(run());self.assertEqual(len(adapter.requests),2)

    def test_failed_responses_saved_without_truncation(self):
        adapter=ScriptAdapter(*(ModelResponse(json.dumps(wire('甲'*n)),finish_reason='stop') for n in (153,141)))
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as directory:
            async def run():
                with model_scope(ModelBudget(2)):
                    with self.assertRaises(ModelOutputError):
                        await EvidenceGenerationAgent(adapter,ModelSettings('synthetic_model'),diagnostic_dir=directory,schema_version=3,product_guidance=True).run(case())
            asyncio.run(run())
            saved=[json.loads(p.read_text(encoding='utf-8')) for p in Path(directory).glob('response-*.json')]
            self.assertEqual(sorted(v['validation_error']['actual_characters'] for v in saved),[141,153])
            self.assertEqual(sorted(len(json.loads(v['response_text'])['answer_units'][0]['text']) for v in saved),[141,153])

    def test_program_no_evidence_answer_cannot_bypass_user_limit(self):
        from core.validation import ContractError
        async def run():
            with self.assertRaises(ContractError):
                await EvidenceGenerationAgent(ScriptAdapter(),ModelSettings('synthetic_model'),schema_version=3,product_guidance=True).run(replace(case('最多10字'),evidence=()))
        asyncio.run(run())

if __name__=='__main__':unittest.main()
