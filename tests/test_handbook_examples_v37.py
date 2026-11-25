"""Executable synthetic teaching examples. No credentials, network or private data."""
import asyncio,json,unittest
from copy import deepcopy
from pathlib import Path
from agents.contracts import GenerationInput
from agents.generation import parse_units,messages_for
from core.models import AnswerDraft,Evidence,TaskMode,TaskRequest
from core.validation import ContractError
from services.claim_obligations import parse
from services.structured_model import structured_request
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelBudget,ModelClient
from model_adapter.deepseek import DeepSeekAdapter

DATA=json.loads((Path(__file__).resolve().parents[1]/'docs/learning/examples/formal-path-v37.json').read_text(encoding='utf-8'))
def answer(version=1):return AnswerDraft(DATA['answer']['id'],version,DATA['answer']['text'])
def inputs():
    evidence=Evidence('teaching-e1','teaching-source','v1','synthetic teaching source',DATA['answer']['text'],'synthetic_fixture')
    request=TaskRequest('teaching',TaskMode.QUESTION_ANSWER,'concept','Explain device A under C.')
    return GenerationInput(request,(evidence,))

class TeachingExamples(unittest.TestCase):
    def test_formal_generation_and_v7_accept_and_preserve_binding(self):
        a,sufficient=parse_units(DATA['generation'],inputs(),product_guidance=True)
        self.assertEqual(a.text,answer().text);self.assertTrue(sufficient)
        self.assertEqual(a.citations[0].evidence_ids,('teaching-e1',))
        out=parse(DATA['extraction_v7'],answer())
        self.assertEqual(out.claims[0].text,answer().text)
        self.assertEqual(out.claims[0].component_obligations,('technical_truth',))
    def test_wrong_target_unknown_evidence_and_stale_version_are_rejected(self):
        bad=deepcopy(DATA['extraction_v7']);bad['claims'][0]['components'][0]['verification_obligation']='answer_scope'
        with self.assertRaises(ContractError):parse(bad,answer())
        with self.assertRaises(ContractError):parse(DATA['extraction_v7'],answer(2))
        bad=deepcopy(DATA['generation']);bad['answer_units'][0]['evidence_ids']=['unknown']
        with self.assertRaises(ContractError):parse_units(bad,inputs())
    def test_legal_shape_does_not_prove_semantic_equivalence(self):
        bad=deepcopy(DATA['extraction_v7']);bad['claims'][0]['proposition']='Only under C, device A supplies reactive power.'
        bad['claims'][0]['components'][0]['proposition']=bad['claims'][0]['proposition']
        self.assertTrue(parse(bad,answer()).claims) # Deliberate semantic flaw, not a pass label.
    def test_real_client_adapter_envelope_parser_and_one_correction_offline(self):
        async def go():
            payloads=[]
            def exchange(body,timeout,limit):
                payloads.append(json.loads(body))
                content={'unexpected':True} if len(payloads)==1 else DATA['generation']
                return 200,json.dumps({'model':'deepseek-flash','choices':[{'message':{'content':json.dumps(content)},'finish_reason':'stop'}], 'usage':{'prompt_tokens':2,'completion_tokens':1,'total_tokens':3}}).encode()
            settings=ModelSettings('deepseek-flash',max_output_tokens=8000,max_response_chars=96000)
            adapter=DeepSeekAdapter(settings,exchange=exchange);budget=ModelBudget(limit=2)
            try:
                # Same runtime ownership boundary as production, with only HTTP replaced.
                from model_adapter.runtime import model_scope
                with model_scope(budget):
                    value,numbers=await structured_request(ModelClient(adapter,settings),messages_for(inputs(),3), 'teaching-generation-v37',lambda v:parse_units(v,inputs(),product_guidance=True))
                self.assertEqual(len(payloads),2);self.assertEqual(budget.used,2)
                self.assertEqual(len(budget.records),2)
                self.assertEqual(payloads[0]['model'],'deepseek-flash')
                self.assertFalse(payloads[0]['stream'])
                self.assertGreater(len(payloads[1]['messages']),len(payloads[0]['messages']))
                self.assertIn('FORMAT_CORRECTION_DATA_UNTRUSTED',payloads[1]['messages'][-1]['content'])
                self.assertEqual(value[0].text,answer().text)
            finally:adapter.close()
        asyncio.run(go())


class MarkdownJSONTests(unittest.TestCase):
    def test_all_json_fences_in_chapters_parse_as_displayed(self):
        import re
        chapters=Path(__file__).resolve().parents[1]/'docs/learning/chapters'
        for path in chapters.glob('*.md'):
            for index,match in enumerate(re.finditer(r'```json\s*\n(.*?)\n```',path.read_text(encoding='utf-8'),re.S)):
                with self.subTest(chapter=path.name,block=index):
                    from services.structured_model import strict_json
                    strict_json(match[1])
    def test_displayed_http_envelope_parses_but_business_content_is_rejected(self):
        import re
        from model_adapter.deepseek import parse_response
        from services.structured_model import strict_json
        path=Path(__file__).resolve().parents[1]/'docs/learning/chapters/24-model-wire.md'
        block=re.findall(r'```json\s*\n(.*?)\n```',path.read_text(encoding='utf-8'),re.S)[0]
        response=parse_response(200,block.encode('utf-8'),'deepseek-flash')
        self.assertEqual(strict_json(response.text),{'unexpected':True})
        with self.assertRaises(ContractError):parse_units(strict_json(response.text),inputs())


class PrintedTimelineArithmeticTests(unittest.TestCase):
    def test_interview_inputs_and_outputs_match_case_table(self):
        import re
        chapters=Path(__file__).resolve().parents[1]/'docs/learning/chapters'
        interview=(chapters/'17-interview.md').read_text(encoding='utf-8')
        cases=re.findall(r'F=(\d+)、领域读取(\d+)、事实审核(\d+)、领域审核(\d+)，旧终态(\d+)秒，新终态(\d+)秒',interview)
        self.assertEqual(len(cases),2)
        table=(chapters/'35-case-overlap.md').read_text(encoding='utf-8')
        table_inputs=[tuple(map(int,x)) for x in re.findall(r'F=(\d+)，R=(\d+)，V=(\d+)，D=(\d+)',table)]
        self.assertEqual([tuple(map(int,x[:4])) for x in cases],table_inputs)
        for row in cases:
            f,r,v,d,old,new=map(int,row)
            self.assertEqual(old,f+r+max(v,d))
            self.assertEqual(new,f+max(v,r+d))
