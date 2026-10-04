"""Actual loopback HTTP demo; refuses a real-model service before submitting."""
import argparse
import json
import time
from pathlib import Path
from uuid import uuid4
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from backend.config import ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    base=f'http://127.0.0.1:{args.port}'
    # Client reads the server-managed local token; neither logs nor archives headers.
    token=(ROOT/'data/runtime_local/access-token').read_text(encoding='ascii').strip()
    def call(path,body=None,authorized=True):
        headers={'Content-Type':'application/json'}
        if authorized:headers['Authorization']='Bearer '+token
        req=Request(base+path,None if body is None else json.dumps(body).encode(),headers,method='GET' if body is None else 'POST')
        try:
            with urlopen(req,timeout=10) as r:return r.status,json.loads(r.read())
        except HTTPError as r:return r.code,json.loads(r.read())
    status,health=call('/health',authorized=False)
    if status!=200 or health['profile']!='synthetic_fixture':raise RuntimeError('Demo requires explicitly synthetic_fixture server; no tasks submitted')
    rows=[]
    for mode in ('question_answer','assess_existing'):
        body={'mode':mode,'question':'synthetic_fixture: how does reactive power affect voltage?',
              'references':[{'label':'synthetic_fixture','text':'Reactive power affects voltage.'}]}
        if mode=='assess_existing':body['existing_answer']='Reactive power affects voltage.'
        status,created=call('/runs',body);assert status==202
        rid=created['run_id'];prefix='/runs/'+rid
        for _ in range(100):
            _,state=call(prefix)
            if state['status'] not in ('queued','running'):break
            time.sleep(.05)
        status,result=call(prefix+'/result');assert status==200 and state['status']=='finished'
        _,trace=call(prefix+'/trace');evidence=result['evidence'][0]
        status,queried=call(prefix+'/evidence/'+evidence['evidence_id']);assert status==200 and queried['text']==evidence['text']
        answer=result['answer']['final'];finding=result['findings']['model_fact'][0]
        feedback={'answer_id':answer['answer_id'],'answer_version':answer['version'],'finding_id':finding['finding_id'],
            'action':'pending','source':'ai_assisted_user_supervised','reviewer_id':'local-demo-user','note':'synthetic_fixture only; not a real model review'}
        status,review=call(prefix+'/reviews',feedback);assert status==201
        _,reviews=call(prefix+'/reviews');status,bad=call(prefix+'/reviews',dict(feedback,answer_version=999));assert status==409
        unauthorized,_=call(prefix,authorized=False);assert unauthorized==401
        rows.append({'mode':mode,'run_id':rid,'state':state,'result':result,'trace_events':len(trace['events']),
            'evidence_roundtrip':queried,'feedback':review,'review_count':len(reviews),'bad_version_http':status,'unauthorized_http':unauthorized})
    target=ROOT/'data/runtime_local'/('http-demo-'+uuid4().hex+'.json')
    with target.open('x',encoding='utf-8') as f:json.dump({'scope':'synthetic_fixture only; no paid calls; no real audit quality claim','runs':rows},f,ensure_ascii=False,indent=2)
    print(json.dumps({'profile':'synthetic_fixture','paid_calls':0,'runs':[{k:r[k] for k in ('mode','run_id','trace_events','bad_version_http','unauthorized_http')} for r in rows],
        'private_report':str(target)},ensure_ascii=True))

if __name__=='__main__':main()
