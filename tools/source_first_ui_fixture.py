"""Synthetic scope-label preview only; no candidate model/index/production access."""
import argparse,json,tempfile
from dataclasses import asdict
from core.models import ExecutionStatus
from harness.contracts import RetrievalRecord
from tools.ui_fixture import fixture_app

async def scope_record(service,factory):
    # Existing synthetic seeding is deliberately reused; locate by SQL identity,
    # never touch the production Store or user history.
    rid=service.store.db.execute("SELECT id FROM runs WHERE json_extract(request,'$.question') LIKE '%正常答案%' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    raw=service.store.get(rid)['result']
    raw['retrieval_records']=[asdict(RetrievalRecord('synthetic-scope','verification','',
        'source_first_audit_v1',raw['answer']['version'],'synthetic-k',ExecutionStatus.SUCCEEDED,
        'source_scope',reason=json.dumps(dict(external_cross_check='not_executed',source_truth_verified=False))))]
    service.store.mark(rid,'finished',result=raw)
    return {'source_first_scope_synthetic_fixture':rid}

def main():
    import uvicorn
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);a=p.parse_args()
    if a.port in (8765,8770):raise ValueError('Use isolated fixture port')
    with tempfile.TemporaryDirectory(prefix='source-first-ui-') as root:
        uvicorn.run(fixture_app(root,seed_extra=scope_record),host='127.0.0.1',port=a.port)

if __name__=='__main__':main()
