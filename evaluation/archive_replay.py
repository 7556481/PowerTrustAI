"""Strict local archive reconstruction and v8 replay, not semantic adjudication."""
from copy import deepcopy
from dataclasses import fields, is_dataclass, MISSING, asdict
from enum import Enum
import hashlib
import json
from pathlib import Path
import types
from typing import get_args, get_origin, get_type_hints, Union

from agents.contracts import EvidenceVerificationInput
from agents.verification_contract_v8 import baseline, translate, mark
from agents.verification_contract_v7 import parse_v7
from core.models import TaskRequest, TaskMode, ClaimExtractionOutput
from core.validation import validate_types, validate_extraction, ContractError
from harness.contracts import HarnessResult
from harness.evidence_review_demo import restore_answer, restore_evidence, restore_snapshot
from services.review_isolation import WireIsolation
from services.scoped_candidates import CandidateScope
from services.structured_model import strict_json


def restore(value, cls):
    """Only instantiate declared dataclass/enum types; no imports from file data."""
    if value is None:
        if cls is type(None) or type(None) in get_args(cls):
            return None
        raise ValueError("Unexpected null in archived declared type")
    origin, args = get_origin(cls), get_args(cls)
    if origin in (Union, types.UnionType):
        choices = [a for a in args if a is not type(None)]
        if len(choices) != 1:
            raise ValueError("Unsupported archived union")
        return restore(value, choices[0])
    if origin is tuple:
        if type(value) is not list:
            raise ValueError("Archived tuple must be a JSON array")
        return tuple(restore(item, args[0]) for item in value)
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(value)
    if is_dataclass(cls):
        extensions={'ComponentReview':('fidelity_status','core.models','FidelityComponentReview'),'Claim':('assertion_role','core.models','ContextualClaim'),'TypedBasis':('calculation_result_id','core.models','CalculationBasis'),
            'EvidenceVerificationInput':('tool_results','agents.contracts','ReliabilityVerificationInput'),
            'EvidenceVerificationOutput':('tool_results','agents.contracts','ReliabilityVerificationOutput'),
            'PowerDomainReviewInput':('tool_results','agents.contracts','ReliabilityDomainInput'),'HarnessResult':('tool_results','harness.contracts','ToolHarnessResult')}
        if cls.__name__ in extensions:
            field_name,module,name=extensions[cls.__name__]
            if type(value) is dict and field_name in value:cls=getattr(__import__(module,fromlist=[name]),name)
        if cls.__name__=='ContextualClaim' and 'component_basis_targets' in value:
            from core.models import BasisAwareClaim
            cls=BasisAwareClaim
        if cls.__name__=='BasisAwareClaim' and 'component_obligations' in value:
            from core.models import ObligationClaim
            cls=ObligationClaim
        declared = {f.name for f in fields(cls)}
        required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
        if type(value) is not dict or set(value) - declared or not required <= set(value):
            raise ValueError("Archive fields differ from declared dataclass")
        hints = get_type_hints(cls)
        output = cls(**{key: restore(item, hints[key]) for key, item in value.items()})
        validate_types(output, cls)
        return output
    return value


def find_frozen_extraction(source, answer, knowledge_version):
    """Reuse only an actually archived accepted extraction of this exact answer."""
    from evaluation.acceptance_preparation import PRIVATE, sha
    seen = set()
    path = Path(source).resolve()
    for _ in range(8):
        if not path.is_relative_to(PRIVATE.resolve()) or path in seen:
            raise ValueError("Invalid private archive ancestry")
        seen.add(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["knowledge_version"] != knowledge_version:
            raise ValueError("Frozen knowledge version mismatch")
        for run in data.get("runs", []):
            for phase in ("rereview", "initial"):
                result = run.get(phase) or {}
                if result.get("answer") != json.loads(json.dumps(asdict(answer))):
                    continue
                raw = result.get("extraction_output")
                if raw is None:
                    continue
                output = restore(raw, ClaimExtractionOutput)
                validate_extraction(output, answer)
                return output, {"path": str(path), "sha256": sha(path), "scenario": run["scenario"],
                                "phase": phase, "answer_sha256": hashlib.sha256(answer.text.encode()).hexdigest(),
                                "note": "Previously accepted real extraction; not a new model extraction or business cache."}
        parent = data.get("prior_source")
        if not parent:
            break
        path = Path(parent["path"]).resolve()
        if not path.is_relative_to(PRIVATE.resolve()) or sha(path) != parent["sha256"]:
            raise ValueError("Archive ancestry integrity mismatch")
    raise ValueError("No valid real extraction for exact frozen answer")


class FrozenArchivedExtraction:
    """Experiment-only reuse of a validated service output, not a new Agent."""
    def __init__(self, answer, output):
        validate_extraction(output, answer)
        self.answer, self.output = answer, output

    async def extract(self, answer):
        if answer != self.answer:
            raise ValueError("Archived extraction requires identical frozen answer")
        validate_extraction(self.output, answer)
        return self.output


def replay_failed_review(path, scenario="engineering-data"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    run = next(r for r in data["runs"] if r["scenario"] == scenario)
    result = restore(run["rereview"], HarnessResult)
    snapshot = restore_snapshot(run["revision"]["evidence_snapshot"])
    request = TaskRequest("offline-replay", TaskMode.ASSESS_EXISTING, "voltage_stability_reactive_support",
                          snapshot.question, snapshot.user_context, result.answer, result.evidence, snapshot.engineering_context)
    records = [r for r in result.model_records if r.prompt_version.startswith("evidence-verification-v8")
               and r.output_status == "invalid_structure"]
    rows, isolation = [], None
    for record in records:
        catalog = json.loads(Path(record.candidate_catalog_path).read_text(encoding="utf-8"))
        known = {e.evidence_id: e for e in result.evidence}
        seed = tuple(known[e["evidence_id"]] for e in catalog["EVIDENCE_METADATA"])
        inputs = EvidenceVerificationInput(request, result.answer, result.extraction_output.claims,
                                          seed, (), catalog["knowledge_version"], result.evidence, snapshot)
        scope = CandidateScope(result.answer, inputs.knowledge_version, catalog["purpose"], seed,
                               check_id=catalog["check_id"], protocol_version=catalog["protocol_version"])
        assert scope.scope_id == catalog["scope_id"]
        base = baseline(inputs)
        def strict(value):
            expanded = deepcopy(base)
            expanded["findings"] = translate(value, scope)["findings"]
            return parse_v7(expanded, inputs)
        if isolation is None:
            isolation = WireIsolation({"findings": base["findings"]}, strict, {"findings": "claim_id"}, mark)
        raw = json.loads(Path(record.diagnostic_path).read_text(encoding="utf-8"))
        assert hashlib.sha256(raw["response_text"].encode()).hexdigest() == raw["response_sha256"]
        try:
            isolation.parse(strict_json(raw["response_text"]))
        except ContractError as exc:
            errors = exc.diagnostic.get("errors", [exc.diagnostic])
            historical = record.validation_error.get("errors", [record.validation_error])
            same_constraints = [(e["field_path"], e["constraint"]) for e in errors] == [
                (e["field_path"], e["constraint"]) for e in historical]
            rows.append({"correction": record.correction, "raw_path": record.diagnostic_path,
                         "historical_output_status": record.output_status, "replay_status": "failed",
                         "same_historical_paths_and_constraints": same_constraints,
                         "errors": errors, "retained_items": exc.diagnostic.get("retained_items", [])})
        else:
            raise AssertionError("Historical failed response unexpectedly accepted")
    return rows
