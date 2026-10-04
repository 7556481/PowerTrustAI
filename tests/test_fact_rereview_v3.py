"""Offline standalone-protocol development regressions, no API or .env."""
from tests.fixture_paths import synthetic_diagnostics
import asyncio
from copy import deepcopy
from dataclasses import replace,asdict
import json
import tempfile
import unittest
from pathlib import Path
from core.models import AnswerDraft,Evidence,CitationBinding,TaskRequest,TaskMode,VerificationStatus
from core.validation import validate_review,ContractError
from services.claim_obligations import parse
from services.answer_anchors import anchors
from services.evidence_scope import make_snapshot
from agents.contracts import ReliabilityVerificationInput
from agents.evidence_verification import ModelEvidenceVerificationAgent
from agents.review_templates_v3 import INDEPENDENT,ORIGINAL,COMMON
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope

def inputs(citation=True,two=False):
    text='There are three equipment ratings: stator winding rating, field current rating, and terminal voltage rating.'
    answer=AnswerDraft('synthetic-answer',2,text,citations=(CitationBinding(0,len(text),('original',)),) if citation else ())
    item={'anchor_id':anchors(answer)[0]['anchor_id'],'proposition':text,'claim_type':'technical_fact',
        'assertion_role':'asserted','semantic_qualifiers':[],'components':[{'category':'technical_fact',
        'proposition':text,'basis_target':'technical_content','verification_obligation':'technical_truth'}]}
    claims=parse({'claims':[item]+([dict(deepcopy(item),proposition='A separate technical implication.')] if two else []),'non_claims':[]},answer).claims
    seed=Evidence('independent','s1','v1','synthetic fixture, characters 0..n',text,'synthetic_fixture')
    original=Evidence('original','s2','v1','synthetic fixture, characters 0..n',text,'synthetic_fixture')
    req=TaskRequest('synthetic-task',TaskMode.ASSESS_EXISTING,'voltage_stability_reactive_support','Review the statement.',existing_answer=answer)
    return ReliabilityVerificationInput(req,answer,claims,(seed,),original_evidence=(original,),
        generation_snapshot=make_snapshot(answer,(seed,original),None,request=req,prompt_version='synthetic_fixture'))

def response(data,*,status='supported',fidelity='faithful'):
    if 'original_citation' in data:
        return {'citation_reviews':[{'citation_index':data['original_citation']['citation_index'],'status':status,
            'rationale':'Synthetic semantic example.','applicability_conditions':[],
            'bases':[{'type':'text_excerpt','quote_id':data['QUOTE_CANDIDATES'][0]['quote_id']}] if status=='supported' else []}]}
    findings=[]
    for c in data['claims']:
        definitive=status in ('supported','contradicted')
        findings.append({'claim_id':c['claim_id'],'rationale':'Synthetic bounded judgment.',
            'applicability_conditions':[],'bases':[{'type':'text_excerpt','quote_id':data['QUOTE_CANDIDATES'][0]['quote_id']}] if definitive else [],
            'component_reviews':[{'component_index':n,'status':status,'basis_indexes':[0] if definitive else [],
            'rationale':'Source supports the bounded proposition.' if definitive else 'Meaning remains unresolved.',
            'semantic_review':{'fidelity':fidelity,'assertion_role':c['assertion_role'],
                'verification_obligation':c['component_obligations'][n],'rationale':'Independent comparison of anchor and normalized target.'}}
                for n in data['MODEL_COMPONENT_INDEXES'][c['claim_id']]]})
    return {'findings':findings}

def run(inp,build,diag=None):
    seen=[]
    class Adapter:
        async def complete(self,req):
            seen.append(req);data=json.loads(req.messages[1].content)
            return ModelResponse(json.dumps(build(data,req,len(seen))),req.model_id,finish_reason='stop')
    async def invoke():
        budget=ModelBudget(1+len(inp.answer.citations)+1)
        with model_scope(budget):
            output=await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic'),schema_version=12,diagnostic_dir=diag).run(inp)
        return output,budget.records
    out,records=asyncio.run(invoke());return out,records,seen

class FactRereviewV3Tests(unittest.TestCase):
    def test_full_requests_have_one_root_and_dedicated_templates(self):
        out,_,seen=run(inputs(),lambda d,*_:response(d))
        self.assertFalse(out.execution_issues)
        self.assertNotIn('findings',COMMON);self.assertNotIn('citation_reviews',COMMON)
        self.assertNotIn('citation_reviews',INDEPENDENT);self.assertNotIn('findings',ORIGINAL)
        self.assertEqual(seen[0].messages[0].content,INDEPENDENT)
        self.assertEqual(seen[1].messages[0].content,ORIGINAL)
        self.assertNotIn('"citation_reviews"',seen[0].messages[0].content+seen[0].messages[1].content)
        self.assertNotIn('"findings"',seen[1].messages[0].content+seen[1].messages[1].content)

    def test_joined_root_is_rejected_and_correction_preserves_own_template(self):
        def build(d,r,n):
            v=response(d)
            if n==1:v['citation_reviews']=[]
            return v
        with synthetic_diagnostics() as diag:
            out,records,seen=run(inputs(False),build,diag)
            self.assertFalse(out.execution_issues);self.assertEqual(len(records),2)
            self.assertTrue(records[1].correction)
            self.assertEqual(seen[1].messages[0].content,INDEPENDENT)
            correction=json.loads(seen[1].messages[-1].content)
            self.assertIn('unexpected_fields_not_allowed',[x['constraint'] for x in correction['validation_errors']])
            self.assertEqual(len(list(Path(diag).glob('response-*.json'))),2)

    def test_legal_uncertain_and_insufficient_are_business_not_execution_failure(self):
        for status,fidelity in (('not_assessable','uncertain'),('insufficient_evidence','faithful')):
            out,records,_=run(inputs(False),lambda d,*_:response(d,status=status,fidelity=fidelity))
            self.assertFalse(out.execution_issues);self.assertEqual(len(records),1)
            self.assertEqual(out.findings[0].status.value,status)

    def test_disputed_supported_rejected_not_silently_downgraded(self):
        out,records,_=run(inputs(False),lambda d,*_:response(d,fidelity='disputed'))
        self.assertTrue(out.execution_issues);self.assertEqual(len(records),2)
        self.assertTrue(all(r.output_status=='invalid_structure' for r in records))
        self.assertEqual(out.findings[0].component_reviews[0].origin,'execution_incomplete')

    def test_wrong_basis_type_and_unknown_id_strict(self):
        for basis in ({'type':'input_snapshot_reference'},{'type':'text_excerpt','quote_id':'UNKNOWN'}):
            def build(d,*_):
                v=response(d);v['findings'][0]['bases']=[basis];return v
            out,records,_=run(inputs(False),build)
            self.assertTrue(out.execution_issues);self.assertEqual(len(records),2)

    def test_original_binding_cannot_use_independent_scope(self):
        independent=[]
        def build(d,*_):
            v=response(d)
            if 'original_citation' not in d:independent.append(d['QUOTE_CANDIDATES'][0]['quote_id'])
            else:v['citation_reviews'][0]['bases'][0]['quote_id']=independent[0]
            return v
        out,records,_=run(inputs(),build)
        self.assertTrue(out.execution_issues);self.assertEqual(len(records),3)
        self.assertEqual(out.findings[0].status,VerificationStatus.SUPPORTED)
        self.assertNotEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)

    def test_one_stage_correction_and_valid_sibling_retained(self):
        def build(d,*_):
            v=response(d)
            if 'original_citation' not in d:v['findings'][1]['bases'][0]['quote_id']='UNKNOWN'
            else:v['citation_reviews'][0]['bases'][0]['quote_id']='UNKNOWN'
            return v
        out,records,_=run(inputs(two=True),build)
        self.assertEqual(sum(r.correction for r in records),1)
        self.assertEqual(len(records),3)
        self.assertEqual(out.findings[0].status,VerificationStatus.SUPPORTED)
        self.assertEqual(out.findings[1].component_reviews[0].origin,'execution_incomplete')
        self.assertTrue(out.execution_issues)

    def test_core_requires_semantic_review_in_new_protocol(self):
        from core.models import ComponentReview
        inp=inputs(False);out,_,_=run(inp,lambda d,*_:response(d))
        r=out.findings[0].component_reviews[0]
        stripped=ComponentReview(r.component_id,r.status,r.basis_indexes,r.rationale)
        out=replace(out,findings=(replace(out.findings[0],component_reviews=(stripped,)),))
        with self.assertRaises(ContractError):validate_review(out,inp.answer,inp.claims,out.evidence,True)
