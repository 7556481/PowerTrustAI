"""Exact generation input scope and mechanically checkable metadata references."""
from dataclasses import asdict
import hashlib
import json
from core.models import GenerationEvidenceSnapshot
from core.validation import require, merge_evidence, validate_types


def snapshot_id(answer, evidence, knowledge_version, full_input=None):
    items=[answer.answer_id, answer.version, answer.text, knowledge_version,[asdict(e) for e in evidence]]
    if full_input is not None:items.append(full_input)
    data = json.dumps(items, ensure_ascii=False, sort_keys=True)
    return "generation-input-" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def make_snapshot(answer, evidence, knowledge_version, *, request=None, answer_requirements=(), prompt_version=None, evidence_bindings=()):
    merge_evidence(evidence)
    if request is not None:
        full={"snapshot_version":"generation-full-input-v2","question":request.question,"user_context":request.user_context,
            "engineering_context":None if request.engineering_context is None else asdict(request.engineering_context),
            "answer_requirements":answer_requirements,"input_prompt_version":prompt_version,"evidence_bindings":[asdict(b) for b in evidence_bindings]}
        return GenerationEvidenceSnapshot(answer.answer_id,answer.version,evidence,snapshot_id(answer,evidence,knowledge_version,full),knowledge_version,
            "generation-full-input-v2",request.question,request.user_context,request.engineering_context,answer_requirements,prompt_version,evidence_bindings)
    return GenerationEvidenceSnapshot(answer.answer_id, answer.version, evidence,
                                      snapshot_id(answer, evidence, knowledge_version), knowledge_version)


def validate_snapshot(snapshot, answer):
    validate_types(snapshot, GenerationEvidenceSnapshot)
    require((snapshot.answer_id, snapshot.answer_version) == (answer.answer_id, answer.version),
            "generation input answer binding mismatch", path="$.generation_snapshot.answer_version")
    merge_evidence(snapshot.evidence)
    require(snapshot.snapshot_version in ("generation-evidence-only-v1","generation-full-input-v2"),"Unknown snapshot version",path="$.generation_snapshot.snapshot_version")
    full=None
    if snapshot.snapshot_version=="generation-full-input-v2":
        require(snapshot.question is not None and snapshot.user_context is not None and bool(snapshot.input_prompt_version),"Full generation input fields missing",path="$.generation_snapshot")
        full={k:v for k,v in asdict(snapshot).items() if k in ("snapshot_version","question","user_context","engineering_context","answer_requirements","input_prompt_version","evidence_bindings")}
        require(all(b.evidence_id in {e.evidence_id for e in snapshot.evidence} for b in snapshot.evidence_bindings),"Unknown snapshot origin binding",path="$.generation_snapshot.evidence_bindings")
    else:
        require(snapshot.question is None and snapshot.user_context is None and snapshot.engineering_context is None and not snapshot.answer_requirements and snapshot.input_prompt_version is None and not snapshot.evidence_bindings,
            "Historic evidence-only snapshot cannot acquire later input fields",path="$.generation_snapshot")
    require(snapshot.snapshot_id == snapshot_id(answer, snapshot.evidence, snapshot.knowledge_version,full),
            "generation input snapshot hash mismatch", path="$.generation_snapshot.snapshot_id")


def metadata_fields(evidence):
    fields = {key: getattr(evidence, key) for key in ("source_id", "source_version", "source_type", "applicability")}
    if evidence.provenance:
        fields.update(("provenance." + key, value) for key, value in asdict(evidence.provenance).items())
    return fields


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def citation_coverage(answer, claims, citation, findings=()):
    binding = answer.citations[citation]
    overlapping = tuple(c for c in claims if c.start_offset < binding.end_offset and c.end_offset > binding.start_offset)
    partial = tuple(c.claim_id for c in overlapping if not
                    (binding.start_offset <= c.start_offset and c.end_offset <= binding.end_offset))
    issues = []
    if partial:
        issues.append("partial_claim_anchor_coverage_requires_review")
    if any(f.claim_id in {c.claim_id for c in overlapping} and f.status.value == "supported"
           and not set(f.evidence_ids) <= set(binding.evidence_ids) for f in findings):
        issues.append("independent_support_uses_unbound_evidence_not_original_citation_support")
    return partial, tuple(issues)
