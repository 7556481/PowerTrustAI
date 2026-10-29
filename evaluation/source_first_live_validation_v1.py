"""Admission-only stop path for the fixed batch. Never loads env before proof."""
import json
from pathlib import Path
from evaluation.source_first_materials_v1 import LOCAL as MATERIALS
from evaluation.natural_draft_audit_v1 import sha
from backend.config import ROOT

VERSION='source-first-audit-live-validation-v1'
LOCAL=ROOT/'data/retrieval_local'/VERSION
def preflight():
    m=json.loads((MATERIALS/'materials-v1.1.json').read_text(encoding='utf-8'))
    identity=json.loads((MATERIALS/'materials-v1.1-identity.json').read_text(encoding='utf-8'))
    if sha(m)!=identity['sha256']:raise RuntimeError('Frozen material mismatch')
    rows=[]
    for i,row in enumerate(m['cases']):
        citations=len(row['request']['existing_answer']['citations'])
        for variant in (('baseline','candidate') if i%2==0 else ('candidate','baseline')):
            rows.append(dict(id=row['id']+'-'+variant,status='unexecuted',initial_calls=2+citations if variant=='baseline' else 2,
                correction='Existing bounded corrections only; mutually exclusive with first-attempt success',
                supplement='Candidate: at most one additional fact review after up to3 queries; baseline: existing subject supplement',
                revision='Conditional once: Revision1 + re-extraction1 + full fact/domain audit; new citation count and payload unknown',
                input_upper=None,output_upper_per_request=8000,per_chain_cap=12,
                reason='Complete provider billing envelope bound unverified; no request admitted'))
    result=dict(version=VERSION,materials_sha256=sha(m),status='blocked_before_paid_attempt',
        reason='No verified token upper bound for complete hosted chat envelope; arbitrary2048 removed from new accounting',
        accounting='Per actual request reservation with trustworthy usage settlement; no upfront96-slot multiplication',
        planned=rows,actual_requests=0,actual_tokens=0,unsettled_reservations=0,cost_amount=None,
        env_loaded=False,real_index_opened=False,complete_live_runner_validated=False,
        limitation='Budget accounting substitute tests do not prove full live entry. No successful paid A/B or speed/quality conclusion.',
        official_sources=['https://api-docs.deepseek.com/quick_start/token_usage/','https://api-docs.deepseek.com/api/create-chat-completion/'])
    LOCAL.mkdir(parents=True,exist_ok=True)
    with (LOCAL/'admission.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False))
    return result
if __name__=='__main__':preflight()
