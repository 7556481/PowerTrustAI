"""Read-only, body-free summary of existing monotonic Harness measurements.

No model invocation, FTS query, index scan or credential loading. Wall-clock
queue/save offsets are explicitly labelled; nested/parallel totals are not added.
"""
import argparse
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3


UNKNOWN = ('queue_monotonic_seconds', 'fts_prepare_seconds',
           'fts_execute_fetch_sort_seconds', 'body_read_seconds',
           'retrieval_validation_seconds', 'persistence_seconds',
           'browser_first_paint_seconds', 'provider_internal_queue_seconds')


def wall_seconds(start, end):
    if not start or not end:
        return None
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()


def summarize(row, events, observation=None, request_roles=None):
    raw = row.get('result') or row.get('snapshot') or {}
    calls = raw.get('model_records', [])
    retrieval = raw.get('retrieval_records', [])
    stages = []
    first_save = None
    for ordinal, item in enumerate(events, 1):
        event = item['event']
        component = event['component']
        if component == 'answer_created' and first_save is None:
            first_save = wall_seconds(row.get('started'), event.get('timestamp_utc'))
        if component in ('generation', 'claim_extraction', 'evidence_verification',
                         'power_domain_review', 'revision', 'generation_query_conversion'):
            end_offset = wall_seconds(row.get('started'), event.get('timestamp_utc'))
            stages.append({'ordinal': ordinal, 'event_id': event['event_id'],
                           'stage': component, 'answer_version': event.get('answer_version'),
                           'status': event['status'], 'seconds': event['duration_ms'] / 1000,
                           'end_wall_offset_seconds': end_offset,
                           'start_wall_offset_seconds': None if end_offset is None else end_offset - event['duration_ms'] / 1000})
    model = []
    for c in calls:
        usage = c.get('usage') or {}
        scopes = (c.get('request_metrics') or {}).get('scope_ids', [])
        model.append({'request_id': f"{row['id']}:model:{c['call_number']}",
                      'call_number': c['call_number'], 'invocation_id': c.get('invocation_id'),
                      'stage': c.get('component'), 'answer_version': c.get('answer_version'),
                      'seconds': c['duration_ms'] / 1000, 'correction': c['correction'],
                      'status': c['status'], 'output_status': c.get('output_status'),
                      'input_tokens': usage.get('input_tokens'),
                      'output_tokens': usage.get('output_tokens'),
                      'total_tokens': usage.get('total_tokens'),
                      'review_scope_count': len(scopes),
                      'review_role': (request_roles or {}).get(c['call_number'], 'unknown')
                      if (request_roles or {}).get(c['call_number'], 'unknown') in
                      ('independent_fact', 'original_citations') else 'unknown'})
    queries = [{'retrieval_id': r['retrieval_id'], 'purpose': r['purpose'],
                'answer_version': r.get('answer_version'), 'seconds': r['duration_ms'] / 1000,
                'status': r['status'], 'outcome': r['outcome'], 'hits': len(r.get('hits', [])),
                'core_delivered': len(r.get('core_evidence_ids', [])),
                'context_delivered': len(r.get('context_evidence_ids', [])),
                'accepted_chars': r.get('accepted_chars'),
                'reused_from_retrieval_id': r.get('reused_from_retrieval_id')} for r in retrieval]
    # This sum is explicitly resource work, not a claim about elapsed critical path.
    durations = [r['seconds'] for r in queries]
    known_tokens = [c['total_tokens'] for c in model if c['total_tokens'] is not None]
    report = raw.get('report') or {}
    config = row.get('config') or {}
    return {'version': 'existing-trace-performance-profile-v1', 'run_id': row['id'],
            'execution_status': row['status'], 'harness_seconds': None if raw.get('duration_ms') is None else raw['duration_ms'] / 1000,
            'run_wall_seconds': wall_seconds(row.get('started'), row.get('ended')),
            'queue_wall_seconds': wall_seconds(row.get('created'), row.get('started')),
            'answer_created_event_wall_offset_seconds': first_save,
            'observation': {k: v for k, v in (observation or {}).items() if k in
                            ('run_id', 'poll_seconds', 'observer_end_seconds',
                             'first_saved_answer_observed_seconds', 'browser_first_paint_seconds',
                             'terminal_status', 'observation_timeout')}, 'unknown': dict.fromkeys(UNKNOWN),
            'stages': stages, 'model_calls': model, 'retrievals': queries,
            'model_call_count': len(model), 'correction_count': sum(c['correction'] for c in model),
            'revision_count': len(raw.get('revision_outputs', [])),
            'recorded_total_tokens': sum(known_tokens), 'unknown_usage_calls': len(model) - len(known_tokens),
            'retrieval_record_count': len(queries), 'retrieval_resource_seconds_sum': sum(durations),
            'model_resource_seconds_sum': sum(c['seconds'] for c in model),
            'decision_kind': (report.get('decision') or {}).get('kind'),
            'execution_issue_count': len(raw.get('execution_issues', [])),
            'configuration': {k: config.get(k) for k in ('model_id', 'knowledge_version', 'protocols', 'policy', 'retrieval_mode', 'fact_retrieval_strategy', 'budget')},
            'limits': ['Stage/model/retrieval durations are existing monotonic counters, truncated to milliseconds.',
                       'Wall timestamps are not monotonic; queue/save offsets are approximate.',
                       'answer_created is before observer persistence; it is neither commit time nor browser first paint.',
                       'Nested request/stage times and parallel fact/domain times must not be added to elapsed time.',
                       'FTS plan/match cardinality not collected: no expensive query or scan rerun.',
                       'Existing scope catalogs label independent/original-citation requests; request duration is not a separate substage timer.']}


def read_summary(database, run_id, observation=None):
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        found = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if found is None:
            raise ValueError('Run ID not found')
        row = dict(found)
        for k in ('result', 'snapshot', 'config'):
            row[k] = json.loads(row[k]) if row[k] else None
        events = [{'event': json.loads(r['payload'])} for r in db.execute(
            'SELECT payload FROM events WHERE run_id=? ORDER BY ordinal', (run_id,))]
    # Read only existing opt-in scope catalogs to label request purpose; never
    # copy their contents. No prompts/responses or provider headers are opened.
    diagnostic_root = Path(__file__).resolve().parents[1] / 'data/retrieval_local'
    roles = {}
    for c in (row.get('result') or row.get('snapshot') or {}).get('model_records', []):
        if c.get('component') != 'evidence_verification' or not c.get('candidate_catalog_path'):
            continue
        path = Path(c['candidate_catalog_path']).resolve()
        if not path.is_relative_to(diagnostic_root.resolve()) or not path.name.startswith('scope-') or path.suffix != '.json':
            continue
        try:
            catalog = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if catalog.get('section') == 'BOUNDED_ORIGINAL_CITATIONS_UNTRUSTED':
            roles[c['call_number']] = 'original_citations'
        elif catalog.get('section') == 'SCOPED_REVIEW_DATA_UNTRUSTED' and 'MODEL_COMPONENT_INDEXES' in catalog:
            roles[c['call_number']] = 'independent_fact'
    return summarize(row, events, observation, roles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path('data/runtime_local/runs.sqlite3'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--observation', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    observed = json.loads(args.observation.read_text(encoding='utf-8')) if args.observation else None
    result = read_summary(args.database, args.run_id, observed)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('run_id', 'harness_seconds', 'model_call_count', 'recorded_total_tokens', 'retrieval_resource_seconds_sum')}))


if __name__ == '__main__':
    main()
