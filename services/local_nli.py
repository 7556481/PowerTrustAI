"""Optional diagnostic only; no Agent, policy, retrieval or revision authority."""
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4
from evaluation.support_dataset import make_sample,canonical,digest,task_key,public_metadata
from evaluation.support_nli import semantic_pair,VERSION as ADAPTER

VERSION='local-nli-sidecar-v1'
RISK='已见SSIAG实验曾出现4/23错误支持；NLI支持不表示整体通过。'


def frame(sample,*,run_id,answer_id,answer_version,claim_id,component_id,production_status=None,comparison_source='fact_agent'):
    return {'sample':sample,'binding':{'run_id':run_id,'answer_id':answer_id,'answer_version':answer_version,
        'claim_id':claim_id,'component_id':component_id},'production_status':production_status,
        'comparison_source':comparison_source}


def production_frames_v1(raw,expected_knowledge_version=None):
    """Only explicit complete per-component delivery + frozen whole candidates.

    Aggregate/legacy pools and original citations lack an unambiguous component
    scope here and are skipped. Never borrow a finding's chosen basis subset.
    """
    rounds=raw.get('review_rounds') or [{'answer':raw.get('answer'),
        'extraction':raw.get('extraction_output'),'verification':raw.get('verification_output')}]
    output=[]
    for round in rounds:
        answer=round.get('answer') or {};verification=round.get('verification') or {}
        claims=(round.get('extraction') or {}).get('claims') or verification.get('claims') or []
        for claim in claims:
            components=claim.get('components') or [{'component_id':'unresolved','proposition':claim.get('proposition') or claim.get('text')}]
            findings=[f for f in verification.get('findings',[]) if f.get('claim_id')==claim['claim_id']]
            for i,component in enumerate(components):
                finding=findings[0] if len(findings)==1 else {}
                reviews=[r for r in finding.get('component_reviews',[]) if r.get('component_id')==component['component_id']]
                status=reviews[0].get('status') if len(reviews)==1 else finding.get('status')
                item=frame(None,run_id=raw['run_id'],answer_id=answer.get('answer_id'),answer_version=answer.get('version'),
                    claim_id=claim['claim_id'],component_id=component['component_id'],production_status=status)
                reason=None
                targets=claim.get('component_basis_targets') or []
                target=targets[i] if i<len(targets) else None
                item['input_context']={'claim':public_metadata(claim),'component':component,'basis_target':target}
                if target not in ('document_body','technical_content'):reason='unsupported_basis_target'
                elif claim.get('assertion_role')!='asserted':reason='unsupported_assertion_role'
                elif status=='not_assessable':reason='production_not_assessable'
                elif verification.get('execution_issues'):reason='verification_execution_incomplete'
                elif (claim.get('answer_id'),claim.get('answer_version'))!=(answer.get('answer_id'),answer.get('version')):reason='claim_answer_version_mismatch'
                elif (verification.get('answer_id'),verification.get('answer_version'))!=(answer.get('answer_id'),answer.get('version')):reason='verification_answer_version_mismatch'
                matches=[m for rec in raw.get('retrieval_records',[]) for m in rec.get('fact_bindings',[])
                    if (m.get('answer_id'),m.get('answer_version'),m.get('claim_id'),m.get('component_id'))==
                    (answer.get('answer_id'),answer.get('version'),claim['claim_id'],component['component_id'])]
                if reason is None and len(matches)!=1:reason='explicit_component_delivery_missing_or_ambiguous'
                if reason is None:
                    try:delivery=json.loads(verification.get('delivery_summary') or '')
                    except (ValueError,TypeError):delivery={}
                    snapshots=[m for m in delivery.get('fact_bindings',[]) if m==matches[0]]
                    if len(snapshots)!=1:reason='verification_delivery_snapshot_missing_or_mismatched'
                if reason is None:
                    mapping=matches[0]
                    if mapping.get('basis_target')!=target:reason='delivery_target_mismatch'
                    elif expected_knowledge_version is not None and mapping.get('knowledge_version')!=expected_knowledge_version:reason='delivery_knowledge_version_mismatch'
                    elif mapping.get('outcome') not in ('hits','empty'):reason='delivery_not_complete'
                    elif not mapping.get('delivered_evidence_ids'):reason='no_body_delivered'
                if reason is None:
                    evidence=[];known={e['evidence_id']:e for e in verification.get('evidence',[])}
                    for eid in matches[0]['delivered_evidence_ids']:
                        e=known.get(eid)
                        quotes=[q for q in verification.get('quote_candidates',[]) if q.get('evidence_id')==eid and q.get('method')=='whole_fragment']
                        if e is None or len(quotes)!=1 or quotes[0].get('text')!=e['text'] or quotes[0].get('start_offset')!=0 or quotes[0].get('end_offset')!=len(e['text']):
                            reason='frozen_whole_body_candidate_missing';break
                        metadata={k:v for k,v in e.items() if k!='text'}
                        evidence.append({'basis_id':quotes[0]['quote_id'],'evidence_id':eid,'text':e['text'],
                            'text_sha256':digest(e['text']),'start_offset':0,'end_offset':len(e['text']),'metadata':public_metadata(metadata)})
                    if reason is None:
                        qualifiers=list(claim.get('qualifiers') or [])+list(claim.get('semantic_qualifiers') or [])
                        task={'task_type':'factual_support','knowledge_version':matches[0]['knowledge_version'],
                            'claim':{'text':claim['text'],'proposition':component['proposition'],'assertion_role':'asserted',
                                'basis_target':'document_body','category':component.get('category'),'qualifiers':qualifiers,'scope':qualifiers},
                            'answer_excerpt':claim['text'],'evidence':evidence,'other_basis':[],'delivery_state':'complete'}
                        item['sample']=make_sample(task,dict(item['binding'],conversion='explicit-frozen-delivery-v1'),{'structure_valid':True})
                if reason:item['skip_reason']=reason
                output.append(item)
    if not output:
        output=[dict(frame(None,run_id=raw['run_id'],answer_id=(raw.get('answer') or {}).get('answer_id'),
            answer_version=(raw.get('answer') or {}).get('version'),claim_id=None,component_id=None),skip_reason='no_explicit_supported_components')]
    return output


CONVERSION_V2='local-nli-production-conversion-v2'

def production_frames(raw,expected_knowledge_version=None):
    """Version-bound singleton literal; mixed/shared anchors fail closed.

    Current ClaimComponent has no independent literal spans. A model-normalized
    proposition alone is not a permission to guess a substring of its parent.
    """
    rounds=raw.get('review_rounds') or [{'answer':raw.get('answer'),
        'extraction':raw.get('extraction_output'),'verification':raw.get('verification_output')}]
    result=[]
    for round in rounds:
        answer=round.get('answer') or {};verification=round.get('verification') or {}
        claims=(round.get('extraction') or {}).get('claims') or verification.get('claims') or []
        narrowed=dict(raw,review_rounds=[round])
        try:frames=production_frames_v1(narrowed,expected_knowledge_version)
        except (KeyError,TypeError,ValueError,AttributeError,AssertionError):
            frames=[dict(frame(None,run_id=raw['run_id'],answer_id=answer.get('answer_id'),
                answer_version=answer.get('version'),claim_id=None,component_id=None),skip_reason='malformed_production_delivery_shape')]
        for item in frames:
            item['converter_version']=CONVERSION_V2
            if item.get('skip_reason'):result.append(item);continue
            cid=item['binding']['claim_id'];parts=[c for c in claims if c.get('claim_id')==cid]
            reason=None
            if len(parts)!=1:reason='claim_identity_missing_or_duplicate'
            else:
                claim=parts[0];components=claim.get('components',[]);targets=claim.get('component_basis_targets')
                if type(targets) is not list or len(targets)!=len(components) or any(type(t) is not str for t in targets):reason='component_target_mapping_type_or_count_mismatch'
                elif len(components)!=1:reason='mixed_component_literal_binding_missing'
                else:
                    start=claim.get('start_offset');end=claim.get('end_offset');text=answer.get('text')
                    if type(start) is not int or type(end) is not int or type(text) is not str or not 0<=start<end<=len(text) or text[start:end]!=claim.get('text'):
                        reason='literal_answer_span_missing_or_mismatched'
                    elif sum((c.get('start_offset'),c.get('end_offset'))==(start,end) for c in claims)!=1:
                        reason='shared_parent_anchor_without_component_literal_binding'
                    else:
                        rows=[f for f in verification.get('findings',[]) if f.get('claim_id')==cid]
                        reviews=[r for f in rows for r in f.get('component_reviews',[]) if r.get('component_id')==components[0]['component_id']]
                        if len(rows)!=1 or len(reviews)!=1:reason='exact_component_fact_review_missing'
                        elif reviews[0].get('fidelity_status')!='faithful' or reviews[0].get('reviewed_assertion_role')!='asserted' or reviews[0].get('verification_obligation')!='technical_truth':
                            reason='component_target_fidelity_unproven'
                        elif not any(c==claim for c in verification.get('claims',[])):
                            reason='verification_extraction_claim_mismatch'
                        else:
                            item['production_status']=reviews[0]['status']
                            item['literal_binding']={'type':'unique_single_component_parent_span','answer_id':answer['answer_id'],
                                'answer_version':answer['version'],'start_offset':start,'end_offset':end,
                                'text_sha256':digest(text[start:end]),'claim_id':cid,'component_id':components[0]['component_id'],
                                'normalized_fidelity_is_model_judgment':True}
            if reason:item['sample']=None;item['skip_reason']=reason
            result.append(item)
    return result


class LocalNLI:
    """One service-owned CPU process, one in-flight request, no waiting queue.

    Timeout kills the owned subprocess (not the application) and disables this
    instance until restart. Busy requests fail independently. No automatic retry.
    """
    def __init__(self,config):
        self.config=config;self.process=None;self.lock=asyncio.Lock();self.identity=None;self.failure=None
    async def start(self):
        try:
            if not all((self.config.nli_python,self.config.nli_checkpoint,self.config.nli_profile)):
                raise ValueError('Explicit isolated interpreter/checkpoint/profile required')
            self.process=await asyncio.create_subprocess_exec(str(self.config.nli_python),'-m','backend.nli_worker',
                '--checkpoint',str(self.config.nli_checkpoint),'--profile',str(self.config.nli_profile),
                cwd=str(Path(__file__).resolve().parents[1]),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,limit=4_000_000)
            self.process.stdin.write((json.dumps({'owner_pid':os.getpid(),'launcher_pid':self.process.pid})+'\n').encode('utf-8'))
            await self.process.stdin.drain()
            line=await asyncio.wait_for(self.process.stdout.readline(),30)
            ready=json.loads(line)
            if not ready.get('ready'):raise RuntimeError('Model unavailable')
            self.identity=ready['identity']
        except Exception:
            self.failure='model_unavailable';await self.close()
    async def close(self):
        if self.process:
            if self.process.returncode is None:
                try:self.process.kill()
                except ProcessLookupError:pass
            await self.process.wait();self.process=None
            # Windows venv redirectors may have a child interpreter. The worker
            # watches the exact launcher identity and exits when it disappears.
            if self.identity and self.identity.get('worker_pid'):await asyncio.sleep(.3)
    async def diagnose(self,item):
        record={'schema_version':VERSION,'diagnostic_id':uuid4().hex,**item['binding'],
            'authority':'diagnostic_only','affects_decision':False,'risk_note':RISK,
            'production_status':item.get('production_status'),'comparison_source':item.get('comparison_source','fact_agent'),
            'model':self.identity,'adapter_version':ADAPTER,'nli_three_class_result':None,'logits':None,'disagreement':None}
        record.update(converter_version=item.get('converter_version','explicit-frozen-sample'),literal_binding=item.get('literal_binding'))
        if item.get('skip_reason'):
            context=item.get('input_context',{})
            return dict(record,status='skipped',reason=item['skip_reason'],input_context=context,
                input_id=digest(canonical({'binding':item['binding'],'unconverted_input':context})))
        sample=item['sample']
        record.update(input_task=public_metadata(sample['task']),task_sha256=task_key(sample['task']),
            input_id=digest(canonical({'binding':item['binding'],'task':sample['task']})))
        if sample['task'].get('task_type')!='factual_support':return dict(record,status='skipped',reason='unsupported_task_type')
        if item.get('production_status')=='not_assessable':return dict(record,status='skipped',reason='production_not_assessable')
        try:pair=semantic_pair(sample)
        except (ValueError,AssertionError,KeyError,TypeError):return dict(record,status='skipped',reason='unsupported_or_invalid_body_adapter_input')
        record.update(input_id=digest(canonical({'binding':item['binding'],'pair':pair})),task_sha256=task_key(sample['task']),semantic_input=pair)
        if self.failure or not self.process:return dict(record,status='failed',reason=self.failure or 'model_unavailable')
        if self.lock.locked():return dict(record,status='failed',reason='local_concurrency_busy')
        async with self.lock:
            try:
                async def exchange():
                    self.process.stdin.write((json.dumps({'pair':pair},ensure_ascii=False)+'\n').encode('utf-8'))
                    await self.process.stdin.drain()
                    return await self.process.stdout.readline()
                line=await asyncio.wait_for(exchange(),self.config.nli_timeout_seconds)
                result=json.loads(line)
                record.update(result)
                if result.get('status')=='complete':record['disagreement']=None if item.get('production_status') is None else result['nli_three_class_result']!=item['production_status']
                return record
            except asyncio.TimeoutError:
                self.failure='local_inference_timeout';await self.close();return dict(record,status='failed',reason=self.failure)
            except Exception:
                self.failure='local_model_failure';await self.close();return dict(record,status='failed',reason=self.failure)
