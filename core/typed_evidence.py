"""Core constraints independent of model prompt shape, not semantic certification."""
from core.models import VerificationStatus
from core.validation import require, validate_excerpts, nonempty
from services.evidence_scope import metadata_fields, canonical

REQUIRED = {"technical_fact": "text_excerpt", "source_quality_metadata": "metadata_reference",
            "input_evidence_coverage": "input_snapshot_reference", "answer_scope": "answer_text_reference"}


def aggregate_status(reviews):
    states = {r.status for r in reviews}
    for status in (VerificationStatus.CONTRADICTED, VerificationStatus.NOT_ASSESSABLE, VerificationStatus.INSUFFICIENT_EVIDENCE):
        if status in states: return status
    return VerificationStatus.SUPPORTED


def validate_bases(bases, output, answer, path, *, allowed_ids=None, citation=False):
    known = {e.evidence_id:e for e in output.evidence}
    v6 = output.prompt_version is not None and output.prompt_version.startswith(("evidence-verification-v6", "evidence-verification-v7", "evidence-verification-v8", "evidence-verification-v9"))
    catalog = {c.quote_id:c for c in output.quote_candidates}
    for i, basis in enumerate(bases):
        p = f"{path}[{i}]"
        expected = {"text_excerpt": {"evidence_id", "excerpt"}, "metadata_reference": {"evidence_id", "metadata_reference"},
                    "input_snapshot_reference": {"snapshot_id"}, "answer_text_reference": {"answer_excerpt"}}
        if output.prompt_version and output.prompt_version.startswith('evidence-verification-v9'):
            expected['calculation_result_reference']={'calculation_result_id'}
        require(basis.type in expected, "unknown basis type", path=p + ".type")
        populated = {name for name in ("evidence_id", "excerpt", "metadata_reference", "snapshot_id", "answer_excerpt", "calculation_result_id") if getattr(basis, name) is not None}
        require(populated == expected[basis.type], "typed basis field combination mismatch", path=p)
        if basis.calculation_result_id:
            from tools.unit_conversion import validate_result
            from core.models import ExecutionStatus
            catalog_tools={t.result_id:t for t in output.tool_results}
            require(not citation and basis.calculation_result_id in catalog_tools,'registered current tool result required',path=p)
            tool=catalog_tools[basis.calculation_result_id];validate_result(tool)
            require(tool.status==ExecutionStatus.SUCCEEDED,'failed calculation cannot support judgment',path=p)
        if v6 and basis.type == "text_excerpt":
            require(basis.quote_id is not None and basis.quote_id in catalog, "required program candidate missing", path=p + ".quote_id")
        if basis.quote_id is not None:
            import hashlib
            require(basis.type == "text_excerpt" and basis.evidence_id in known,
                    "catalog quote only allowed on text evidence", path=p + ".quote_id")
            evidence = known[basis.evidence_id]
            if v6:
                candidate = catalog[basis.quote_id]
                require(basis.evidence_id == candidate.evidence_id and basis.excerpt.text == candidate.text
                        and basis.excerpt.start_offset == candidate.start_offset and basis.excerpt.end_offset == candidate.end_offset,
                        "selected candidate binding mismatch",path=p + ".quote_id")
            else:
                expected_id = "quote-" + hashlib.sha256((evidence.evidence_id + "\0" + evidence.text).encode("utf-8")).hexdigest()[:24]
                require(basis.quote_id == expected_id and basis.excerpt.text == evidence.text and basis.excerpt.start_offset == 0
                        and basis.excerpt.end_offset == len(evidence.text), "catalog quote binding mismatch", path=p + ".quote_id")
        if basis.evidence_id is not None:
            require(basis.evidence_id in known and (allowed_ids is None or basis.evidence_id in allowed_ids), "basis evidence outside permitted scope", path=p + ".evidence_id")
        if basis.excerpt is not None:
            require(basis.excerpt.evidence_id == basis.evidence_id, "basis excerpt ID mismatch", path=p)
            validate_excerpts((basis.excerpt,), output.evidence, p + ".excerpt")
        if basis.metadata_reference is not None:
            ref = basis.metadata_reference
            data = metadata_fields(known[basis.evidence_id])
            require(ref.evidence_id == basis.evidence_id and ref.field_path in data and data[ref.field_path] is not None,
                    "metadata must bind existing nonnull field", path=p + ".metadata_reference")
            require(ref.value_json == canonical(data[ref.field_path]), "metadata actual value mismatch", path=p + ".metadata_reference.value_json")
        if basis.snapshot_id is not None:
            require(not citation and output.generation_snapshot is not None and basis.snapshot_id == output.generation_snapshot.snapshot_id,
                    "complete generation snapshot required", path=p + ".snapshot_id")
        if basis.answer_excerpt is not None:
            span = basis.answer_excerpt
            require(not citation and 0 <= span.start_offset < span.end_offset <= len(answer.text)
                    and answer.text[span.start_offset:span.end_offset] == span.text, "frozen answer basis mismatch", path=p + ".answer_excerpt")


def validate_typed_finding(finding, claim, output, answer, path):
    require(finding.assessment_basis == "typed_components" and finding.scope_id is None, "typed finding binding mismatch", path=path)
    require(bool(claim.components), "explicit frozen components required", path=path + ".component_reviews")
    categories = {c.category for c in claim.components}
    require(finding.claim_category == (next(iter(categories)) if len(categories) == 1 else "mixed"), "component category projection mismatch", path=path)
    validate_bases(finding.bases, output, answer, path + ".bases")
    for i,basis in enumerate(finding.bases):
        if basis.calculation_result_id:
            tool=next(t for t in output.tool_results if t.result_id==basis.calculation_result_id)
            require(tool.payload['input']['claim_id']==claim.claim_id,'calculation belongs to another frozen claim',path=f'{path}.bases[{i}]')
    require(finding.excerpts == tuple(b.excerpt for b in finding.bases if b.excerpt)
            and finding.metadata_refs == tuple(b.metadata_reference for b in finding.bases if b.metadata_reference), "typed basis projection mismatch", path=path)
    require(finding.evidence_ids == tuple(dict.fromkeys(b.evidence_id for b in finding.bases if b.evidence_id)), "typed evidence IDs mismatch", path=path)
    parts = {p.component_id:p for p in claim.components}
    require(len(finding.component_reviews) == len(parts) and {r.component_id for r in finding.component_reviews} == set(parts), "component coverage incomplete", path=path)
    for i, rev in enumerate(finding.component_reviews):
        p = f"{path}.component_reviews[{i}]"
        nonempty(rev.rationale, p + ".rationale")
        require(len(set(rev.basis_indexes)) == len(rev.basis_indexes) and all(type(n) is int and 0 <= n < len(finding.bases) for n in rev.basis_indexes), "invalid basis indexes", path=p)
        category = parts[rev.component_id].category
        if output.prompt_version=='evidence-verification-v9.4-standalone-templates' and rev.origin=='model_judgment':
            require(type(rev).__name__=='FidelityComponentReview','new model judgment requires its semantic target review',path=p)
        if type(rev).__name__=='FidelityComponentReview':
            from services.answer_anchors import ROLES
            from services.claim_obligations import TARGET_OBLIGATIONS
            require(rev.fidelity_status in ('faithful','disputed','uncertain') and rev.reviewed_assertion_role in ROLES and rev.verification_obligation in set(TARGET_OBLIGATIONS.values()),'invalid semantic target review',path=p)
            nonempty(rev.fidelity_rationale,p+'.fidelity_rationale')
            index=next(n for n,c in enumerate(claim.components) if c.component_id==rev.component_id)
            mismatch=rev.reviewed_assertion_role!=claim.assertion_role or rev.verification_obligation!=claim.component_obligations[index]
            if rev.fidelity_status!='faithful' or mismatch:
                require(rev.status==VerificationStatus.NOT_ASSESSABLE,'unresolved target fidelity cannot assert technical support',path=p)
        require(rev.origin in ("model_judgment","program_precondition","execution_incomplete"), "unknown component origin", path=p + ".origin")
        if rev.origin=="execution_incomplete":
            require(rev.status==VerificationStatus.NOT_ASSESSABLE and not rev.basis_indexes and rev.reason_code=="model_execution_incomplete",
                    "Unexecuted semantic check cannot assert support",path=p)
        if rev.origin=="program_precondition":
            v9=bool(output.prompt_version and output.prompt_version.startswith('evidence-verification-v9'))
            require(category=="input_evidence_coverage" and (output.generation_snapshot is None or output.generation_snapshot.snapshot_version!="generation-full-input-v2" or v9 and not output.input_body_delivered)
                    and rev.reason_code in ({'missing_input_snapshot','input_body_not_delivered'} if v9 else {'missing_input_snapshot'}) and rev.status==VerificationStatus.NOT_ASSESSABLE and not rev.basis_indexes,
                    "Program premise cannot replace a semantic judgment",path=p)
        if output.prompt_version and output.prompt_version.startswith(("evidence-verification-v7","evidence-verification-v8")) and category == "input_evidence_coverage" and (output.generation_snapshot is None or output.prompt_version.startswith(("evidence-verification-v7.1","evidence-verification-v8")) and output.generation_snapshot.snapshot_version!="generation-full-input-v2"):
            require(rev.origin == "program_precondition" and rev.reason_code == "missing_input_snapshot" and rev.status==VerificationStatus.NOT_ASSESSABLE and not rev.basis_indexes,
                    "missing snapshot must be owned by program",path=p)
        if rev.classification_issue is not None:
            issue = rev.classification_issue
            require(issue.suggested_category in set(REQUIRED) | {"review_recommendation"} and issue.suggested_category != category,
                    "classification suggestion must be different known category", path=p + ".classification_issue")
            nonempty(issue.rationale, p + ".classification_issue.rationale")
            require(rev.status == VerificationStatus.NOT_ASSESSABLE, "classification disagreement cannot weaken support rules", path=p + ".status")
        types = {finding.bases[n].type for n in rev.basis_indexes}
        if rev.status in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED):
            calc=bool(output.prompt_version and output.prompt_version.startswith('evidence-verification-v9') and category=='technical_fact' and 'calculation_result_reference' in types)
            require(REQUIRED.get(category) in types or calc, "component lacks matching support basis", path=p)
            if calc:
                targets=getattr(claim,'component_basis_targets',())
                if targets:
                    target=targets[next(i for i,c in enumerate(claim.components) if c.component_id==rev.component_id)]
                    require(target=='mathematical_relation','calculation cannot support document attribution or engineering content',path=p+'.basis_indexes')
                from tools.unit_conversion import validate_claim_conversion
                for n in rev.basis_indexes:
                    b=finding.bases[n]
                    if b.calculation_result_id:
                        tool=next(t for t in output.tool_results if t.result_id==b.calculation_result_id)
                        validate_claim_conversion(parts[rev.component_id].proposition,claim.claim_id,tool,rev.status,p+'.basis_indexes')
        if category == "input_evidence_coverage" and output.generation_snapshot is None:
            require(rev.status == VerificationStatus.NOT_ASSESSABLE and not rev.basis_indexes, "historical input coverage unavailable", path=p)
        if category == "review_recommendation":
            require(rev.status == VerificationStatus.NOT_ASSESSABLE, "advice is not verified fact", path=p)
        if category != "input_evidence_coverage":
            require("input_snapshot_reference" not in types, "snapshot is not support for another category", path=p)
    require(finding.status == aggregate_status(finding.component_reviews), "mixed claim aggregate status mismatch", path=path + ".status")
