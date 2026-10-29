"""Literal provenance checks, not a deterministic semantic classifier."""
import json,unittest
from copy import deepcopy
from dataclasses import replace
from services.source_first_audit_v3 import parse_grounded_relation
from services.literal_review_v1 import catalog
from services.answer_anchors import anchors
from tests.test_literal_review_v1 import fixture,response
from tests.test_source_first_quality_v4 import RelationSubstitute
from core.validation import ContractError

class GroundedSubstitute(RelationSubstitute):
    async def complete(self,r):
        out=await super().complete(replace(r,prompt_version='source_first_audit_v2') if r.prompt_version=='source_first_audit_v3' else r)
        value=json.loads(out.text);d=json.loads(r.messages[1].content)
        if r.prompt_version=='source_first_audit_v3':
            quotes={q['quote_id']:q for q in d['quotes']}
            for unit in d['units']:
                if '也必须一律假定已经动作' in unit['text']:
                    row=next(x for x in value['units'] if x['anchor_id']==unit['anchor_id']);row['status']='contradicted'
                    ids=[q for q in unit['allowed_quote_ids'] if 'may be assumed' in quotes[q]['text']][:1]
                    row['quote_ids']=ids
                    value['defects'].append(dict(anchor_id=unit['anchor_id'],original_text='也必须一律假定已经动作',difference='Synthetic optional assumption strengthened; not a model score',correction_boundary='Change only optional capacitor assumption; retain voltage limit, dynamic device assumption and contingency obligation',quote_ids=ids))
            for row in value['units']:
                row['relation_check']=dict(source_relation=quotes[row['quote_ids'][0]]['text'] if row['quote_ids'] else None,
                    answer_relation='确定性夹具关系，非模型语义成绩',entailment='entailed' if row['status']=='supported' else 'not_entailed' if row['status']=='contradicted' else 'unknown')
        elif r.prompt_version=='local-revision-source-actions-v2':
            for edit in value['edits']:edit['text']=edit['text'].replace('也必须一律假定已经动作','可以假定已经动作')
        return replace(out,text=json.dumps(value,ensure_ascii=False))

class GroundingTests(unittest.TestCase):
    def sample(self):
        inp=fixture();_,ind,orig=catalog(inp)
        v=response(dict(units=anchors(inp.answer),INDEPENDENT_QUOTE_IDS=list(ind),original_citations=[dict(citation_index=i,allowed_quote_ids=list(q)) for i,q in orig.items()]))
        for row in v['units']:
            row['relation_check']=dict(source_relation=ind[row['quote_ids'][0]].text,answer_relation='完整回答关系',entailment='not_entailed' if row['status']=='contradicted' else 'entailed')
        return inp,v
    def test_exact_multi_sentence_source_and_defect_preserved(self):
        inp,v=self.sample();o=parse_grounded_relation(v,inp);self.assertEqual(len(o.literal_defects),1)
        self.assertIn('condition C',o.literal_reviews[1].reason)
    def test_free_summary_even_with_legal_citation_is_rejected(self):
        inp,v=self.sample();v['units'][1]['relation_check']['source_relation']='Source requires a universal duty.'
        with self.assertRaises(ContractError):parse_grounded_relation(v,inp)
    def test_source_not_selected_for_same_unit_rejected(self):
        inp,v=self.sample();v['units'][1]['quote_ids']=[]
        with self.assertRaises(ContractError):parse_grounded_relation(v,inp)
    def test_null_is_honest_gap_not_edit_authority(self):
        inp,v=self.sample();row=v['units'][1];row.update(status='insufficient_evidence',quote_ids=[]);row['relation_check'].update(source_relation=None,entailment='unknown')
        parse_grounded_relation(v,inp)
        row['status']='supported'
        with self.assertRaises(ContractError):parse_grounded_relation(v,inp)
    def test_null_with_adverse_defect_cannot_authorize_revision(self):
        inp,v=self.sample();row=v['units'][0];row.update(status='insufficient_evidence');row['relation_check'].update(source_relation=None,entailment='unknown')
        with self.assertRaises(ContractError):parse_grounded_relation(v,inp)
    def test_literal_binding_does_not_claim_semantic_classifier(self):
        inp,v=self.sample();v['units'][1]['reason']='Synthetic misreading of a legal quote.'
        o=parse_grounded_relation(v,inp);self.assertEqual(o.literal_reviews[1].status,'supported')
        # A legal citation and internally consistent verdict still need source review.
        v['units'][1]['relation_check']['entailment']='not_entailed'
        with self.assertRaises(ContractError):parse_grounded_relation(v,inp)
    def test_independent_version_manifest_default_unchanged(self):
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory
        c=ServiceConfig(audit_strategy='source_first_audit_v3',fact_review_contract='literal_v1',local_revision_interface='source_actions_v2')
        m=ComponentFactory(c).manifest(c.knowledge_version,fixed_evidence_only=True)
        self.assertEqual(m['audit_strategy'],'source_first_audit_v3');self.assertEqual(ServiceConfig().audit_strategy,'baseline')
        self.assertNotEqual(m['template_sha256']['literal'],ComponentFactory(replace(c,audit_strategy='source_first_audit_v2')).manifest(c.knowledge_version,fixed_evidence_only=True)['template_sha256']['literal'])
    def test_budget_boundary_and_frozen_order(self):
        from evaluation.source_first_modality_v6 import Gate
        from types import SimpleNamespace as NS
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            g=Gate(Path(t));r=NS(model_id='deepseek-flash',max_output_tokens=8000,messages=[])
            for c in range(14):
                for n in range(20):g(dict(case=c,variant='test'),r,n)
            self.assertEqual(g.calls,280);self.assertEqual(g.threshold,4500000)
            with self.assertRaises(RuntimeError):g(dict(case=14,variant='test'),r,1)
