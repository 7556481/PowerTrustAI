"""Scoped source inputs; reuse v3 strict parser and bounded trial controller."""
import argparse
import json
from pathlib import Path
import subprocess

from evaluation import requirement_review_v3 as base
from evaluation import requirement_trial_v3 as trial
from evaluation.text_bound_review import canonical, sha, write
from model_adapter.contracts import ModelMessage

VERSION = 'scoped-explicit-requirements-eval-v1'
PROMPT = base.PROMPT + '''
The input conditional_support_boundaries constrain additional assertions only
when their trigger applies. They are not extra mandatory coverage requirements.
Do not penalize a short duties answer for omitting optional rating explanations.
Assess any added capability or safety guarantee separately from supported duties;
preserve specified conditions and distinguish insufficient evidence from conflict.
'''
parse = base.parse


def model_input(card, example, source):
    return {
        'sample_id': example['id'], 'question': card['question'],
        'requirements': [{'requirement_id': r['id'],
                          'description': r['model_visible_task_requirement']}
                         for r in card['requirements']],
        'conditional_support_boundaries': [card['conditional_support_boundary']],
        'answer': example['answer'],
        'answer_units': base.build_units(example['id'], example['answer']),
        'unit_version': base.UNIT_VERSION,
        'evidence': [{'evidence_id': e['evidence_id'], 'text': e['text'],
                      'source_pdf_sha256': card['source_pdf_sha256'],
                      'title': source['title'], 'edition': source['edition'],
                      'edition_date': source['edition_date'],
                      'source_scope': source['scope'],
                      'printed_page': e['printed_page'],
                      'pdf_page_1based': e['pdf_page_1based'],
                      'text_basis': e['normalization'],
                      'raw_text_span': e['raw_text_span'],
                      'offset_basis': e['raw_span_basis']}
                     for e in card['evidence']]}


def messages(task):
    return (ModelMessage('system', PROMPT), ModelMessage('user', canonical(task)))


def prepare(root, output):
    card_path = root / 'SW-001.owner-confirmed-v1.json'
    labels_path = root / 'SW-001.synthetic-owner-confirmed-v1.json'
    card = json.loads(card_path.read_text(encoding='utf-8'))
    labels = json.loads(labels_path.read_text(encoding='utf-8'))
    assert labels['status'] == 'owner_confirmed_synthetic_labels_and_expressions'
    assert labels['parent_card_sha256'] == sha(card_path.read_bytes())
    source_path = root / card['source_manifest']
    source = json.loads(source_path.read_text(encoding='utf-8'))
    assert sha((source_path.parent / 'ABB-1SDC008001D0204.pdf').read_bytes()) == card['source_pdf_sha256']
    assert sha((root / card['selected_excerpts']).read_bytes()) == card['selected_excerpts_sha256']
    for e in card['evidence']:
        raw_path = source_path.parent / e['raw_extracted_page_file']
        assert sha(raw_path.read_bytes()) == e['raw_page_extraction_sha256']
        assert raw_path.read_text(encoding='utf-8')[slice(*e['raw_text_span'])] == e['raw_text']
        assert sha(e['text'].encode()) == e['text_sha256_utf8']
    tasks = [model_input(card, ex, source) for ex in labels['examples']]
    assert len(tasks) == 3 and len({t['sample_id'] for t in tasks}) == 3
    for t in tasks:
        assert {r['requirement_id'] for r in t['requirements']} == {'R1', 'R2'}
        assert ''.join(u['text'] for u in t['answer_units']) == t['answer']
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'input.json', tasks)
    write(output / 'expectations-private.json', labels)
    write(output / 'messages-preview.json', [[{'role': m.role, 'content': m.content}
                                             for m in messages(t)] for t in tasks])
    files = [Path(__file__), Path(base.__file__), Path(trial.__file__),
             Path('evaluation/text_bound_review_v2.py'), Path('evaluation/text_bound_review.py'),
             Path('services/validation_diagnostics.py')]
    manifest = {
        'version': VERSION, 'status': 'offline_prepared_no_execution',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'working_tree_hashes': {str(p): sha(p.read_bytes()) for p in files},
        'card_sha256': sha(card_path.read_bytes()),
        'confirmed_labels_sha256': sha(labels_path.read_bytes()),
        'prompt_sha256': sha(PROMPT.encode()), 'planned_items': 3,
        'api_calls': 0, 'independent_test': False,
    }
    for file, key in [('input.json', 'input_sha256'),
                      ('expectations-private.json', 'expectations_sha256'),
                      ('messages-preview.json', 'messages_preview_sha256')]:
        manifest[key] = sha((output / file).read_bytes())
    write(output / 'offline-manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'freeze', 'run'))
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = sys.modules[__name__]
    if args.action == 'prepare':
        print(canonical(prepare(Path('data/evaluation_local/evidence-bound-v1'), args.output)))
    elif args.action == 'freeze':
        print(canonical(trial.freeze(args.prepared, args.output, protocol=protocol)))
    else:
        trial.run(args.output, protocol=protocol)
