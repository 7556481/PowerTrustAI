"""Single-worker finite queue around the existing Harness, not an audit scheduler."""
import asyncio
from uuid import uuid4
from backend.assembly import ComponentFactory
from backend.serialization import wire,safe
from backend.store import StorageError
from core.models import TaskRequest,TaskMode,AnswerDraft,Evidence
from core.validation import validate_request
from harness.runtime import HarnessObserverError

class QueueFullError(RuntimeError):pass
class ServiceUnavailable(RuntimeError):pass

class ApplicationService:
    def __init__(self,config,store,factory=None):
        self.config=config;self.store=store;self.factory=factory or ComponentFactory(config)
        self.queue=asyncio.Queue(config.queue_capacity);self.lock=asyncio.Lock()
        self.worker=None;self.active=None;self.active_bundle=None;self.closing=False;self.storage_fault=False
        self.volatile_errors={}
        self.nli=None;self.nli_tasks=set();self.nli_errors={}
    async def start(self):
        if hasattr(self.factory,'initialize_retrieval'):self.factory.initialize_retrieval()
        self.store.recover();self.worker=asyncio.create_task(self._worker())
        if self.config.nli_enabled:
            from services.local_nli import LocalNLI
            self.nli=LocalNLI(self.config);await self.nli.start()
    async def stop(self):
        self.closing=True
        for task in self.nli_tasks:task.cancel()
        if self.nli_tasks:await asyncio.gather(*self.nli_tasks,return_exceptions=True)
        if self.nli:await self.nli.close()
        if self.active_bundle:await self.active_bundle.harness.cancel(self.active)
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker,return_exceptions=True)
        self.store.recover() # queued/running become interrupted; no auto-enqueue
        if hasattr(self.factory,'close'):await self.factory.close()

    async def submit(self,request,*,answer_requirements=(),indexed_reference_ids=()):
        validate_request(request,self.config.budget)
        knowledge=self.factory.preflight()
        if self.config.profile=='real' and request.existing_answer and request.existing_answer.citations:
            from agents.verification_contract_v10_batched import citation_payload,original_template,CONTRACT_VERSION
            from services.scoped_candidates import CandidateScope
            from services.citation_workload import pack
            from core.validation import InputError
            answer=request.existing_answer;original={e.evidence_id:e for e in request.provided_evidence}
            scopes=[None]+[CandidateScope(answer,knowledge,'original_citation',tuple(original[e] for e in c.evidence_ids),
                check_id=i,protocol_version=CONTRACT_VERSION) for i,c in enumerate(answer.citations)]
            groups,rejected=pack(range(len(answer.citations)),lambda g:citation_payload(answer,request.question,scopes,g),
                original_template(),self.config.citation_workload)
            if rejected:raise InputError('Complete citation scopes exceed configured capacity; citation_indexes='+str(list(rejected)))
        async with self.lock:
            if self.closing or self.storage_fault:raise ServiceUnavailable('Service not accepting work')
            if self.queue.full():raise QueueFullError('Waiting queue is full')
            rid=uuid4().hex;manifest=self.factory.manifest(knowledge)
            manifest['answer_requirements']=answer_requirements
            manifest['indexed_reference_ids']=indexed_reference_ids
            self.store.create(rid,request,manifest)
            self.queue.put_nowait((rid,request,knowledge,answer_requirements,indexed_reference_ids))
        return rid

    async def cancel(self,rid):
        row=self.store.get(rid)
        if row['status'] not in ('queued','running'):
            return {'run_id':rid,'cancel_requested':bool(row['cancel_requested']),'status':row['status'],'already_terminal':True}
        self.store.cancellation(rid)
        if row['status']=='queued':
            self.store.mark(rid,'cancelled',error_code='CANCELLED_BEFORE_START')
            # Free the queue slot; queue mutations are serialized on this event loop.
            retained=[]
            while not self.queue.empty():
                item=self.queue.get_nowait();self.queue.task_done()
                if item[0]!=rid:retained.append(item)
            for item in retained:self.queue.put_nowait(item)
        elif self.active==rid and self.active_bundle:await self.active_bundle.harness.cancel(rid)
        return {'run_id':rid,'cancel_requested':True,'status':self.store.get(rid)['status'],
            'termination_guaranteed':False,'note':'Cooperative cancellation; sent remote requests or worker threads may remain active.'}

    async def _worker(self):
        while not self.closing:
            if self.storage_fault:return
            rid,request,knowledge,requirements,indexed_ids=await self.queue.get()
            bundle=None
            try:
                if self.store.get(rid)['status']!='queued':continue
                self.active=rid;self.store.mark(rid,'running')
                bundle=self.factory.create(rid,lambda snapshot:self.store.checkpoint(rid,snapshot))
                self.active_bundle=bundle
                result=await bundle.harness.run(request,self.config.budget,knowledge_version=knowledge,
                    answer_requirements=tuple(requirements),indexed_reference_ids=tuple(indexed_ids),run_id=rid)
                status='interrupted' if self.closing else 'cancelled' if result.state.value=='cancelled' else 'failed' if result.state.value=='failed' else 'finished'
                self.store.mark(rid,status,error_code='PROCESS_INTERRUPTED' if self.closing else None,result=result)
                if self.nli and not self.closing:
                    task=asyncio.create_task(self.diagnose_completed(rid,wire(result)))
                    self.nli_tasks.add(task);task.add_done_callback(self.nli_tasks.discard)
            except asyncio.CancelledError:
                try:self.store.mark(rid,'interrupted',error_code='PROCESS_INTERRUPTED')
                except StorageError:self.storage_fault=True;self.volatile_errors[rid]='RUN_STORAGE_FAILED'
                raise
            except (StorageError,HarnessObserverError):
                self.storage_fault=True;self.volatile_errors[rid]='RUN_STORAGE_FAILED'
                try:self.store.mark(rid,'interrupted',error_code='RUN_STORAGE_FAILED')
                except StorageError:pass
            except Exception:
                try:self.store.mark(rid,'failed',error_code='SERVICE_EXECUTION_FAILED')
                except StorageError:self.storage_fault=True;self.volatile_errors[rid]='RUN_STORAGE_FAILED'
            finally:
                if bundle:
                    try:await bundle.drain()
                    finally:bundle.close()
                self.active=None;self.active_bundle=None;self.queue.task_done()

    def state(self,rid):
        row=self.store.get(rid)
        return safe({'schema_version':'local-review-service-v1','run_id':rid,'status':row['status'],
            'created_utc':row['created'],'started_utc':row['started'],'ended_utc':row['ended'],
            'cancel_requested':bool(row['cancel_requested']),'harness_state':row['harness_state'],
            'error_code':self.volatile_errors.get(rid) or row['error_code'],'profile':row['config']['profile'],
            'knowledge_version':row['config']['knowledge_version'],'persisted_result_available':row['result'] is not None,
            'partial_result_available':row['snapshot'] is not None,'persistence_confirmed':rid not in self.volatile_errors})

    async def diagnose_completed(self,rid,raw):
        # Audit has already terminated. Never pass diagnostics to a Harness input.
        from services.local_nli import production_frames
        try:
            for item in production_frames(raw,self.store.get(rid)['config']['knowledge_version']):
                record=await self.nli.diagnose(item)
                self.store.add_nli_diagnostic(rid,record)
        except asyncio.CancelledError:raise
        except Exception:self.nli_errors[rid]='diagnostic_conversion_or_storage_failed'

    def nli_result(self,rid):
        self.store.get(rid)
        from services.local_nli import RISK,VERSION
        return safe({'schema_version':VERSION,'enabled':self.config.nli_enabled,
            'model_available':bool(self.nli and self.nli.identity and not self.nli.failure),
            'records':self.store.objects(rid,'nli_diagnostic'),'error_code':self.nli_errors.get(rid),
            'authority':'diagnostic_only','affects_decision':False,'risk_note':RISK,
            'note':'仅展示已保存诊断，不重算历史交付；默认关闭时不加载模型。'})

    def result(self,rid):
        row=self.store.get(rid);raw=row['result'] or row['snapshot']
        if raw is None:return {'execution':self.state(rid),'result_available':False,'reason':'No stage result persisted yet'}
        raw=dict(raw)
        if row['result'] is None:
            # Use already persisted valid sibling outputs, not a second execution.
            names={'generation':'generation_output','claim_extraction':'extraction_output',
                   'evidence_verification':'verification_output','power_domain_review':'domain_output'}
            for stage in self.store.events(rid):
                name=names.get(stage['event']['component']);output=stage['stage_output']
                if not name or not isinstance(output,dict):continue
                if output.get('answer_version') is not None and raw.get('answer') and output['answer_version']!=raw['answer']['version']:continue
                if raw.get(name) is None:raw[name]=output
        report=raw.get('report');decision=None if not report else report['decision']
        rounds=raw.get('review_rounds',[])
        issues=list(raw.get('execution_issues',[]))
        for output in (raw.get('verification_output'),raw.get('domain_output')):
            if output:issues+=output.get('execution_issues',[])
        current_version=(raw.get('answer') or {}).get('version')
        no_answer=(raw.get('generation_output') or {}).get('substantive_answer') is False
        if no_answer and not issues:complete=True
        complete=bool(rounds) and rounds[-1]['answer']['version']==current_version and all(not r[k].get('execution_issues') for r in rounds for k in ('verification','domain_review')) and not issues
        verification=raw.get('verification_output') or {};domain=raw.get('domain_output') or {}
        original=row['request'].get('existing_answer')
        if original is None and raw.get('generation_output'):original=raw['generation_output']['answer']
        checked=complete and all(f.get('status')!='not_assessable' for f in verification.get('findings',[])) and all(f.get('check_status')!='not_assessable' for f in domain.get('findings',[])) and not any(c['status']=='incomplete' for c in verification.get('consistency_checks',[]))
        if decision and decision.get('policy_version','').startswith('product-decision-v1'):
            checked=complete and decision.get('execution_integrity')=='complete' and not any(c[1] in ('not_assessable','unknown') for c in decision.get('applicable_checks',[]))
        if not decision and row['config'].get('policy','').startswith('product-decision-v1') and row['status'] in ('failed','interrupted','cancelled','finished'):
            # A projection of execution failure, never a retroactive report/answer judgment.
            decision={'kind':'execution_incomplete','policy_version':row['config']['policy'],
                'execution_integrity':'incomplete','risk_level':'unknown','resolution':'unable_to_answer',
                'reason_codes':['NO_COMPLETED_AUDIT_REPORT'],'reasons':['No completed audit report; no factual or safety conclusion'],
                'origin':'service_execution_projection'}
        charged=(row['snapshot'] or {}).get('budget_usage',{})
        retrieval=raw.get('retrieval_records',[])
        projection=safe({'schema_version':'local-review-service-v1','execution':dict(self.state(rid),
            required_stages_complete=complete,all_required_checks_assessed=checked,execution_issues=issues,termination_reason=raw.get('termination_reason'),
            partial_only=row['result'] is None),'decision':decision,
            'no_substantive_answer':no_answer,
            'answer':{'original':original,
                'final':raw.get('answer'),'versions':self.store.objects(rid,'answer'),'revisions':raw.get('revision_outputs',[])},
            'findings':{'model_fact':verification.get('findings',[]),'domain':domain.get('findings',[]),
                'original_citations':verification.get('citation_reviews',[]),
                'program_rules':verification.get('consistency_checks',[]),'tools':raw.get('tool_results',[])},
            'evidence':self.store.objects(rid,'evidence'),'evidence_bindings':raw.get('evidence_bindings',[]),
            'snapshots':{'generation':raw.get('generation_output'),'extraction':raw.get('extraction_output'),
                'verification_input':verification.get('generation_snapshot'),'delivery':verification.get('delivery_summary')},
            'review_rounds':rounds,'model_usage':raw.get('model_records',[]),'retrieval':raw.get('retrieval_records',[]),
            'feedback_targets':[{'answer_id':f['answer_id'],'answer_version':f['answer_version'],'finding_id':f['finding_id']}
                for f in self.store.objects(rid,'finding') if f.get('answer_id') and f.get('answer_version')],
            'budget_usage':{'model_slots_charged':charged.get('model_calls'),
                'actual_model_request_records':len(raw.get('model_records',[])),
                'tool_calls':charged.get('tool_calls'),'retrieval_calls':retrieval[-1]['calls_used'] if retrieval else 0,
                'retrieval_chars':retrieval[-1]['cumulative_chars'] if retrieval else 0},
            'configuration':row['config'],'limitations':[
                'Local single-user prototype; review decisions are not engineering safety certification.',
                'Known model limitations: target conversion and confusion of fidelity with factual support.',
                'No engineering simulation; domain rules are development demonstrations.',
                'Missing evidence and engineering inputs remain unresolved; no aggregate confidence score.',
                'Simulated agents and synthetic_fixture: not evidence of real model ability.' if row['config']['profile']=='synthetic_fixture' else 'Model judgments are fallible; task approval is not safety certification.']})
        from backend.presentation import explain
        projection['presentation']=explain(projection)
        return projection

