"""Read-only history audit and low-cost query planning; never fabricate requests.

This run did not record max_results/context_options. No historical replay may
be performed from it. EXPLAIN below uses declared diagnostic LIMIT 0 and cannot
measure SQLite runtime, cardinality, or pretend to restore the missing limit.
"""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from rag.chinese_terms import query_expression


def request_gaps(record):
    # Output hit count is never used as a substitute for requested max_results.
    required = ('query','scenario_id','purpose','knowledge_version','max_results','context_options')
    return [k for k in required if k not in record]


def union_seconds(intervals):
    total = 0.0
    start = end = None
    for a, b in sorted(intervals):
        if start is None:
            start, end = a, b
        elif a > end:
            total += end - start
            start, end = a, b
        else:
            end = max(end, b)
    return total + (0 if start is None else end - start)


def diagnose(database, index, run_id):
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        row = db.execute('SELECT request,config,result FROM runs WHERE id=?',(run_id,)).fetchone()
        request, config, result = map(json.loads, row)
        events = [json.loads(r[0]) for r in db.execute('SELECT payload FROM events WHERE run_id=? ORDER BY ordinal',(run_id,))]
    records = result['retrieval_records']
    roots = ('retrieval_generation','retrieval_verification','retrieval_domain_review')
    root_intervals = [(datetime.fromisoformat(e['timestamp_utc']).timestamp()-e['duration_ms']/1000,
                       datetime.fromisoformat(e['timestamp_utc']).timestamp()) for e in events if e['component'] in roots]
    cumulative = sum(r['duration_ms']/1000 for r in records)
    sum_events = sum(e['duration_ms']/1000 for e in events if e['component'].startswith('retrieval_'))
    data = {'version':'retrieval-diagnosis-v1','run_id':run_id,'requests':[],
            'historical_record_seconds_sum':cumulative,'all_retrieval_event_seconds_sum_do_not_use':sum_events,
            'root_wrapper_wall_union_seconds_approx':union_seconds(root_intervals),
            'record_sum_over_harness_counter_ratio':cumulative/(result['duration_ms']/1000),
            'ratio_is_not_measured_critical_path_share':True,
            'historical_replay_count':0,'query_plan_runtime_estimate':None,'match_cardinality':None,
            'gap_note':'scenario_id saved in original TaskRequest; max_results/context_options not saved in trace or examined diagnostics'}
    with closing(sqlite3.connect(Path(index).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        seal = json.loads(db.execute('SELECT manifest FROM corpus_seal WHERE knowledge_version=?',(config['knowledge_version'],)).fetchone()[0])
        assert seal['query_version']==config['corpus_index']['query_version']
        for i, r in enumerate(records, 1):
            expression = query_expression(r['query'], seal['query_version'])
            plan = [x[3] for x in db.execute('EXPLAIN QUERY PLAN SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?', (expression, 0))]
            gaps = request_gaps(r)
            if 'scenario_id' in request and 'scenario_id' in gaps:
                gaps.remove('scenario_id') # actual TaskRequest, not a guess
            data['requests'].append({'id':'R'+str(i),'retrieval_id':r['retrieval_id'],
                'query_sha256':hashlib.sha256(r['query'].encode()).hexdigest(),'purpose':r['purpose'],
                'historical_seconds':r['duration_ms']/1000,'returned_hits':len(r['hits']),
                'missing_request_fields':gaps,'plan_only_with_diagnostic_limit_zero':plan,
                'first_replay_seconds':None,'repeat_seconds':[], 'result_comparison':'not_measured',
                'segments':dict.fromkeys(('query_prepare','fts_execute_fetch_sort','body_evidence_construct','result_validation'))})
        data['chunk_indexes']=[r[1] for r in db.execute("PRAGMA index_list('corpus_chunks')")]
        data['native_columns']=[{'name':r[1],'primary_key':bool(r[5])} for r in db.execute("PRAGMA table_info('corpus_native')")]
    assert all(x['missing_request_fields'] for x in data['requests'])
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=Path('data/runtime_local/runs.sqlite3'))
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    value=diagnose(args.database,args.index,args.run_id)
    args.output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'historical_replay_count':value['historical_replay_count'],
                      'root_wrapper_wall_union_seconds_approx':value['root_wrapper_wall_union_seconds_approx'],
                      'queries':[(v['id'],v['missing_request_fields'],v['plan_only_with_diagnostic_limit_zero']) for v in value['requests']]}))


if __name__=='__main__':main()
