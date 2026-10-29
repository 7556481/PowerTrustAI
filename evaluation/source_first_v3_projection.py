"""Reopen isolated replay Store via ordinary result projection; never starts work."""
import json,sqlite3
from dataclasses import replace
from backend.store import RunStore
from backend.service import ApplicationService
from backend.assembly import ComponentFactory
from evaluation.source_first_real_v3 import LOCAL,configuration
from evaluation.source_first_live_v2 import material
from evaluation.natural_draft_audit_v1 import save

def check(directory):
    c=replace(configuration(material()),run_db=directory/'projection.sqlite3',audit_strategy='source_first_audit_v1',
        fact_review_contract='literal_v1',local_revision_interface='source_actions_v2')
    if c.run_db.exists():raise RuntimeError('Do not overwrite projection archive')
    with sqlite3.connect((directory/'runs.sqlite3').as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(c.run_db) as dest:source.backup(dest)
    f=ComponentFactory(c);manifest=f.manifest(c.knowledge_version,fixed_evidence_only=True)
    manifest['model_id']='deepseek-flash'
    manifest['offline_provenance']='archived_response_replay' if 'replay' in directory.name else 'deterministic_models_real_index'
    store=RunStore(c.run_db);checks=[]
    try:
        ids=[r[0] for r in store.db.execute('SELECT id FROM runs').fetchall()]
        for rid in ids:
            inp=json.loads((directory/rid/'input.json').read_text(encoding='utf-8'))
            with store.tx():store.db.execute('UPDATE runs SET config=?,request=? WHERE id=?',(json.dumps(manifest),json.dumps(inp['request']),rid))
        service=ApplicationService(c,store,factory=f)
        for rid in ids:
            result=service.result(rid)
            checks.append(dict(run_id=rid,answer_version=result['answer']['final']['version'],
                complete=result['execution']['required_stages_complete'],audit_scope=result['presentation'].get('audit_scope'),
                inline_review=result['presentation'].get('inline_review')))
            save(directory/rid/'read-projection.json',result)
        save(directory/'projection-acceptance.json',dict(reopened=True,read_only_projection_copy=True,checks=checks))
        assert all(x['complete'] for x in checks)
    finally:store.close()
    print(directory.name,':',len(checks),'normal result projections verified')

if __name__=='__main__':
    check(LOCAL/'replay-after-verified');check(LOCAL/'real-paths-verified')
