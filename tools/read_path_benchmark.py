"""Bounded synthetic read benchmark; no environment, adapters or production data."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time
from types import SimpleNamespace

from backend.service import ApplicationService
from backend.store import RunStore
from backend.serialization import dumps


def measure(output):
    records = []
    with tempfile.TemporaryDirectory(prefix='powertrust-read-bench-') as directory:
        store = RunStore(Path(directory)/'runs.sqlite3')
        service = ApplicationService(SimpleNamespace(queue_capacity=2), store, factory=object())
        for name, size in [('normal', 2048), ('large', 524288)]:
            rid = name
            answer = dict(answer_id=name+'-answer', version=1, text='答'*(size//3), citations=[])
            evidence = dict(evidence_id=name+'-evidence', source_id='synthetic', source_version='1', text='据'*(size//3))
            raw = dict(answer=answer, evidence=[evidence], review_rounds=[])
            store.create(rid, dict(mode='question_answer', question='synthetic '+name),
                         dict(profile='synthetic_fixture', knowledge_version='synthetic-v1'))
            store.mark(rid, 'finished', result=raw)
            store.db.execute('UPDATE runs SET snapshot=?,created=?,ended=? WHERE id=?',
                             (dumps(raw), '2026-10-27T00:00:00+00:00', '2026-10-27T00:00:01+00:00', rid))
            store.db.commit()
            for label, call in [('state', lambda: service.state(rid)), ('result', lambda: service.result(rid)),
                                ('trace', lambda: store.events(rid)), ('reviews', lambda: store.reviews(rid))]:
                call()  # one warm-up, five fixed measurements; instrumentation separate
                times = []
                for _ in range(5):
                    start = time.perf_counter(); value = call(); times.append((time.perf_counter()-start)*1000)
                queries = []; decodes = []
                original = json.loads
                def loads(value, *args, **kwargs):
                    decodes.append(len(value.encode('utf8')) if isinstance(value, str) else len(value))
                    return original(value, *args, **kwargs)
                store.db.set_trace_callback(queries.append)
                json.loads = loads
                try: call()
                finally:
                    json.loads = original
                    store.db.set_trace_callback(None)
                encoded = dumps(value).encode('utf8')
                records.append(dict(sample=name, endpoint=label, sql_count=len(queries),
                                    json_decodes=len(decodes), large_decodes=sum(n>500000 for n in decodes),
                                    decoded_bytes=sum(decodes), median_ms=statistics.median(times), times_ms=times,
                                    output_bytes=len(encoded), output_sha256=hashlib.sha256(encoded).hexdigest()))
        store.close()
        database_bytes = sum(p.stat().st_size for p in Path(directory).iterdir())
    result = dict(model_requests=0, warmups=1, repetitions=5, database_bytes=database_bytes,
                  large_structure='answer 524286 UTF8 bytes + evidence 524286 bytes, both result and snapshot; plus indexed objects',
                  records=records)
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    measure(parser.parse_args().output)
