"""Offline supervised-review import and task-version-safe quality amendments.

Dispositions are not labels. No label is inferred from a mutation recipe.
"""
from collections import Counter
from copy import deepcopy
import hashlib
from pathlib import Path
import zipfile

from evaluation.support_dataset import (LABELS, VERSION, apply_reviews, canonical,
    digest, read, task_key, validate_sample, write, INCOMPLETE_RETRIEVAL)

DISPOSITIONS = ('candidate_ready', 'auxiliary_only', 'hold')
BLOCKING_FLAGS = frozenset({'stale_qualifiers', 'changed_tool_inputs', 'ambiguous_target',
    'ambiguous_exhaustivity', 'incomplete_proposition', 'anchor_mismatch', 'wrong_assertion_role',
    'incoherent_scope_extension', 'task_type_mixed', 'compound_input_and_fact',
    'missing_original_proposal', 'negation_of_unresolved_parent'})


def read_review_zip(path):
    import json
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        required = ('review-report-91.md', 'review-analysis-91.json')
        if any(names.count(name) != 1 for name in required):
            raise ValueError('missing or duplicated review member')
        if any(archive.getinfo(name).file_size > 5_000_000 for name in required):
            raise ValueError('review member exceeds capacity')
        # Read only named data; never execute or extract archive instructions.
        report = archive.read(required[0]).decode('utf8')
        analysis = json.loads(archive.read(required[1]))
    return analysis, report, hashlib.sha256(Path(path).read_bytes()).hexdigest()


def import_analysis(samples, analysis, *, expected_source_zip_sha256,
                    review_zip_sha256, confirmed_selection=()):
    if analysis['summary']['source_zip_sha256'] != expected_source_zip_sha256:
        raise ValueError('review references a different frozen source package')
    byid = {s['sample_id']: s for s in samples}
    if len(byid) != len(samples):
        raise ValueError('duplicate frozen sample ID')
    rows = analysis['reviews']
    if len(rows) != len(samples) or len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('review must cover each frozen sample exactly once')
    output = deepcopy(samples)
    out = {s['sample_id']: s for s in output}
    for row in rows:
        sid = row['sample_id']
        if sid not in byid or row['task_sha256'] != task_key(byid[sid]['task']):
            raise ValueError('review task identity mismatch')
        if row['task_type'] != byid[sid]['task']['task_type']:
            raise ValueError('review task type mismatch')
        for key in ('group_id', 'split'):
            if key in row and row[key] != byid[sid].get(key):
                raise ValueError('review lineage/split mismatch')
        if row['disposition'] not in DISPOSITIONS:
            raise ValueError('unknown disposition')
        if row['proposed_label'] is not None and row['proposed_label'] not in LABELS:
            raise ValueError('unknown label')
        allowed = {q['basis_id'] for q in byid[sid]['task']['evidence']} | {
            b['basis_id'] for b in byid[sid]['task']['other_basis']}
        if not set(row['basis_ids']) <= allowed:
            raise ValueError('review basis outside frozen task')
        if row['disposition'] == 'candidate_ready' and (row['proposed_label'] is None or BLOCKING_FLAGS.intersection(row['quality_flags'])):
            raise ValueError('ready candidate lacks label or carries unresolved quality flag')
        validate_sample(byid[sid])
        out[sid]['quality_review'] = dict(row, review_zip_sha256=review_zip_sha256,
            source='ai_assisted_user_supervised', task_mutated=False)
        out[sid]['prior_eligible_for_baseline'] = byid[sid]['eligible_for_baseline']
        out[sid]['eligible_for_baseline'] = bool(byid[sid]['eligible_for_baseline']) and row['disposition'] == 'candidate_ready'
    counts = dict(Counter(r['disposition'] for r in rows))
    if counts != analysis['summary']['dispositions']:
        raise ValueError('review disposition summary mismatch')
    # Explicit per-ID confirmation only; no --confirm-all or recipe shortcut.
    reviewed = {r['sample_id']: r for r in rows}
    for selection in confirmed_selection:
        row = reviewed.get(selection['sample_id'])
        if row is None or row['disposition'] != 'candidate_ready':
            raise ValueError('only explicitly selected ready candidates can be confirmed here')
        if selection['label'] not in LABELS:
            raise ValueError('invalid supervised label')
        if (selection['label'] != row['proposed_label'] or set(selection['basis_ids']) != set(row['basis_ids'])) and not selection.get('note', '').strip():
            raise ValueError('user correction requires an explicit rationale, not an implicit AI label change')
        if selection['status'] != 'confirmed' or not selection.get('reviewer_id'):
            raise ValueError('explicit reviewer confirmation required')
    output = apply_reviews(output, {'reviews': list(confirmed_selection)})
    return output, {'dispositions': counts, 'confirmed_labels': sum(
        s['supervision']['status'] == 'confirmed' for s in output),
        'task_identity_unchanged': all(task_key(s['task']) == task_key(byid[s['sample_id']]['task']) for s in output),
        'flag_counts': dict(Counter(f for r in rows for f in r['quality_flags']))}


def amend_task(sample, new_task, *, reason):
    """Create a new frozen task; preserve lineage, drop old predictions/reviews."""
    validate_sample(sample)
    changed = deepcopy(sample)
    changed['task'] = deepcopy(new_task)
    changed['sample_id'] = task_key(new_task)
    if changed['sample_id'] == sample['sample_id']:
        raise ValueError('amendment must change the actual task and its hash')
    changed['observations'] = []
    changed['eligible_for_baseline'] = new_task['delivery_state'] not in INCOMPLETE_RETRIEVAL | {'capacity_omitted', 'retrieval_failed'}
    changed['supervision'] = dict(changed['supervision'], status='pending', label=None,
        suggestion_label=None, suggestion_method='withheld_after_task_amendment',
        source='ai_assisted_user_supervised', reviewer_id=None,
        rationale='修订任务必须重新逐项审阅；不继承父项真假。')
    for key in ('basis_ids', 'note', 'task_sha256'):
        changed['supervision'].pop(key, None)
    for key in ('review_history', 'quality_review'):
        changed.pop(key, None)
    for origin in changed['origins']:
        source_origin = deepcopy(origin)
        origin.update(parent_sample_id=sample['sample_id'], amended_from_task_sha256=task_key(sample['task']),
                      amendment_reason=reason, source_origin=source_origin, run_id=None,
                      answer_id='quality-amendment-' + changed['sample_id'][:16], answer_version=1,
                      request_sha256=None, response_sha256=None)
    changed['synthetic'] = True
    changed['recipe'] = {'method': 'supervised-quality-amendment-v1', 'reason': reason,
                         'parent_task_sha256': task_key(sample['task'])}
    return validate_sample(changed)


def prediction_scope(samples, baseline):
    allowed = {s['sample_id']: digest(canonical(s['task'])) for s in samples}
    valid, excluded = [], []
    for prediction in baseline['predictions']:
        sid = prediction['sample_id']
        if sid not in allowed or baseline['task_hashes'].get(sid) != allowed[sid]:
            excluded.append({'sample_id': sid, 'reason': 'not_the_original_frozen_task'})
        elif prediction.get('status') in ('complete', 'valid_partial'):
            valid.append(prediction)
    return {'valid_original_predictions': valid, 'excluded': excluded,
            'rule': 'No parent-based replay into repaired tasks; no new API calls.'}


def quality_entry(sample, *, disposition, proposed_label, flags, rationale):
    if disposition not in DISPOSITIONS or proposed_label not in (*LABELS, None):
        raise ValueError('invalid quality decision')
    if disposition == 'hold' and proposed_label is not None:
        raise ValueError('hold label is withheld, not silently trained')
    if disposition == 'candidate_ready' and (BLOCKING_FLAGS.intersection(flags) or proposed_label is None):
        raise ValueError('unresolved flags cannot be called ready')
    return {'sample_id': sample['sample_id'], 'task_sha256': task_key(sample['task']),
            'task_type': sample['task']['task_type'], 'disposition': disposition,
            'proposed_label': proposed_label, 'quality_flags': flags, 'rationale': rationale,
            'basis_ids': [q['basis_id'] for q in sample['task']['evidence']],
            'source': 'ai_assisted_pending_user_supervision', 'label_status': 'pending',
            'original_suggestion_label': sample['supervision']['suggestion_label']}


def apply_quality_layer(samples, entries):
    """New dataset view, immutable tasks; hold/aux cannot enter core training."""
    byid = {s['sample_id']: s for s in samples}
    if len(byid) != len(samples) or len(entries) != len(samples) or len({e['sample_id'] for e in entries}) != len(entries):
        raise ValueError('quality layer must cover unique samples exactly once')
    output = []
    for entry in entries:
        old = byid.get(entry['sample_id'])
        if old is None or entry['task_sha256'] != task_key(old['task']):
            raise ValueError('quality task mismatch')
        if old['supervision']['status'] != 'pending':
            raise ValueError('AI quality layer must not undo confirmed/disputed supervision')
        allowed = {q['basis_id'] for q in old['task']['evidence']} | {b['basis_id'] for b in old['task']['other_basis']}
        if not set(entry['basis_ids']) <= allowed:
            raise ValueError('quality basis outside task')
        checked = quality_entry(old, disposition=entry['disposition'], proposed_label=entry['proposed_label'],
                                flags=entry['quality_flags'], rationale=entry['rationale'])
        # A reviewer may select a strict subset; do not widen it to every quote.
        checked['basis_ids'] = list(entry['basis_ids'])
        revised = deepcopy(old)
        revised['prior_supervision'] = deepcopy(old['supervision'])
        revised['quality_review'] = checked
        revised['prior_eligible_for_baseline'] = old['eligible_for_baseline']
        revised['eligible_for_baseline'] = bool(old['eligible_for_baseline']) and entry['disposition'] == 'candidate_ready'
        revised['supervision'].update(suggestion_label=entry['proposed_label'],
            suggestion_method='independent_delivered_quote_and_target_quality_review_v1',
            rationale=entry['rationale'])
        output.append(validate_sample(revised))
    return output


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', required=True); p.add_argument('--review-zip', required=True)
    p.add_argument('--source-zip', required=True); p.add_argument('--output', required=True)
    p.add_argument('--confirmed-selection')
    args = p.parse_args()
    analysis, report, zip_hash = read_review_zip(args.review_zip)
    dataset = read(args.dataset)
    selection = read(args.confirmed_selection)['reviews'] if args.confirmed_selection else []
    samples, checks = import_analysis(dataset['samples'], analysis,
        expected_source_zip_sha256=hashlib.sha256(Path(args.source_zip).read_bytes()).hexdigest(),
        review_zip_sha256=zip_hash, confirmed_selection=selection)
    root = Path(args.output); root.mkdir(parents=True, exist_ok=False)
    write(root / 'reviewed-dataset.json', dict(dataset, samples=samples))
    write(root / 'import-checks.json', checks)
    (root / 'source-review-report.md').write_text(report, encoding='utf8')
    for disposition in DISPOSITIONS:
        write(root / (disposition + '.json'), {'schema_version': VERSION,
              'samples': [s for s in samples if s['quality_review']['disposition'] == disposition]})


if __name__ == '__main__':
    main()
