"""Optional FastAPI boundary. No model requests on import or health checks."""
from contextlib import asynccontextmanager
from typing import Literal
import secrets
from uuid import uuid4
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from pathlib import Path
from pydantic import BaseModel,ConfigDict,Field
from backend.config import ServiceConfig
from backend.service import ApplicationService,QueueFullError,ServiceUnavailable
from backend.assembly import ConfigurationError
from backend.store import RunStore,StorageError,BindingError
from backend.serialization import safe
from backend.local_access import ProcessLease,token_for
from core.models import TaskRequest,TaskMode,AnswerDraft,Evidence,EngineeringContext,EngineeringQuantity,CitationBinding
from core.validation import InputError,ContractError

class StrictModel(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Reference(StrictModel):
    text:str=Field(min_length=1,max_length=20000)
    label:str=Field(default='user reference',max_length=200)
class Quantity(StrictModel):
    kind:str=Field(min_length=1,max_length=80)
    value:float=Field(allow_inf_nan=False)
    unit:str=Field(min_length=1,max_length=40)
    reference:str=Field(default='user supplied',max_length=400)
class Engineering(StrictModel):
    goal:Literal['conceptual','plant_assessment']='conceptual'
    network_model:str|None=Field(default=None,max_length=4000)
    operating_point:str|None=Field(default=None,max_length=4000)
    limits:str|None=Field(default=None,max_length=4000)
    contingencies:list[str]=Field(default_factory=list,max_length=30)
    quantities:list[Quantity]=Field(default_factory=list,max_length=30)
class ExistingCitation(StrictModel):
    start_offset:int=Field(ge=0)
    end_offset:int=Field(gt=0)
    fragment_ids:list[str]=Field(min_length=1)

class Submit(StrictModel):
    mode:Literal['question_answer','assess_existing']
    question:str=Field(min_length=1,max_length=8000)
    user_context:str=Field(default='',max_length=10000)
    existing_answer:str|None=Field(default=None,min_length=1,max_length=80000)
    existing_citations:list[ExistingCitation]=Field(default_factory=list)
    references:list[Reference]=Field(default_factory=list,max_length=10)
    engineering_context:Engineering|None=None
    answer_requirements:list[str]=Field(default_factory=list,max_length=10)
    def task(self,indexed_evidence=()):
        if not self.question.strip() or self.existing_answer is not None and not self.existing_answer.strip():raise InputError('Nonempty question/answer required')
        if (self.mode=='assess_existing')!=(self.existing_answer is not None):raise InputError('Existing answer required only for assess_existing')
        if self.existing_citations and self.mode!='assess_existing':raise InputError('Citation bindings require existing answer')
        if any(len(s)>4000 for s in self.answer_requirements):raise InputError('Answer requirement too long')
        aid=uuid4().hex
        by_fragment={e.provenance.fragment_id:e.evidence_id for e in indexed_evidence}
        citations=tuple(CitationBinding(c.start_offset,c.end_offset,tuple(by_fragment[f] for f in c.fragment_ids)) for c in self.existing_citations)
        answer=None if self.existing_answer is None else AnswerDraft(aid,1,self.existing_answer,citations=citations)
        refs=tuple(Evidence('user-'+uuid4().hex,'user_supplied','unverified',r.label,r.text,'user_reference') for r in self.references)
        e=self.engineering_context
        engineering=None if e is None else EngineeringContext(e.goal,e.network_model,e.operating_point,e.limits,
            tuple(e.contingencies),tuple(EngineeringQuantity(uuid4().hex,q.kind,q.value,q.unit,q.reference) for q in e.quantities))
        return TaskRequest(uuid4().hex,TaskMode(self.mode),'voltage_stability_reactive_support',self.question,self.user_context,answer,refs+tuple(indexed_evidence),engineering)
class HumanReview(StrictModel):
    answer_id:str=Field(min_length=1,max_length=150)
    answer_version:int=Field(ge=1)
    finding_id:str|None=Field(default=None,max_length=180)
    action:Literal['confirm','disagree','pending','note']
    reviewer_id:str=Field(default='local-user',min_length=1,max_length=100)
    source:Literal['user','ai_assisted_user_supervised']='user'
    note:str=Field(default='',max_length=10000)

def create_app(config=None,*,store=None,factory=None,access_token=None,shutdown=None):
    config=config or ServiceConfig()
    injected=store is not None
    @asynccontextmanager
    async def lifespan(app):
        lease=ProcessLease(config.run_db.with_suffix('.process-lock'));lease.acquire()
        service=None;runtime_store=None
        try:
            runtime_store=store or RunStore(config.run_db)
            app.state.token=access_token or token_for(config.token_file)
            from backend.local_session import LocalSessions
            app.state.sessions=LocalSessions(config.run_db)
            service=ApplicationService(config,runtime_store,factory);app.state.service=service
            await service.start();yield
        finally:
            try:
                if service:await service.stop()
            finally:
                if runtime_store and not injected:runtime_store.close()
                lease.close()
    app=FastAPI(title='PowerTrustAI local assisted review',version='1',lifespan=lifespan,
                docs_url='/docs',redoc_url=None)
    auth=HTTPBearer(auto_error=False)
    async def authorized(request:Request,credentials:HTTPAuthorizationCredentials|None=Depends(auth)):
        bearer=credentials is not None and credentials.scheme.lower()=='bearer' and secrets.compare_digest(credentials.credentials,request.app.state.token)
        session=request.app.state.sessions.valid(request.cookies.get(request.app.state.sessions.cookie))
        if (credentials is not None and not bearer) or (credentials is None and not session):
            raise HTTPException(401,detail={'code':'LOCAL_TOKEN_REQUIRED'},headers={'WWW-Authenticate':'Bearer'})
    def svc(request):return request.app.state.service

    @app.middleware('http')
    async def local_only(request,call_next):
        if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
            return JSONResponse(status_code=403,content={'code':'LOCAL_ONLY'})
        if request.query_params:return JSONResponse(status_code=400,content={'code':'QUERY_PARAMETERS_NOT_ALLOWED'})
        host=request.headers.get('host','').split(':')[0]
        if host not in ('127.0.0.1','localhost','testserver','[','::1'):
            return JSONResponse(status_code=400,content={'code':'INVALID_LOCAL_HOST'})
        if request.method=='POST':
            origin=request.headers.get('origin')
            if origin and origin!=str(request.base_url).rstrip('/') and not (request.url.path=='/session/bootstrap' and origin=='null'):
                return JSONResponse(status_code=403,content={'code':'SAME_ORIGIN_REQUIRED'})
            body=await request.body()
            if len(body)>256000:return JSONResponse(status_code=413,content={'code':'BODY_TOO_LARGE'})
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        if request.url.path=='/' or request.url.path.startswith('/ui/'):
            response.headers['Content-Security-Policy']="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.get('/',include_in_schema=False)
    async def page():return FileResponse(Path(__file__).parent/'static/index.html')

    @app.get('/ui/{asset}',include_in_schema=False)
    async def ui_asset(asset:str):
        if asset not in ('app.js','connection_memory.js','style.css'):raise HTTPException(404)
        return FileResponse(Path(__file__).parent/'static'/asset)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Never echo request input, which might contain an accidentally pasted secret.
        return JSONResponse(status_code=422,content={'code':'INPUT_VALIDATION_FAILED',
            'errors':[{'field_path':list(e['loc']),'constraint':e['type']} for e in exc.errors()]})
    @app.exception_handler(StorageError)
    async def storage_error(request,exc):return JSONResponse(status_code=503,content={'code':'RUN_STORAGE_FAILED','persisted':False})
    @app.exception_handler(KeyError)
    async def missing(request,exc):return JSONResponse(status_code=404,content={'code':'RUN_SCOPED_RECORD_NOT_FOUND'})
    @app.exception_handler(BindingError)
    async def bad_binding(request,exc):return JSONResponse(status_code=409,content={'code':'INVALID_RUN_ANSWER_FINDING_BINDING'})

    @app.get('/health')
    async def health(request:Request):
        service=svc(request)
        if not service.store.healthy():service.storage_fault=True
        try:service.factory.preflight();ready=True;reason=None
        except ConfigurationError:ready=False;reason='CONFIGURATION_UNAVAILABLE'
        return {'status':'degraded' if service.storage_fault or not ready else 'ready','health_model_requests':0,
            'local_session_version':'localhost-launch-session-v1',
            'profile':config.profile,'configuration_ready':ready,'reason':reason,
            'retrieval_mode':config.retrieval_mode if config.profile=='real' else 'none',
            'fact_retrieval_strategy':config.fact_strategy,'knowledge_version':config.knowledge_version if config.profile=='real' else None,
            'storage_healthy':not service.storage_fault,'active_run':service.active is not None,
            'queue_capacity':config.queue_capacity,'queued':service.queue.qsize(),'workers_supported':1}

    @app.post('/session/launch',dependencies=[Depends(authorized)])
    async def launch(request:Request):
        # Launcher is an OS-local client. A cookie alone may not mint launch files.
        credentials=await auth(request)
        if credentials is None or not secrets.compare_digest(credentials.credentials,request.app.state.token):
            raise HTTPException(403,detail={'code':'LOCAL_LAUNCHER_REQUIRED'})
        return {'html':request.app.state.sessions.issue(str(request.base_url).rstrip('/'))}

    @app.post('/session/remember',dependencies=[Depends(authorized)],include_in_schema=False)
    async def remember(request:Request):
        credentials=await auth(request)
        if credentials is None or not secrets.compare_digest(credentials.credentials,request.app.state.token):
            raise HTTPException(403,detail={'code':'LOCAL_BEARER_REQUIRED'})
        # Upgrade an existing explicitly remembered connection; no token in response.
        sessions=request.app.state.sessions
        import re
        nonce=re.search(r'name="ticket" value="([^"]+)"',sessions.issue(str(request.base_url).rstrip('/')))[1]
        session=sessions.redeem(nonce)
        response=JSONResponse({'version':sessions.version,'connected':True})
        response.set_cookie(sessions.cookie,session,max_age=sessions.lifetime,httponly=True,samesite='strict',path='/')
        return response

    @app.post('/session/stop',dependencies=[Depends(authorized)],include_in_schema=False)
    async def stop_local(request:Request):
        credentials=await auth(request)
        if credentials is None or not secrets.compare_digest(credentials.credentials,request.app.state.token):
            raise HTTPException(403,detail={'code':'LOCAL_LAUNCHER_REQUIRED'})
        if shutdown is None:raise HTTPException(404)
        service=svc(request)
        if service.active is not None or not service.queue.empty():raise HTTPException(409,detail={'code':'SERVICE_BUSY'})
        shutdown()
        return {'shutdown':'graceful_requested'}

    @app.post('/session/bootstrap',include_in_schema=False)
    async def bootstrap(request:Request):
        from urllib.parse import parse_qs
        try:fields=parse_qs((await request.body()).decode('ascii',errors='strict'))
        except UnicodeDecodeError:raise HTTPException(401,detail={'code':'INVALID_LAUNCH_TICKET'}) from None
        if set(fields)!={'ticket'} or len(fields['ticket'])!=1:raise HTTPException(401,detail={'code':'INVALID_LAUNCH_TICKET'})
        session=request.app.state.sessions.redeem(fields['ticket'][0])
        if session is None:raise HTTPException(401,detail={'code':'LAUNCH_TICKET_EXPIRED_OR_USED'})
        response=RedirectResponse('/',status_code=303)
        response.set_cookie(request.app.state.sessions.cookie,session,max_age=request.app.state.sessions.lifetime,
            httponly=True,samesite='strict',path='/')
        return response

    @app.get('/session',dependencies=[Depends(authorized)])
    async def session_status():return {'connected':True,'version':'localhost-launch-session-v1'}

    @app.post('/session/logout',dependencies=[Depends(authorized)])
    async def logout(request:Request):
        request.app.state.sessions.forget(request.cookies.get(request.app.state.sessions.cookie))
        response=JSONResponse({'connected':False})
        response.delete_cookie(request.app.state.sessions.cookie,path='/',httponly=True,samesite='strict')
        return response

    @app.post('/runs',status_code=202,dependencies=[Depends(authorized)])
    async def submit(body:Submit,request:Request):
        try:
            indexed=()
            if body.existing_citations:
                if config.profile!='real':raise InputError('Indexed references require real knowledge snapshot')
                if body.mode!='assess_existing' or body.existing_answer is None:raise InputError('Existing answer required')
                for c in body.existing_citations:
                    if not 0<=c.start_offset<c.end_offset<=len(body.existing_answer):raise InputError('Citation span outside answer')
                import asyncio
                def resolve():
                    from rag.storage import KnowledgeStore
                    ids=tuple(dict.fromkeys(f for c in body.existing_citations for f in c.fragment_ids))
                    with KnowledgeStore(config.index_db,readonly=True) as index:
                        return tuple(index.evidence(f,config.knowledge_version) for f in ids)
                indexed=await asyncio.to_thread(resolve)
            rid=await svc(request).submit(body.task(indexed),answer_requirements=tuple(body.answer_requirements),
                indexed_reference_ids=tuple(e.evidence_id for e in indexed))
        except InputError as exc:
            if str(exc).startswith('Complete citation scopes exceed configured capacity; citation_indexes='):
                raise HTTPException(422,detail={'code':'REVIEW_MESSAGE_CAPACITY_EXCEEDED',
                    'citation_indexes':[int(n) for n in str(exc).split('=')[-1].strip('[]').split(',') if n.strip()]}) from None
            raise HTTPException(422,detail={'code':'INPUT_CONTRACT_ERROR'}) from None
        except ContractError:raise HTTPException(422,detail={'code':'INPUT_CONTRACT_ERROR'}) from None
        except ConfigurationError:raise HTTPException(503,detail={'code':'CONFIGURATION_UNAVAILABLE'}) from None
        except QueueFullError:raise HTTPException(429,detail={'code':'QUEUE_FULL'},headers={'Retry-After':'5'}) from None
        except ServiceUnavailable:raise HTTPException(503,detail={'code':'SERVICE_UNAVAILABLE'}) from None
        return {'run_id':rid,'status':'queued','profile':config.profile}

    @app.get('/runs/{run_id}',dependencies=[Depends(authorized)])
    async def state(run_id:str,request:Request):return svc(request).state(run_id)
    @app.get('/runs/page/{offset}',dependencies=[Depends(authorized)])
    async def run_page(offset:int,request:Request):
        if offset<0 or offset>1000000:raise HTTPException(422,detail={'code':'INVALID_PAGE_OFFSET'})
        return safe(svc(request).store.list_runs(offset))
    @app.get('/runs/{run_id}/result',dependencies=[Depends(authorized)])
    async def result(run_id:str,request:Request):
        value=svc(request).result(run_id)
        return JSONResponse(status_code=200 if value.get('answer') else 202,content=value)
    @app.get('/runs/{run_id}/trace',dependencies=[Depends(authorized)])
    async def trace(run_id:str,request:Request):return safe({'run_id':run_id,'events':svc(request).store.events(run_id)})
    @app.get('/runs/{run_id}/nli',dependencies=[Depends(authorized)])
    async def nli(run_id:str,request:Request):return svc(request).nli_result(run_id)
    @app.get('/runs/{run_id}/evidence/{evidence_id}',dependencies=[Depends(authorized)])
    async def evidence(run_id:str,evidence_id:str,request:Request):return safe(svc(request).store.evidence(run_id,evidence_id))
    @app.post('/runs/{run_id}/cancel',dependencies=[Depends(authorized)])
    async def cancel(run_id:str,request:Request):return await svc(request).cancel(run_id)
    @app.post('/runs/{run_id}/reviews',status_code=201,dependencies=[Depends(authorized)])
    async def add_review(run_id:str,body:HumanReview,request:Request):return safe(svc(request).store.add_review(run_id,body.model_dump()))
    @app.get('/runs/{run_id}/reviews',dependencies=[Depends(authorized)])
    async def reviews(run_id:str,request:Request):return safe(svc(request).store.reviews(run_id))
    return app

