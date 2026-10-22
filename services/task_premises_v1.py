"""Development-only task premises: identity/positions are program owned, never truth."""
from dataclasses import asdict, fields, replace
import hashlib
import json

from core.models import PremiseTaskRequest, TaskPremise, PremiseBoundClaim
from core.validation import require

VERSION = 'task-premise-catalog-v1'
PROFILE = 'public-review-premise-boundary-v1-dev'
OBJECTS = {'literature', 'premise_restatement', 'scenario_application', 'external_claim', 'uncertain', 'ordinary'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def catalog(request):
    # No answer, generation assumptions, mapping, or generated snapshot is read.
    context = digest({'task_id': request.task_id, 'scenario_id': request.scenario_id,
        'question': request.question, 'user_context': request.user_context,
        'engineering_context': None if request.engineering_context is None else asdict(request.engineering_context)})
    out = []
    for declaration in getattr(request, 'premise_declarations', ()):
        require(type(request) is PremiseTaskRequest, 'explicit premise task required')
        require(declaration.source_field in ('question', 'user_context'), 'only current task text can declare premises')
        require(declaration.kind in ('stipulated', 'unverified_report'), 'explicit premise kind required')
        source, text = getattr(request, declaration.source_field), declaration.quote
        require(bool(text.strip()) and source.count(text) == 1, 'premise must select one unique exact task substring')
        start = source.index(text)
        ident = 'task-premise-' + digest((VERSION, context, declaration.source_field, declaration.kind, text, start))[:32]
        item = TaskPremise(ident, request.task_id, context, declaration.source_field, declaration.kind, text, start, start + len(text))
        require(item not in out, 'duplicate premise declaration')
        out.append(item)
    return tuple(out)


def validate_catalog(request, items):
    require(tuple(items) == catalog(request), 'premise catalog differs from actual task text/version')


def validate_claim(claim):
    from services.answer_basis_targets import TARGETS
    from services.claim_obligations import TARGET_OBLIGATIONS
    n = len(claim.components)
    require(claim.semantic_origin == PROFILE, 'explicit candidate claim version required')
    require(all(len(v) == n for v in (claim.component_objects, claim.component_premise_ids,
        claim.component_basis_targets, claim.component_obligations)), 'one object, target, premise selection and obligation per component')
    for i, (part, kind, ids, target, obligation) in enumerate(zip(claim.components, claim.component_objects,
            claim.component_premise_ids, claim.component_basis_targets, claim.component_obligations)):
        require(kind in OBJECTS and len(set(ids)) == len(ids), 'known object and unique premise selections required')
        if kind == 'premise_restatement':
            require((part.category, target, obligation) == ('input_evidence_coverage', 'task_premise', 'input_provided'),
                    'task premise verifies provided premise, not technical truth or generation coverage')
        else:
            require(TARGETS.get(target) == part.category and TARGET_OBLIGATIONS.get(target) == obligation, 'original target/category/obligation gate retained')
            if kind in ('literature', 'scenario_application', 'external_claim', 'uncertain'):
                require(part.category == 'technical_fact' and target in ('technical_content', 'document_body'), 'object requires technical content obligation')
            if kind not in ('scenario_application',):
                require(not ids, 'premise references cannot support another assessment object')


def parse_extraction(value, answer, request):
    """New fields remain in a typed extension; old v7 parser remains unchanged."""
    from copy import deepcopy
    from services.claim_obligations import parse
    from services.validation_diagnostics import ErrorCollector
    raw = deepcopy(value)
    ec = ErrorCollector(PROFILE + '-extraction')
    ec.fields(raw, {'claims', 'non_claims'}, set(), '$')
    bindings, known = [], {p.premise_id for p in catalog(request)}
    for i, item in enumerate(raw.get('claims', []) if isinstance(raw, dict) else []):
        objects, premises = [], []
        for j, component in enumerate(item.get('components', []) if isinstance(item, dict) else []):
            path = f'$.claims[{i}].components[{j}]'
            if not ec.fields(component, {'category', 'proposition', 'basis_target', 'verification_obligation', 'object_kind', 'premise_ids'}, set(), path):
                continue
            kind, ids = component.pop('object_kind'), component.pop('premise_ids')
            ec.check(type(kind) is str and kind in OBJECTS and type(ids) is list and all(type(x) is str and x in known for x in ids), path, 'select_existing_task_premises_and_object')
            objects.append(kind); premises.append(tuple(ids) if type(ids) is list else ())
            # Only a parser carrier transformation, undone below, never an Evidence.
            if kind == 'premise_restatement':
                ec.check(component['basis_target'] == 'task_premise' and component['category'] == 'input_evidence_coverage'
                         and component['verification_obligation'] == 'input_provided', path, 'independent_task_premise_target_required')
                component['basis_target'] = 'input_snapshot'
        bindings.append((tuple(objects), tuple(premises)))
    ec.finish()
    output = parse(raw, answer)
    claims = []
    for c, (objects, premises) in zip(output.claims, bindings):
        targets = tuple('task_premise' if k == 'premise_restatement' else t for k, t in zip(objects, c.component_basis_targets))
        item = PremiseBoundClaim(**{f.name: getattr(c, f.name) for f in fields(c) if f.name not in ('component_basis_targets', 'semantic_origin')},
            component_basis_targets=targets, semantic_origin=PROFILE, component_objects=objects, component_premise_ids=premises)
        validate_claim(item)
        claims.append(item)
    return replace(output, claims=tuple(claims))


EXTRACTION_INSTRUCTION = '''
PUBLIC REVIEW PREMISE CANDIDATE v1 overrides only the following component fields:
Every component ALSO has object_kind and premise_ids. object_kind: literature,
premise_restatement, scenario_application, external_claim, uncertain, ordinary.
Select premise_ids only from TASK_PREMISES derived from CURRENT TASK input. Never
promote answer.assumptions, generated claims or reviewer notes into task premises.
Premise restatement: category input_evidence_coverage, basis_target task_premise,
verification_obligation input_provided. It verifies what was stipulated/reported,
not a real observation. Scenario application: technical_fact, technical_content,
technical_truth; select applicable premise IDs. Literature/external/uncertain use
technical_content or document_body, technical_fact, technical_truth, premise_ids [].
Ordinary retains existing category/target/obligation and premise_ids [].
Split input restatement, literature rule, conditional application and actual-world
assertion when independently expressed. Do not invent clauses or correct errors.
A mixed sentence may need several components. An unregistered answer assumption
is not a premise. Unknown classification remains uncertain, never forced supported.
The declared object is your judgment, not program proof. All previous literal-anchor,
negation, qualifiers, quantities, scope, permission/obligation and strict JSON rules remain.
'''
