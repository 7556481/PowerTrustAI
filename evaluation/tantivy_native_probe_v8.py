"""Real native I/O failure selfcheck, confined to one disposable diagnostic index."""
import json
import sys
import time
from pathlib import Path

from evaluation.tantivy_full_identity_v1 import DiagnosticWriter
from evaluation.tantivy_native_trace_v8 import phase, wait_ready
from rag.tantivy_build import atomic, create_index


def worker(plan_path):
    import tantivy
    plan = json.loads(Path(plan_path).read_text())
    wait_ready(plan)
    root = Path(plan['probe_root'])
    phase('create_writer')
    index = create_index(root / 'tantivy')
    writer = DiagnosticWriter(index.writer(heap_size=128000000, num_threads=1), root, phase=phase)
    primary = None
    result = {'synthetic': True, 'started': time.time()}
    try:
        phase('feed')
        for n in range(12000):
            writer.add_document(tantivy.Document(rowid=n, terms='controlled native failure test'))
        writer.commit()
        result['completed'] = True
    except BaseException as error:
        primary = error
        result['primary'] = repr(error)
    finally:
        try:
            writer.wait_merging_threads()
        except BaseException as error:
            result['cleanup'] = repr(error)
        result['ended'] = time.time()
        atomic(root / 'result.json', result)
    if primary:
        raise primary


if __name__ == '__main__':
    worker(sys.argv[1])
