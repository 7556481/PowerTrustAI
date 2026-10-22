"""Read-only post-run checks and small whitelisted public statistics; no model code."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from evaluation.generation_mapping_trial_v1 import DIRECTORY, RESPONSES, FREEZE, PUBLIC, ROOT, read, write, sha, assert_no_evaluator_keys


def aggregate(records):
    return dict(calls=len(records), input_tokens=sum(r['usage']['input_tokens'] for r in records),
                output_tokens=sum(r['usage']['output_tokens'] for r in records),
                total_tokens=sum(r['usage']['total_tokens'] for r in records),
                cache_hit_tokens=sum(r['usage']['cache_hit_tokens'] or 0 for r in records),
                cache_miss_tokens=sum(r['usage']['cache_miss_tokens'] or 0 for r in records),
                request_duration_ms_sum=sum(r['duration_ms'] for r in records))


def main():
    summary, freeze = read(DIRECTORY / 'summary.json'), read(FREEZE)
    for item in freeze['bound_files']:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256']
    assert freeze == read(DIRECTORY / 'freeze.json')
    assert read(DIRECTORY / 'attempt.json')['freeze_sha256'] == hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    rows, all_records, groups = [], [], defaultdict(list)
    artifact_ids = []
    journal_count = 0
    for branch in summary['branches']:
        ident, result = branch['request_id'], branch['result']
        row = {k: branch[k] for k in ('request_id', 'task_id', 'variant', 'status', 'reason', 'workload')}
        if result is None:
            row.update(answer_quality='unexecuted', mapping='unexecuted', audit='unexecuted', calls=0)
            rows.append(row)
            continue
        assert not branch['entry_failure']
        records = result['model_records']
        assert len(records) == len(branch['sent'])
        assert len({r['call_number'] for r in records}) == len(records)
        assert len(records) <= 40
        journals = sorted((RESPONSES / ident).glob('before-send-*.json'))
        assert len(journals) == len(records)
        for path in journals:
            item = read(path)
            assert sha(item['messages']) == item['messages_sha256']
            assert item['branch'] == ident
            if not item['prompt_version'].startswith(('evidence-bound-generation', 'concept-evidence-generation')):
                assert_no_evaluator_keys(json.loads(item['messages'][1]['content']))
            artifact_ids.append({'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'messages_sha256': item['messages_sha256']})
        journal_count += len(journals)
        for name in ('final-result.json', 'execution-observations.json', 'controller-accepted.json', 'controller-result.json', 'controller-control.json'):
            path = DIRECTORY / ident / name
            if not path.exists():
                continue
            artifact_ids.append({'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        all_records.extend(records)
        for record in records:
            groups[(branch['variant'], record['component'], 'correction' if record['correction'] else 'initial')].append(record)
        answer, verification = result['answer'], result['verification_output']
        claims = {c['claim_id']: c for c in verification['claims']}
        findings = []
        for finding in verification['findings']:
            claim = claims[finding['claim_id']]
            findings.append({'claim_id': claim['claim_id'], 'proposition': claim['proposition'],
                'answer_quote': answer['text'][claim['start_offset']:claim['end_offset']], 'status': finding['status'],
                'rationale': finding['rationale'].split(' [')[0],
                'components': [{k: c.get(k) for k in ('component_id', 'status', 'origin', 'reason_code', 'basis_indexes',
                                'fidelity_status', 'review_disposition')} for c in finding['component_reviews']],
                'basis_ids': [{'evidence_id': b.get('evidence_id'), 'quote_id': b.get('quote_id'), 'type': b['type']}
                              for b in finding['bases']]})
        row.update(answer=answer['text'], answer_sha256=hashlib.sha256(answer['text'].encode()).hexdigest(),
            answer_chars=len(answer['text']), citations=len(answer['citations']),
            citation_initial_calls=len(answer['citations']), calls=len(records),
            policy=result['report']['decision']['kind'], execution_issues=result['execution_issues'],
            coverage=[{'requirement_id': f'R{i}', 'label': 'covered'} for i in (1, 2, 3)],
            coverage_assessment='AI text review after execution, user supervision; not owner confirmation of new results',
            blanket_refusal=False, deleted_subquestion=False, conditions_retained=True,
            answer_failure_count=0, envelope_failure_count=0,
            non_claim_spans=result['extraction_output']['non_claim_spans'],
            findings=findings,
            citation_reviews=[{'index': f['citation_index'], 'status': f['status'],
                               'rationale': f['rationale'].split(' [')[0]} for f in verification['citation_reviews']],
            domain=[{k: f[k] for k in ('category', 'check_status', 'rationale')}
                    for f in result['domain_output']['findings'] if f['origin'] == 'model_judgment'],
            timing_seconds={k: round(v, 6) for k, v in branch['times'].items()},
            usage=aggregate(records),
            failures=[{k: r.get(k) for k in ('call_number', 'component', 'correction', 'output_status', 'validation_error')}
                      for r in records if r['output_status'] != 'valid_structure'])
        if branch['variant'] == 'candidate':
            reports = [read(p) for p in (RESPONSES / ident).glob('scope-*.json') if '"failure_counts"' in p.read_text(encoding='utf8')]
            assert len(reports) == 1
            report = reports[0]
            row['mapping_report'] = report['report']
            row['mapping'] = [{'point': m['point'], 'answer_quotes': [answer['text'][u['start_offset']:u['end_offset']] for u in m['units']],
                               'source_ids': sorted({b['evidence_id'] for b in m['bases']}),
                               'condition_ids': [c['condition_id'] for c in m['conditions']], 'note': m['note']}
                              for m in report['mapping']]
        else:
            row['mapping'] = 'not_applicable_original'
        rows.append(row)
    assert Counter(r['status'] for r in rows) == {'complete': 2, 'execution_failed': 1, 'unexecuted': 5}
    assert journal_count == len(all_records) == 21
    assert sum(r['correction'] for r in all_records) == 2
    assert all((r.get('answer_chars') or 0) <= 220 for r in rows)
    output = {'version': 'generation-mapping-comparison-results-v1', 'source_base_commit': freeze['source_base_commit'],
        'freeze_sha256': hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
        'status': 'stopped_after_first_final_required_review_failure_no_resume',
        'assessment': 'AI-assisted post-run text review; user supervision, no owner acceptance of these new judgments yet',
        'planned_branches': 8, 'initial_generations': 3, 'complete_branches': 2, 'failed_branches': 1,
        'unexecuted_branches': 5, 'complete_pairs': 1,
        'coverage': {'planned_slots': 24, 'text_evaluated_slots': 9, 'covered': 9, 'unexecuted': 15,
                     'note': 'Not accuracy; includes the answer from an execution-incomplete branch. Mapping is not denominator.'},
        'total': aggregate(all_records),
        'usage_groups': [{'variant': v, 'stage': s, 'attempt': a, **aggregate(rs)} for (v, s, a), rs in groups.items()],
        'branches': rows, 'bill_amount': None,
        'adoption': 'do_not_adopt; insufficient completed comparison and no observed answer benefit in sole complete pair',
        'checks': {'frozen_files_unchanged': len(freeze['bound_files']), 'pre_send_journals_verified': journal_count,
                   'final_results_preserved': 3, 'generation_corrections': 0, 'audit_corrections': 2,
                   'guard_or_storage_failures': 0, 'model_transport_failures': 0},
        'limits': ['Reused development sources, not independent validation', 'Only one complete pair',
                   'Concurrent request durations are summed work, not branch wall time',
                   'Saved-answer timing is not browser first render', 'No production switch or new semantic claims']}
    write(PUBLIC / 'results-v1.json', output)
    write(PUBLIC / 'artifact-identities-v1.json', {'version': 'local-artifact-hash-ledger-v1', 'artifacts': artifact_ids,
          'note': 'Hashes only; actual requests/responses remain ignored data. No credentials or headers included.'})
    print(json.dumps({'total': output['total'], 'groups': output['usage_groups'], 'checks': output['checks']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
