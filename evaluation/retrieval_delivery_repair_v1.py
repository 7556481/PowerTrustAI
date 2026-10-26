"""Bounded source/FTS diagnostics. No environment loading or model clients."""
import hashlib
import json
from pathlib import Path
from time import monotonic

from rag.storage import KnowledgeStore
from rag.corpus_index import seal
from rag.topic_lanes import plan
from rag.chinese_terms import query_expression, TOPIC_VERSION
from evaluation.natural_answer_benefit_v3_materials import N

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'data/retrieval_local/retrieval-delivery-repair-v1'
PUBLIC = ROOT / 'docs/evaluation/retrieval-delivery-repair-v1'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def run():
    old = ROOT / 'data/retrieval_local/natural-answer-benefit-v3'
    freeze = json.loads((old/'freeze.json').read_text(encoding='utf-8'))
    materials = json.loads((old/'materials.json').read_text(encoding='utf-8'))
    summary = json.loads((old/'batch/summary.json').read_text(encoding='utf-8'))
    cfg = freeze['configuration']
    ledger_path = LOCAL/'query-ledger.json'
    queries = json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else []
    def query(con, purpose, sql, args=()):
        for previous in queries:
            if previous['sql']==sql and previous['parameters']==list(args) and 'rows' in previous:
                return previous['rows']
        # Persist intent before every explicit diagnostic query. Internal seal/body
        # validation reads are separately identified, not counted as search runs.
        if len(queries) >= 31:
            raise RuntimeError('32 total queries including initial membership check')
        row = dict(number=len(queries)+2, purpose=purpose, sql=sql, parameters=args)
        queries.append(row); save(LOCAL/'query-ledger.json', queries)
        begin = monotonic(); deadline = begin+120
        con.set_progress_handler(lambda: int(monotonic()>deadline), 10000)
        try:
            result = [dict(r) for r in con.execute(sql, args)]
            row.update(seconds=monotonic()-begin, rows=result)
            return result
        finally:
            con.set_progress_handler(None, 0)
            save(LOCAL/'query-ledger.json', queries)
    with KnowledgeStore(cfg['index_db'], readonly=True) as store:
        start = monotonic(); identity = seal(store, cfg['knowledge_version'])
        startup = monotonic()-start
        save(LOCAL/'seal-verification.json',dict(seconds=startup,knowledge_version=cfg['knowledge_version'],
            file_bytes=Path(cfg['index_db']).stat().st_size,identity=identity))
        con = store.connection
        members = query(con, 'Small base document catalog with immutable versions',
            'SELECT s.document_id,s.version,v.metadata FROM snapshot_documents s JOIN versions v USING(document_id,version) WHERE s.knowledge_version=?',
            (identity['base_knowledge_version'],))
        save(LOCAL/'catalog.json', members)
        sources = materials['reference_sources']
        source = next(iter(sources.values()))
        rows = query(con, 'Exact target fragment membership in native FTS; no industry body scan',
            'SELECT f.fragment_id,f.raw_text,n.id FROM fragments f JOIN corpus_native n USING(fragment_id) WHERE f.document_id=? AND f.version=?',
            (source['source_id'], source['source_version']))
        save(LOCAL/'target-native.json', rows)
        cases=[]
        for item in N:
            expr = plan(item['question'])[0][1]
            positive = query_expression(item['question'], TOPIC_VERSION)
            # Restrict rowids first: this asks whether target chunks satisfy the
            # exact MATCH, not a costly global ranking or a new retrieval variant.
            sql = '''SELECT n.fragment_id,
              EXISTS(SELECT 1 FROM corpus_fts WHERE rowid=-n.id AND corpus_fts MATCH ?) AS actual_match,
              EXISTS(SELECT 1 FROM corpus_fts WHERE rowid=-n.id AND corpus_fts MATCH ?) AS positive_match
              FROM corpus_native n JOIN fragments f USING(fragment_id)
              WHERE f.document_id=? AND f.version=?'''
            matches=query(con, item['id']+' exact target MATCH membership; isolate subject constraint from positive lexical terms',
                sql,(expr,positive,source['source_id'],source['source_version']))
            output = next(summary['outputs'][r['accepted']['run_id']] for r in summary['control']
                if r['accepted']['spec']['id']==item['id'] and r['accepted']['spec']['line']=='G')
            rec=output['retrieval_records'][0]
            ref=sources[item['family']]
            fid=ref['provenance']['fragment_id']
            match=next((r for r in matches if r['fragment_id']==fid),None)
            cases.append(dict(id=item['id'],family=item['family'],question=item['question'],
                expression=expr,positive_expression=positive,target_document_matching_chunks=sum(r['actual_match'] for r in matches),
                target_document_positive_matching_chunks=sum(r['positive_match'] for r in matches),
                reference_fragment_id=fid,reference_fragment_match=match,
                reference_sha256=hashlib.sha256(ref['text'].encode()).hexdigest(),
                historical_record=rec,delivered_sources=[dict(source_id=e['source_id'],source_version=e['source_version'],
                    locator=e['locator'],chars=len(e['text'])) for e in output['evidence']],
                generation_snapshot=output['generation_output']['evidence_snapshot']))
        result=dict(version='retrieval-delivery-repair-v1-diagnosis',startup_seal_seconds=startup,
            knowledge_version=cfg['knowledge_version'],database_sha256=json.loads(Path(cfg['index_db']+'.manifest.json').read_text())['database_sha256'],
            base_knowledge_version=identity['base_knowledge_version'],target_native_fragments=len(rows),
            diagnostic_queries=1+len(queries),cases=cases)
        save(LOCAL/'diagnosis.json',result)
        public={k:v for k,v in result.items() if k!='cases'}
        public['cases']=[{k:v for k,v in row.items() if k!='generation_snapshot'} for row in cases]
        save(PUBLIC/'diagnosis.json',public)
        print(json.dumps(dict(startup=startup,queries=result['diagnostic_queries'],cases=[{k:r[k] for k in ('id','target_document_matching_chunks','target_document_positive_matching_chunks','reference_fragment_match')} for r in cases])))


if __name__ == '__main__':
    run()
