"""Explicit local composition; generic ComponentFactory remains unchanged."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from backend.assembly import ComponentFactory, ConfigurationError


class OverlapFactory(ComponentFactory):
    def preflight(self):
        c = self.config
        if (c.profile != 'real' or c.retrieval_mode != 'bm25' or
            c.verification_schema != 13 or c.fact_review_execution != 'serial_v1' or
            c.audit_strategy != 'baseline' or c.fact_internal_flow != 'production' or
            c.fact_review_contract != 'production' or c.domain_internal_flow != 'production' or
            c.review_result_transport != 'json' or c.revision_answer_delivery != 'production' or
            c.local_revision_interface != 'production'):
            raise ConfigurationError('Overlap requires accepted SQLite/schema13 production policies')
        return super().preflight()

    def create(self, *args, **kwargs):
        bundle = super().create(*args, **kwargs)
        bundle.harness.fact_domain_retrieval_overlap = True
        return bundle


class ManagedFactory(OverlapFactory):
    def __init__(self, config, selection='component'):
        if selection not in ('component', 'overlap'):
            raise ValueError('Invalid managed Factory selection')
        super().__init__(config)
        self.selection = selection
        self.actual_enabled = None
        self._trace_lock = threading.Lock()
        self._events = {}
        self._revision = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1],
            text=True).strip()

    def preflight(self):
        if self.config.profile == 'real' and os.environ.get('DEEPSEEK_MODEL_ID') != 'deepseek-flash':
            raise ConfigurationError('Managed local service requires deepseek-flash')
        if self.selection == 'overlap':
            return OverlapFactory.preflight(self)
        return ComponentFactory.preflight(self)

    def runtime_status(self):
        return dict(version='managed-overlap-release-v25', selection=self.selection,
                    startup_factory_probe_enabled=self.actual_enabled, source_commit=self._revision,
                    run_db=str(self.config.run_db.resolve()),
                    budget_ledger='existing RunStore snapshots/results and service_private diagnostics; no global batch gate',
                    trace=str(self.config.run_db.parent / 'managed-overlap-events.jsonl'))

    def manifest(self, *args, **kwargs):
        value = super().manifest(*args, **kwargs)
        value['managed_factory'] = self.runtime_status()
        return value

    def emit(self, rid, kind, **details):
        event = dict(run_id=rid, kind=kind, wall=time.time(), **details)
        with self._trace_lock:
            path = self.config.run_db.parent / 'managed-overlap-events.jsonl'
            with path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + '\n')
            if kind == 'retrieval_start' and details.get('purpose') == 'domain_review':
                self._events[rid] = {'domain_start': event['wall']}
            row = self._events.get(rid)
            if row is not None and kind == 'fact_http_worker_begin':
                row.setdefault('fact_http_worker_begin', event['wall'])
            if kind == 'retrieval_return' and details.get('purpose') == 'domain_review' and row is not None:
                row['domain_return'] = event['wall']
                if 'fact_http_worker_begin' in row:
                    observation = dict(run_id=rid, selection=self.selection, source_commit=self._revision,
                        first_natural_task_observed=True, **row,
                        overlap_observed=row['domain_start'] < row['fact_http_worker_begin'] < row['domain_return'],
                        meaning='HTTP worker entry, not exact socket POST; no answer quality claim')
                    receipt = self.config.run_db.parent / 'overlap-first-natural-observation.json'
                    if not receipt.exists():
                        receipt.write_text(json.dumps(observation, ensure_ascii=False, indent=2), encoding='utf-8')
                self._events.pop(rid, None)

    def warm_corpus_index(self):
        super().warm_corpus_index()
        self.preflight()
        # Instantiate the actual composition without submitting or charging a run.
        bundle = self.create('__managed_startup_probe__', None)
        try:
            self.actual_enabled = getattr(bundle.harness, 'fact_domain_retrieval_overlap', False)
            if self.actual_enabled != (self.selection == 'overlap'):
                raise ConfigurationError('Actual Factory selection mismatch')
        finally:
            bundle.close()
        receipt = dict(self.runtime_status(), pid=os.getpid(), configured_at=time.time(),
                       configuration_effective=True, first_natural_task_observed=False,
                       model_calls_from_startup_probe=0)
        path = self.config.run_db.parent / 'managed-service-runtime.json'
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

    def create(self, rid, observer, **kwargs):
        bundle = ComponentFactory.create(self, rid, observer, **kwargs)
        if self.selection == 'overlap':
            bundle.harness.fact_domain_retrieval_overlap = True
        self.emit(rid, 'factory_created', selection=self.selection,
                  enabled=getattr(bundle.harness, 'fact_domain_retrieval_overlap', False))
        retriever = bundle.harness.retriever
        if retriever is not None:
            original = retriever.retrieve
            async def retrieve(request):
                self.emit(rid, 'retrieval_start', purpose=request.purpose.value)
                try:
                    return await original(request)
                finally:
                    self.emit(rid, 'retrieval_return', purpose=request.purpose.value)
            retriever.retrieve = retrieve
        client = bundle.harness.verification.client
        adapter = client.adapter
        if hasattr(adapter, '_exchange'):
            previous_complete = client.complete
            previous_exchange = adapter._exchange
            active = False
            async def complete(*args, **kwargs):
                nonlocal active
                active = True
                try:
                    return await previous_complete(*args, **kwargs)
                finally:
                    active = False
            def exchange(*args, **kwargs):
                if active:
                    self.emit(rid, 'fact_http_worker_begin')
                return previous_exchange(*args, **kwargs)
            client.complete = complete
            adapter._exchange = exchange
        return bundle
