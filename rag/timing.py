"""Opt-in monotonic retrieval spans; never collect queries or Evidence bodies."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
import re
from threading import Lock
from time import perf_counter
from uuid import uuid4

_log = ContextVar('retrieval_timing_log', default=None)
_parent = ContextVar('retrieval_timing_parent', default=None)


class TimingLog:
    def __init__(self,run_id=None,retrieval_id=None):
        for ident in (run_id,retrieval_id):
            if ident is not None and (type(ident) is not str or re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',ident) is None):
                raise ValueError('Timing identity must be an opaque ID')
        self.run_id,self.retrieval_id=run_id,retrieval_id
        self.started = perf_counter()
        self.records = []
        self.lock = Lock()


@contextmanager
def capture_timing(*,run_id=None,retrieval_id=None):
    log = TimingLog(run_id,retrieval_id)
    token = _log.set(log)
    parent = _parent.set(None)
    try:
        yield log
    finally:
        _parent.reset(parent)
        _log.reset(token)


@contextmanager
def span(phase):
    log = _log.get()
    details = {}
    if log is None:
        yield details
        return
    ident = uuid4().hex
    parent = _parent.get()
    token = _parent.set(ident)
    start = perf_counter()
    status = 'succeeded'
    try:
        yield details
    except BaseException:
        status = 'failed'
        raise
    finally:
        end = perf_counter()
        _parent.reset(token)
        # Only small mechanical flags/counts, never arbitrary values or exceptions.
        allowed = {k: v for k, v in details.items() if k in
                   ('result_count', 'body_count', 'ranking_replayed', 'ranking_replay_attempted', 'certificate_hit')
                   and type(v) in (int, bool)}
        record = {'version':'retrieval-timing-v1','run_id':log.run_id,'retrieval_id':log.retrieval_id,
                  'span_id': ident, 'parent_id': parent, 'phase': phase,
                  'start_seconds': start - log.started, 'end_seconds': end - log.started,
                  'seconds': end - start, 'status': status, **allowed}
        with log.lock:
            if phase=='result_validation' and details.get('_fts_mode'):
                descendants={ident}
                while True:
                    expanded=descendants | {r['span_id'] for r in log.records if r['parent_id'] in descendants}
                    if expanded==descendants:break
                    descendants=expanded
                sql=[r for r in log.records if r['span_id'] in descendants and r['phase']=='fts_execute_fetch_sort']
                record['ranking_sql_calls']=len(sql)
                record['ranking_replayed']=bool(sql)
            log.records.append(record)


def timed(phase):
    def decorate(function):
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def asynchronous(*args, **kwargs):
                with span(phase):
                    return await function(*args, **kwargs)
            return asynchronous
        @wraps(function)
        def synchronous(*args, **kwargs):
            with span(phase):
                return function(*args, **kwargs)
        return synchronous
    return decorate
