"""Batched request-scoped bases, real calculation IDs and explicit delivery scope."""
from copy import deepcopy
from dataclasses import asdict,replace
import json
from agents.verification_contract_v8 import SYSTEM as SEMANTICS
from agents.verification_contract_v5 import parse_v5
from agents.verification_contract_v6 import parse_bases as source_bases
from agents.verification_contract_v7 import missing_parts
from agents.verification_contract_v8 import baseline, projected_snapshot
from agents.contracts import EvidenceVerificationOutput
from core.models import TypedBasis,CalculationBasis,ExecutionIssue,ExecutionStatus
from core.validation import merge_evidence,validate_review
from services.answer_anchors import anchors
from services.scoped_candidates import CandidateScope
from services.quote_candidates import build_candidates
from services.evidence_scope import metadata_fields
from services.quantity_checks import check_verification_quantities
from services.review_isolation import WireIsolation
from services.structured_model import structured_request
from services.validation_diagnostics import ErrorCollector
from model_adapter.contracts import ModelMessage
from model_adapter.runtime import current_budget

PROMPT_VERSION='evidence-verification-v9.1-delivery-tools-context'
CONTRACT_VERSION='evidence-verification-output-v9.1'
SYSTEM=SEMANTICS+'''
V9 overrides request grouping: ONE root EXACT findings,citation_reviews, cover all supplied eligible
claims and each original citation. Each citation has its OWN permitted scoped quote list; NEVER
select an independent quote to repair an original citation. A valid finding is not evidence of all others.
answer_text_reference EXACT type,anchor_id from ANSWER_ANCHORS; program binds original paragraph.
calculation_result_reference EXACT type,result_id from TOOL_RESULTS. Only complete mathematical
scalar equality propositions may use calculation basis. Phrase that component as A unit = B unit,
or A unit does not equal B unit. Never use conversion to support stability, feasibility or unit category law.
A correct conversion has a real rule/result; user input is unverified, do not rewrite MW as Mvar.
input_snapshot_reference supports accurate reports of supplied input and its actual coverage only.
The FULL_INPUT_DELIVERY object says whether ALL original bodies were actually delivered.
If false, program-owned missing components are excluded. Hashes do not prove absence from body text.
Preserve assertion_role: reported_error/input_report is not endorsement; corrections expose new facts
for review. A provided number is not a verified physical state. A bounded inference may be assessed
from source meaning with stated conditions, without requiring identical wording; reasoning still matters.
METADATA_ORIGINS identify index/user-maintained fields, NOT official body quotes. Never attribute
an index applicability note to the PDF itself. Document-content attributions still require body text.
DELIVERY_RECORD omissions bound this request, not an exhaustive search of all literature/world.
Legal unsupported response: {"findings":[{"claim_id":"actual-claim","rationale":"No support for this qualified claim.","applicability_conditions":[],"bases":[],"component_reviews":[{"component_index":0,
"status":"insufficient_evidence","basis_indexes":[],"rationale":"No matching support."}]}],"citation_reviews":[]}.
Legal basis shapes: {"type":"text_excerpt","quote_id":"current-scoped-id"},
{"type":"metadata_reference","evidence_id":"actual-evidence","field_path":"actual-nonnull-field"},
{"type":"input_snapshot_reference"}, {"type":"answer_text_reference","anchor_id":"actual-answer-anchor"},
{"type":"calculation_result_reference","result_id":"actual-tool-result"}. No null/extra fields.
'''

def catalog(inputs,protocol_version=CONTRACT_VERSION):
    independent=CandidateScope(inputs.answer,inputs.knowledge_version,'independent',inputs.seed_evidence,protocol_version=protocol_version)
    original={e.evidence_id:e for e in inputs.original_evidence}
    scopes=[independent]+[CandidateScope(inputs.answer,inputs.knowledge_version,'original_citation',tuple(original[e] for e in c.evidence_ids),check_id=i,protocol_version=protocol_version) for i,c in enumerate(inputs.answer.citations)]
    return scopes

def full_delivered(inputs):
    s=inputs.generation_snapshot
    return bool(s and s.snapshot_version=='generation-full-input-v2' and sum(len(e.text) for e in s.evidence)<=32000)

def parse(value,inputs,scopes,prompt_version=PROMPT_VERSION):
    missing={} if full_delivered(inputs) else {c.claim_id:tuple(i for i,p in enumerate(c.components) if p.category=='input_evidence_coverage') for c in inputs.claims}
    ec=ErrorCollector('evidence_verification_v9');ec.fields(value,{'findings','citation_reviews'},set(),'$')
    value=deepcopy(value)
    if not ec.check(isinstance(value,dict) and type(value.get('findings')) is list,'$.findings','array_required'):ec.finish()
    expected={c.claim_id for c in inputs.claims if len(missing.get(c.claim_id,()))<len(c.components)}
    ec.check({f.get('claim_id') for f in value['findings'] if type(f) is dict}==expected,'$.findings','eligible_claims_exactly_once_required')
    for f in value['findings']:
        if not isinstance(f,dict):continue
        forbidden=missing.get(f.get('claim_id'),())
        for r in f.get('component_reviews',[]) if type(f.get('component_reviews')) is list else []:
            ec.check(isinstance(r,dict) and r.get('component_index') not in forbidden,'$.findings.component_reviews','program_owned_missing_body_component_forbidden')
    ec.finish()
    by_id={f['claim_id']:f for f in value['findings']}
    for c in inputs.claims:
        if c.claim_id not in by_id:by_id[c.claim_id]={'claim_id':c.claim_id,'rationale':'Required input body not delivered','applicability_conditions':[],'bases':[],'component_reviews':[]}
        for i in missing.get(c.claim_id,()):by_id[c.claim_id]['component_reviews'].append({'component_index':i,'status':'not_assessable','basis_indexes':[],'rationale':'missing_input_snapshot_or_body_not_delivered'})
    value['findings']=[by_id[c.claim_id] for c in inputs.claims]
    anchor_map={a['anchor_id']:a for a in anchors(inputs.answer)}
    def basis_parser(items,current,path,*,citation=None,collector=None):
        ec=collector or ErrorCollector('evidence_verification_v9');out=[];scope=scopes[0 if citation is None else citation+1]
        if not ec.check(type(items) is list,path,'basis_array_required'):return ()
        for i,item in enumerate(items):
            p=f'{path}[{i}]';kind=item.get('type') if type(item) is dict else None
            if kind=='calculation_result_reference':
                if ec.fields(item,{'type','result_id'},set(),p) and ec.check(citation is None and item['result_id'] in {t.result_id for t in current.tool_results if t.status==ExecutionStatus.SUCCEEDED},p+'.result_id','current_successful_calculation_required_not_original_citation'):
                    out.append(CalculationBasis(kind,calculation_result_id=item['result_id']))
                else:out.append(None)
                continue
            translated=deepcopy(item)
            if kind=='answer_text_reference':
                if not ec.fields(item,{'type','anchor_id'},set(),p) or not ec.check(citation is None and item['anchor_id'] in anchor_map,p+'.anchor_id','current_answer_anchor_required'):
                    out.append(None);continue
                a=anchor_map[item['anchor_id']];translated={'type':kind,'quote':a['text'],'prefix':current.answer.text[:a['start_offset']],'suffix':current.answer.text[a['end_offset']:]}
            if kind=='text_excerpt':
                if not ec.fields(item,{'type','quote_id'},set(),p):out.append(None);continue
                resolved=scope.resolve(item['quote_id'],p+'.quote_id',ec)
                if resolved is None:out.append(None);continue
                translated={'type':kind,'quote_id':resolved}
            if kind=='input_snapshot_reference' and not ec.check(full_delivered(current),p,'complete_original_body_delivery_required'):
                out.append(None);continue
            out.extend(source_bases([translated],current,p,citation=citation,collector=ec,candidates=scope.candidates))
        return tuple(out)
    result=parse_v5(value,inputs,basis_parser=basis_parser,response_prompt_version=prompt_version,
        quote_candidates=build_candidates(tuple(e for e in merge_evidence(inputs.seed_evidence,inputs.original_evidence) if e.evidence_id in {c.evidence_id for s in scopes for c in s.candidates})))
    result=replace(result,consistency_checks=check_verification_quantities(result,version='quantity-enumeration-v1.2'))
    if missing:
        reason='input_body_not_delivered' if inputs.generation_snapshot and inputs.generation_snapshot.snapshot_version=='generation-full-input-v2' else 'missing_input_snapshot'
        missing_ids={c.claim_id:{c.components[i].component_id for i in missing.get(c.claim_id,())} for c in inputs.claims}
        result=replace(result,findings=tuple(replace(f,component_reviews=tuple(replace(r,origin='program_precondition',reason_code=reason)
            if r.component_id in missing_ids.get(f.claim_id,set()) else r for r in f.component_reviews)) for f in result.findings))
    return result

async def run(agent,inputs):
    if current_budget() is None:
        from model_adapter.runtime import ModelBudget,model_scope
        with model_scope(ModelBudget(2)):return await run(agent,inputs)
    scopes=catalog(inputs);wire=baseline(inputs)
    missing={} if full_delivered(inputs) else {c.claim_id:tuple(i for i,p in enumerate(c.components) if p.category=='input_evidence_coverage') for c in inputs.claims}
    wire['findings']=[f for f in wire['findings'] if len(missing.get(f['claim_id'],()))<len(f['component_reviews'])]
    for f in wire['findings']:f['component_reviews']=[r for r in f['component_reviews'] if r['component_index'] not in missing.get(f['claim_id'],())]
    def mark(output,rejected,errors):
        return replace(output,findings=tuple(replace(f,component_reviews=tuple(replace(r,origin='execution_incomplete',reason_code='model_execution_incomplete')
            if r.origin!='program_precondition' else r for r in f.component_reviews)) if ('findings',f.claim_id) in rejected else f for f in output.findings),
            execution_issues=(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,'PARTIAL_CONTRACT_ERROR','Rejected findings incomplete; valid peers retained'),))
    isolation=WireIsolation(wire,lambda v:parse(v,inputs,scopes),{'findings':'claim_id','citation_reviews':'citation_index'},mark)
    all_evidence=merge_evidence(inputs.seed_evidence,inputs.original_evidence)
    payload={'answer':asdict(inputs.answer),'claims':[asdict(c) for c in inputs.claims],
        'ANSWER_ANCHORS':anchors(inputs.answer),'INDEPENDENT':scopes[0].payload(),
        'ORIGINAL_CITATION_SCOPES':[s.payload() for s in scopes[1:]],'METADATA_FIELDS':{e.evidence_id:metadata_fields(e) for e in all_evidence},
        'METADATA_ORIGINS':{e.evidence_id:{k:('index_maintenance_information' if k in ('applicability','source_type') else 'index_or_user_source_manifest_unverified_against_body') for k in metadata_fields(e)} for e in all_evidence},
        'TOOL_RESULTS':[asdict(t) for t in inputs.tool_results],
        'DELIVERY_RECORD':inputs.delivery_summary,
        'FULL_INPUT_DELIVERY':{'snapshot_saved':inputs.generation_snapshot is not None,'full_body_delivered':full_delivered(inputs),'metadata_only':inputs.generation_snapshot is not None and not full_delivered(inputs)},
        'GENERATION_INPUT_SNAPSHOT':asdict(inputs.generation_snapshot) if full_delivered(inputs) else projected_snapshot(inputs),
        'PROGRAM_OWNED_MISSING_COMPONENTS':missing}
    path=None if agent.diagnostics is None else agent.diagnostics.save_scope(payload)
    before=len(current_budget().records)
    try:
        result,records=await structured_request(agent.client,(__import__('model_adapter.contracts',fromlist=['ModelMessage']).ModelMessage('system',SYSTEM),
            __import__('model_adapter.contracts',fromlist=['ModelMessage']).ModelMessage('user',json.dumps(payload,ensure_ascii=False))),PROMPT_VERSION,isolation.parse,
            diagnostics=agent.diagnostics,response_contract_version=CONTRACT_VERSION,candidate_catalog_path=path)
        return replace(result,model_records=tuple(r for r in records if r.prompt_version==PROMPT_VERSION))
    except Exception as exc:
        if not getattr(exc,'code',None):raise
        result=getattr(exc,'partial_output',None) or parse(wire,inputs,scopes)
        return replace(result,execution_issues=(ExecutionIssue('evidence_verification',ExecutionStatus.FAILED,exc.code,'Verification incomplete; validated peers retained'),),
            model_records=tuple(r for r in current_budget().records[before:] if r.prompt_version==PROMPT_VERSION))
