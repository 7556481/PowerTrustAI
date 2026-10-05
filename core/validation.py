"""Boundary validation. Invalid user input and invalid component output differ."""

from dataclasses import fields, is_dataclass
from enum import Enum
import math
import types
from typing import Union, get_args, get_origin, get_type_hints

from core.models import *


class ContractError(ValueError):
    def __init__(self, message, diagnostic=None):
        self.diagnostic = diagnostic
        super().__init__(message)


class InputError(ContractError):
    pass


def require(condition, message, *, path=None):
    if not condition:
        diagnostic = None if path is None else {
            "stage": "core_validation", "field_path": path, "constraint": message}
        raise ContractError(message, diagnostic)


def validate_types(value, annotation=None, path="value"):
    """Validate nested dataclasses, immutable tuples, enums and primitive types."""
    if annotation is not None:
        origin, args = get_origin(annotation), get_args(annotation)
        from collections.abc import Mapping
        if origin in (dict,Mapping):
            require(isinstance(value,Mapping),'expected mapping',path=path)
            def json_value(item,where,depth=0):
                require(depth<=64,'JSON nesting limit exceeded',path=where)
                if type(item) is dict:
                    for key,child in item.items():
                        require(type(key) is str,'JSON key must be string',path=where)
                        json_value(child,where+'.'+key,depth+1)
                elif type(item) in (tuple,list):
                    for i,child in enumerate(item):json_value(child,f'{where}[{i}]',depth+1)
                else:require(item is None or type(item) in (str,int,bool) or type(item) is float and math.isfinite(item),'finite JSON value required',path=where)
            json_value(dict(value),path)
            return
        if origin in (Union, types.UnionType):
            for option in args:
                try:
                    validate_types(value, option, path)
                    return
                except ContractError:
                    pass
            require(False, "incompatible union value", path=path)
        if origin is tuple:
            require(type(value) is tuple, "expected tuple", path=path)
            for index, item in enumerate(value):
                validate_types(item, args[0], f"{path}[{index}]")
            return
        if annotation is float:
            require(type(value) in (int, float) and math.isfinite(value), "expected finite number", path=path)
        else:
            allowed_subtypes={'AuditDecision':'ProductDecision','ComponentReview':'FidelityComponentReview','Claim':'ContextualClaim','TypedBasis':'CalculationBasis','EvidenceVerificationInput':'ReliabilityVerificationInput',
                'EvidenceVerificationOutput':'ReliabilityVerificationOutput','PowerDomainReviewInput':'ReliabilityDomainInput','HarnessResult':'ToolHarnessResult'}
            if isinstance(annotation,type) and is_dataclass(annotation) and type(value).__name__ in ((allowed_subtypes.get(annotation.__name__),) if annotation.__name__!='Claim' else ('ContextualClaim','BasisAwareClaim','ObligationClaim')) and type(value).__module__==annotation.__module__ and isinstance(value,annotation):
                validate_types(value);return
            require(isinstance(value, annotation) if isinstance(annotation, type) and issubclass(annotation, Enum)
                    else type(value) is annotation, f"expected {annotation}", path=path)
    if is_dataclass(value):
        hints = get_type_hints(type(value))
        for field in fields(value):
            validate_types(getattr(value, field.name), hints[field.name], f"{path}.{field.name}")


def nonempty(value, name):
    require(isinstance(value, str) and bool(value.strip()), "nonempty string required", path=name)


def unique(items, attribute):
    ids = [getattr(item, attribute) for item in items]
    require(len(ids) == len(set(ids)), f"duplicate {attribute}")
    for identifier in ids:
        nonempty(identifier, attribute)


def merge_evidence(*groups):
    merged = {}
    for group in groups:
        unique(group, "evidence_id")
        for evidence in group:
            validate_types(evidence, Evidence)
            for name in ("source_id", "source_version", "locator", "text", "source_type"):
                nonempty(getattr(evidence, name), name)
            require(evidence.evidence_id not in merged or merged[evidence.evidence_id] == evidence,
                    f"conflicting evidence ID: {evidence.evidence_id}")
            merged[evidence.evidence_id] = evidence
    return tuple(merged.values())


def validate_answer(answer, evidence):
    validate_types(answer, AnswerDraft)
    nonempty(answer.answer_id, "answer_id")
    nonempty(answer.text, "answer.text")
    require(answer.version >= 1, "answer version must be positive")
    known = {e.evidence_id for e in evidence}
    for binding in answer.citations:
        require(0 <= binding.start_offset < binding.end_offset <= len(answer.text), "invalid citation span")
        require(bool(binding.evidence_ids) and set(binding.evidence_ids) <= known, "unknown citation evidence ID")


def validate_claims(claims, answer):
    validate_types(claims, tuple[Claim, ...])
    require(bool(claims), "claim extraction must not silently return an empty audit")
    unique(claims, "claim_id")
    for claim in claims:
        require((claim.answer_id, claim.answer_version) == (answer.answer_id, answer.version), "claim answer version mismatch")
        require(0 <= claim.start_offset < claim.end_offset <= len(answer.text), "invalid claim span")
        require(answer.text[claim.start_offset:claim.end_offset] == claim.text, "claim text differs from answer span")
        nonempty(claim.claim_type, "claim_type")
        if claim.proposition is not None:
            nonempty(claim.proposition, "claim.proposition")
        require(claim.assertion_role in {'legacy_unspecified','asserted','input_report','reported_error','correction','conditional','assumption','missing_information'},'unknown assertion semantic role',path='$.claims.assertion_role')
        require(all(q in claim.text and q.strip() for q in claim.qualifiers), "claim qualifier not literal")
        if isinstance(claim,BasisAwareClaim):
            from services.answer_basis_targets import validate_targets
            validate_targets(claim)
        if type(claim).__name__=='ObligationClaim':
            from services.claim_obligations import validate_obligations
            validate_obligations(claim)
        unique(claim.components, "component_id")
        for component in claim.components:
            require(component.category in {"technical_fact", "source_quality_metadata", "input_evidence_coverage", "answer_scope", "review_recommendation"}, "unknown component category")
            nonempty(component.proposition, "component.proposition")


def validate_excerpts(excerpts, evidence, path="$.excerpts"):
    known = {e.evidence_id: e for e in evidence}
    for index, quote in enumerate(excerpts):
        item_path = f"{path}[{index}]"
        validate_types(quote, EvidenceExcerpt)
        require(quote.evidence_id in known, "unknown excerpt evidence", path=f"{item_path}.evidence_id")
        text = known[quote.evidence_id].text
        require(0 <= quote.start_offset < quote.end_offset <= len(text), "invalid evidence excerpt span", path=item_path)
        require(text[quote.start_offset:quote.end_offset] == quote.text, "evidence excerpt text mismatch", path=f"{item_path}.text")


def validate_extraction(output, answer):
    validate_types(output, ClaimExtractionOutput)
    require((output.answer_id, output.answer_version) == (answer.answer_id, answer.version), "Extraction version mismatch")
    validate_claims(output.claims, answer)
    for span in output.non_claim_spans + output.uncovered_spans:
        require(0 <= span.start_offset < span.end_offset <= len(answer.text), "Invalid extraction coverage span")
        require(answer.text[span.start_offset:span.end_offset] == span.text, "Invalid coverage quote")
        nonempty(span.reason, "coverage reason")
    from services.claim_extractor import uncovered_spans
    require(output.uncovered_spans == uncovered_spans(answer, output.claims, output.non_claim_spans), "Uncovered spans differ")


def validate_request(request, budget):
    from harness.contracts import RunBudget
    try:
        validate_types(request, TaskRequest)
        validate_types(budget, RunBudget)
        for name in ("task_id", "scenario_id"):
            nonempty(getattr(request, name), name)
        if request.engineering_context is not None:
            import math
            context=request.engineering_context
            require(context.goal in ("conceptual","plant_assessment"),"Unknown engineering review goal")
            require(context.origin=="user_input_unverified","Engineering inputs cannot impersonate computed results")
            unique(context.quantities,"quantity_id")
            for q in context.quantities:
                require(math.isfinite(q.value),"Engineering value must be finite")
                for field in ("quantity_id","kind","unit","reference"):
                    nonempty(getattr(q,field),field)
        evidence = merge_evidence(request.provided_evidence)
        if request.mode == TaskMode.QUESTION_ANSWER:
            nonempty(request.question, "question")
            require(request.existing_answer is None, "question_answer must not contain existing_answer")
        else:
            require(request.existing_answer is not None, "existing_answer required for assessment")
            validate_answer(request.existing_answer, evidence)
        for name in ("max_revision_rounds", "max_tool_calls", "max_retrieval_calls", "max_transient_retries",
                     "max_retrieval_chars_per_call", "max_retrieval_chars_total"):
            require(getattr(budget, name) >= 0, f"{name}: must be nonnegative")
        require(budget.max_model_calls > 0, "max_model_calls: must be positive")
        require(budget.max_duration_seconds > 0 and budget.step_timeout_seconds > 0, "timeouts must be positive")
    except ContractError as exc:
        raise InputError(str(exc)) from exc


def validate_review(output, answer, claims, evidence, verification):
    from agents.contracts import EvidenceVerificationOutput, PowerDomainReviewOutput
    validate_types(output, EvidenceVerificationOutput if verification else PowerDomainReviewOutput, path="$")
    require((output.answer_id, output.answer_version) == (answer.answer_id, answer.version), "review answer version mismatch", path="$.answer_version")
    known_evidence = {e.evidence_id for e in merge_evidence(evidence, output.evidence)}
    known_claims = {c.claim_id for c in claims}
    unique(output.findings, "finding_id")
    if verification:
        v6 = output.prompt_version is not None and output.prompt_version.startswith(("evidence-verification-v6", "evidence-verification-v7", "evidence-verification-v8", "evidence-verification-v9"))
        if v6:
            from services.quote_candidates import validate_catalog
            validate_catalog(output.quote_candidates,output.evidence)
        if output.prompt_version and output.prompt_version.startswith(("evidence-verification-v7","evidence-verification-v8","evidence-verification-v9")):
            from services.quantity_checks import check_verification_quantities
            require(output.consistency_checks==check_verification_quantities(output,version="quantity-enumeration-v1.2" if output.prompt_version.startswith("evidence-verification-v9") else "quantity-enumeration-v1" if output.prompt_version=="evidence-verification-v7-program-preconditions" else "quantity-enumeration-v1.1"),"Program quantity check changed",path="$.consistency_checks")
        if output.generation_snapshot is not None:
            from services.evidence_scope import validate_snapshot
            validate_snapshot(output.generation_snapshot, answer)
        require(output.claims == claims, "verification changed frozen claim list", path="$.claims")
        require({f.claim_id for f in output.findings} == known_claims, "verification must cover every claim", path="$.findings")
        for index, finding in enumerate(output.findings):
            path = f"$.findings[{index}]"
            require(finding.claim_id in known_claims, "unknown claim ID", path=f"{path}.claim_id")
            nonempty(finding.checker_version, f"{path}.checker_version")
            if finding.status == VerificationStatus.SUPPORTED and finding.assessment_basis in ("text_evidence", "metadata"):
                require(bool(finding.evidence_ids), "supported finding requires evidence", path=f"{path}.evidence_ids")
            validate_excerpts(finding.excerpts, merge_evidence(evidence, output.evidence), f"{path}.excerpts")
            require(set(q.evidence_id for q in finding.excerpts) <= set(finding.evidence_ids), "excerpt not in finding IDs", path=f"{path}.excerpts")
        if output.prompt_version is not None:
            require(len(output.findings) == len(claims), "duplicate claim review", path="$.findings")
            require({c.citation_index for c in output.citation_reviews} == set(range(len(answer.citations)))
                    and len(output.citation_reviews) == len(answer.citations), "original citation coverage incomplete", path="$.citation_reviews")
            for index, finding in enumerate(output.findings):
                path = f"$.findings[{index}]"
                nonempty(finding.check_method, f"{path}.check_method")
                if v6 or output.prompt_version in ("evidence-verification-v4-typed-evidence", "evidence-verification-v5-component-bases", "evidence-verification-v5.1-component-bases-classification", "evidence-verification-v5.2-typed-quote-references"):
                    dimensions = {"quantity", "negation", "causality", "conditions", "jurisdiction"}
                    require(set(finding.required_dimensions) == dimensions and len(finding.required_dimensions) == 5
                            and not finding.checked_dimensions, "required checks must not be represented as completed checks", path=f"{path}.required_dimensions")
                    observed = [d.dimension for d in finding.dimension_findings]
                    require(len(observed) == len(set(observed)) and set(observed) <= dimensions,
                            "invalid dimension observations", path=f"{path}.dimension_findings")
                    for index, observation in enumerate(finding.dimension_findings):
                        nonempty(observation.observation, f"{path}.dimension_findings[{index}].observation")
                else:
                    require(set(finding.checked_dimensions) == {"quantity", "negation", "causality", "conditions", "jurisdiction"}
                        and len(finding.checked_dimensions) == 5, "incomplete finding dimensions", path=f"{path}.checked_dimensions")
                require(finding.assessment_basis != "text_evidence" or finding.status not in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED)
                        or bool(finding.excerpts), "definitive model finding requires matched excerpts", path=f"{path}.excerpts")
                if v6 or output.prompt_version in ("evidence-verification-v5-component-bases", "evidence-verification-v5.1-component-bases-classification", "evidence-verification-v5.2-typed-quote-references"):
                    from core.typed_evidence import validate_typed_finding
                    validate_typed_finding(finding, next(c for c in claims if c.claim_id == finding.claim_id), output, answer, path)
                else:
                    validate_finding_basis(finding, output, merge_evidence(evidence, output.evidence), path)
            for index, review in enumerate(output.citation_reviews):
                path = f"$.citation_reviews[{index}]"
                require(review.evidence_ids == answer.citations[review.citation_index].evidence_ids, "original citation IDs changed", path=f"{path}.evidence_ids")
                validate_excerpts(review.excerpts, merge_evidence(evidence, output.evidence), f"{path}.excerpts")
                require(set(q.evidence_id for q in review.excerpts) <= set(review.evidence_ids), "original citation substituted evidence", path=f"{path}.excerpts")
                nonempty(review.rationale, f"{path}.rationale")
                nonempty(review.check_method, f"{path}.check_method")
                require(set(review.claim_ids) <= known_claims, "unknown original citation claim ID", path=f"{path}.claim_ids")
                binding = answer.citations[review.citation_index]
                require(review.claim_ids == tuple(c.claim_id for c in claims if c.start_offset < binding.end_offset
                        and c.end_offset > binding.start_offset), "citation claim overlap mapping mismatch", path=f"{path}.claim_ids")
                require(review.status not in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED)
                        or bool(review.excerpts), "definitive citation review requires matched excerpts", path=f"{path}.excerpts")
                if v6 or output.prompt_version in ("evidence-verification-v5-component-bases", "evidence-verification-v5.1-component-bases-classification", "evidence-verification-v5.2-typed-quote-references"):
                    from core.typed_evidence import validate_bases
                    validate_bases(review.bases, output, answer, path + ".bases", allowed_ids=set(review.evidence_ids), citation=True)
                    require(review.excerpts == tuple(b.excerpt for b in review.bases if b.excerpt), "citation typed basis projection mismatch", path=path + ".excerpts")
                if v6 or output.prompt_version in ("evidence-verification-v3-basis", "evidence-verification-v4-typed-evidence", "evidence-verification-v5-component-bases", "evidence-verification-v5.1-component-bases-classification", "evidence-verification-v5.2-typed-quote-references"):
                    from services.evidence_scope import citation_coverage
                    partial, issues = citation_coverage(answer, claims, review.citation_index, output.findings)
                    require(review.partial_claim_ids == partial and review.coverage_issues == issues,
                            "citation coverage diagnostics changed", path=f"{path}.coverage_issues")
    else:
        if output.prompt_version and output.prompt_version.startswith(("power-domain-review-v1","power-domain-review-v2","power-domain-review-v3")):
            from agents.power_domain_review import validate_domain_output
            validate_domain_output(output,answer,claims)
        for finding in output.findings:
            require((finding.answer_id, finding.answer_version) == (answer.answer_id, answer.version), "domain finding version mismatch")
            require(set(finding.claim_ids) <= known_claims, "unknown domain claim ID")
    for index, finding in enumerate(output.findings):
        path = f"$.findings[{index}]"
        nonempty(finding.rationale, f"{path}.rationale")
        require(set(finding.evidence_ids) <= known_evidence, "unknown finding evidence ID", path=f"{path}.evidence_ids")
        if verification and output.prompt_version and output.prompt_version.startswith('evidence-verification-v9'):
            from tools.unit_conversion import validate_result
            for tool in output.tool_results:validate_result(tool)
            require(set(finding.tool_result_ids)<={t.result_id for t in output.tool_results if t.status==ExecutionStatus.SUCCEEDED},'unregistered tool result',path=f'{path}.tool_result_ids')
        else:
            require(not finding.tool_result_ids, "offline harness has no registered tool results", path=f"{path}.tool_result_ids")
    for index, issue in enumerate(output.execution_issues):
        require(issue.status != ExecutionStatus.SUCCEEDED, "execution issue cannot be successful", path=f"$.execution_issues[{index}].status")


def validate_finding_basis(finding, output, evidence, path):
    from services.evidence_scope import metadata_fields, canonical
    basis = finding.assessment_basis
    pairs = {"technical_fact": "text_evidence", "source_quality_metadata": "metadata",
             "answer_scope": "answer_text", "input_evidence_coverage": "generation_input_evidence",
             "review_recommendation": "review_advice"}
    require(basis in set(pairs.values()), "unknown assessment basis", path=f"{path}.assessment_basis")
    if output.prompt_version in ("evidence-verification-v3-basis", "evidence-verification-v4-typed-evidence"):
        require(pairs.get(finding.claim_category) == basis, "category and basis mismatch", path=f"{path}.claim_category")
    require(basis == "metadata" or not finding.metadata_refs, "metadata references on nonmetadata finding", path=f"{path}.metadata_refs")
    if basis == "metadata":
        require(not finding.excerpts, "metadata cannot use unrelated body excerpts", path=f"{path}.excerpts")
        known = {e.evidence_id: e for e in evidence}
        for index, ref in enumerate(finding.metadata_refs):
            rp = f"{path}.metadata_refs[{index}]"
            require(ref.evidence_id in known and ref.evidence_id in finding.evidence_ids, "unknown metadata evidence", path=f"{rp}.evidence_id")
            fields = metadata_fields(known[ref.evidence_id])
            require(ref.field_path in fields and fields[ref.field_path] is not None, "metadata field missing or unknown", path=f"{rp}.field_path")
            require(ref.value_json == canonical(fields[ref.field_path]), "metadata field value mismatch", path=f"{rp}.value_json")
        require(finding.status not in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED) or bool(finding.metadata_refs),
                "definitive metadata finding requires fields", path=f"{path}.metadata_refs")
    if basis in ("answer_text", "review_advice"):
        require(not finding.excerpts and not finding.evidence_ids, "non-evidence basis cannot attach body evidence", path=f"{path}.excerpts")
    if basis == "review_advice":
        require(finding.status == VerificationStatus.NOT_ASSESSABLE, "advice is not a verified fact", path=f"{path}.status")
    if basis == "generation_input_evidence":
        snapshot = output.generation_snapshot
        if snapshot is None:
            require(finding.status == VerificationStatus.NOT_ASSESSABLE and finding.scope_id is None
                    and not finding.excerpts and not finding.evidence_ids,
                    "complete generation input unavailable", path=f"{path}.scope_id")
        else:
            require(finding.scope_id == snapshot.snapshot_id, "generation input scope mismatch", path=f"{path}.scope_id")
            require(set(finding.evidence_ids) <= {e.evidence_id for e in snapshot.evidence},
                    "coverage finding substituted non-generation evidence", path=f"{path}.evidence_ids")
    else:
        require(finding.scope_id is None, "unexpected generation scope", path=f"{path}.scope_id")


def validate_revision(output, previous, evidence, findings):
    from agents.contracts import RevisionOutput
    validate_types(output, RevisionOutput)
    validate_answer(output.answer, merge_evidence(evidence, output.evidence))
    require(output.answer.answer_id == previous.answer_id and output.answer.version == previous.version + 1,
            "revision must keep answer ID and increment version by one")
    known = {f.finding_id for f in findings}
    if output.finding_actions:
        unique(output.finding_actions,"finding_id")
        require({a.finding_id for a in output.finding_actions}==known,"Per-finding action coverage incomplete")
        for action in output.finding_actions:
            require(action.action in ("modified","retained","unresolved"),"Unknown finding action")
            nonempty(action.explanation,"finding action explanation")
        require({a.finding_id for a in output.finding_actions if a.action=="modified"}=={i for c in output.changes for i in c.finding_ids},
            "Finding action and change projection mismatch")
        require(set(output.unresolved_finding_ids)=={a.finding_id for a in output.finding_actions if a.action!="modified"},
            "Nonmodified findings must remain explicit")
    require(set(output.unresolved_finding_ids) <= known, "unknown unresolved finding ID")
    for change in output.changes:
        require(bool(change.finding_ids) and set(change.finding_ids) <= known, "unknown revision finding ID")
        nonempty(change.description, "change description")
    require(bool(output.changes), "revision requires a change record")
    for issue in output.execution_issues:
        require(issue.status != ExecutionStatus.SUCCEEDED, "execution issue cannot be successful")


def validate_report(report):
    validate_types(report, AuditReport)
    evidence = merge_evidence(report.evidence)
    validate_answer(report.answer, evidence)
    from core.models import ProductDecision, DecisionKind
    no_answer = (isinstance(report.decision, ProductDecision) and
                 report.decision.reason_codes == ('NO_SUBSTANTIVE_ANSWER',))
    if no_answer:
        require(report.decision.kind == DecisionKind.NEEDS_INFORMATION and
                not report.claims and not report.answer.citations and bool(report.answer.missing_information) and
                not report.verification_findings and not report.domain_findings and not report.execution_issues,
                'No-answer path requires missing information and no substantive audit; cannot pass')
    else:
        validate_claims(report.claims, report.answer)
    all_findings = report.verification_findings + report.domain_findings
    unique(all_findings, "finding_id")
    known_claims = {c.claim_id for c in report.claims}
    known_evidence = {e.evidence_id for e in evidence}
    for binding in report.evidence_bindings:
        require(binding.evidence_id in known_evidence, "binding references unknown evidence")
        require(binding.origin in ("user_reference", "index_core_hit", "index_adjacent_context",
                                   "agent_output_unverified", "index_saved_reference"), "invalid evidence origin")
    for finding in all_findings:
        refs = (finding.claim_id,) if isinstance(finding, VerificationFinding) else finding.claim_ids
        require(set(refs) <= known_claims, "report references unknown claim")
        require(set(finding.evidence_ids) <= known_evidence, "report references unknown evidence")
        if isinstance(finding, VerificationFinding):
            require(finding.status != VerificationStatus.SUPPORTED or bool(finding.evidence_ids) or
                    finding.assessment_basis == "typed_components" and bool(finding.bases),
                    "supported finding requires evidence")
        else:
            require((finding.answer_id, finding.answer_version) == (report.answer.answer_id, report.answer.version),
                    "report domain version mismatch")
    for name in ("report_id", "task_id"):
        nonempty(getattr(report, name), name)
    nonempty(report.decision.policy_version, "policy_version")
    require(set(report.decision.unresolved_finding_ids) <= {f.finding_id for f in all_findings}, "decision references unknown finding")
    require(bool(report.decision.reasons), "decision requires reasons")
    from core.models import ProductDecision, DecisionKind
    if isinstance(report.decision, ProductDecision):
        d=report.decision
        require(d.policy_version in ('product-decision-v1','product-decision-v1.1'),'Unknown product policy version')
        require(d.execution_integrity in ('complete','incomplete'),'Unknown execution integrity')
        require(d.risk_level in ('low','medium','high','unknown'),'Unknown risk level')
        require(d.resolution in ('complete','partial','unable_to_answer'),'Unknown resolution')
        require(bool(d.reason_codes) and bool(d.classification_basis),'Product rationale/classification required')
        require(all(len(c)==3 and all(c) for c in d.applicable_checks),'Check applicability reason required')
        if d.kind==DecisionKind.PASS:
            require(d.execution_integrity=='complete' and d.risk_level=='low','Pass requires complete checks and bounded low risk')
            require(bool(report.claims) and bool(report.verification_findings) and bool(report.domain_findings),'Empty audit cannot pass')
            require(not report.execution_issues and all(f.status==VerificationStatus.SUPPORTED for f in report.verification_findings),'Incomplete or unsupported audit cannot pass')
