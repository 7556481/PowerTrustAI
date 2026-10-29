"""Versioned supply only: production reviewers, contracts and policy are unchanged."""
from dataclasses import replace,asdict
from time import perf_counter
from uuid import uuid4
import asyncio,json
from core.models import EvidenceBinding,ExecutionStatus
from core.validation import merge_evidence,require
from harness.contracts import RetrievalRecord
from harness.retrieval import Delivery
from rag.contracts import ContextOptions,RetrievalPurpose
VERSION='production-evidence-reuse-v1'
def eligible(ex):
 c=ex.request.engineering_context
 return getattr(ex.harness,'audit_evidence_profile','baseline_v1')=='deferred_subject_v1' and c is not None and c.goal=='conceptual' and not c.quantities
async def domain_supply(ex):
 ex.domain_reused=False
 # A mandatory independent full-corpus fact query has already completed. Never
 # turn citation count, lexical coverage or model support into proof of no counterevidence.
 roots=tuple(ex.active_snapshot.evidence) if ex.active_snapshot is not None else ex.original_evidence
 if ex.vd.issue or not roots or len(roots)>12 or any(e.provenance is None or e.provenance.knowledge_version!=ex.knowledge_version for e in roots):
  return await ex.retrieve_for(RetrievalPurpose.DOMAIN_REVIEW)
 remaining=min(ex.budget.step_timeout_seconds,ex.deadline-perf_counter());require(remaining>0,'Source supply timeout')
 start=perf_counter();context=await asyncio.wait_for(ex.harness.retriever.source_context(roots,ex.knowledge_version,ContextOptions(2400,6,1,True,'storage_order')),remaining)
 bodies=merge_evidence(roots,tuple(i.evidence for i in context.items),ex.vd.evidence)
 chars=sum(len(e.text) for e in bodies)
 if chars>min(16000,ex.budget.max_retrieval_chars_per_call,ex.budget.max_retrieval_chars_total-ex.retrieval.chars):
  return await ex.retrieve_for(RetrievalPurpose.DOMAIN_REVIEW)
 await asyncio.wait_for(ex.harness.retriever.validate_evidence(bodies,ex.knowledge_version),min(ex.budget.step_timeout_seconds,max(.001,ex.deadline-perf_counter())))
 rid=uuid4().hex;existing={b.evidence_id:b for b in ex.vd.bindings};adj={i.evidence.evidence_id:i for i in context.items};bindings=[]
 for e in bodies:
  if e.evidence_id in existing:b=replace(existing[e.evidence_id],purpose='domain_review')
  elif e.evidence_id in adj:b=EvidenceBinding(e.evidence_id,'index_adjacent_context','domain_review',ex.answer.version,rid,tuple(l.core_evidence_id for l in adj[e.evidence_id].links))
  else:b=EvidenceBinding(e.evidence_id,'index_saved_reference','domain_review',ex.answer.version,rid)
  bindings.append(b)
 ex.retrieval.chars+=chars;ex.retrieval.known_evidence.update((e.evidence_id,e) for e in bodies)
 record=RetrievalRecord(rid,'domain_review','',VERSION,ex.answer.version,ex.knowledge_version,ExecutionStatus.SUCCEEDED,'source_scope',core_evidence_ids=tuple(e.evidence_id for e in roots),context_evidence_ids=tuple(e.evidence.evidence_id for e in context.items),accepted_chars=chars,offered_chars=chars,cumulative_chars=ex.retrieval.chars,calls_used=ex.retrieval.calls,duration_ms=int((perf_counter()-start)*1000),reason='Original snapshot + bounded same-source context + mandatory independent fact retrieval. Domain full-corpus query deferred to explicit literature/assessment gap; not exhaustive cross-check.',answer_id=ex.answer.answer_id)
 ex.retrieval.records.append(record);ex.bindings+=tuple(bindings);ex.evidence=merge_evidence(ex.evidence,bodies);ex.domain_reused=True
 ex.record('production_domain_source_supply',ExecutionStatus.SUCCEEDED,start,record.reason)
 return Delivery(bodies,tuple(bindings),None,record)
async def domain_gap(ex):
 if not getattr(ex,'domain_reused',False) or ex.d_issue or ex.domain.execution_issues:return
 gaps=[f for f in ex.domain.findings if f.origin=='model_judgment' and (f.check_status=='not_assessable' or (f.basis_kind=='literature' and f.check_status!='no_issue'))]
 if not gaps:return
 start=perf_counter();extra=await ex.retrieve_for(RetrievalPurpose.DOMAIN_REVIEW)
 if extra.issue:
  ex.domain=replace(ex.domain,execution_issues=ex.domain.execution_issues+(extra.issue,));return
 evidence=merge_evidence(ex.d_evidence,extra.evidence);inputs=replace(ex.d_input,evidence=evidence,evidence_bindings=ex.d_input.evidence_bindings+extra.bindings,delivery_summary=json.dumps(dict(version=VERSION,scope='source_pool_plus_original_domain_gap',prior=ex.d_input.delivery_summary,latest=asdict(extra.record)),ensure_ascii=False))
 updated,issue=await ex.review('power_domain_review',ex.harness.domain_review,inputs,evidence,False,None)
 if issue:ex.domain=replace(ex.domain,execution_issues=ex.domain.execution_issues+(issue,));return
 ex.domain=updated;ex.d_input=inputs;ex.d_evidence=evidence
 ex.record('production_domain_gap_recheck',ExecutionStatus.SUCCEEDED,start,json.dumps(dict(trigger_ids=[f.finding_id for f in gaps],retrieval_id=extra.record.retrieval_id)))
