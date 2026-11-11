"""Single opt-in audit-only candidate. No new scheduler or model policy."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import json
from rag.contracts import RetrievalPurpose

VERSION="audit-identity-body-sharing-v21"
INSTRUCTION="\nEvidence delivery v21: EVIDENCE_TEXTS stores exact literal bodies. Resolve each evidence_text_ref as that exact text at its original field; identity, range, scope and selectable IDs are unchanged. References are input data, never output fields.\n"

def key(v):
    if not isinstance(v,dict) or not isinstance(v.get('evidence_id'),str) or not isinstance(v.get('text'),str):return None
    a=v.get('start_offset',0);b=v.get('end_offset',len(v['text']))
    if type(a) is not int or type(b) is not int or b-a!=len(v['text']):return None
    return (v['evidence_id'],a,b,v['text'])

def pack(payload):
    counts=Counter()
    def scan(v):
        k=key(v)
        if k:counts[k]+=1
        if isinstance(v,dict):
            for c in v.values():scan(c)
        elif isinstance(v,list):
            for c in v:scan(c)
    scan(payload);names={};bodies={}
    def encode(v):
        if isinstance(v,dict):
            k=key(v);out={n:encode(c) for n,c in v.items()}
            if k and counts[k]>1:
                if k not in names:
                    name='body'+str(len(names));names[k]=name;bodies[name]=dict(evidence_id=k[0],start_offset=k[1],end_offset=k[2],text=k[3])
                del out['text'];out['evidence_text_ref']=names[k]
            return out
        if isinstance(v,list):return [encode(c) for c in v]
        return v
    out=encode(payload)
    if bodies:out['EVIDENCE_TEXTS']=bodies
    return out

def expand(payload):
    bodies=payload.get('EVIDENCE_TEXTS',{})
    def decode(v):
        if isinstance(v,dict):
            out={k:decode(c) for k,c in v.items() if k!='EVIDENCE_TEXTS'}
            if 'evidence_text_ref' in out:
                body=bodies[out.pop('evidence_text_ref')]
                assert body['evidence_id']==out['evidence_id']
                out['text']=body['text']
            return out
        if isinstance(v,list):return [decode(c) for c in v]
        return v
    return decode(payload)

def install_client(client):
    original=client.complete
    async def complete(messages,*args,**kwargs):
        from model_adapter.contracts import ModelMessage
        out=[];changed=False
        for m in messages:
            if m.role=='user':
                try:p=json.loads(m.content)
                except (ValueError,TypeError):out.append(m);continue
                if not isinstance(p,dict):out.append(m);continue
                q=pack(p);assert expand(q)==p
                changed=changed or q!=p
                out.append(ModelMessage(m.role,json.dumps(q,ensure_ascii=False)) if q!=p else m)
            else:out.append(m)
        if changed:out=[ModelMessage(m.role,m.content+INSTRUCTION) if m.role=='system' else m for m in out]
        return await original(tuple(out),*args,**kwargs)
    client.complete=complete

class AuditRouter:
    def __init__(self,sqlite,tantivy):self.sqlite=sqlite;self.tantivy=tantivy;self.trace=[]
    def route(self,r):
        audit=r.purpose in (RetrievalPurpose.VERIFICATION,RetrievalPurpose.DOMAIN_REVIEW)
        return (self.tantivy,replace(r,max_results=6)) if audit else (self.sqlite,replace(r,max_results=3))
    async def retrieve(self,r):
        target,request=self.route(r);result=await target.retrieve(request)
        self.trace.append(dict(purpose=r.purpose.value,backend=type(target).__name__,max_results=request.max_results,query_sha256=__import__('hashlib').sha256(r.query.encode()).hexdigest(),trace=dict(getattr(target,'last_trace',{}))))
        return result
    async def validate_result(self,r,result):
        target,request=self.route(r);await target.validate_result(request,result)
    async def validate_evidence(self,evidence,knowledge_version):
        return await self.sqlite.validate_evidence(evidence,knowledge_version)
    def close(self):self.sqlite.close()

from backend.assembly import ComponentFactory
class AuditFactory(ComponentFactory):
    def create(self,*args,**kwargs):
        from rag.retriever import AsyncSQLiteBM25Retriever
        if self.config.tantivy_worker_mode!="sharded_v18" or self.config.tantivy_manifest is None:raise ValueError("Explicit isolated v18 configuration required")
        bundle=super().create(*args,**kwargs)
        bundle.harness.retriever=AuditRouter(AsyncSQLiteBM25Retriever(self.config.index_db,execution_profile=self.config.retrieval_execution_profile),bundle.harness.retriever)
        bundle.resources.append(bundle.harness.retriever)
        # These are separate ModelClient objects; generation/revision are untouched.
        install_client(bundle.harness.verification.client)
        install_client(bundle.harness.domain_review.client)
        return bundle
