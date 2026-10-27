"""Isolated bounded page measurements on ui_fixture; never production resources."""
import argparse
from contextlib import asynccontextmanager
import copy
import hashlib
import http.cookiejar
import json
from pathlib import Path
import re
import statistics
import time
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request

from fastapi.responses import Response
from tools.ui_fixture import fixture_app
from backend.serialization import dumps, safe

SAMPLES = ('page-normal-v3', 'page-large-v3')


def populate(service, base):
    store = service.store
    counts = []
    original = store.get(base)
    evidence = store.objects(base, 'evidence')[0]
    events = store.events(base)
    for rid, scale in zip(SAMPLES, (1, 8)):
        try: store.get(rid)
        except KeyError:
            raw = copy.deepcopy(original['result'])
            def extend(value):
                if isinstance(value, list):
                    for v in value: extend(v)
                elif isinstance(value, dict):
                    if 'answer_id' in value and 'text' in value and 'version' in value:
                        value['text'] += '\n' + ('合成页面测量：保留适用范围、来源与工程输入，不能视作真实模型判断。\n' * (12*scale))
                    if value.get('findings') and 'finding_id' in value['findings'][0]:
                        originals = value['findings']
                        value['findings'] = [dict(copy.deepcopy(originals[i % len(originals)]),
                            finding_id=originals[i % len(originals)]['finding_id']+'-page-'+str(i),
                            reason=originals[i % len(originals)].get('reason','')+' 合成受限规模发现说明。'*16)
                            for i in range(4*scale)]
                    for v in list(value.values()): extend(v)
            extend(raw)
            raw['fixture_evidence'] = [dict(evidence, evidence_id='page-evidence-'+str(i),
                locator='synthetic paragraph '+str(i), text=evidence['text']+'\n'+'合成证据正文，不能外推工程事实。'* (32*scale)) for i in range(3*scale)]
            request=copy.deepcopy(original['request']);extend(request)
            store.create(rid, dict(request, question='synthetic_fixture · '+rid), original['config'])
            store.mark(rid, 'finished', result=raw)
            with store.tx():
                store.db.execute('UPDATE runs SET snapshot=?,created=?,ended=? WHERE id=?',
                                 (dumps(raw),'2026-10-27T00:00:00+00:00','2026-10-27T00:00:01+00:00',rid))
                for i in range(12*scale):
                    source = events[i % len(events)]
                    event = dict(source['event'], event_id=rid+'-event-'+str(i),
                                 fixture_context='合成轨迹上下文。'*(24*scale))
                    store.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                                     (rid,event['event_id'],i+1,dumps(event),dumps(source['stage_output'])))
            answer = store.objects(rid,'answer')[0]
            for i in range(3 if scale==1 else 8):
                store.add_review(rid,dict(answer_id=answer['answer_id'], answer_version=answer['version'],
                    action='note', source='ai_assisted_user_supervised', reviewer_id='synthetic-page-measure',
                    note='合成反馈，不是专家金标准。'*32))
        row=store.get(rid)
        counts.append(dict(run_id=rid,events=len(store.events(rid)),answers=len(store.objects(rid,'answer')),
            findings=len(store.objects(rid,'finding')),evidence=len(store.objects(rid,'evidence')),
            reviews=len(store.reviews(rid)),max_answer_chars=max(len(a['text']) for a in store.objects(rid,'answer')),
            result_utf8_bytes=len(dumps(row['result']).encode()),snapshot_utf8_bytes=len(dumps(row['snapshot']).encode())))
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    size=sum(p.stat().st_size for p in store.path.parent.glob('runs.sqlite3*'))
    if size>20*1024*1024:raise RuntimeError('Synthetic database exceeds 20MiB bound')
    return dict(samples=counts,database_bytes=size,model_requests=0)


def timed(call):
    call();times=[]
    for _ in range(5):
        start=time.perf_counter();value=call();times.append((time.perf_counter()-start)*1000)
    return value,dict(times_ms=times,median_ms=statistics.median(times))


def performance_app(directory, source):
    app=fixture_app(directory)
    parent=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(app):
        async with parent(app):
            app.state.page_samples=populate(app.state.service,app.state.fixture_cases['一次修订与版本1/2'])
            print(json.dumps(app.state.page_samples,ensure_ascii=False),flush=True)
            yield
    app.router.lifespan_context=lifespan
    @app.get('/fixture/service-measure')
    async def measure_service():
        service=app.state.service;records=[]
        for rid in SAMPLES:
            for name,call in [('state',lambda:service.state(rid)),('result',lambda:service.result(rid)),
                              ('trace',lambda:safe({'run_id':rid,'events':service.store.events(rid)})),
                              ('reviews',lambda:safe(service.store.reviews(rid)))]:
                value,record=timed(call)
                queries=[];decodes=[];original=json.loads
                def loads(v,*a,**kw):
                    decodes.append(len(v));return original(v,*a,**kw)
                service.store.db.set_trace_callback(queries.append);json.loads=loads
                try:call()
                finally:json.loads=original;service.store.db.set_trace_callback(None)
                payload=dumps(value).encode()
                records.append(dict(record,run_id=rid,endpoint=name,sql_count=len(queries),json_decodes=len(decodes),
                    output_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
        return dict(app.state.page_samples,service=records,warmups=1,repetitions=5)
    @app.get('/ui/app.js')
    async def instrumented_script():
        text=Path(source).read_text(encoding='utf8')
        hooks=Path('tools/ui_page_probe.js').read_text(encoding='utf8')
        for name in ('renderAnswers','renderFindings','renderEvidence','renderTrace','renderReviews','renderLocalNLI','reviewOptions','renderFactDelivery'):
            text=text.replace('function '+name+'(', 'function fixtureOriginal_'+name+'(')
            hooks+='\nfunction '+name+'(...args){const start=performance.now();try{return fixtureOriginal_'+name+'(...args);}finally{if(fixtureMetrics.current)fixtureMetrics.current.sync_ms["'+name+'"]=(fixtureMetrics.current.sync_ms["'+name+'"]||0)+performance.now()-start;}}'
        text=text.replace("const $ = id => document.getElementById(id);", "const $ = id => document.getElementById(id);\n"+hooks)
        # Hooks are confined to this tool's app; the production static route is untouched.
        return Response(text,media_type='application/javascript')
    route=app.router.routes.pop();app.router.routes.insert(0,route)
    return app


def http_measure(port, output):
    root=f'http://127.0.0.1:{port}'
    opener=build_opener(ProxyHandler({}),HTTPCookieProcessor(http.cookiejar.CookieJar()))
    html=opener.open(root+'/fixture/connect').read().decode()
    ticket=re.search(r'name="ticket" value="([^"]+)"',html).group(1)
    opener.open(Request(root+'/session/bootstrap',data=('ticket='+ticket).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})).close()
    result=json.loads(opener.open(root+'/fixture/service-measure').read())
    result['http']=[]
    for rid in SAMPLES:
        for endpoint in ('result','trace','reviews'):
            def call():
                with opener.open(root+'/runs/'+rid+'/'+endpoint) as response:return response.read()
            payload,record=timed(call)
            result['http'].append(dict(record,run_id=rid,endpoint=endpoint,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
    result['http_boundary']='urllib open through complete body read on actual loopback HTTP; includes server serialization, transport and client read; not independently separated'
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Measured fixed samples; database bytes',result['database_bytes'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['serve','measure'])
    parser.add_argument('--directory',default='data/maintenance_local/slow-auxiliary-v3/fixture-valid')
    parser.add_argument('--source',default='backend/static/app.js')
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--output',default='data/maintenance_local/slow-auxiliary-v3/http.json')
    args=parser.parse_args()
    if args.port!=8766:parser.error('This isolated task entry uses only 8766')
    if args.action=='measure':http_measure(args.port,args.output);return
    import uvicorn
    uvicorn.run(performance_app(args.directory,args.source),host='127.0.0.1',port=args.port,access_log=False,log_level='warning')


if __name__=='__main__':main()
