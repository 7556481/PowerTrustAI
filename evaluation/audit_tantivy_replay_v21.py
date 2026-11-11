"""Immutable v20 records, new identity-sharing delivery only; no model calls."""
import json,hashlib,statistics
from pathlib import Path
from evaluation.audit_tantivy_v21 import pack,expand
HOME=Path('D:/PowerTrustAI/data/runtime_local/audit-tantivy-v21')
OLD=HOME.parent/'tantivy-delivery-replay-v20'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def chars(p):
    if isinstance(p,dict):return (len(p['text']) if isinstance(p.get('evidence_id'),str) and isinstance(p.get('text'),str) else 0)+sum(chars(v) for k,v in p.items() if k!='text')
    if isinstance(p,list):return sum(chars(v) for v in p)
    return 0

def run():
    HOME.mkdir(exist_ok=False);freeze=read(OLD/'freeze.json');rows=[json.loads(l) for l in (OLD/'measurements.jsonl').read_text(encoding='utf8').splitlines()];out=[]
    for request in freeze['requests']:
        if request['purpose']=='generation':continue
        routes={r['route']:r for r in rows if r['slot']==request['slot']};delivery={}
        for name in ('sqlite','v18'):
            r=routes[name];assert r['status']=='ok';result=r['result'];evidence=result['evidence']+[i['evidence'] for i in (result.get('context') or {}).get('items',[])]
            payload={'QUOTE_CANDIDATES':[dict(evidence_id=e['evidence_id'],text=e['text'],start_offset=0,end_offset=len(e['text'])) for e in evidence]}
            # Independent requests additionally carry the same preserved generation body snapshot.
            prior=read(HOME.parent/'tantivy-product-v19'/(request['case']+'-baseline-result.json'))
            if request['purpose']=='verification':
                snap=prior['snapshots'];payload['GENERATION_INPUT_SNAPSHOT']=snap
            packed=pack(payload) if name=='v18' else payload;assert expand(packed)==payload
            delivery[name]={'reading_seconds':r['total_seconds'],'body_chars':chars(packed),'unshared_chars':chars(payload),'evidence_ids':[e['evidence_id'] for e in evidence]}
        out.append(dict(slot=request['slot'],case=request['case'],origin=request['origin'],purpose=request['purpose'],query_sha256=request['query_sha256'],question=prior['task_context']['question'],routes=delivery,saving_seconds=delivery['sqlite']['reading_seconds']-delivery['v18']['reading_seconds'],extra_chars=delivery['v18']['body_chars']-delivery['sqlite']['body_chars']))
    assert len(out)==36
    summary={'rows':out,'model_calls':0,'reading_saving_seconds':sum(r['saving_seconds'] for r in out),'sqlite_body_chars':sum(r['routes']['sqlite']['body_chars'] for r in out),'candidate_body_chars':sum(r['routes']['v18']['body_chars'] for r in out),'measurement_scope':'per frozen retrieval body carriers plus preserved SQLite snapshot, not full model request; original citation scopes/corrections not replayed; full-request gate remains unproven','inputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (OLD/'freeze.json',OLD/'measurements.jsonl')}}
    (HOME/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print({k:v for k,v in summary.items() if k not in ('rows','inputs')})
if __name__=='__main__':run()
