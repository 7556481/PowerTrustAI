"""Receive pending review opinions and freeze baseline inputs, without API access."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
from itertools import combinations
from pathlib import Path
import re

from evaluation.support_dataset import (VERSION, canonical, digest, normalized,
    read, task_key, validate_sample, write)
from evaluation.support_review_quality import apply_quality_layer, prediction_scope
from evaluation.support_baseline import messages, model_input, pack, PROMPT_VERSION, PROMPT


def receive(samples, analysis, *, review_sha256):
    """Exact frozen coverage; opinions cannot promote pending supervision."""
    rows = analysis['reviews']
    byid = {s['sample_id']: s for s in samples}
    if len(byid) != len(samples) or {r['sample_id'] for r in rows} != set(byid) or len(rows) != len(samples):
        raise ValueError('review coverage/duplicate mismatch')
    for row in rows:
        s = byid[row['sample_id']]
        if row['task_type'] != s['task']['task_type']:
            raise ValueError('review task type mismatch')
        if row.get('label_status') != 'pending':
            raise ValueError('reception accepts pending opinions only')
        if 'claim' in row and row['claim'] != s['task']['claim']['proposition']:
            raise ValueError('review proposition mismatch')
        if 'quote' in row and row['quote'] not in [q['text'] for q in s['task']['evidence']]:
            raise ValueError('review quotation mismatch')
    output = apply_quality_layer(samples, rows)
    for s in output:
        s['quality_review'].update(review_sha256=review_sha256,
            source='ai_assisted_user_supervision_pending', task_mutated=False)
    return output


def merge(groups):
    """Keep all dispositions; preserve frozen group/split and parent lineage."""
    all_samples = []
    for name, samples in groups:
        for original in samples:
            s = deepcopy(original)
            validate_sample(s)
            if s['supervision']['status'] != 'pending' or s['supervision']['label'] is not None:
                raise ValueError('pending merge cannot import confirmed labels')
            s['merge_cohort'] = name
            all_samples.append(s)
    byid = {s['sample_id']: s for s in all_samples}
    if len(byid) != len(all_samples):
        raise ValueError('duplicate merged sample ID')
    for s in all_samples:
        for o in s['origins']:
            parent = o.get('parent_sample_id')
            if parent and parent in byid and (s['group_id'], s['split']) != (byid[parent]['group_id'], byid[parent]['split']):
                raise ValueError('parent lineage crosses frozen split')
    primary = [s for s in all_samples if s['quality_review']['disposition'] == 'candidate_ready']
    if any(not s['eligible_for_baseline'] for s in primary):
        raise ValueError('primary candidate has incomplete delivery/invalid structure')
    manifest = [{'sample_id': s['sample_id'], 'task_key': task_key(s['task']),
        'task_sha256': digest(canonical(s['task'])), 'cohort': s['merge_cohort'],
        'task_type': s['task']['task_type'], 'synthetic': s['synthetic'],
        'group_id': s['group_id'], 'split': s['split'],
        'parent_sample_ids': sorted({o['parent_sample_id'] for o in s['origins'] if o.get('parent_sample_id')}),
        'disposition': s['quality_review']['disposition'],
        'suggestion_label': s['quality_review']['proposed_label'],
        'basis_ids': s['quality_review']['basis_ids'],
        'label_source': s['quality_review'].get('source', s['quality_review'].get('review_source')),
        'label_status': 'pending', 'confirmed_label': None,
        'review_sha256': s['quality_review'].get('review_sha256', s['quality_review'].get('review_zip_sha256'))}
        for s in all_samples]
    counts = Counter(s['quality_review']['proposed_label'] for s in primary)
    report = {'total': len(all_samples), 'primary': len(primary),
        'dispositions': dict(Counter(s['quality_review']['disposition'] for s in all_samples)),
        'primary_labels': {k: counts[k] for k in ('supported', 'contradicted', 'insufficient_evidence', 'not_assessable')},
        'primary_task_types': dict(Counter(s['task']['task_type'] for s in primary)),
        'primary_cohorts': dict(Counter(s['merge_cohort'] for s in primary)),
        'primary_families': len({s['group_id'] for s in primary}),
        'primary_splits': dict(Counter(s['split'] for s in primary)),
        'confirmed_labels': 0, 'independent_test': False}
    return all_samples, primary, manifest, report


def relationships(samples):
    """Expose quote/page/document sharing and near duplicates without re-splitting."""
    buckets = {k: defaultdict(set) for k in ('quote', 'evidence', 'document')}
    byid = {s['sample_id']: s for s in samples}
    for s in samples:
        for q in s['task']['evidence']:
            meta = q['metadata']
            keys = {'quote': q['text_sha256'], 'evidence': q['evidence_id'],
                    'document': canonical([meta.get('source_id'), meta.get('source_version')])}
            for kind, key in keys.items():
                buckets[kind][key].add(s['sample_id'])
    result = {}
    for kind, bucket in buckets.items():
        result[kind] = [{'key': k, 'sample_ids': sorted(ids),
            'splits': sorted({byid[i]['split'] for i in ids}),
            'cross_split': len({byid[i]['split'] for i in ids}) > 1}
            for k, ids in sorted(bucket.items()) if len(ids) > 1]
    tokens = {s['sample_id']: set(re.findall(r'\w+', normalized(s['task']['claim']['proposition']))) for s in samples}
    result['near_duplicates'] = []
    for a, b in combinations(samples, 2):
        if a['task']['task_type'] != b['task']['task_type']:
            continue
        x, y = tokens[a['sample_id']], tokens[b['sample_id']]
        score = len(x & y) / len(x | y) if x | y else 0
        if score >= .9:
            result['near_duplicates'].append({'sample_ids': [a['sample_id'], b['sample_id']],
                'token_jaccard': score, 'cross_split': a['split'] != b['split']})
    result['rule'] = 'Frozen splits preserved; shared documents are not independent cross-document evaluation.'
    return result


def prepare(primary, baseline):
    """One sample per request, exact task-only messages; never load environment."""
    batches, excluded = pack(primary, max_items=1)
    scope = prediction_scope(primary, baseline)
    reusable = {p['sample_id'] for p in scope['valid_original_predictions']}
    requests = [{'sample_id': b[0]['sample_id'],
        'task_sha256': digest(canonical(b[0]['task'])),
        'messages': [{'role': m.role, 'content': m.content} for m in messages(b)],
        'message_chars': sum(len(m.content) for m in messages(b)),
        'reusable_original_prediction': b[0]['sample_id'] in reusable} for b in batches]
    return {'prompt_version': PROMPT_VERSION, 'prompt_sha256': digest(PROMPT),
        'task_version': VERSION, 'model_input': model_input(primary),
        'requests': requests, 'excluded': excluded, 'max_items': 1,
        'max_corrections_per_sample': 1, 'maximum_requests_without_reuse': 2 * len(requests),
        'maximum_requests_with_exact_reuse': 2 * sum(not r['reusable_original_prediction'] for r in requests),
        'prediction_scope': scope, 'actual_calls': 0, 'execution_started': False,
        'semantic_metrics': None, 'runner_ready': False,
        'runner_blocker': 'Existing execute stops globally on any batch failure; sample-local failure continuation requires a separately tested runner change before execution.'}


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('old', 'expansion', 'amended', 'review-directory', 'original-zip', 'quality-zip', 'baseline', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    received = Path(a.review_directory)
    integrity = read(received / 'integrity-checks.json')
    for name, path in [('support-review-expansion-v1.zip', a.original_zip), ('quality-supplement-v3.zip', a.quality_zip)]:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != integrity['uploaded_zip_sha256'][name]:
            raise ValueError('frozen source ZIP hash mismatch')
    expansion = read(a.expansion)['samples']; amended = read(a.amended)['samples']
    rows = read(received / 'review-analysis-54.json')
    opinion_hash = hashlib.sha256((received / 'review-analysis-54.json').read_bytes()).hexdigest()
    revised = receive(expansion + amended, rows, review_sha256=opinion_hash)
    exp_ids = {s['sample_id'] for s in expansion}
    combined, primary, manifest, report = merge([
        ('old_91', read(a.old)['samples']),
        ('expansion_48', [s for s in revised if s['sample_id'] in exp_ids]),
        ('amended_6', [s for s in revised if s['sample_id'] not in exp_ids])])
    root = Path(a.output); root.mkdir(parents=True, exist_ok=False)
    write(root / 'all-pending.json', {'schema_version': VERSION, 'samples': combined})
    write(root / 'primary-pending.json', {'schema_version': VERSION, 'samples': primary})
    write(root / 'merge-manifest.json', {'items': manifest, 'report': report})
    write(root / 'relationships.json', relationships(combined))
    write(root / 'baseline-preparation.json', prepare(primary, read(a.baseline)))
    for disposition in ('auxiliary_only', 'hold'):
        write(root / (disposition + '.json'), {'schema_version': VERSION,
            'samples': [s for s in combined if s['quality_review']['disposition'] == disposition]})
    print(canonical(report))


if __name__ == '__main__':
    main()
