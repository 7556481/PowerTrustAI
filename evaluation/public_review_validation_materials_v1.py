"""Offline-only B validation material identities; no provider or execution action."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

from agents.contracts import GenerationInput
from agents.generation import messages_for
from core.models import (AnswerDraft, EngineeringContext, Evidence, EvidenceBinding,
                         PremiseDeclaration, PremiseTaskRequest, TaskMode)
from core.validation import require, validate_answer, validate_types
from services.task_premises_v1 import catalog

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'docs/evaluation/public-review-validation-v1'
PRIVATE = ROOT / 'data/evaluation_local/public-review-validation-v1/preparation-v1'
ORDER = ('BTV-01-QA', 'BTV-02-QA', 'BTV-02-DIAG', 'BTV-03-QA', 'BTV-04-QA')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def build_inputs(document):
    require(set(document) == {'version', 'status', 'common_answer_requirements', 'sources', 'cases', 'diagnostic'}, 'Input document whitelist')
    sources = {}
    for source in document['sources']:
        require(set(source) == {'source_id', 'source_version', 'locator', 'text', 'source_type'}, 'Source whitelist')
        require(source['source_id'] not in sources, 'Unique source identity')
        sources[source['source_id']] = source
    require(set(sources) == {'BTV-S1', 'BTV-S2', 'BTV-S3'}, 'Three declared synthetic source groups')
    out = {}
    for case in document['cases']:
        require(set(case) == {'case_id', 'question', 'user_context', 'requirements', 'premise_declarations', 'source_id'}, 'Case whitelist')
        require(case['case_id'] not in out, 'Unique case ID')
        source = sources[case['source_id']]
        evidence = (Evidence(case['case_id'] + '-E1', **source),)
        requirements = []
        for row in case['requirements']:
            require(set(row) == {'requirement_id', 'description'}, 'Visible requirement whitelist')
            requirements.append(row['description'])
        require([r['requirement_id'] for r in case['requirements']] == ['R1', 'R2', 'R3'], 'Three independent declared requirements')
        declarations = []
        for row in case['premise_declarations']:
            require(set(row) == {'source_field', 'quote', 'kind'}, 'Explicit task declaration whitelist')
            declarations.append(PremiseDeclaration(**row))
        request = PremiseTaskRequest(case['case_id'], TaskMode.QUESTION_ANSWER, 'concept_fixed_premise_validation_v1',
            case['question'], user_context=case['user_context'], provided_evidence=evidence,
            engineering_context=EngineeringContext(goal='conceptual'), premise_declarations=tuple(declarations))
        value = GenerationInput(request, evidence, tuple(EvidenceBinding(e.evidence_id, 'user_reference') for e in evidence),
                                None, tuple(requirements + document['common_answer_requirements']))
        validate_types(value, GenerationInput)
        require(len(catalog(request)) == 1, 'One explicit task-only stipulated premise per case')
        out[case['case_id']] = value
    require(set(out) == {'BTV-01', 'BTV-02', 'BTV-03', 'BTV-04'}, 'Four fixed cases')
    diag = document['diagnostic']
    require(set(diag) == {'request_id', 'case_id', 'answer_id', 'answer_version', 'text'}, 'Actual diagnostic input whitelist')
    require(diag['case_id'] == 'BTV-02' and diag['request_id'] == 'BTV-02-DIAG', 'One fixed additional diagnostic')
    answer = AnswerDraft(diag['answer_id'], diag['answer_version'], diag['text'])
    request = replace(out['BTV-02'].request, mode=TaskMode.ASSESS_EXISTING, existing_answer=answer)
    validate_types(request, PremiseTaskRequest)
    validate_answer(answer, request.provided_evidence)
    require(not answer.citations, 'No invented original references for diagnostic')
    require(catalog(request) == catalog(out['BTV-02'].request), 'Same task catalog across input modes')
    return out, request


def identities(values, diagnostic):
    rows, private = [], []
    for ident in ORDER:
        case_id = ident[:6]
        is_diag = ident.endswith('DIAG')
        value = values[case_id]
        request = diagnostic if is_diag else value.request
        messages = None if is_diag else [asdict(m) for m in messages_for(value, 3, product_guidance=True)]
        row = {'request_id': ident, 'case_id': case_id, 'mode': request.mode.value,
               'request_sha256': sha(asdict(request)), 'premise_catalog_sha256': sha([asdict(p) for p in catalog(request)]),
               'generation_input_sha256': None if is_diag else sha(asdict(value)),
               'initial_generation_messages_sha256': None if is_diag else sha(messages),
               'answer_sha256': sha(request.existing_answer.text) if is_diag else None,
               'generation_snapshot': 'must_remain_none' if is_diag else 'save_actual_future_generation_delivery'}
        rows.append(row)
        private.append({'identity': row, 'request': asdict(request), 'generation_input': None if is_diag else asdict(value),
                        'unsent_initial_generation_messages': messages, 'task_premises': [asdict(p) for p in catalog(request)]})
    return rows, private


def prepare():
    require(not (PUBLIC / 'freeze-plan-v1.json').exists() and not PRIVATE.exists(), 'Never overwrite prepared material identity')
    document = read(PUBLIC / 'tasks-v1.json')
    values, diag = build_inputs(document)
    rows, private = identities(values, diag)
    source_manifest = {'version': 'B-synthetic-source-manifest-v1', 'scope': 'development_materials_not_independent_holdout',
        'sources': [{**s, 'text_utf8_sha256': hashlib.sha256(s['text'].encode()).hexdigest(),
                     'provenance': 'AI-assisted new teaching text, 2026-10-22; pending user material review; no official source claim'} for s in document['sources']],
        'lineage': 'BTV-01/02 share BTV-S1; two other source groups. Threshold/permission structure intentionally resembles earlier synthetic development cases. Not a new isolation or pretraining-novelty proof.'}
    write(PUBLIC / 'source-manifest-v1.json', source_manifest)
    paths = {Path(__file__).resolve(), ROOT / 'tests/test_public_review_validation_materials_v1.py', ROOT / 'evaluation/batch_control.py'}
    for directory in ('agents', 'core', 'harness', 'model_adapter', 'services', 'tools'):
        paths.update((ROOT / directory).rglob('*.py'))
    paths.update(PUBLIC / name for name in ('tasks-v1.json', 'review-criteria-v1.json', 'source-manifest-v1.json'))
    plan = {'version': 'public-review-validation-freeze-plan-v1', 'source_base_commit': '90bdfeacd6a2b993a7604acf29b40fd7845cb265',
        'status': 'prepared_pending_whole_batch_review_and_new_paid_authorization', 'execution_authorized': False,
        'entry': {'path': 'evaluation/public_review_validation_trial_v1.py', 'implemented': False,
                  'gate': 'After authorization, bind actual entry and tests; offline admission/storage/stop gates required. This file has no execute action.'},
        'order': rows, 'main_qa_cases': 4, 'additional_existing_answer_diagnostics': 1,
        'initial_generations': 4, 'seeded_diagnostic_answers': 1, 'live_original_reviewer_control_branches': 0,
        'model_proposal': {'endpoint': 'https://api.deepseek.com', 'model_id': 'deepseek-flash', 'max_output_tokens': 8000,
                           'max_response_chars': 96000, 'request_timeout_seconds': 90, 'thinking': 'disabled',
                           'temperature': 'service default', 'seed': None, 'stream': False, 'response_format': 'json_object'},
        'pipeline': {'generation': 'original schema3 product_guidance=True', 'mapping_A': False,
            'extractor': 'PremiseClaimExtractor', 'fact': 'PremiseVerificationAgent schema13 public-review-premise-boundary-v1-dev',
            'domain': 'original protocol5 safety/task-applicability', 'policy': 'product-decision-v1.5',
            'execution_path': 'sequential', 'retriever': None, 'knowledge_version': None,
            'unit_tool': 'original scalar-si-conversion-v2 only', 'correction_accounting': 'invocation_scoped_v1'},
        'budget_proposal': {'per_branch_model_calls_shared': 40, 'extra_batch_call_cap': None, 'revision': 0,
            'transient_retries': 0, 'retrieval_calls': 0, 'step_timeout_seconds': 110, 'branch_timeout_seconds': 800,
            'initial_request_formula': 'QA C+I+3, diagnostic C+I+2; C actual original citations, I eligible independent request 0/1',
            'conditional_correction_bound': 'QA C+I+7; diagnostic C+I+5. Capacity/time/failure may prevent completion; no completion guarantee.',
            'all_five_initial_formula': '14 + sum(I) + sum(C); 19+sum(C) only if all I=1. Diagnostic has C=0.',
            'corrections': 'QA generation <=1; each extraction/domain <=1; independent fact and all original citations share <=1; all consume original shared 40'},
        'stop': 'Any final execution/required-review/storage failure: archive partial output, stop subsequent branches, list unexecuted. Semantic reject/insufficiency is not itself execution failure. No resume/retry-to-pass.',
        'dynamic_message_identity': 'Persist actual extraction/review/correction messages and identity before sending, never invent future hashes. No evaluator criteria or reference clauses in model payloads.',
        'accounting_reporting': 'Initial/final judgments, correction owner/component and actual calls separate. No live old-accounting rerun; provenance observations are not a counterfactual success-rate claim.',
        'conclusion_limit': 'Single B verification batch, not a live original-vs-B semantic improvement experiment. No production admission or safety proof.',
        'bound_files': [{'path': str(p.relative_to(ROOT)).replace('\\', '/'), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]}
    write(PUBLIC / 'freeze-plan-v1.json', plan)
    write(PRIVATE / 'unsent-inputs-and-messages-v1.json', {'status': 'PREPARATION_ONLY_NOT_SENT', 'branches': private})
    print('Prepared four original-generator inputs and one fixed diagnostic; zero model requests; no paid attempt')


def check():
    plan = read(PUBLIC / 'freeze-plan-v1.json')
    values, diag = build_inputs(read(PUBLIC / 'tasks-v1.json'))
    rows, _ = identities(values, diag)
    require(rows == plan['order'] and not plan['execution_authorized'], 'Prepared identities, not a paid authorization')
    for item in plan['bound_files']:
        require(hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], 'Prepared source/material identity changed')
    require(not (ROOT / 'data/evaluation_local/public-review-validation-v1/batch-v1/attempt.json').exists(), 'No paid attempt expected during preparation')
    print('Five task identities, four initial messages, same-mode-independent catalog and bound files verified offline')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'check'))
    action = parser.parse_args().action
    prepare() if action == 'prepare' else check()
