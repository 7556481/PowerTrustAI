"""Selection provenance is deterministic; semantic judgments are not."""
import unittest,json
from dataclasses import replace,asdict
from copy import deepcopy
from tests.test_literal_review_v1 import fixture,response
from tests.test_source_first_modality_v6 import GroundedSubstitute
from services.literal_review_v1 import catalog
from services.answer_anchors import anchors
from services.source_first_audit_v4 import prepare,parse_references,choices
from core.validation import ContractError

class ReferenceSubstitute(GroundedSubstitute):
    async def complete(self,r):
        original=r
        if r.prompt_version=='source_first_audit_v4':r=replace(r,prompt_version='source_first_audit_v3')
        if r.prompt_version=='power-domain-review-reference-v7':r=replace(r,prompt_version='power-domain-review-v3.5-task-obligations')
        out=await super().complete(r)
        if original.prompt_version=='source_first_audit_v4':
            d=json.loads(original.messages[1].content);v=json.loads(out.text)
            for row in v['units']:
                unit=next(a for a in d['units'] if a['anchor_id']==row['anchor_id'])
                row['relation_check']['source_relation']=[q['reference_ref'] for q in unit['source_relation_choices'] if q['quote_id'] in row['quote_ids']]
            out=replace(out,text=json.dumps(v,ensure_ascii=False))
        return out

class ReferenceTests(unittest.TestCase):
    def sample(self,inp=None):
        inp=inp or fixture();qs,ind,orig=catalog(inp)
        data=dict(units=anchors(inp.answer),INDEPENDENT_QUOTE_IDS=list(ind),quotes=[asdict(q) for q in qs.values()],original_citations=[dict(citation_index=i,allowed_quote_ids=list(q)) for i,q in orig.items()])
        v=response(data);prepare(data,inp)
        for row in v['units']:
            unit=next(a for a in data['units'] if a['anchor_id']==row['anchor_id'])
            row['relation_check']=dict(source_relation=[q['reference_ref'] for q in unit['source_relation_choices'] if q['quote_id'] in row['quote_ids']],answer_relation='完整主体/条件与义务比较；合成测试',entailment='not_entailed' if row['status']=='contradicted' else 'entailed')
        return inp,data,v
    def test_selected_ids_restore_exact_separate_source_spans(self):
        inp,d,v=self.sample();out=parse_references(v,inp);qs,_,_=catalog(inp)
        for row,unit in zip(v['units'],out.literal_reviews):
            self.assertEqual([(s.evidence_id,s.text,s.start_offset,s.end_offset) for s in unit.sources],[(qs[q].evidence_id,qs[q].text,qs[q].start_offset,qs[q].end_offset) for q in row['quote_ids']])
        self.assertTrue(out.literal_defects);self.assertNotIn('text',d['units'][0]['source_relation_choices'][0])
    def test_invented_wrong_unit_and_duplicate_refs_rejected(self):
        for kind in ('invented','wrong_unit','duplicate'):
            inp,d,v=self.sample();refs=v['units'][0]['relation_check']['source_relation']
            v['units'][0]['relation_check']['source_relation']=['invented'] if kind=='invented' else v['units'][1]['relation_check']['source_relation'] if kind=='wrong_unit' else refs+refs
            with self.assertRaises(ContractError):parse_references(v,inp)
    def test_wrong_answer_version_reference_rejected(self):
        inp,d,v=self.sample();old=v['units'][0]['relation_check']['source_relation']
        newer=replace(inp,answer=replace(inp.answer,version=2));_,d,v=self.sample(newer)
        v['units'][0]['relation_check']['source_relation']=old
        with self.assertRaises(ContractError):parse_references(v,newer)
    def test_wrong_source_or_knowledge_version_reference_rejected(self):
        inp,d,v=self.sample();old=v['units'][0]['relation_check']['source_relation']
        for newer in (replace(inp,knowledge_version='another-version'),replace(inp,seed_evidence=tuple(replace(e,source_version='new-source-version') for e in inp.seed_evidence),original_evidence=tuple(replace(e,source_version='new-source-version') for e in inp.original_evidence))):
            _,d,v=self.sample(newer);v['units'][0]['relation_check']['source_relation']=old
            with self.assertRaises(ContractError):parse_references(v,newer)
    def test_free_copy_is_not_normalized_or_repaired(self):
        inp,d,v=self.sample();v['units'][0]['relation_check']['source_relation']='actual source with changed whitespace'
        with self.assertRaises(ContractError):parse_references(v,inp)
    def test_empty_relation_gap_no_repair_authority(self):
        inp,d,v=self.sample();row=v['units'][1];row.update(status='insufficient_evidence',quote_ids=[]);row['relation_check'].update(source_relation=[],entailment='unknown')
        parse_references(v,inp)
        row['status']='supported'
        with self.assertRaises(ContractError):parse_references(v,inp)
    def test_illegal_original_citation_not_filled_from_new_review_source(self):
        from core.models import Evidence
        inp=fixture();extra=Evidence('extra','extra-source','v2','loc','New gap source body not in old original citation.','synthetic_fixture')
        inp=replace(inp,seed_evidence=inp.seed_evidence+(extra,));_,d,v=self.sample(inp)
        illegal=next(q['quote_id'] for q in d['quotes'] if q['evidence_id']=='extra');v['citations'][0]['quote_ids']=[illegal]
        with self.assertRaises(ContractError):parse_references(v,inp)
    def test_malformed_id_is_contract_failure_not_type_error(self):
        inp,d,v=self.sample();v['units'][0]['quote_ids']=[{}]
        with self.assertRaises(ContractError):parse_references(v,inp)
    def test_correct_force_not_decided_by_program(self):
        inp,d,v=self.sample();v['units'][1]['reason']='Synthetic legal citation but semantically mistaken interpretation.'
        parse_references(v,inp)
        v['units'][1]['relation_check']['entailment']='not_entailed'
        with self.assertRaises(ContractError):parse_references(v,inp)
    def test_candidate_manifest_and_default_isolated(self):
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory
        c=ServiceConfig(audit_strategy='source_first_audit_v4',fact_review_contract='literal_v1',local_revision_interface='source_actions_v2')
        m=ComponentFactory(c).manifest(c.knowledge_version,fixed_evidence_only=True)
        self.assertEqual(m['audit_strategy'],'source_first_audit_v4');self.assertEqual(m['prompts']['domain'],'power-domain-review-reference-v7');self.assertEqual(ServiceConfig().audit_strategy,'baseline')
    def test_domain_shape_instruction_retains_required_scope_and_strict_fields(self):
        from services.audit_reference_v7 import DOMAIN_SYSTEM
        self.assertIn('ONLY analysis_scope',DOMAIN_SYSTEM);self.assertIn('task_scope',DOMAIN_SYSTEM);self.assertIn('No extra fields',DOMAIN_SYSTEM)
    def test_two_hundred_request_boundary(self):
        from evaluation.audit_reference_v7 import Gate
        from types import SimpleNamespace as NS
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            gate=Gate(Path(t));r=NS(model_id='deepseek-flash',max_output_tokens=8000,messages=[])
            for c in range(10):
                for n in range(20):gate(dict(case=c,variant='candidate'),r,n)
            self.assertEqual(gate.calls,200);self.assertEqual(gate.threshold,3500000)
            with self.assertRaises(RuntimeError):gate(dict(case=10,variant='candidate'),r,1)
