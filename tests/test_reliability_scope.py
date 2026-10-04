"""Development regressions for archived category/namespace mistakes, no API."""
import asyncio
from dataclasses import asdict,replace
import json
import unittest
from core.models import Evidence,AnswerDraft,CitationBinding
from core.validation import ContractError,validate_review
from services.answer_anchors import anchors
from services.answer_basis_targets import parse
from tests import test_review_reliability as fixtures

class ScopeTests(unittest.TestCase):
    def test_conversion_does_not_prove_document_statement(self):
        from agents.verification_contract_v9 import parse as parse_review,catalog
        from tests.test_review_reliability import tool
        i=fixtures.ReliabilityTests().inputs()
        wire=self.wire(i.answer,target='document_body');c=parse(wire,i.answer).claims[0]
        i=replace(i,claims=(c,),tool_results=(tool(c.claim_id),))
        value={'findings':[{'claim_id':c.claim_id,'rationale':'Conversion cannot prove a printed statement.',
            'applicability_conditions':[],'bases':[{'type':'calculation_result_reference','result_id':i.tool_results[0].result_id}],
            'component_reviews':[{'component_index':0,'status':'supported','basis_indexes':[0],'rationale':'Wrong attribution basis.'}]}],'citation_reviews':[]}
        with self.assertRaises(ContractError):parse_review(value,i,catalog(i))

    def test_snapshot_body_preserved_old_reviewer_context_explicitly_omitted(self):
        from agents.verification_contract_v9_scoped import body_snapshot
        i=fixtures.ReliabilityTests().inputs()
        old='{"previous_review":{"quote_id":"OLD-ID"}}'
        from services.evidence_scope import make_snapshot
        body=Evidence('body','s','v','synthetic','Literal body retained.','synthetic_fixture')
        i=replace(i,generation_snapshot=make_snapshot(i.answer,(body,),None,request=i.request,answer_requirements=('Keep conditions.',old),prompt_version='synthetic_fixture'))
        projected=body_snapshot(i)
        self.assertEqual(projected['answer_requirements'],['Keep conditions.'])
        self.assertEqual(list(projected['evidence']),[asdict(e) for e in i.generation_snapshot.evidence])
        self.assertNotIn('OLD-ID',json.dumps(projected))
        self.assertTrue(projected['nonbody_context_omissions']);self.assertIn(old,i.generation_snapshot.answer_requirements)

    def test_harness_injects_tools_into_scoped_protocol(self):
        from model_adapter.contracts import ModelResponse,ModelSettings
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from agents.power_domain_review import ModelPowerDomainReviewAgent
        from services.claim_extractor import ModelClaimExtractor
        from harness.runtime import OfflineHarness
        from harness.contracts import RunBudget
        from tools.unit_conversion import UnitConversionTool
        observed=[]
        class Adapter:
            async def complete(self,request):
                data=json.loads(request.messages[1].content)
                if request.prompt_version.startswith('atomic-claims-v6'):
                    value={'claims':[{'anchor_id':data['ANSWER_ANCHORS'][0]['anchor_id'],'proposition':'230 kV = 230000 V',
                        'claim_type':'technical_fact','assertion_role':'asserted','semantic_qualifiers':[],
                        'components':[{'category':'technical_fact','proposition':'230 kV = 230000 V','basis_target':'mathematical_relation'}]}],'non_claims':[]}
                elif request.prompt_version.startswith('evidence-verification-v9.2'):
                    observed.append(data)
                    value={'findings':[{'claim_id':data['claims'][0]['claim_id'],'rationale':'Actual scalar result.',
                        'applicability_conditions':[],'bases':[{'type':'calculation_result_reference','result_id':data['TOOL_RESULTS'][0]['result_id']}],
                        'component_reviews':[{'component_index':0,'status':'supported','basis_indexes':[0],'rationale':'230 multiplied by 1000.'}]}]}
                else:value={'checks':[{'check_id':k,'status':'no_issue','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule',
                    'rationale':'Synthetic check only.','missing_prerequisites':[]} for k in ('answer_units','analysis_scope','operating_prerequisites')]}
                return ModelResponse(json.dumps(value),request.model_id,finish_reason='stop')
        i=fixtures.ReliabilityTests().inputs();settings=ModelSettings('synthetic-model');adapter=Adapter()
        harness=OfflineHarness(None,ModelEvidenceVerificationAgent(adapter,settings,schema_version=10),
            ModelPowerDomainReviewAgent(adapter,settings,protocol_version=3),None,ModelClaimExtractor(adapter,settings,protocol_version=6),unit_tool=UnitConversionTool())
        result=asyncio.run(harness.run(i.request,RunBudget(max_model_calls=6,max_revision_rounds=0)))
        self.assertFalse(result.execution_issues);self.assertEqual(len(result.tool_results),2)
        self.assertTrue(observed[0]['TOOL_RESULTS']);self.assertIn('DELIVERY_RECORD',observed[0])
        self.assertEqual(result.verification_output.findings[0].status.value,'supported')

    def wire(self,a,target='document_body',category='technical_fact'):
        return {'claims':[{'anchor_id':anchors(a)[0]['anchor_id'],'proposition':a.text,'claim_type':'technical_fact',
            'assertion_role':'asserted','semantic_qualifiers':[],
            'components':[{'category':category,'proposition':a.text,'basis_target':target}]}],'non_claims':[]}

    def test_body_metadata_target_consistency_and_archive(self):
        a=AnswerDraft('synthetic-a',1,'The document states its applicability is region R.')
        with self.assertRaises(ContractError) as caught:parse(self.wire(a,category='source_quality_metadata'),a)
        self.assertIn('basis_target',caught.exception.diagnostic['field_path'])
        c=parse(self.wire(a),a).claims[0]
        from evaluation.archive_replay import restore
        from core.models import Claim
        self.assertEqual(asdict(restore(json.loads(json.dumps(asdict(c))),Claim)),asdict(c))
        self.assertEqual(c.text,a.text)
        with self.assertRaises(ContractError):parse(self.wire(a,target='invented'),a)

    def test_math_and_quantity_category_not_same(self):
        a=AnswerDraft('synthetic-math',1,'230 kV equals 230 V at the same bus.')
        wire=self.wire(a,target='mathematical_relation');wire['claims'][0]['components'][0]['proposition']='230 kV = 230 V'
        c=parse(wire,a).claims[0]
        self.assertEqual(c.text,a.text);self.assertEqual(c.components[0].proposition,'230 kV = 230 V')
        with self.assertRaises(ContractError):parse(self.wire(a,target='mathematical_relation',category='source_quality_metadata'),a)

    def test_scoped_stage_one_correction_and_valid_peer_preserved(self):
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from model_adapter.contracts import ModelResponse,ModelSettings
        i=fixtures.ReliabilityTests().inputs('A standalone statement.')
        old=Evidence('original','s','v','synthetic','A standalone statement.','synthetic_fixture')
        new=Evidence('independent','s','v','synthetic','A standalone statement.','synthetic_fixture')
        answer=replace(i.answer,citations=(CitationBinding(0,len(i.answer.text),(old.evidence_id,)),))
        i=replace(i,answer=answer,seed_evidence=(new,),original_evidence=(old,),tool_results=())
        calls=[]
        class Adapter:
            async def complete(self,request):
                d=json.loads(request.messages[1].content);calls.append((request,d))
                if d['purpose']=='independent':
                    q=d['QUOTE_CANDIDATES'][0]['quote_id'] if len(request.messages)>2 else 'UNKNOWN-ID'
                    v={'findings':[{'claim_id':i.claims[0].claim_id,'rationale':'Synthetic support.','applicability_conditions':[],
                        'bases':[{'type':'text_excerpt','quote_id':q}],
                        'component_reviews':[{'component_index':0,'status':'supported','basis_indexes':[0],'rationale':'Synthetic premise.'}]}]}
                else:v={'citation_reviews':[{'citation_index':0,'status':'supported','rationale':'Invalid ID.','applicability_conditions':[],
                    'bases':[{'type':'text_excerpt','quote_id':'UNKNOWN-ID'}]}]}
                return ModelResponse(json.dumps(v),request.model_id,finish_reason='stop')
        agent=ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic-model'),schema_version=10)
        out=asyncio.run(agent.run(i));validate_review(out,answer,i.claims,out.evidence,True)
        self.assertEqual(len(calls),3);self.assertEqual(sum(r.correction for r in out.model_records),1)
        self.assertTrue(out.execution_issues);self.assertEqual(out.findings[0].status.value,'supported')
        self.assertEqual([q['evidence_id'] for q in calls[-1][1]['QUOTE_CANDIDATES']],[old.evidence_id])
        self.assertNotIn('TOOL_RESULTS',calls[-1][1]);self.assertNotIn('GENERATION_INPUT_SNAPSHOT',calls[-1][1])
