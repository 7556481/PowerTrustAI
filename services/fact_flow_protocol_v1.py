"""Versioned internal-flow protocol. IDs and bindings reuse existing catalogs.

No B extractor/profile or evaluation reviewer is selected. Classification and
fidelity are independent records. Numeric relations retain operand provenance.
"""
from copy import deepcopy
from dataclasses import asdict, fields, replace
from decimal import Decimal, InvalidOperation
import re
from agents.verification_contract_v14 import ReviewCatalog, SYSTEM as BASE_SYSTEM
from agents import verification_contract_v9 as common
from agents.contracts import FactFlowOutput
from core.models import VerificationStatus as V
from core.validation import require
from services.validation_diagnostics import ErrorCollector
from services.task_premises_v1 import catalog as premise_catalog
from services.premise_review_protocol_v1 import parse_basis

VERSION = 'fact-internal-flow-v1'
PROMPT = 'evidence-verification-v9.30-fact-internal-flow-v1-dev'
KINDS = {'literature_rule','premise_restatement','rule_application','numeric_comparison','external_fact','engineering_relation','ordinary','uncertain'}
SYSTEM = BASE_SYSTEM + '''
INTERNAL FLOW V1 overrides the objection field above: do NOT output objection.
Each judgment additionally requires object_kind, classification_objection, fidelity,
fidelity_reason, dependencies, comparison. classification_objection is null or a
nonempty reason describing disagreement with the supplied extracted category or
obligation. Fidelity is faithful/disputed/uncertain and ONLY compares literal answer
with extracted proposition. An answer saying the opposite of evidence may still
be faithfully extracted. Classification is independent of support and coverage.
object_kind: literature_rule, premise_restatement, rule_application,
numeric_comparison, external_fact, engineering_relation, ordinary, uncertain.
For citations use ordinary, classification_objection=null, fidelity=faithful,
dependencies=[], comparison=null. Original citation scopes NEVER accept premises.
dependencies is the exact subset of selected basis_ids actually needed for the
conclusion: do not select irrelevant premises to satisfy a count. The complete
premise catalog is NOT a requirement to use every premise. Rule restatement does
not depend on current premises merely because an application shares its paragraph.
Rule application requires relevant rule BODY and stipulated current premises;
explain all necessary conditions, exceptions, polarity and causal direction.
Premise restatement judges reporting accuracy, not real-world truth of a premise.
For numeric_comparison, comparison EXACT {left,right,operator,left_basis_id,
right_basis_id}; left/right EXACT {value,quote}. value is a decimal string, quote
is the literal source substring containing that value. operator is <,<=,==,!=,>=,>.
Both operand basis IDs must be selected dependencies, from body or premises.
Explain common units and scope; absent equivalence or engineering assumptions
requires uncertainty. Program verifies only the scalar relation, NOT physical
meaning, device behavior, engineering formula or source truth. Numeric sources
must not disappear even when the relation is simple. For other kinds comparison=null.
Engineering relations require body evidence; absent actual tool capability must
remain an explicit limitation in reason. Do not pretend scalar conversion proves
an engineering formula. No new tools are exposed at this step. Supplied successful
tool results retain their original narrow scope. Missing evidence permits honest
insufficient_evidence; unsupported tools or unresolved classification permit
not_assessable. No search until pass. Classification objection never silently
reclassifies and passes. Program supplies identities, fields, legal scope and
positions; return semantic judgments and exact catalog selections only.
'''


def full_wire(inputs):
    return {'findings':[{'claim_id':c.claim_id,'rationale':'model_execution_incomplete',
        'applicability_conditions':[],'bases':[], 'component_reviews':[
        {'component_index':i,'status':'not_assessable','basis_indexes':[],
         'rationale':'model_execution_incomplete'} for i in range(len(c.components))]}
        for c in inputs.claims], 'citation_reviews':[{'citation_index':i,
        'status':'not_assessable','rationale':'model_execution_incomplete',
        'applicability_conditions':[],'bases':[]} for i in range(len(inputs.answer.citations))]}, {}


def validate_projection(output, claim, review, finding, path):
    require(output.flow_protocol in (VERSION, 'fact-internal-flow-v2'), 'known flow protocol required', path=path)
    record=next((r for r in output.object_reviews if r['claim_id']==claim.claim_id and r['component_id']==review.component_id),None)
    require(record is not None, 'candidate object record required', path=path)
    if record['classification_objection'] or record['fidelity']!='faithful' or record['object_kind']=='uncertain':
        require(review.status==V.NOT_ASSESSABLE, 'object/fidelity objection cannot pass', path=path)
    return record['object_kind'] in KINDS-{'ordinary'}


class Catalog(ReviewCatalog):
    protocol_version = VERSION
    prompt_version_flow = PROMPT
    def __init__(self, inputs):
        super().__init__(inputs, wire_factory=full_wire,contract_version=self.protocol_version)
        self.premises=premise_catalog(inputs.request)
        for i,p in enumerate(self.premises):
            self.bases['P'+str(i)]={'wire':{'type':'task_premise_reference','premise_id':p.premise_id},
                'text':p.text, 'scope_index':0, 'premise':asdict(p)}
        for tid,t in self.targets.items():
            if t['kind']=='fact' and t['category'] in ('technical_fact','input_evidence_coverage'):
                allowed=[b for b,v in self.bases.items() if v['scope_index']==0 and v['wire']['type'] in ('text_excerpt','task_premise_reference')]
                delivery=t.get('delivery')
                if delivery:
                    allowed=[b for b in allowed if self.bases[b]['wire']['type']!='text_excerpt' or self.bases[b]['evidence_id'] in delivery['delivered_evidence_ids']]
                    if delivery['outcome'] in ('failed','budget_exhausted','timed_out','cancelled','classification_unresolved'):allowed=[]
                # Preserve narrow original capabilities as alternatives, not truths.
                t['allowed_basis_ids']=list(dict.fromkeys(t['allowed_basis_ids']+allowed))
            t['basis_types']=sorted({self.bases[b]['wire']['type'] for b in t['allowed_basis_ids']})
            t['condition_basis_ids']=[b for b in t['allowed_basis_ids'] if self.bases[b]['wire']['type']=='text_excerpt']
            t['repair_basis_ids']=list(t['condition_basis_ids'])
            self.rows[tid].pop('objection')
            self.rows[tid].update(object_kind='ordinary' if t['kind']=='citation' else 'uncertain',
                classification_objection=None,fidelity='faithful' if t['kind']=='citation' else 'uncertain',
                fidelity_reason='model_execution_incomplete',dependencies=[],comparison=None)
        self.active_rows=self.rows

    def payload(self, ids):
        value=super().payload(ids);value['contract']=self.protocol_version
        value['answer_id']=self.inputs.answer.answer_id;value['answer_version']=self.inputs.answer.version
        value['available_tools']=[]
        if any(self.targets[t]['kind']=='fact' for t in ids):
            value['delivered_tool_outcomes']=[{'result_id':t.result_id,'status':t.status.value,'tool_name':t.tool_name} for t in self.inputs.tool_results]
        value['tool_policy']='Already delivered scalar tool results only; no device/engineering calculator.'
        return value

    def parse_one(self,row,target,path):
        ec=ErrorCollector(self.protocol_version)
        required={'target_id','status','basis_ids','reason','conditions','repair','requires_authoritative_source',
                  'object_kind','classification_objection','fidelity','fidelity_reason','dependencies','comparison'}
        if not ec.fields(row,required,set(),path):ec.finish()
        kind=row['object_kind'];obj=row['classification_objection'];ids=row['basis_ids'];deps=row['dependencies']
        ec.check(type(kind) is str and kind in KINDS,path+'.object_kind','known_object_kind')
        ec.check(obj is None or type(obj) is str and bool(obj.strip()),path+'.classification_objection','null_or_explicit_objection')
        ec.check(row['fidelity'] in ('faithful','disputed','uncertain'),path+'.fidelity','independent_fidelity_required')
        ec.check(type(row['fidelity_reason']) is str and bool(row['fidelity_reason'].strip()),path+'.fidelity_reason','fidelity_reason_required')
        ec.check(type(ids) is list and all(type(b) is str and b in target['allowed_basis_ids'] for b in ids),path+'.basis_ids','legal_scoped_ids')
        ec.check(type(deps) is list and all(type(b) is str and type(ids) is list and b in ids for b in deps) and len(set(deps))==len(deps),path+'.dependencies','selected_dependency_subset')
        ec.finish()
        if target['kind']=='citation':
            ec.check(kind=='ordinary' and obj is None and row['fidelity']=='faithful' and not deps and row['comparison'] is None,path,'original_citation_scope_only')
        if target['kind']=='fact' and kind not in ('ordinary','uncertain'):
            expected_category='input_evidence_coverage' if kind=='premise_restatement' else 'technical_fact'
            ec.check(target['category']==expected_category or obj is not None,path+'.classification_objection','changed_obligation_requires_explicit_objection')
        types={self.bases[b]['wire']['type'] for b in deps}
        definitive=row['status'] in ('supported','contradicted')
        if kind=='literature_rule':ec.check('task_premise_reference' not in {self.bases[b]['wire']['type'] for b in ids},path,'rule_restatement_does_not_borrow_premises')
        if definitive and not obj and kind!='uncertain':
            if kind in ('literature_rule','external_fact','engineering_relation'):
                ec.check('text_excerpt' in types,path,'body_dependency_required')
            elif kind=='premise_restatement':
                ec.check(bool(types) and types=={'task_premise_reference'},path,'premise_dependency_required')
            elif kind=='rule_application':
                ec.check({'text_excerpt','task_premise_reference'}<=types,path,'actual_rule_and_premise_dependencies_required')
                ec.check(all(self.bases[b].get('premise',{}).get('kind')=='stipulated' for b in deps if self.bases[b]['wire']['type']=='task_premise_reference'),path,'unverified_report_not_stipulated')
        comparison=row['comparison'];computed=None
        if kind=='numeric_comparison' and comparison is not None:
            if ec.fields(comparison,{'left','right','operator','left_basis_id','right_basis_id'},set(),path+'.comparison'):
                numbers=[]
                for side in ('left','right'):
                    operand=comparison[side];bid=comparison[side+'_basis_id']
                    legal=type(bid) is str and bid in deps and self.bases[bid]['wire']['type'] in ('text_excerpt','task_premise_reference')
                    ec.check(legal,path+'.comparison','operand_source_must_be_selected_dependency')
                    if ec.fields(operand,{'value','quote'},set(),path+'.comparison.'+side):
                        q=operand['quote'];v=operand['value']
                        ec.check(type(q) is str and bool(q) and legal and q in self.bases[bid].get('text','') and type(v) is str and re.search(r'(?<![A-Za-z0-9.+-])'+re.escape(v)+r'(?![A-Za-z0-9.])',self.bases[bid].get('text','')) is not None and v in q,path+'.comparison.'+side,'literal_operand_source_required')
                        try:
                            n=Decimal(v);ec.check(n.is_finite(),path,'finite_decimal_required');numbers.append(n)
                        except (InvalidOperation,TypeError,ValueError):ec.check(False,path,'decimal_required')
                op=comparison['operator'];ec.check(op in ('<','<=','==','!=','>=','>'),path,'scalar_operator_required');ec.finish()
                a,b=numbers;computed={'<':a<b,'<=':a<=b,'==':a==b,'!=':a!=b,'>=':a>=b,'>':a>b}[op]
                if definitive:ec.check((row['status']=='supported')==computed,path,'scalar_result_disagrees_with_model_support')
        else:
            ec.check(comparison is None,path,'comparison_only_for_numeric_object')
            if kind=='numeric_comparison' and definitive:ec.check(False,path,'two_operand_sources_required')
        ec.finish()
        legacy={k:v for k,v in row.items() if k not in required-{'target_id','status','basis_ids','reason','conditions','repair','requires_authoritative_source'}}
        legacy['objection']=({'kind':'classification','reason':obj} if obj else
            {'kind':'fidelity','reason':row['fidelity_reason']} if row['fidelity']=='disputed' else
            {'kind':'uncertain','reason':row['fidelity_reason']} if row['fidelity']=='uncertain' or kind=='uncertain' else None)
        result=super().parse_one(legacy,target,path)
        result.update(object_kind=kind,classification_objection=obj,fidelity=row['fidelity'],
            fidelity_reason=row['fidelity_reason'],dependencies=deps,comparison=comparison,scalar_result=computed,contract=self.protocol_version,
            capability_limit='no_engineering_calculator; body_support_is_not_engineering_validation' if kind=='engineering_relation' else 'scalar_order_only; units_and_relevance_require_semantic_review' if kind=='numeric_comparison' else None)
        return result

    def project(self,rows):
        self.active_rows=rows
        out=super().project(rows)
        # Never encode classification as fidelity, even though the legacy projection
        # conservatively uses its objection channel internally.
        findings=[]
        for ci,f in enumerate(out.findings):
            parts=[]
            for pi,r in enumerate(f.component_reviews):
                row=rows[f'F{ci}C{pi}']
                parts.append(replace(r,fidelity_status=row['fidelity'],fidelity_rationale=row['fidelity_reason'],review_projection_version=self.protocol_version))
            findings.append(replace(f,component_reviews=tuple(parts)))
        return replace(out,findings=tuple(findings),prompt_version=self.prompt_version_flow)

    def mark(self,out,missing,errors):
        result=super().mark(out,missing,errors)
        absent={tid for _,tid in missing}
        missing_keys={(self.inputs.claims[t['claim_index']].claim_id,
                       self.inputs.claims[t['claim_index']].components[t['component_index']].component_id)
                      for tid,t in self.targets.items() if tid in absent and t['kind']=='fact'}
        return replace(result,object_reviews=tuple(dict(r,origin='execution_incomplete'
            if (r['claim_id'],r['component_id']) in missing_keys else 'model_judgment') for r in result.object_reviews))

    def parse_wire(self,wire):
        owner=self
        class Profile:
            @staticmethod
            def missing_components(inputs):return {}
            parse_basis=staticmethod(parse_basis)
            @staticmethod
            def component_validator(claim,index,bases,indexes,status,path,collector):
                ci=next(i for i,c in enumerate(owner.inputs.claims) if c.claim_id==claim.claim_id)
                return owner.active_rows[f'F{ci}C{index}']['object_kind']!='ordinary'
            @staticmethod
            def promote(out,inputs):
                records=[]
                for tid,t in owner.targets.items():
                    if t['kind']!='fact':continue
                    row=owner.active_rows[tid];a=owner.parse_one(row,t,'$.judgments.'+tid)
                    c=inputs.claims[t['claim_index']]
                    records.append(dict(a,claim_id=c.claim_id,component_id=c.components[t['component_index']].component_id))
                return FactFlowOutput(**{f.name:getattr(out,f.name) for f in fields(out)},task_premises=owner.premises,object_reviews=tuple(records),flow_protocol=owner.protocol_version)
        # Apply conservative objection disposition before the existing typed gate.
        safe=deepcopy(wire)
        for ci,f in enumerate(safe['findings']):
            for r in f['component_reviews']:
                tid=f'F{ci}C{r["component_index"]}';a=self.parse_one(self.active_rows[tid],self.targets[tid],'$.judgments.'+tid)
                r['status']=a['effective_support_status']
        return common.parse(safe,self.inputs,self.scopes,prompt_version=self.prompt_version_flow,premise_profile=Profile)
