"""Two actual archived tasks on isolated UI, optionally with exact prior renderer."""
import argparse,json,sqlite3,tempfile,subprocess,types,sys
from pathlib import Path
from unittest.mock import patch
from tools.ui_fixture import fixture_app
from backend.config import ROOT
from evaluation.source_first_quality_v4 import LOCAL
from evaluation.natural_draft_audit_v1 import save

def app(folder,before=False):
    async def seed(service,factory):
        db=sqlite3.connect((ROOT/'data/runtime_local/runs.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        for rid in ('bb263029bd504e2d8990208728be6d55','67113eba5be64d3da38442bd482b52a6'):
            row=db.execute('SELECT request,config,result,status FROM runs WHERE id=?',(rid,)).fetchone()
            service.store.create(rid,json.loads(row['request']),json.loads(row['config']));service.store.mark(rid,row['status'],result=json.loads(row['result']))
        db.close();ordinary=service.result
        if before:
            annotation=types.ModuleType('backend.answer_annotations');presentation=types.ModuleType('prior_presentation')
            exec(subprocess.check_output(['git','show','7ac7f3b:backend/answer_annotations.py'],text=True,encoding='utf-8'),annotation.__dict__)
            exec(subprocess.check_output(['git','show','7ac7f3b:backend/presentation.py'],text=True,encoding='utf-8'),presentation.__dict__)
            def result(rid):
                value=ordinary(rid)
                with patch.dict(sys.modules,{'backend.answer_annotations':annotation}):value['presentation']=presentation.explain(value)
                return value
            service.result=result
        for rid in ('bb263029bd504e2d8990208728be6d55','67113eba5be64d3da38442bd482b52a6'):save(LOCAL/'ui'/('before' if before else 'after')/(rid+'.json'),service.result(rid))
        return {'actual_review_required':'bb263029bd504e2d8990208728be6d55','actual_pass':'67113eba5be64d3da38442bd482b52a6'}
    server=fixture_app(folder,seed_extra=seed)
    if before:
        from fastapi.responses import FileResponse
        assets=LOCAL/'ui/prior-static';assets.mkdir(parents=True,exist_ok=True)
        for name in ('index.html','app.js','inline_review.js','style.css','connection_memory.js','mark.svg','diagnostics.html','diagnostic_input.js'):
            (assets/name).write_bytes(subprocess.check_output(['git','show','7ac7f3b:backend/static/'+name]))
        @server.middleware('http')
        async def old_assets(request,call_next):
            path=request.url.path;name='index.html' if path=='/' else path.removeprefix('/ui/') if path.startswith('/ui/') else ''
            if name in ('index.html','app.js','inline_review.js','style.css','connection_memory.js','mark.svg','diagnostics.html','diagnostic_input.js'):return FileResponse(assets/name)
            return await call_next(request)
    return server

if __name__=='__main__':
    import uvicorn
    p=argparse.ArgumentParser();p.add_argument('--before',action='store_true');p.add_argument('--port',type=int,default=8766);a=p.parse_args()
    if a.port in (8765,8770):raise ValueError('Isolated preview only')
    with tempfile.TemporaryDirectory(prefix='source-first-v4-ui-') as folder:uvicorn.run(app(folder,a.before),host='127.0.0.1',port=a.port)
