"""Synthetic fixture regressions: no credentials, network or paid API."""
import asyncio
from dataclasses import replace
import json
import unittest
from core.models import CitationBinding,VerificationStatus
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelSettings,ModelResponse
from model_adapter.runtime import ModelBudget,model_scope
from services.citation_workload import CitationWorkload,pack
from tests.test_fact_rereview_v3 import inputs,response

def multi(n=4,version=2):
    i=inputs()
    evidence=tuple(replace(i.original_evidence[0],evidence_id='original-'+str(k)) for k in range(n))
    answer=replace(i.answer,version=version,citations=tuple(CitationBinding(0,len(i.answer.text),(e.evidence_id,)) for e in evidence))
    return replace(i,answer=answer,original_evidence=evidence,generation_snapshot=None)

def invoke(i,limits=None,mutate=None,budget_limit=40):
    seen=[]
    class Adapter:
        async def complete(self,r):
            seen.append(r);d=json.loads(r.messages[1].content)
            if 'ORIGINAL_CITATION_SCOPES' in d:
                v={'citation_reviews':[dict(citation_index=s['citation_index'],status='supported',
                    rationale='Synthetic fixture whole-substring support.',applicability_conditions=[],
                    bases=[{'type':'text_excerpt','quote_id':s['QUOTE_CANDIDATES'][0]['quote_id']}])
                    for s in d['ORIGINAL_CITATION_SCOPES']]}
            else:v=response(d)
            if mutate:v=mutate(v,d,r)
            return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
    async def run():
        b=ModelBudget(budget_limit)
        with model_scope(b):
            out=await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture',max_output_tokens=8000,max_response_chars=96000),
                schema_version=13,citation_workload=limits).run(i)
        return out,b
    out,b=asyncio.run(run());return out,b,seen

class CitationWorkloadTests(unittest.TestCase):
    def test_stable_groups_and_no_citation_count_cap(self):
        out,b,seen=invoke(multi(35))
        groups=[json.loads(r.messages[1].content)['ORIGINAL_CITATION_SCOPES'] for r in seen[1:]]
        self.assertEqual([len(g) for g in groups],[32,3])
        self.assertEqual([s['citation_index'] for g in groups for s in g],list(range(35)))
        self.assertEqual(b.used,3);self.assertFalse(out.execution_issues)
        self.assertTrue(all(c.status==VerificationStatus.SUPPORTED for c in out.citation_reviews))

    def test_cross_item_borrowing_rejected_valid_peer_retained(self):
        def bad(v,d,r):
            if 'ORIGINAL_CITATION_SCOPES' in d:
                v['citation_reviews'][1]['bases']=v['citation_reviews'][0]['bases']
            return v
        out,b,_=invoke(multi(3),mutate=bad)
        self.assertEqual(b.used,3);self.assertEqual(sum(r.correction for r in b.records),1)
        self.assertEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)
        self.assertEqual(out.citation_reviews[2].status,VerificationStatus.SUPPORTED)
        self.assertEqual(out.citation_reviews[1].status,VerificationStatus.NOT_ASSESSABLE)
        self.assertTrue(out.execution_issues)

    def test_wrong_index_is_not_silently_dropped(self):
        def bad(v,d,r):
            if 'ORIGINAL_CITATION_SCOPES' in d:v['citation_reviews'][1]['citation_index']=999
            return v
        out,b,_=invoke(multi(),mutate=bad)
        self.assertTrue(out.execution_issues);self.assertEqual(len(out.citation_reviews),4)
        self.assertEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)

    def test_one_correction_across_multiple_groups(self):
        def bad(v,d,r):
            if 'ORIGINAL_CITATION_SCOPES' in d:v['citation_reviews'][0]['bases'][0]['quote_id']='WRONG'
            return v
        out,b,_=invoke(multi(5),CitationWorkload(max_items=2),bad)
        self.assertEqual(b.used,5);self.assertEqual(sum(r.correction for r in b.records),1)
        self.assertTrue(out.execution_issues)

    def test_capacity_exact_and_oversize_explicit(self):
        payload=lambda g:{'items':list(g)}
        n=len(json.dumps(payload([0]),ensure_ascii=False))+3
        groups,rejected=pack([0],payload,'abc',CitationWorkload(32,n,n))
        self.assertEqual(groups,((0,),));self.assertFalse(rejected)
        groups,rejected=pack([0],payload,'abc',CitationWorkload(32,n-1,n))
        self.assertFalse(groups);self.assertEqual(rejected,(0,))
        out,b,_=invoke(multi(),CitationWorkload(32,100,200))
        self.assertEqual(b.used,1);self.assertTrue(out.execution_issues)
        self.assertEqual(out.findings[0].status,VerificationStatus.SUPPORTED)
        self.assertTrue(all(c.status==VerificationStatus.NOT_ASSESSABLE for c in out.citation_reviews))

    def test_known_budget_shortfall_preserves_affordable_partial_checks(self):
        out,b,_=invoke(multi(5),CitationWorkload(max_items=2),budget_limit=3)
        self.assertEqual(b.used,3)
        self.assertEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)
        self.assertEqual(out.citation_reviews[4].status,VerificationStatus.NOT_ASSESSABLE)
        self.assertIn('REVIEW_WORKLOAD_BUDGET_SHORTFALL',[i.code for i in out.execution_issues])

    def test_revision_new_citations_and_versions_get_new_scopes(self):
        out,b,s1=invoke(multi(2,1));out2,b2,s2=invoke(multi(4,2))
        d1=json.loads(s1[1].messages[1].content);d2=json.loads(s2[1].messages[1].content)
        self.assertEqual(len(out2.citation_reviews),4)
        self.assertNotEqual(d1['ORIGINAL_CITATION_SCOPES'][0]['scope_id'],d2['ORIGINAL_CITATION_SCOPES'][0]['scope_id'])
        self.assertEqual(d2['answer_version'],2)

    def test_settings_reject_invalid_capacity(self):
        for kwargs in ({'max_items':0},{'max_message_chars':True},{'max_correction_message_chars':1}):
            with self.assertRaises(ValueError):CitationWorkload(**kwargs)

    def test_duplicate_indexes_invalidate_duplicates_preserve_other(self):
        def bad(v,d,r):
            if 'ORIGINAL_CITATION_SCOPES' in d:v['citation_reviews'][1]['citation_index']=0
            return v
        out,b,_=invoke(multi(3),mutate=bad)
        self.assertEqual(out.citation_reviews[2].status,VerificationStatus.SUPPORTED)
        self.assertNotEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)
        self.assertTrue(out.execution_issues)

    def test_correction_capacity_preserves_valid_peer_without_extra_call(self):
        def bad(v,d,r):
            if 'ORIGINAL_CITATION_SCOPES' in d:
                v['citation_reviews'][1]['bases'][0]['quote_id']='UNKNOWN'
                v['citation_reviews'][1]['rationale']='x'*70000
            return v
        out,b,_=invoke(multi(2),CitationWorkload(32,64000,64000),bad)
        self.assertEqual(b.used,2);self.assertFalse(any(r.correction for r in b.records))
        self.assertEqual(out.citation_reviews[0].status,VerificationStatus.SUPPORTED)
        self.assertIn('REVIEW_MESSAGE_CAPACITY_EXCEEDED',[i.code for i in out.execution_issues])

    def test_concurrent_clients_share_atomic_budget(self):
        from model_adapter.runtime import ModelClient
        from model_adapter.contracts import ModelMessage,ModelBudgetError
        class Adapter:
            async def complete(self,r):
                await asyncio.sleep(.01)
                return ModelResponse('{}',r.model_id,finish_reason='stop')
        async def run():
            b=ModelBudget(3);client=ModelClient(Adapter(),ModelSettings('synthetic_fixture'))
            results=await asyncio.gather(*(client.complete((ModelMessage('user','fixture'),),'synthetic_fixture',b) for _ in range(6)),return_exceptions=True)
            self.assertEqual(b.used,3);self.assertEqual(len(b.records),3)
            self.assertEqual(sum(isinstance(r,ModelBudgetError) for r in results),3)
            self.assertEqual(sorted(r.call_number for r in b.records),[1,2,3])
        asyncio.run(run())

    def test_original_group_capacity_does_not_cap_independent_review(self):
        i=multi(2)
        i=replace(i,seed_evidence=(replace(i.seed_evidence[0],text=i.seed_evidence[0].text+' x'*33000),))
        out,b,seen=invoke(i)
        self.assertGreater(sum(len(m.content) for m in seen[0].messages),64000)
        self.assertFalse(out.execution_issues)
        self.assertEqual(b.used,2)
