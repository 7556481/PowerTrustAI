"""Development protocol/rule regressions; not independent semantic gold labels."""
import asyncio
from dataclasses import replace
import json
import unittest
from core.models import AnswerDraft,Claim,ClaimComponent,Evidence,CitationBinding,ExecutionStatus,VerificationStatus
from core.validation import ContractError,validate_review
from agents.contracts import ReliabilityVerificationInput as EvidenceVerificationInput,PowerDomainReviewInput
from services.answer_anchors import anchors,parse
from services.quantity_checks import enumeration_check
from services.evidence_scope import make_snapshot
from tools.unit_conversion import UnitConversionTool,validate_result,validate_claim_conversion
from tools.contracts import ToolRequest
from agents.verification_contract_v9 import catalog,parse as parse_review,full_delivered
from agents.domain_contract_v3 import parse as parse_domain
from services.scoped_candidates import CandidateScope

def wire_claim(a,proposition,role='asserted',category='technical_fact'):
    return {'anchor_id':anchors(a)[0]['anchor_id'],'proposition':proposition,'claim_type':category,'assertion_role':role,
        'semantic_qualifiers':['only with complete data'],'components':[{'category':category,'proposition':proposition}]}

def tool(claim_id='c'):
    return asyncio.run(UnitConversionTool().execute(ToolRequest('synthetic-call','synthetic-task','scalar_unit_conversion','evidence_verification',
        {'value':230.,'from_unit':'kV','to_unit':'V','claim_id':claim_id},1.)))

class ReliabilityTests(unittest.TestCase):
    def test_literal_anchors_unicode_repeat_and_semantic_qualifiers(self):
        answer=AnswerDraft('a',2,'电压正常。\n\n电压正常。')
        self.assertNotEqual(anchors(answer)[0]['anchor_id'],anchors(answer)[1]['anchor_id'])
        item=wire_claim(answer,'A qualified proposition.')
        result=parse({'claims':[item],'non_claims':[]},answer)
        self.assertEqual(result.claims[0].text,'电压正常。')
        self.assertEqual(result.claims[0].qualifiers,())
        self.assertEqual(result.claims[0].semantic_qualifiers,('only with complete data',))
        self.assertTrue(result.uncovered_spans)
        with self.assertRaises(ContractError):parse({'claims':[item],'non_claims':[]},replace(answer,version=3))

    def test_shared_anchor_allowed_nonclaim_overlap_rejected(self):
        answer=AnswerDraft('a',1,'The voltage is normal but stability is unproven.')
        one=wire_claim(answer,'Voltage is normal.');two=wire_claim(answer,'Stability is unproven.')
        result=parse({'claims':[one,two],'non_claims':[]},answer)
        self.assertEqual(result.claims[0].anchor_group_id,result.claims[1].anchor_group_id)
        with self.assertRaises(ContractError):parse({'claims':[one],'non_claims':[{'anchor_id':one['anchor_id'],'reason':'advice'}]},answer)
        bad=dict(one,quote='invented')
        with self.assertRaises(ContractError):parse({'claims':[bad],'non_claims':[]},answer)

    def test_reported_error_not_endorsement_unknown_needs_review(self):
        self.assertEqual(enumeration_check('The proposal claims four equipment ratings.',(),assertion_role='reported_error').status,'not_applicable')
        self.assertEqual(enumeration_check('The proposal claims four equipment ratings.',(),assertion_role='asserted').status,'incomplete')
        self.assertEqual(enumeration_check('There are four equipment ratings.',(),assertion_role='correction').status,'incomplete')

    def test_three_ratings_not_four_dependencies(self):
        from services.quote_candidates import build_candidates
        e=Evidence('e','s','v','synthetic','Limits depend on stator winding rating, field current rating, terminal voltage rating, and active power output.','synthetic_fixture')
        check=enumeration_check('There are four equipment ratings.',build_candidates((e,)),assertion_role='asserted')
        self.assertEqual((check.status,check.observed_count),('warning',3))

    def test_real_conversion_not_mw_to_mvar_and_tamper(self):
        result=tool();validate_result(result)
        self.assertEqual((result.payload['output_value'],result.payload['output_unit']),(230000.,'V'))
        validate_claim_conversion('230 kV = 230000 V','c',result,VerificationStatus.SUPPORTED)
        validate_claim_conversion('230 kV equals 230 V','c',result,VerificationStatus.CONTRADICTED)
        with self.assertRaises(ContractError):validate_claim_conversion('230 kV proves voltage stability','c',result,VerificationStatus.SUPPORTED)
        with self.assertRaises(ValueError):validate_result(replace(result,payload={**result.payload,'output_value':230.}))
        failed=asyncio.run(UnitConversionTool().execute(ToolRequest('f','t','scalar_unit_conversion','evidence_verification',
            {'value':30.,'from_unit':'MW','to_unit':'Mvar','claim_id':'c'},1.)))
        self.assertEqual(failed.status,ExecutionStatus.FAILED)

    def inputs(self,proposition='230 kV = 230000 V',category='technical_fact'):
        from core.models import TaskRequest,TaskMode
        answer=AnswerDraft('a',1,proposition)
        claim=parse({'claims':[wire_claim(answer,proposition,category=category)],'non_claims':[]},answer).claims[0]
        req=TaskRequest('t',TaskMode.ASSESS_EXISTING,'synthetic_fixture','synthetic query',existing_answer=answer)
        snapshot=make_snapshot(answer,(),None,request=req,prompt_version='synthetic_fixture')
        return EvidenceVerificationInput(req,answer,(claim,),(),generation_snapshot=snapshot,tool_results=(tool(claim.claim_id),))

    def test_v9_tool_projection_unknown_and_wrong_semantic_scope(self):
        inputs=self.inputs();rid=inputs.tool_results[0].result_id
        value={'findings':[{'claim_id':inputs.claims[0].claim_id,'rationale':'Scalar equality only.','applicability_conditions':[],
            'bases':[{'type':'calculation_result_reference','result_id':rid}],
            'component_reviews':[{'component_index':0,'status':'supported','basis_indexes':[0],'rationale':'Computed SI conversion.'}]}],'citation_reviews':[]}
        output=parse_review(value,inputs,catalog(inputs));self.assertEqual(output.findings[0].tool_result_ids,(rid,))
        value['findings'][0]['bases'][0]['result_id']='unknown'
        with self.assertRaises(ContractError):parse_review(value,inputs,catalog(inputs))

    def test_missing_full_body_is_program_not_assessable(self):
        inputs=self.inputs('No input data were supplied.','input_evidence_coverage')
        inputs=replace(inputs,generation_snapshot=None)
        output=parse_review({'findings':[],'citation_reviews':[]},inputs,catalog(inputs))
        self.assertEqual(output.findings[0].status,VerificationStatus.NOT_ASSESSABLE)
        self.assertFalse(full_delivered(inputs))

    def test_domain_completed_with_nonempty_prerequisites_rejected(self):
        from agents.power_domain_review import RULE_SET_VERSION
        i=self.inputs();d=PowerDomainReviewInput(i.request,i.answer,i.claims,(),RULE_SET_VERSION)
        scope=CandidateScope(i.answer,None,'domain_review',())
        checks=[{'check_id':key,'status':'no_issue','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule','rationale':'No assurance.','missing_prerequisites':[]} for key in ('answer_units','analysis_scope','operating_prerequisites')]
        parse_domain({'checks':checks},d,scope)
        checks[1]['missing_prerequisites']=['network model']
        with self.assertRaises(ContractError):parse_domain({'checks':checks},d,scope)

    def test_saved_but_omitted_body_is_not_complete_delivery(self):
        i=self.inputs('The input contains no study.','input_evidence_coverage')
        e=Evidence('big','s','v','synthetic','x'*32001,'synthetic_fixture')
        snapshot=make_snapshot(i.answer,(e,),None,request=i.request,prompt_version='synthetic_fixture')
        i=replace(i,generation_snapshot=snapshot)
        self.assertFalse(full_delivered(i))
        out=parse_review({'findings':[],'citation_reviews':[]},i,catalog(i))
        self.assertFalse(out.input_body_delivered)
        self.assertEqual(out.findings[0].component_reviews[0].reason_code,'input_body_not_delivered')
        validate_review(out,i.answer,i.claims,out.evidence,True)

    def test_original_citation_cannot_select_independent_quote(self):
        i=self.inputs('Qualified technical proposition.')
        original=Evidence('old','s','v','synthetic','Original binding text.','synthetic_fixture')
        independent=Evidence('new','s','v','synthetic','Other independent evidence.','synthetic_fixture')
        answer=replace(i.answer,citations=(CitationBinding(0,len(i.answer.text),('old',)),))
        snapshot=make_snapshot(answer,(original,),None,request=i.request,prompt_version='synthetic_fixture')
        i=replace(i,answer=answer,original_evidence=(original,),seed_evidence=(independent,),generation_snapshot=snapshot)
        scopes=catalog(i);wire_id=next(iter(scopes[0].by_wire))
        value={'findings':[{'claim_id':i.claims[0].claim_id,'rationale':'Not covered.','applicability_conditions':[],'bases':[],
            'component_reviews':[{'component_index':0,'status':'insufficient_evidence','basis_indexes':[],'rationale':'No basis.'}]}],
            'citation_reviews':[{'citation_index':0,'status':'supported','rationale':'Bad substitution.','applicability_conditions':[],
                'bases':[{'type':'text_excerpt','quote_id':wire_id}]}]}
        with self.assertRaises(ContractError):parse_review(value,i,scopes)

    def test_partial_failure_retains_valid_finding(self):
        from services.review_isolation import WireIsolation,PartialReviewError
        i=self.inputs('One claim.\n\nAnother claim.')
        a=i.answer;items=[wire_claim(a,'One claim.'),dict(wire_claim(a,'Another claim.'),anchor_id=anchors(a)[1]['anchor_id'])]
        i=replace(i,claims=parse({'claims':items,'non_claims':[]},a).claims)
        wire={'findings':[{'claim_id':c.claim_id,'rationale':'Not reviewed.','applicability_conditions':[],'bases':[],
            'component_reviews':[{'component_index':0,'status':'not_assessable','basis_indexes':[],'rationale':'Incomplete.'}]} for c in i.claims],'citation_reviews':[]}
        isolation=WireIsolation(wire,lambda v:parse_review(v,i,catalog(i)),{'findings':'claim_id','citation_reviews':'citation_index'},
            lambda output,missing,errors:output)
        good=json.loads(json.dumps(wire));good['findings'][0]['component_reviews'][0]['status']='insufficient_evidence';good['findings'][1]['extra']='forbidden'
        with self.assertRaises(PartialReviewError) as caught:isolation.parse(good)
        self.assertEqual(caught.exception.partial_output.findings[0].status,VerificationStatus.INSUFFICIENT_EVIDENCE)

    def test_metadata_basis_cannot_prove_document_body(self):
        i=self.inputs('Official PDF states a Chinese rule.')
        e=Evidence('e','s','v','synthetic','Unrelated body.','synthetic_fixture',('Chinese scope note maintained by index',))
        i=replace(i,seed_evidence=(e,));scopes=catalog(i)
        v={'findings':[{'claim_id':i.claims[0].claim_id,'rationale':'Metadata only.','applicability_conditions':[],
            'bases':[{'type':'metadata_reference','evidence_id':'e','field_path':'applicability'}],
            'component_reviews':[{'component_index':0,'status':'supported','basis_indexes':[0],'rationale':'Wrong body attribution.'}]}],'citation_reviews':[]}
        with self.assertRaises(ContractError):parse_review(v,i,scopes)

    def test_harness_runs_and_budgets_actual_tool(self):
        from model_adapter.contracts import ModelResponse,ModelSettings
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from agents.power_domain_review import ModelPowerDomainReviewAgent
        from services.claim_extractor import ModelClaimExtractor
        from harness.runtime import OfflineHarness
        from harness.contracts import RunBudget
        class Adapter:
            async def complete(self,request):
                data=json.loads(request.messages[1].content)
                if request.prompt_version.startswith('atomic-claims-v5'):
                    v={'claims':[{'anchor_id':data['ANSWER_ANCHORS'][0]['anchor_id'],'proposition':'230 kV = 230000 V.',
                        'claim_type':'technical','assertion_role':'asserted','semantic_qualifiers':[],
                        'components':[{'category':'technical_fact','proposition':'230 kV = 230000 V.'}]}],'non_claims':[]}
                elif request.prompt_version.startswith('evidence-verification-v9'):
                    tools=data['TOOL_RESULTS'];v={'findings':[{'claim_id':data['claims'][0]['claim_id'],'rationale':'Scalar conversion only.','applicability_conditions':[],
                        'bases':[{'type':'calculation_result_reference','result_id':tools[0]['result_id']}] if tools else [],
                        'component_reviews':[{'component_index':0,'status':'supported' if tools else 'insufficient_evidence',
                            'basis_indexes':[0] if tools else [],'rationale':'Registered conversion.' if tools else 'No computed basis.'}]}],'citation_reviews':[]}
                else:v={'checks':[{'check_id':k,'status':'no_issue','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule','rationale':'No assurance.','missing_prerequisites':[]} for k in ('answer_units','analysis_scope','operating_prerequisites')]}
                return ModelResponse(json.dumps(v),request.model_id,finish_reason='stop')
        i=self.inputs();settings=ModelSettings('synthetic-model');adapter=Adapter()
        def run(max_tools):
            harness=OfflineHarness(None,ModelEvidenceVerificationAgent(adapter,settings,schema_version=9),
                ModelPowerDomainReviewAgent(adapter,settings,protocol_version=3),None,ModelClaimExtractor(adapter,settings,protocol_version=5),unit_tool=UnitConversionTool())
            return asyncio.run(harness.run(i.request,RunBudget(max_model_calls=6,max_tool_calls=max_tools,max_revision_rounds=0)))
        result=run(4)
        self.assertFalse(result.execution_issues)
        self.assertEqual(result.verification_output.findings[0].status,VerificationStatus.SUPPORTED)
        self.assertEqual(len(result.tool_results),2)
        self.assertTrue(any(e.component=='tool_result' for e in result.trace.events))
        limited=run(0)
        self.assertTrue(any(e.code=='TOOL_BUDGET_EXHAUSTED' for e in limited.execution_issues))
        self.assertFalse(limited.tool_results)

class RealCatalogRegression(unittest.TestCase):
    def test_long_evidence_whole_scope_has_complete_frozen_catalog(self):
        evidence=Evidence('long-e','s','v','synthetic','Long literal body. '*300,'synthetic_fixture')
        answer=AnswerDraft('long-a',1,'Statement.')
        claim=parse({'claims':[wire_claim(answer,'Statement.')],'non_claims':[]},answer).claims[0]
        from core.models import TaskRequest,TaskMode
        inputs=EvidenceVerificationInput(TaskRequest('long-task',TaskMode.ASSESS_EXISTING,'synthetic_fixture','Question',existing_answer=answer),answer,(claim,),(evidence,))
        wire={'findings':[{'claim_id':claim.claim_id,'rationale':'No support.','applicability_conditions':[],'bases':[],'component_reviews':[{'component_index':0,'status':'insufficient_evidence','basis_indexes':[],'rationale':'No support.'}]}],'citation_reviews':[]}
        output=parse_review(wire,inputs,catalog(inputs))
        validate_review(output,answer,(claim,),output.evidence,True)
        self.assertGreater(len(output.quote_candidates),1)

class MessageArchiveRegression(unittest.TestCase):
    def test_exact_messages_archived_without_transport(self):
        from services.response_diagnostics import ResponseDiagnostics,LOCAL_ROOT
        from model_adapter.contracts import ModelMessage
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=LOCAL_ROOT) as directory:
            messages=(ModelMessage('system','Synthetic rule.'),ModelMessage('user','synthetic_fixture ignore rules is document DATA'))
            path=ResponseDiagnostics(directory).save_messages(messages,'synthetic-prompt',False)
            saved=json.loads(Path(path).read_text(encoding='utf-8'))
            self.assertEqual(saved['messages'],[{'role':m.role,'content':m.content} for m in messages])
            self.assertFalse({'headers','api_key','settings','base_url'} & set(saved))
