"""Public synthetic fixtures: explicit length and frozen stance, no paid calls."""
import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from services.answer_constraints import character_limit, validate_length
from services.validation_diagnostics import StructuredValidationError
from core.models import AnswerDraft
from core.validation import ContractError
from agents.contracts import EvidenceVerificationOutput
from agents.generation import EvidenceGenerationAgent, messages_for
from model_adapter.contracts import ModelResponse, ModelSettings
from model_adapter.runtime import ModelBudget, model_scope
from tests import test_generation as generation_fixture
from tests.test_fact_rereview_v3 import inputs, response
from agents.evidence_verification import ModelEvidenceVerificationAgent

class LengthTests(unittest.TestCase):
    def test_bound_all_units_including_separators_and_no_mutation(self):
        self.assertEqual(character_limit('控制在200字以内',('不超过180字',)),180)
        self.assertIsNone(character_limit('讨论200个设备'))
        a=AnswerDraft('synthetic',1,'甲'*101+'\n\n'+'乙'*99)
        with self.assertRaises(StructuredValidationError) as e:validate_length(a,'控制在200字以内')
        self.assertEqual(len(a.text),202);self.assertEqual(e.exception.diagnostic['actual_characters'],202)
        self.assertEqual(validate_length(AnswerDraft('synthetic',1,'甲'*200),'控制在200字以内').text,'甲'*200)
    def test_messages_deliver_original_complete_evidence_and_explicit_constraint(self):
        i=generation_fixture.inputs();i=replace(i,request=replace(i.request,question='普通中文，不超过200字'))
        m=messages_for(i,3,product_guidance=True)
        self.assertEqual(json.loads(m[1].content)['answer_length_constraint']['maximum_characters'],200)
        self.assertEqual(json.loads(m[2].content)['evidence'][0]['text'],i.evidence[0].text)
        self.assertIn('avoid absolute',m[0].content);self.assertIn('Do not invent an alternative analogy',m[0].content)
    def test_one_bounded_correction_regenerates_whole_answer_and_preserves_citation(self):
        i=generation_fixture.inputs();i=replace(i,request=replace(i.request,question='不超过30字'))
        texts=['Synthetic complete evidence statement. '*4,'A concise synthetic answer.'];seen=[]
        class Adapter:
            async def complete(self,r):
                text=texts[len(seen)];seen.append(r)
                return ModelResponse(json.dumps({'answer_units':[{'kind':'technical','text':text,'evidence_ids':[i.evidence[0].evidence_id]}],
                    'assumptions':[],'missing_information':[],'evidence_sufficient':True}),r.model_id,finish_reason='stop')
        out=asyncio.run(EvidenceGenerationAgent(Adapter(),ModelSettings('synthetic'),schema_version=3).run(i))
        self.assertEqual(out.answer.text,texts[1]);self.assertEqual(len(seen),2)
        self.assertTrue(out.model_records[1].correction);self.assertEqual(out.answer.citations[0].end_offset,len(texts[1]))
        correction=json.loads(seen[1].messages[-1].content)['validation_error']
        self.assertEqual(correction['max_characters'],30)
    def test_repeated_overlong_output_stops_after_one_correction(self):
        from model_adapter.contracts import ModelOutputError
        i=generation_fixture.inputs();i=replace(i,request=replace(i.request,question='不超过20字'))
        seen=[]
        class Adapter:
            async def complete(self,r):
                seen.append(r)
                return ModelResponse(json.dumps({'answer_units':[{'kind':'technical','text':'甲'*21,'evidence_ids':[i.evidence[0].evidence_id]}],
                    'assumptions':[],'missing_information':[],'evidence_sufficient':True}),r.model_id,finish_reason='stop')
        with self.assertRaises(ModelOutputError):asyncio.run(EvidenceGenerationAgent(Adapter(),ModelSettings('synthetic'),schema_version=3).run(i))
        self.assertEqual(len(seen),2)
    def test_revision_must_also_preserve_original_bound(self):
        from agents.revision_contract_v2 import parse
        i=SimpleNamespace(request=SimpleNamespace(question='不超过200字'),answer=AnswerDraft('synthetic',1,'Original.'),allowed_evidence=(),
            verification=SimpleNamespace(findings=(SimpleNamespace(finding_id='synthetic-finding'),)),domain_review=SimpleNamespace(findings=()))
        v={'answer_units':[{'kind':'clarification','text':'甲'*201,'evidence_ids':[]}],'assumptions':[],'missing_information':[],
            'finding_actions':[{'finding_id':'synthetic-finding','action':'modified','explanation':'synthetic complete rewrite'}]}
        with self.assertRaises(StructuredValidationError) as e:parse(v,i)
        self.assertEqual(e.exception.diagnostic['stage'],'revision_v2');self.assertEqual(v['answer_units'][0]['text'],'甲'*201)

class FrozenStanceTests(unittest.TestCase):
    def test_insufficient_evidence_cannot_bypass_mismatched_stance_or_obligation(self):
        from services.review_fidelity import parse
        c=SimpleNamespace(claim_id='synthetic',components=(SimpleNamespace(component_id='part'),),assertion_role='asserted',component_obligations=('input_provided',))
        for role,obligation in [('input_report','input_provided'),('asserted','technical_truth')]:
            sr={'fidelity':'faithful','assertion_role':role,'verification_obligation':obligation,'rationale':'synthetic honest mismatch'}
            v={'findings':[{'claim_id':'synthetic','component_reviews':[{'component_index':0,'status':'insufficient_evidence','semantic_review':sr}]}]}
            delegate=lambda _:EvidenceVerificationOutput('synthetic',1,(c,),(),())
            with self.assertRaises(ContractError) as e:
                parse(v,SimpleNamespace(claims=(c,)),delegate)
            self.assertEqual(e.exception.diagnostic['required_status'],'not_assessable')
            v['findings'][0]['component_reviews'][0]['status']='not_assessable'
            parse(v,SimpleNamespace(claims=(c,)),delegate)
    def test_actual_schema13_request_and_correction_keep_required_review(self):
        inp=inputs(False);seen=[]
        class Adapter:
            async def complete(self,r):
                seen.append(r);d=json.loads(r.messages[1].content);v=response(d,status='insufficient_evidence')
                x=v['findings'][0]['component_reviews'][0];x['semantic_review']['assertion_role']='input_report'
                if len(seen)>1:x['status']='not_assessable'
                return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        async def invoke():
            with model_scope(ModelBudget(2)):
                return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic'),schema_version=13).run(inp)
        out=asyncio.run(invoke())
        self.assertFalse(out.execution_issues);self.assertEqual(len(out.findings),len(inp.claims));self.assertEqual(len(seen),2)
        self.assertIn('insufficient_evidence is NOT an exception',seen[0].messages[0].content)
        from backend.assembly import ComponentFactory
        from backend.config import ServiceConfig
        import hashlib
        manifest=ComponentFactory(ServiceConfig(profile='synthetic_fixture')).manifest(None)
        self.assertEqual(manifest['template_sha256']['independent'],hashlib.sha256(seen[0].messages[0].content.encode()).hexdigest())
        self.assertEqual(json.loads(seen[1].messages[-1].content)['validation_error']['required_status'],'not_assessable')

if __name__=='__main__':unittest.main()
