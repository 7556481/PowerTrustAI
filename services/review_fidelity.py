"""Mandatory reviewer judgment of target fidelity; no automatic equivalence proof."""
from copy import deepcopy
from dataclasses import fields,replace
from services.validation_diagnostics import ErrorCollector
from services.answer_anchors import ROLES
from services.claim_obligations import TARGET_OBLIGATIONS
from core.models import FidelityComponentReview

def parse(value,inputs,delegate,*,strict_bindings=False):
    wire=deepcopy(value);ec=ErrorCollector('verification_target_fidelity_v1');reviews={}
    claims={c.claim_id:c for c in inputs.claims}
    for i,f in enumerate(wire.get('findings',[]) if type(wire) is dict else []):
        if type(f) is not dict:continue
        claim=claims.get(f.get('claim_id'))
        for j,r in enumerate(f.get('component_reviews',[]) if type(f.get('component_reviews')) is list else []):
            p=f'$.findings[{i}].component_reviews[{j}].semantic_review'
            if type(r) is not dict:continue
            sr=r.get('semantic_review')
            if not ec.fields(sr,{'fidelity','assertion_role','verification_obligation','rationale'},set(),p):continue
            ec.check(sr['fidelity'] in ('faithful','disputed','uncertain'),p+'.fidelity','explicit_fidelity_judgment_required')
            ec.check(sr['assertion_role'] in ROLES,p+'.assertion_role','known_answer_stance_required')
            ec.check(sr['verification_obligation'] in set(TARGET_OBLIGATIONS.values()),p+'.verification_obligation','known_semantic_obligation_required')
            ec.check(type(sr['rationale']) is str and bool(sr['rationale'].strip()),p+'.rationale','nonempty_semantic_fidelity_reason_required')
            index=r.get('component_index')
            if claim is not None and type(index) is int and 0<=index<len(claim.components):
                target=getattr(claim,'component_obligations',())
                mismatch=bool(target) and (sr['verification_obligation']!=target[index] or sr['assertion_role']!=claim.assertion_role)
                if sr['fidelity']!='faithful' or mismatch:
                    ec.check(r.get('status')=='not_assessable',p,'disputed_or_unresolved_verification_target_cannot_be_supported_or_contradicted')
                reviews[(claim.claim_id,index)]=sr
            del r['semantic_review']
    ec.finish();out=delegate(wire)
    findings=[]
    for f in out.findings:
        c=claims[f.claim_id];components=[]
        for index,r in enumerate(f.component_reviews):
            bound_index=next(n for n,part in enumerate(c.components) if part.component_id==r.component_id) if strict_bindings else index
            sr=reviews.get((c.claim_id,bound_index))
            if sr is None:components.append(r);continue # only program-owned missing/precondition components
            components.append(FidelityComponentReview(**{fld.name:getattr(r,fld.name) for fld in fields(r)},
                fidelity_status=sr['fidelity'],reviewed_assertion_role=sr['assertion_role'],verification_obligation=sr['verification_obligation'],fidelity_rationale=sr['rationale']))
        findings.append(replace(f,component_reviews=tuple(components)))
    return replace(out,findings=tuple(findings))

SYSTEM='''
CURRENT V9.3 independent finding component_reviews ALSO require semantic_review EXACT
{fidelity,assertion_role,verification_obligation,rationale}. This is a mandatory MODEL semantic
judgment, not program proof. fidelity faithful,disputed,uncertain. Inspect the literal original
anchor against the normalized proposition: did extraction preserve the technical assertion,
stance, negation, numbers, qualifications and required verification object?
verification_obligation technical_truth,metadata_value,input_provided,answer_scope,recommendation.
The fact that an answer WRITES X does NOT establish X is true. Endorsed technical X must
remain technical_truth even if an extractor incorrectly labeled it answer_scope.
If target/stance/fidelity is disputed or uncertain, status MUST not_assessable. Use the existing
classification_issue only for an ACTUAL different known category; never suggest the same category.
Uncertain equivalence with the same category needs not_assessable and a specific rationale, no issue.
Do not silently reclassify or repair the assertion. Other valid findings still continue.
Input_provided proves input presence/transcription only, not reality or engineering adequacy.
Report/refutation of an old error is not endorsement. Review the NEW corrected technical facts too.
An input_snapshot_reference basis is EXACT {"type":"input_snapshot_reference"}; the program
binds IDs/versions. Use it only for ACTUALLY DELIVERED snapshot fields/body, never omitted JSON.
An empty basis list with insufficient_evidence/not_assessable is valid. Same-category uncertainty
does NOT require inventing a classification_issue or switching to an unrelated basis.
Example component: {"component_index":0,"status":"not_assessable","basis_indexes":[],
"rationale":"Normalization changed verification target.","semantic_review":{"fidelity":"disputed",
"assertion_role":"asserted","verification_obligation":"technical_truth",
"rationale":"The anchor endorses a count but normalization merely reports answer wording."},
"classification_issue":{"suggested_category":"technical_fact","rationale":"A technical count needs truth checking."}}.
For correct mathematical relations, choose a real current conversion result. For unit-category
claims choose relevant body or insufficient_evidence, never scalar conversion alone.
'''
