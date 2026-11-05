"""Public tiny Windows -> Linux append -> Windows product-reader experiment.

No production constants, models, environment credentials, or formal build ledger.
Each phase is one process. Artifacts contain only the synthetic source and index.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import sqlite3
import sys
import time

from rag.tantivy_build import atomic, stored_ids, accept_complete
from rag.tantivy_manifest import sha, package_manifest, tokenizer_identity, query_identity

QUERIES = [('电压与无功资源', -1), ('并联电容', 1), ('继电保护', 2),
           ('变压器油温', 3), ('频率偏差', 4)]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def environment():
    import tantivy.tantivy as binding
    assert importlib.metadata.version('tantivy') == '0.27.0'
    return {'system': platform.platform(), 'machine': platform.machine(),
            'python': sys.version, 'binding_version': importlib.metadata.version('tantivy'),
            'binding_file': Path(binding.__file__).name, 'binding_sha256': sha(binding.__file__),
            'tokenizer': tokenizer_identity(), 'query_implementation': query_identity()}


def inventory(root):
    return {f.relative_to(root).as_posix(): {'bytes': f.stat().st_size, 'sha256': sha(f)}
            for f in sorted(root.rglob('*')) if f.is_file()
            and not f.name.endswith('.lock') and f.name != 'transport.json'}


def verify_transport(root):
    assert read(root / 'transport.json') == inventory(root), 'Transport file identity mismatch'


def export(root):
    atomic(root / 'transport.json', inventory(root))


def audit(root, count):
    import tantivy
    from rag.storage import KnowledgeStore
    rows = read(root / 'input.json')
    identity = read(root / 'identity.json')
    with KnowledgeStore(root / 'source.sqlite3', readonly=True) as source:
        for row in rows:
            e = source.evidence(row[2], identity['snapshot'])
            source.verify_evidence(e)
            assert hashlib.sha256(e.text.encode()).hexdigest() == row[3]
            assert hashlib.sha256(row[5].encode()).hexdigest() == row[4]
    with sqlite3.connect((root / 'build/mapping.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as con:
        mapped = [list(x) for x in con.execute('select * from rows order by position')]
    assert mapped == [row[:5] for row in rows[:count]], 'Mapping/ID/body/terms mismatch'
    index = tantivy.Index.open(str(root / 'build/tantivy'))
    ids = list(stored_ids(index, root / 'build/tantivy'))
    assert len(ids) == len(set(ids)) == count
    assert sorted(ids) == sorted(row[1] for row in rows[:count])
    cp = read(root / 'build/checkpoint.json')
    h = hashlib.sha256()
    for row in mapped:
        h.update(json.dumps(tuple(row)).encode())
    assert cp['count'] == count and cp['mapping_hash'] == h.hexdigest()
    meta = read(root / 'build/tantivy/meta.json')
    assert cp['opstamp'] == meta['opstamp']
    return {'all_ids': sorted(ids), 'mapping_hash': h.hexdigest(),
            'all_source_bodies_and_input_terms_verified': True, 'checkpoint': cp,
            'native_schema': meta['schema'], 'segments': len(meta['segments'])}


def seed(root):
    assert platform.system() == 'Windows', 'Seed must originate on Windows'
    root.mkdir(parents=True, exist_ok=False)
    from tests.test_corpus_index import CorpusTests
    from rag.storage import KnowledgeStore
    from rag.corpus_index import add_record
    from rag.tantivy_members import members
    from evaluation.tantivy_full_identity_v1 import FullCheckpoint
    fixture = CorpusTests()
    fixture.setUp()
    try:
        with KnowledgeStore(fixture.p) as st:
            add_record(st.connection, text='synthetic_fixture：变压器油温需要结合负载与环境温度判断，不能仅凭油温确定故障。', record_id=3, row_number=2, **fixture.args)
            add_record(st.connection, text='synthetic_fixture：频率偏差反映有功供需不平衡，现场判断还需要频率和时间记录。', record_id=4, row_number=3, **fixture.args)
            st.connection.commit()
        with sqlite3.connect(fixture.p) as src, sqlite3.connect(root / 'source.sqlite3') as dst:
            src.backup(dst)
        with KnowledgeStore(root / 'source.sqlite3', readonly=True) as source:
            rows = list(members(source, fixture.k))
        assert len(rows) == 5 and [r[1] for r in rows] == [-1, 1, 2, 3, 4]
        identity = {'expected': len(rows), 'snapshot': fixture.k, 'scope': 'public-synthetic-crossenv-v15'}
        atomic(root / 'identity.json', identity)
        atomic(root / 'input.json', rows)
        started = time.monotonic()
        b = FullCheckpoint(root / 'build', identity, total_seconds=7200, segment_seconds=120)
        try:
            b.append(rows[:3])
        finally:
            cleanup = b.close()
        assert cleanup == []
        atomic(root / 'windows-seed.json', {'environment': environment(), 'audit': audit(root, 3),
               'append_and_normal_close_seconds': time.monotonic() - started,
               'source_sha256': sha(root / 'source.sqlite3'), 'queries': QUERIES, 'models': 0})
        export(root)
    finally:
        fixture.tearDown()


def resume(root):
    assert platform.system() == 'Linux', 'Continuation must run on Linux'
    verify_transport(root)
    before = audit(root, 3)
    seed_record = read(root / 'windows-seed.json')
    env = environment()
    assert env['tokenizer'] == seed_record['environment']['tokenizer']
    assert env['query_implementation'] == seed_record['environment']['query_implementation']
    from evaluation.tantivy_full_identity_v1 import FullCheckpoint
    started = time.monotonic()
    b = FullCheckpoint(root / 'build', read(root / 'identity.json'), total_seconds=7200, segment_seconds=120)
    try:
        # Project's existing prepared-journal/native-commit/mapping/checkpoint protocol.
        b.append(read(root / 'input.json')[3:])
    finally:
        cleanup = b.close()
    assert cleanup == []
    elapsed = time.monotonic() - started
    assert sha(root / 'source.sqlite3') == seed_record['source_sha256']
    after = audit(root, 5)
    assert after['native_schema'] == before['native_schema']
    atomic(root / 'linux-resume.json', {'environment': env, 'before': before, 'after': after,
           'added': 2, 'append_and_normal_close_seconds': elapsed,
           'tiny_sample_rows_per_second': 2 / elapsed, 'models': 0})
    export(root)


def product_read(root, label):
    assert platform.system() == 'Windows', 'Returned product read must run on Windows'
    verify_transport(root)
    before = inventory(root)
    identity = read(root / 'identity.json')
    full = audit(root, 5)
    proof = accept_complete(root / 'build', identity)
    assert proof['n'] == 5
    manifest = root / 'manifest.json'
    # Absolute reader paths are created at the destination, not copied as usable paths.
    package_manifest(root / 'build/tantivy', root / 'build/acceptance.json', manifest,
                     knowledge_version=identity['snapshot'], source_total=5, scope='isolated',
                     build=identity, source_identity={'kind': 'public-synthetic-crossenv-v15'})
    from backend.config import ServiceConfig
    from backend.assembly import ComponentFactory
    from rag.contracts import RetrievalRequest, RetrievalPurpose, ContextOptions
    cfg = ServiceConfig(index_db=root / 'source.sqlite3', knowledge_version=identity['snapshot'],
                        run_db=root / 'unused-runs.sqlite3', tantivy_manifest=manifest,
                        tantivy_isolated=True, tantivy_worker_mode='fast_v1')
    factory = ComponentFactory(cfg)
    results = []

    async def run():
        factory.initialize_retrieval()
        adapter = factory.semantic_resource
        pid = adapter._native.pid
        try:
            for query, rid in QUERIES:
                req = RetrievalRequest(query, 'public-synthetic-crossenv-v15', RetrievalPurpose.GENERATION,
                                       identity['snapshot'], 6, ContextOptions())
                started = time.monotonic()
                result = await adapter.retrieve(req)
                await adapter.validate_result(req, result)
                expected = next(r[2] for r in read(root / 'input.json') if r[1] == rid)
                assert expected in [e.provenance.fragment_id for e in result.evidence], (query, rid)
                assert adapter._native.pid == pid, 'Unexpected worker replacement'
                results.append({'query': query, 'expected_rowid': rid,
                                'fragment_ids': [e.provenance.fragment_id for e in result.evidence],
                                'body_hashes': [hashlib.sha256(e.text.encode()).hexdigest() for e in result.evidence],
                                'context_count': len(result.context.items) if result.context else 0,
                                'seconds': time.monotonic() - started, 'trace': adapter.last_trace})
        finally:
            await factory.close()
        assert factory.semantic_resource is None

    asyncio.run(run())
    assert sha(root / 'source.sqlite3') == read(root / 'windows-seed.json')['source_sha256']
    assert {n: v for n, v in before.items() if n.startswith('build/tantivy/')} == {
        n: v for n, v in inventory(root).items() if n.startswith('build/tantivy/')}, 'Reader changed native files'
    atomic(root / (label + '.json'), {'passed': True, 'environment': environment(), 'audit': full,
           'queries': results, 'factory': 'ComponentFactory.initialize_retrieval/fast_v1',
           'worker_reused': True, 'resource_released': True, 'models': 0})
    export(root)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['seed-windows', 'resume-linux', 'read-windows'])
    p.add_argument('root', type=Path)
    p.add_argument('--label', default='windows-product-read')
    a = p.parse_args()
    root = a.root.resolve()
    if 'crossenv' not in root.name.casefold():
        raise ValueError('Explicit crossenv tiny directory required')
    if a.stage == 'seed-windows':
        seed(root)
    elif a.stage == 'resume-linux':
        resume(root)
    else:
        product_read(root, a.label)
    print(json.dumps({'stage': a.stage, 'passed': True, 'root': str(root), 'models': 0}))


if __name__ == '__main__':
    main()
