"""Independent v2 development fixtures, including wording not used in the guard."""
import asyncio
from copy import deepcopy
from dataclasses import asdict,replace
import json
import unittest
from types import SimpleNamespace
from tests import test_review_reliability as fixture
from core.models import AnswerDraft,EngineeringContext,VerificationStatus,Claim
from core.validation import ContractError,validate_review,validate_extraction
from services.answer_anchors import anchors
from services.claim_obligations import parse

def wire(answer,proposition=None,target='mathematical_relation',role='asserted'):
    from services.claim_obligations import TARGET_OBLIGATIONS
    from services.answer_basis_targets import TARGETS
    return {'claims':[{'anchor_id':anchors(answer)[0]['anchor_id'],'proposition':proposition or answer.text,
        'claim_type':TARGETS[target],'assertion_role':role,'semantic_qualifiers':[],
        'components':[{'category':TARGETS[target],'proposition':proposition or answer.text,
        'basis_target':target,'verification_obligation':TARGET_OBLIGATIONS[target]}]}],'non_claims':[]}

class ReliabilityV2Tests(unittest.TestCase):
    def test_scope_cannot_replace_archived_positive_technical_count(self):
        a=AnswerDraft('synthetic',1,'There are four equipment ratings: stator winding rating, field current rating, terminal voltage rating, and active power output.')
        with self.assertRaises(ContractError):parse(wire(a,'The answer identifies four equipment ratings.',target='answer_text'),a)
        out=parse(wire(a,target='technical_content'),a);validate_extraction(out,a)
        self.assertEqual(out.claims[0].component_obligations,('technical_truth',))

    def test_legitimate_scope_and_archive_binding(self):
        from evaluation.archive_replay import restore
        a=AnswerDraft('synthetic',2,'This answer does not provide a plant safety certification.')
        c=parse(wire(a,target='answer_text'),a).claims[0]
        self.assertEqual(restore(json.loads(json.dumps(asdict(c))),Claim),c)
        self.assertEqual(c.text,a.text);self.assertEqual(c.semantic_origin,'model-claims-v7-obligations')

    def test_correction_and_nested_reporting_are_not_confirmed_count_errors(self):
        from services.quantity_checks import enumeration_check
        for text in ('The claim of four equipment ratings is inconsistent with the enumeration.',
                     'The reviewer says the proposal claims four equipment ratings; this is incorrect.',
                     'Four equipment ratings were alleged, whereas the actual enumeration names three.',
                     'The assertion of four equipment ratings cannot be sustained.'):
            result=enumeration_check(text,(),version='quantity-enumeration-v1.3',assertion_role='asserted')
            self.assertNotEqual(result.status,'warning')
            if result.status!='not_applicable':self.assertEqual(result.status,'incomplete')

    def test_rating_items_do_not_include_active_power(self):
        from services.quantity_checks import enumeration_check
        c=SimpleNamespace(text='Capability depends on stator winding rating, field current rating, terminal voltage rating, and active power output.',quote_id='synthetic-q')
        result=enumeration_check('There are four equipment ratings: stator, field, terminal, output.',(c,),version='quantity-enumeration-v1.3')
        self.assertEqual(result.status,'warning');self.assertEqual(result.observed_count,3)

    def test_conceptual_scope_not_plant_certification(self):
        from agents.power_domain_review import program_findings
        i=fixture.ReliabilityTests().inputs();a=AnswerDraft('synthetic',1,'Normal voltage does not establish plant stability.')
        c=parse(wire(a,target='technical_content'),a).claims
        i=SimpleNamespace(request=replace(i.request,engineering_context=EngineeringContext()),answer=a,claims=c)
        findings,_=program_findings(i,())
        self.assertEqual(next(f for f in findings if f.category=='simulation_boundary').check_status,'not_applicable')
        self.assertTrue(all(not f.missing_prerequisites for f in findings if f.category.startswith('input_units:')))
        i.request=replace(i.request,engineering_context=EngineeringContext(goal='plant_assessment'))
        findings,_=program_findings(i,())
        self.assertEqual(next(f for f in findings if f.category=='simulation_boundary').check_status,'not_assessable')
        self.assertIn('network_model',next(f for f in findings if f.category=='engineering_inputs').missing_prerequisites)

    def test_fidelity_dispute_cannot_be_supported(self):
        from services.review_fidelity import parse as review_parse
        a=AnswerDraft('synthetic',1,'230 kV equals 230 V.')
        c=parse(wire(a,'230 kV = 230 V'),a).claims[0]
        i=SimpleNamespace(claims=(c,))
        v={'findings':[{'claim_id':c.claim_id,'component_reviews':[{'component_index':0,'status':'supported',
            'semantic_review':{'fidelity':'disputed','assertion_role':'asserted','verification_obligation':'answer_scope','rationale':'Target changed.'}}]}]}
        with self.assertRaises(ContractError):review_parse(v,i,lambda _:None)

    def test_real_harness_wiring_offline(self):
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from agents.power_domain_review import ModelPowerDomainReviewAgent
        from model_adapter.contracts import ModelResponse,ModelSettings
        from services.claim_extractor import ModelClaimExtractor
        from tools.unit_conversion import UnitConversionTool
        from harness.runtime import OfflineHarness
        from harness.contracts import RunBudget
        class Adapter:
            async def complete(self,req):
                data=json.loads(req.messages[1].content)
                if req.prompt_version.startswith('atomic-claims-v7'):
                    a=AnswerDraft(data['answer_id'],data['answer_version'],data['ANSWER_ANCHORS'][0]['text']);value=wire(a,'230 kV = 230,000 V')
                elif req.prompt_version.startswith('evidence-verification-v9.3'):
                    c=data['claims'][0]
                    value={'findings':[{'claim_id':c['claim_id'],'rationale':'Actual conversion verifies scalar equality.','applicability_conditions':[],
                        'bases':[{'type':'calculation_result_reference','result_id':data['TOOL_RESULTS'][0]['result_id']}],
                        'component_reviews':[{'component_index':0,'status':'supported','basis_indexes':[0],'rationale':'230 times 1000.',
                        'semantic_review':{'fidelity':'faithful','assertion_role':'asserted','verification_obligation':'technical_truth','rationale':'Retains equality and grouped number.'}}]}]}
                else:value={'checks':[{'check_id':k,'status':'no_issue','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule','rationale':'Synthetic bounded check.','missing_prerequisites':[]} for k in ('answer_units','analysis_scope','operating_prerequisites')]}
                return ModelResponse(json.dumps(value),req.model_id,finish_reason='stop')
        i=fixture.ReliabilityTests().inputs();a=AnswerDraft(i.answer.answer_id,i.answer.version,'230 kV = 230,000 V')
        req=replace(i.request,existing_answer=a);settings=ModelSettings('synthetic')
        h=OfflineHarness(None,ModelEvidenceVerificationAgent(Adapter(),settings,schema_version=11),
            ModelPowerDomainReviewAgent(Adapter(),settings,protocol_version=4),None,
            ModelClaimExtractor(Adapter(),settings,protocol_version=7),unit_tool=UnitConversionTool(version='scalar-si-conversion-v2'))
        r=asyncio.run(h.run(req,RunBudget(max_model_calls=6,max_revision_rounds=0)))
        self.assertFalse(r.execution_issues);self.assertEqual(r.verification_output.findings[0].status,VerificationStatus.SUPPORTED)
        self.assertEqual(r.verification_output.findings[0].component_reviews[0].fidelity_status,'faithful')
        validate_review(r.verification_output,r.answer,r.extraction_output.claims,r.verification_output.evidence,True)
