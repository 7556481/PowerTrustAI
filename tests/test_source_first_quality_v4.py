"""Engineering only: comparison consistency never proves semantic correctness."""
import json,unittest
from dataclasses import replace
from tests.test_source_first_real_v3 import ActualInputSubstitute
from tests.test_literal_review_v1 import fixture,response
from services.literal_review_v1 import catalog
from services.answer_anchors import anchors
from services.source_first_audit_v2 import parse_relation
from core.validation import ContractError

class RelationSubstitute(ActualInputSubstitute):
    async def complete(self,r):
        if r.prompt_version!='source_first_audit_v2':return await super().complete(r)
        out=await super().complete(replace(r,prompt_version='source_first_audit_v1'))
        value=json.loads(out.text)
        for row in value['units']:
            row['relation_check']=dict(source_relation='确定性工程夹具中的来源关系',answer_relation='确定性工程夹具中的回答关系',entailment='entailed' if row['status']=='supported' else 'not_entailed' if row['status']=='contradicted' else 'unknown')
        return replace(out,text=json.dumps(value,ensure_ascii=False))

class RelationTests(unittest.TestCase):
    def test_missing_comparison_reproduces_contract_failure_then_valid_comparison(self):
        inp=fixture();_,ind,orig=catalog(inp)
        v=response(dict(units=anchors(inp.answer),INDEPENDENT_QUOTE_IDS=list(ind),original_citations=[dict(citation_index=i,allowed_quote_ids=list(q)) for i,q in orig.items()]))
        with self.assertRaises(ContractError):parse_relation(v,inp)
        for row in v['units']:
            row['relation_check']=dict(source_relation='来源明确限定值和适用条件。',answer_relation='回答保留条件，但第一单元数值不同。',entailment='not_entailed' if row['status']=='contradicted' else 'entailed')
        out=parse_relation(v,inp);self.assertTrue(out.literal_defects)
        v['units'][1]['relation_check']['entailment']='unknown'
        with self.assertRaises(ContractError):parse_relation(v,inp)

    def test_version_and_baseline_remain_independent(self):
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory
        c=ServiceConfig(audit_strategy='source_first_audit_v2',fact_review_contract='literal_v1',local_revision_interface='source_actions_v2')
        m=ComponentFactory(c).manifest(c.knowledge_version,fixed_evidence_only=True)
        self.assertEqual(m['audit_strategy'],'source_first_audit_v2')
        self.assertEqual(ServiceConfig().audit_strategy,'baseline')
        self.assertNotEqual(m['template_sha256']['literal'],ComponentFactory(replace(c,audit_strategy='source_first_audit_v1')).manifest(c.knowledge_version,fixed_evidence_only=True)['template_sha256']['literal'])
