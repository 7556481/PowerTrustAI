"""Explicit bounded read-only diagnosis, using frozen private retrieval requests.

No model/service entry point, environment loading, index construction or retries.
Instrumentation is local to this standalone process; production code is unchanged.
"""
import argparse
import asyncio
from collections import Counter
from contextlib import closing
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import sqlite3
from time import perf_counter
from unittest.mock import patch

from backend.serialization import wire
from core.models import AnswerDraft, Evidence, EvidenceProvenance, TaskMode, TaskRequest
from harness.contracts import RetrievalSettings, RunBudget
from harness.retrieval import RetrievalSession
from rag.contracts import ContextOptions, RetrievalPurpose
from rag.corpus_index import seal
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.storage import KnowledgeStore
from rag.timing import capture_timing, span

VERSION = 'audit-retrieval-final-diagnosis-v1'
_counts = ContextVar('audit_diagnostic_counts', default=None)
_connect = sqlite3.connect


class CountedConnection(sqlite3.Connection):
    def execute(self, sql, parameters=(), /):
        counts = _counts.get()
        if counts is not None:
            counts['sql_statements'] += 1
            if 'corpus_fts MATCH' in sql:
                counts['ranking_statements'] += 1
        return super().execute(sql, parameters)


def counted_connect(*args, **kwargs):
    kwargs['factory'] = CountedConnection
    return _connect(*args, **kwargs)


class MeasuredStore(KnowledgeStore):
    def __init__(self, *args, **kwargs):
        with span('store_open_and_schema'):
            super().__init__(*args, **kwargs)

    def close(self):
        with span('store_close'):
            super().close()

    def verify_evidence(self, evidence):
        with span('evidence_recheck'):
            return super().verify_evidence(evidence)


class ObservedRetriever(AsyncSQLiteBM25Retriever):
    """Capture complete outputs only in this diagnosis, without modifying them."""
    async def retrieve(self, request):
        self.observed_request = request
        self.observed_result = await super().retrieve(request)
        return self.observed_result


def restore_evidence(value):
    value = dict(value)
    value['applicability'] = tuple(value.get('applicability', ()))
    if value.get('provenance') is not None:
        value['provenance'] = EvidenceProvenance(**{
            k: tuple(v) if isinstance(v, list) else v for k, v in value['provenance'].items()})
    return Evidence(**value)


def request_projection(value):
    """Only predeclared volatile execution fields are excluded, never business fields."""
    value = wire(value)
    return {k: v for k, v in value.items() if k not in ('retrieval_id', 'duration_ms')}


def phase_summary(records):
    names = {r['phase'] for r in records}
    return {name: sum(r['seconds'] for r in records if r['phase'] == name) for name in sorted(names)}


def service_busy(path):
    with closing(_connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        return db.execute("SELECT 1 FROM runs WHERE status IN ('queued','running') LIMIT 1").fetchone() is not None


def validate_freeze(freeze):
    if freeze.get('version') != 'audit-retrieval-final-freeze-v1' or not 1 <= len(freeze['groups']) <= 3:
        raise ValueError('Expected bounded task freeze')
    if freeze['per_group_query_counts'] != [len(g['audit_records']) for g in freeze['groups']]:
        raise ValueError('Frozen query count mismatch')
    if not 0 < freeze['performance_seconds_cap'] <= 1200:
        raise ValueError('Invalid total performance cap')
    for group in freeze['groups']:
        if group['fact_strategy'] != 'aggregate' or group['execution_profile'] != 'topic_v4_subject_v1':
            raise ValueError('This fixed study requires the recorded aggregate production profile')
        for record in group['audit_records']:
            options = record.get('request_options')
            if (not options or options['scenario_id'] != group['scenario_id'] or
                    options['execution_profile'] != group['execution_profile'] or
                    record['knowledge_version'] != group['knowledge_version'] or
                    record['purpose'] not in ('verification', 'domain_review')):
                raise ValueError('Missing or inconsistent original request parameters')


async def diagnose_group(index, group, global_deadline, archive_path=None):
    budget = RunBudget(**group['budget'])
    retriever = ObservedRetriever(index, execution_profile=group['execution_profile'])
    saved = {e['evidence_id']: restore_evidence(e) for e in group['saved_evidence']}
    provided = tuple(restore_evidence(e) for e in group['provided_evidence'])
    started = perf_counter()
    deadline = min(global_deadline, started + budget.max_duration_seconds)
    first = group['audit_records'][0]
    # Only identity/version are consumed: all original queries are supplied verbatim.
    answer = AnswerDraft(first['answer_id'], first['answer_version'], 'Diagnostic identity carrier.')
    task = TaskRequest('frozen-retrieval-diagnostic', TaskMode.ASSESS_EXISTING,
                       group['scenario_id'], 'Frozen retrieval only.', existing_answer=answer,
                       provided_evidence=provided)
    session = RetrievalSession(retriever, group['knowledge_version'], RetrievalSettings(),
                               budget, deadline, provided)
    session.calls, session.chars = group['initial_calls'], group['initial_chars']
    session.known_evidence.update({eid: saved[eid] for eid in group['known_evidence_ids']})
    summaries, private = [], []
    try:
        with patch('rag.storage.KnowledgeStore', MeasuredStore), patch('rag.storage.sqlite3.connect', counted_connect):
            for ordinal, original in enumerate(group['audit_records']):
                if perf_counter() >= deadline:
                    raise TimeoutError('Fixed group/global deadline exhausted')
                options = original['request_options']
                context = None if options['context_options'] is None else ContextOptions(**options['context_options'])
                session.settings = RetrievalSettings(options['max_results'], context, 'aggregate')
                counter = Counter(sql_statements=0, ranking_statements=0)
                token = _counts.set(counter)
                try:
                    with capture_timing(run_id=group['run_id'], retrieval_id='diagnostic-' + str(ordinal)) as log:
                        call_start = perf_counter()
                        retriever.observed_result = None
                        delivery = await session.retrieve(RetrievalPurpose(original['purpose']), task, answer, (),
                                                          query_override=original['query'])
                        seconds = perf_counter() - call_start
                    private.append(dict(request=wire(getattr(retriever, 'observed_request', None)),
                        result=wire(retriever.observed_result), delivery=wire(delivery), timings=log.records))
                    if delivery.issue:
                        raise RuntimeError('Original retrieval execution failed: ' + delivery.issue.code)
                    # Budget, supply and complete request options are compared, not just hit IDs.
                    difference = [k for k in request_projection(delivery.record)
                                  if request_projection(delivery.record)[k] != request_projection(original)[k]]
                    historical_bodies_equal = all(saved[e.evidence_id] == e for e in delivery.evidence)
                    if difference or not historical_bodies_equal:
                        raise ValueError('Historical record/body difference: ' + ','.join(difference))
                    projection = wire(retriever.observed_result)
                    phases = phase_summary(log.records)
                    summaries.append(dict(ordinal=ordinal, purpose=original['purpose'], seconds=seconds,
                        historical_record_ms=original['duration_ms'], query_sha256=hashlib.sha256(original['query'].encode()).hexdigest(),
                        phases=phases, **counter, certificate_hits=sum(bool(s.get('certificate_hit')) for s in log.records),
                        rank_cache_hits=sum(bool(s.get('rank_cache_hit')) for s in log.records),
                        result_sha256=hashlib.sha256(json.dumps(projection, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                        historical_record_and_delivered_bodies_equal=True,
                        core_count=len(projection['evidence']), context_count=0 if projection['context'] is None else len(projection['context']['items']),
                        calls_used=session.calls, cumulative_chars=session.chars,
                        worker_handoff_seconds=phases.get('retriever_wait', 0)-phases.get('retriever_worker', 0)))
                finally:
                    _counts.reset(token)
    finally:
        while retriever._active is not None and not retriever._active.done():
            await asyncio.sleep(.05)
        retriever.close()
        if archive_path is not None:
            archive_path.write_text(json.dumps(private, ensure_ascii=False)+'\n', encoding='utf-8')
    return dict(run_prefix=group['run_id'][:8], seconds=perf_counter()-started,
                query_count=len(summaries), requests=summaries), private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--run-db', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    frozen_bytes = args.freeze.read_bytes()
    freeze = json.loads(frozen_bytes)
    validate_freeze(freeze)
    if args.output.exists():
        raise ValueError('Never overwrite or repeat a completed/partial fixed diagnosis')
    if service_busy(args.run_db):
        raise RuntimeError('Service busy; no performance work started')
    stat = args.index.stat()
    report = dict(version=VERSION, freeze_sha256=hashlib.sha256(frozen_bytes).hexdigest(),
                  index_size=stat.st_size, index_mtime_ns=stat.st_mtime_ns, new_model_calls=0,
                  application_cache_start=freeze['application_cache_start'], groups=[])
    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    save()
    try:
        start = perf_counter()
        print('Normal full-byte publication seal starting; no MATCH or model requests.', flush=True)
        with KnowledgeStore(args.index, readonly=True) as store:
            for knowledge in dict.fromkeys(g['knowledge_version'] for g in freeze['groups']):
                if seal(store, knowledge) is None:
                    raise ValueError('Frozen knowledge identity absent')
        report['startup_seal_seconds'] = perf_counter() - start
        start = perf_counter()
        from rag.topic_lanes import plan
        plan(freeze['groups'][0]['audit_records'][0]['query'])
        report['dictionary_and_first_plan_seconds'] = perf_counter() - start
        save()
        print(json.dumps({k: report[k] for k in ('startup_seal_seconds', 'dictionary_and_first_plan_seconds')}), flush=True)
        performance_start = perf_counter()
        deadline = performance_start + freeze['performance_seconds_cap']
        async def run():
            for group in freeze['groups']:
                if service_busy(args.run_db):
                    raise RuntimeError('Service became busy; stop without filling slots')
                row, _ = await diagnose_group(args.index, group, deadline,
                    args.output.parent / ('result-private-' + group['run_id'][:8] + '.json'))
                report['groups'].append(row)
                save()
                print(json.dumps(row), flush=True)
        asyncio.run(run())
        report.update(status='completed', performance_seconds=perf_counter()-performance_start)
    except BaseException as exc:
        report.update(status='stopped', error_type=type(exc).__name__)
        save()
        raise
    save()


if __name__ == '__main__':
    main()
