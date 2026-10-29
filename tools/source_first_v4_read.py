"""Ordinary result projection of a small copied archive; no inference or env."""
import json,sqlite3,time,argparse
from dataclasses import replace
from backend.assembly import ComponentFactory
from backend.store import RunStore
from backend.service import ApplicationService
from evaluation.source_first_quality_v4 import LOCAL,material
from evaluation.source_first_real_v3 import configuration
from evaluation.natural_draft_audit_v1 import save

def check(label,*,archive_root=LOCAL,candidate_strategy='source_first_audit_v2',materials=None):
    p=archive_root/label;summary=json.loads((p/'summary.json').read_text(encoding='utf-8'));db=p/'projection.sqlite3'
    if db.exists():raise RuntimeError('Do not overwrite read acceptance')
    with sqlite3.connect((p/'runs.sqlite3').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(db) as dest:source.backup(dest)
    c=replace(configuration(materials or material()),run_db=db);store=RunStore(db);checks=[]
    try:
        for row in summary['control']:
            rid=row['accepted']['run_id'];cfg=replace(c,audit_strategy=candidate_strategy,fact_review_contract='literal_v1',local_revision_interface='source_actions_v2') if row['case_id'].endswith('candidate') else c
            factory=ComponentFactory(cfg);manifest=factory.manifest(cfg.knowledge_version,fixed_evidence_only=False);manifest['model_id']='deepseek-flash'
            inp=json.loads((p/rid/'input.json').read_text(encoding='utf-8'))
            with store.tx():store.db.execute('UPDATE runs SET config=?,request=? WHERE id=?',(json.dumps(manifest),json.dumps(inp['request']),rid))
            start=time.perf_counter();result=ApplicationService(cfg,store,factory=factory).result(rid)
            save(p/rid/'read-projection.json',result)
            assert result['answer']['final']==summary['outputs'][rid]['answer']
            raw=summary['outputs'][rid]
            expected=bool(raw.get('review_rounds')) and not raw.get('execution_issues')
            assert result['execution']['required_stages_complete']==expected
            checks.append(dict(slot=row['case_id'],complete=result['execution']['required_stages_complete'],expected_complete=expected,final_answer_equal=True,read_seconds=time.perf_counter()-start))
    finally:store.close()
    save(p/'read-acceptance.json',dict(passed=True,checks=checks,normal_service_projection=True,small_store_copy_only=True))
    print(label,len(checks),'ordinary reads accepted',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label',choices=['offline-final','offline-verified','live']);check(parser.parse_args().label)
