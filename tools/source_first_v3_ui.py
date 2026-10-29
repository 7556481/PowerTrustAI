"""Read-only UI preview of real-index offline projections; never an inference."""
import argparse,json,tempfile
from pathlib import Path
from copy import deepcopy
from tools.ui_fixture import fixture_app
from evaluation.source_first_real_v3 import LOCAL

async def seed_archive(service,factory):
    directory=LOCAL/'real-paths-final'
    s=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    archived=s['control'][-1]['accepted']['run_id']
    raw=json.loads((directory/archived/'read-projection.json').read_text(encoding='utf-8'))
    rid=service.store.db.execute("SELECT id FROM runs WHERE json_extract(request,'$.question') LIKE '%正常答案%' LIMIT 1").fetchone()[0]
    with service.store.tx():
        req=json.loads(service.store.db.execute('SELECT request FROM runs WHERE id=?',(rid,)).fetchone()[0])
        req['question']='synthetic_fixture · 真实大库离线回放S4（固定响应，非新推理）'
        service.store.db.execute('UPDATE runs SET request=? WHERE id=?',(json.dumps(req),rid))
    original=service.result
    def result(requested):
        if requested!=rid:return original(requested)
        value=deepcopy(raw);value['execution']['run_id']=rid;value['execution']['profile']='synthetic_fixture'
        value['configuration']['profile']='synthetic_fixture'
        return value
    service.result=result
    return {'archived_offline_S4':rid}

if __name__=='__main__':
    import uvicorn
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766);args=parser.parse_args()
    if args.port in (8765,8770):raise ValueError('Isolated UI fixture only')
    with tempfile.TemporaryDirectory(prefix='source-first-v3-ui-') as folder:
        uvicorn.run(fixture_app(folder,seed_extra=seed_archive),host='127.0.0.1',port=args.port)
