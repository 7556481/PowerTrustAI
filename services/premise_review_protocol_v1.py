"""Strict candidate hooks for the existing schema13 fact stage, not a new runner."""
from dataclasses import fields
from core.models import PremiseBoundClaim, TaskPremiseBasis, VerificationStatus
from core.validation import require
from services.task_premises_v1 import PROFILE, catalog, validate_claim

PROMPT = 'evidence-verification-v9.21-task-premise-boundary-v1-dev'


def is_component(claim, index):
    return isinstance(claim, PremiseBoundClaim) and claim.component_objects[index] in ('premise_restatement', 'scenario_application')


def validate_selected(claim, index, bases, status, path):
    kind = claim.component_objects[index] if isinstance(claim, PremiseBoundClaim) else 'ordinary'
    selected = [b for b in bases if b is not None]
    types = {b.type for b in selected}
    references = [b.premise_reference for b in selected if b.type == 'task_premise_reference']
    ids = {p.premise_id for p in references}
    expected = set(claim.component_premise_ids[index]) if isinstance(claim, PremiseBoundClaim) else set()
    require(ids <= expected, 'premise basis must belong to this frozen component selection', path=path)
    if kind == 'premise_restatement':
        require(types <= {'task_premise_reference'}, 'premise restatement cannot borrow snapshot, body or answer truth', path=path)
    elif kind == 'scenario_application':
        require(types <= {'task_premise_reference', 'text_excerpt'}, 'application needs rule body and separate premise, never snapshot', path=path)
    else:
        require('task_premise_reference' not in types, 'task premise cannot prove document or actual-world assertion', path=path)
    if kind == 'uncertain':
        require(status not in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED), 'uncertain object cannot claim definitive support', path=path)
    if is_component(claim, index) and status in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED):
        require(bool(ids) and ids == expected, 'definitive premise/application needs all explicitly selected premises', path=path)
        if kind == 'scenario_application':
            require('text_excerpt' in types, 'rule application also requires selected technical body', path=path)
            require(all(p.kind == 'stipulated' for p in references), 'unverified reports cannot become established application premises', path=path)
    return is_component(claim, index)


def component_validator(claim, index, bases, indexes, status, path, collector):
    collector.capture(lambda: validate_selected(claim, index, [bases[n] for n in indexes], status, path))
    return is_component(claim, index)


def parse_basis(item, inputs, path, citation, collector):
    if not collector.fields(item, {'type', 'premise_id'}, set(), path):
        return None
    known = {p.premise_id: p for p in catalog(inputs.request)}
    if not collector.check(citation is None and type(item['premise_id']) is str and item['premise_id'] in known,
                           path, 'current_task_premise_required_never_original_citation'):
        return None
    return TaskPremiseBasis('task_premise_reference', premise_reference=known[item['premise_id']])


def promote(output, inputs):
    from agents.contracts import PremiseVerificationOutput
    return PremiseVerificationOutput(**{f.name: getattr(output, f.name) for f in fields(output)}, task_premises=catalog(inputs.request))


def missing_components(inputs):
    from agents.verification_contract_v9 import full_delivered
    return {} if full_delivered(inputs) else {c.claim_id: tuple(i for i, p in enumerate(c.components)
        if p.category == 'input_evidence_coverage' and not (isinstance(c, PremiseBoundClaim) and c.component_objects[i] == 'premise_restatement'))
        for c in inputs.claims}


def model_wire(inputs):
    missing = missing_components(inputs)
    for claim in inputs.claims:
        require(isinstance(claim, PremiseBoundClaim), 'candidate extractor must provide explicit object bindings')
        validate_claim(claim)
        known = {p.premise_id for p in catalog(inputs.request)}
        require(all(set(ids) <= known for ids in claim.component_premise_ids), 'claim refers to another task premise')
    return {'findings': [{'claim_id': c.claim_id, 'rationale': 'model_execution_incomplete: no judgment retained',
        'applicability_conditions': [], 'bases': [], 'component_reviews': [{'component_index': i, 'status': 'not_assessable',
        'basis_indexes': [], 'rationale': 'model_execution_incomplete'} for i in range(len(c.components)) if i not in missing.get(c.claim_id, ())]}
        for c in inputs.claims if len(missing.get(c.claim_id, ())) < len(c.components)],
        'citation_reviews': [{'citation_index': i, 'status': 'not_assessable', 'rationale': 'model_execution_incomplete',
        'applicability_conditions': [], 'bases': []} for i in range(len(inputs.answer.citations))]}, missing


INSTRUCTION = '''
PUBLIC REVIEW PREMISE BOUNDARY v1 CANDIDATE supersedes the input-generation-coverage
rule ONLY for components explicitly frozen as premise_restatement/task_premise.
TASK_PREMISES comes from CURRENT TASK, not the answer, generated assumptions or mapping.
Independent new basis EXACT {"type":"task_premise_reference","premise_id":"<existing ID>"}.
Do not output source text, ranges, versions or made-up IDs. Program binds identity only.
Premise restatement checks faithful reporting of the selected current premise, NOT
real-world measurement. It may be assessed even without a generation snapshot.
Scenario application must select BOTH applicable stipulated premise references AND
rule text_excerpt bases. No premise alone proves a rule, and no rule alone proves
the scenario satisfies its conditions. Review the actual conditional conclusion,
inclusive thresholds, exceptions, necessary/sufficient scope and may versus must.
Unverified reported data are not stipulated facts or verified real observations.
An actual-world assertion still needs appropriate actual records and original domain
checks. A task premise is never evidence for a real plant, safety or measurement.
Ordinary literature/technical facts retain original body/snapshot type restrictions.
If object/role/obligation selection is wrong, report disputed/uncertain semantic_review,
do not silently relabel components to get support. Frozen objects are not truths.
Missing rule or premise: insufficient_evidence/not_assessable as appropriate, no
invented premise or body. Selected valid IDs do not establish semantic support.
Original citations still select ONLY their bound body quotes; no task premise may
be used as an original citation basis or substitute a delivered literature quote.
All actual answer clauses remain in scope, including unmapped or added assertions.
'''
