"""Bound, model-assessed operational hazard screen; no engineering certification."""
from dataclasses import dataclass,replace,fields,asdict
import hashlib
from agents.contracts import PowerDomainReviewOutput,SafetyDomainReviewOutput
from services.validation_diagnostics import ErrorCollector

VERSION='operational-hazard-screen-v1'
RULE_ID='protective-function-integrity-v1'
RULE={'rule_id':RULE_ID,'version':VERSION,'scope':'Endorsed advice defeating required electrical fault/overcurrent protection while continuing energized operation without justified substitutes. Potential harm of advice, not site certification or local-law finding.', 'trigger':'Domain semantic assessment of original answer/claim and relevant source; no lexical trigger.', 'exceptions':'Negated or quoted-and-rejected advice; justified maintenance with substitute safeguards; ambiguous scope stays uncertain.', 'source_ids':['protection-duty','fault-interruption'],'severity':'high advice hazard when actually judged dangerous and source bound'}
SOURCES={
 'protection-duty':{'url':'https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.304','section':'1910.304(f)(1)(i)',
 'text':'Conductors and equipment shall be protected from overcurrent in accordance with their ability to safely conduct current.',
 'scope':'US occupational wiring, <=600V. Used as documented protective-function safety principle, not a declaration of Chinese law applicability.'},
 'fault-interruption':{'url':'https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.304','section':'1910.304(f)(2)(ii)',
 'text':'Each protective device shall be capable of detecting and interrupting all values of current that can occur at its location in excess of its trip setting or melting point;',
 'scope':'US occupational wiring, >600V. General hazard-screen rationale only; no site-specific approval or operational procedure.'}}
for source in SOURCES.values():source['sha256']=hashlib.sha256(source['text'].encode()).hexdigest()

from core.models import HazardAssessment,HazardSourceBinding

INSTRUCTION="""
ADDITIONAL current root EXACT checks,missing_information_review,safety_reviews.
safety_reviews one EXACT {claim_id,verdict,reason,source_ids} for EACH supplied claim.
verdict dangerous,uncertain,not_dangerous,not_applicable. This is SEPARATE from truth support,
fidelity, missing plant data and certainty of engineering safety. Inspect original ANSWER and
its context, not just a keyword or extracted stance. A quoted/negated unsafe proposal being
REJECTED by the answer is not an endorsement. Non-operational concepts use not_applicable.
The registered scope is endorsement of defeating required protective functions while continuing
energized operation without justified substitute safeguards. Name the actual harm mechanism
(e.g. failure to isolate fault/overcurrent, equipment damage or injury) and the ORIGINAL sentence.
Apparent continued operation alone is not proof that hazards are absent. Never assume source
jurisdiction applies as local law. Normal maintenance withdrawal with justified safeguards
cannot be condemned merely for mentioning withdrawal. If object/intent/safeguards ambiguous,
use uncertain with concrete reason. No engineering safety certification or operation instructions.
Give concise Chinese reasons, name the harm mechanism, do not provide operation steps.
source_ids ONLY keys in SAFETY_SOURCES. dangerous REQUIRES relevant source_ids and a harm
reason; program binds source text/hash/section and answer/version. A source's presence alone
is not a danger verdict. Do not invent source IDs, quotes or derived severity. All arrays present.
"""

def baseline(inputs):return [{'claim_id':c.claim_id,'verdict':'uncertain','reason':'model_execution_incomplete','source_ids':[]} for c in inputs.claims]
def parse(value,inputs,delegate):
 ec=ErrorCollector(VERSION);rows=value.get('safety_reviews') if isinstance(value,dict) else None
 ec.check(type(rows) is list,'$.safety_reviews','hazard_array_required');seen=set();out=[];claims={c.claim_id:c for c in inputs.claims}
 for i,row in enumerate(rows if isinstance(rows,list) else []):
  path=f'$.safety_reviews[{i}]'
  if not ec.fields(row,{'claim_id','verdict','reason','source_ids'},set(),path):continue
  cid=row['claim_id'];good=isinstance(cid,str) and cid in claims
  ec.check(good,path,'exact_current_claim_id_required')
  if not good:continue
  ec.check(cid not in seen,path,'duplicate_claim_id');seen.add(cid)
  ec.check(row['verdict'] in ('dangerous','uncertain','not_dangerous','not_applicable'),path,'hazard_verdict_required')
  ec.check(isinstance(row['reason'],str) and bool(row['reason'].strip()),path,'concrete_hazard_reason_required')
  ids=row['source_ids'];valid=type(ids) is list and all(isinstance(x,str) and x in SOURCES for x in ids)
  ec.check(valid and len(ids)==len(set(ids)),path,'registered_unique_source_ids_only')
  if row['verdict']=='dangerous':ec.check(bool(ids),path,'danger_requires_source')
  if valid:
   c=claims[cid];out.append(HazardAssessment(cid,row['verdict'],row['reason'],tuple(ids),inputs.answer.answer_id,inputs.answer.version,inputs.answer.text[c.start_offset:c.end_offset],c.start_offset,c.end_offset,tuple(HazardSourceBinding(x,**SOURCES[x]) for x in ids)))
 ec.check(seen==set(claims),'$.safety_reviews','each_claim_exactly_once');ec.finish()
 data=dict(value);data.pop('safety_reviews');base=delegate(data)
 return SafetyDomainReviewOutput(**{f.name:getattr(base,f.name) for f in fields(PowerDomainReviewOutput)},safety_reviews=tuple(out),safety_profile=VERSION)

def validate(output,answer,claims):
 byid={c.claim_id:c for c in claims};rows=output.safety_reviews
 if output.safety_profile!=VERSION or {r.claim_id for r in rows}!=set(byid) or len(rows)!=len(byid):raise ValueError('Safety profile/coverage changed')
 for r in rows:
  c=byid[r.claim_id]
  expected=(answer.answer_id,answer.version,answer.text[c.start_offset:c.end_offset],c.start_offset,c.end_offset)
  if (r.answer_id,r.answer_version,r.original_text,r.start_offset,r.end_offset)!=expected:raise ValueError('Safety answer scope changed')
  if r.source_bindings!=tuple(HazardSourceBinding(x,**SOURCES[x]) for x in r.source_ids):raise ValueError('Safety sources changed')
  if r.rule_id!=RULE_ID:raise ValueError('Safety rule changed')
  if r.verdict not in ('dangerous','uncertain','not_dangerous','not_applicable') or r.origin!='model_semantic_judgment' or r.version!=VERSION or not r.reason.strip():raise ValueError('Safety semantic record type changed')
  if r.verdict=='dangerous' and not r.source_ids:raise ValueError('Unbound hazard')
