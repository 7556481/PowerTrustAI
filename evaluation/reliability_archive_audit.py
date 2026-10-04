"""All saved responses: protocol-specific local replay, never historical migration."""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from evaluation.archive_replay import restore
from evaluation.evidence_delivery_trial import ROOT,load,save_new,digest
from agents.contracts import GenerationInput,RevisionInput,EvidenceVerificationInput,PowerDomainReviewInput
from agents.generation import parse_units
from agents.revision_contract_v2 import parse as parse_revision
from agents.domain_contract_v2 import parse as parse_domain,mark as domain_mark
from agents.verification_contract_v8 import baseline,translate,mark
from agents.verification_contract_v7 import parse_v7
from services.scoped_candidates import CandidateScope
from services.review_isolation import WireIsolation
from services.structured_model import strict_json
from services.claim_extractor import parse_extraction
from harness.evidence_review_demo import restore_answer
from core.validation import ContractError

SOURCE=ROOT/'data/retrieval_local/deepseek/evidence-delivery-v1'

def audit(out,version='v3'):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);summary=load(SOURCE/'summary.json');records=summary['model_records']
    frozen={str(p):digest(p) for p in SOURCE.rglob('*') if p.is_file()}
    wrappers=[]
    classes={'generation':GenerationInput,'revision':RevisionInput,'verification':EvidenceVerificationInput,'domain':PowerDomainReviewInput}
    for path in (SOURCE/'agent-inputs').glob('*.json'):
        v=load(path);wrappers.append((v['agent'],restore(v['input'],classes[v['agent']])))
    answer_by_path={}
    for p in SOURCE.glob('*.json'):
        if p.name in ('summary.json','progress.json','plan.json','offline-audit.json') or p.name.startswith(('paired-','verification-')):continue
        v=load(p)
        if v.get('answer'):
            for r in v.get('model_records',[]):answer_by_path[r['diagnostic_path']]=restore_answer(v['answer'])
    isolation={};rows=[]
    for r in records:
        raw=load(r['diagnostic_path']);text=raw['response_text'];assert hashlib.sha256(text.encode()).hexdigest()==raw['response_sha256']
        row={'response_path':r['diagnostic_path'],'prompt':r['prompt_version'],'correction':r['correction'],'historical_state':r['output_status'],'raw_sha256_verified':True}
        try:
            value=strict_json(text);prompt=r['prompt_version']
            if prompt.startswith('atomic-claims-v4'):
                parse_extraction(value,answer_by_path[r['diagnostic_path']],require_components=True)
            elif prompt.startswith('evidence-bound-generation-'):
                saved=load(r['input_snapshot_path']);inputs=next(i for label,i in wrappers if label=='generation' and i.request.task_id+'-answer'==saved['requested_answer_id'])
                parse_units(value,inputs)
            elif prompt.startswith('bounded-revision-'):
                saved=load(r['input_snapshot_path']);inputs=next(i for label,i in wrappers if label=='revision' and i.answer.answer_id==saved['requested_answer_id'] and i.answer.version+1==saved['requested_answer_version'] and json.loads(json.dumps([asdict(e) for e in i.allowed_evidence]))==saved['evidence'])
                parse_revision(value,inputs)
            elif prompt.startswith(('evidence-verification-v8','power-domain-review-v2')):
                saved=load(r['candidate_catalog_path']);label='verification' if prompt.startswith('evidence-') else 'domain'
                choices=[i for k,i in wrappers if k==label and i.answer.answer_id==saved['answer_id'] and i.answer.version==saved['answer_version'] and hashlib.sha256(i.answer.text.encode()).hexdigest()==saved['answer_sha256']]
                ids=[e['evidence_id'] for e in saved['EVIDENCE_METADATA']]
                inputs=next(i for i in choices if (set(ids)<={e.evidence_id for e in i.seed_evidence+i.original_evidence} if label=='verification' else set(ids)<={e.evidence_id for e in i.evidence}))
                known={e.evidence_id:e for e in (inputs.seed_evidence+inputs.original_evidence if label=='verification' else inputs.evidence)}
                scope=CandidateScope(inputs.answer,inputs.knowledge_version,saved['purpose'],tuple(known[e] for e in ids),check_id=saved['check_id'],protocol_version=saved['protocol_version'])
                assert scope.scope_id==saved['scope_id']
                if r['candidate_catalog_path'] not in isolation:
                    if label=='domain':
                        from agents.power_domain_review import MODEL_KEYS
                        wire={'checks':[{'check_id':k,'status':'not_assessable','claim_ids':[],'quote_ids':[],'basis_kind':'engineering_rule','rationale':'model_execution_incomplete','missing_prerequisites':['model_execution_incomplete']} for k in MODEL_KEYS]}
                        isolation[r['candidate_catalog_path']]=WireIsolation(wire,lambda v,i=inputs,s=scope:parse_domain(v,i,s),{'checks':'check_id'},domain_mark)
                    else:
                        base=baseline(inputs);group='findings' if saved['purpose']=='independent' else 'citation_reviews';index=saved['check_id']
                        wire={group:deepcopy(base[group] if group=='findings' else [base[group][index]])}
                        def strict(v,i=inputs,s=scope,b=base,g=group,ix=index):
                            expanded=deepcopy(b);translated=translate(v,s)
                            if g=='findings':expanded[g]=translated[g]
                            else:expanded[g][ix]=translated[g][0]
                            return parse_v7(expanded,i)
                        isolation[r['candidate_catalog_path']]=WireIsolation(wire,strict,{group:'claim_id' if group=='findings' else 'citation_index'},mark)
                isolation[r['candidate_catalog_path']].parse(value)
            else:
                row.update(replay='not_replayed',reason='Unrecognized saved prompt version');rows.append(row);continue
        except ContractError as exc:
            row.update(replay='invalid_structure',diagnostic=exc.diagnostic)
            historical=r.get('validation_error') or {};current=exc.diagnostic or {}
            row['same_first_constraint']=all(historical.get(k)==current.get(k) for k in ('field_path','constraint'))
        except (KeyError,StopIteration,ValueError) as exc:
            row.update(replay='not_replayed',reason='Archived input association/reconstruction unavailable',error_type=type(exc).__name__)
        else:row['replay']='valid_structure'
        rows.append(row)
    assert len(rows)==88 and all(digest(p)==h for p,h in frozen.items())
    result={'scope':'HISTORICAL ORIGINAL PROTOCOL REPLAY; NO SEMANTIC JUDGMENT OR STATE MIGRATION',
        'source_sha256':frozen,'responses':rows,'counts':dict(Counter(r['replay'] for r in rows)),
        'prompt_counts':dict(Counter(r['prompt'] for r in rows)),'historical_files_unchanged':True}
    save_new(out/('archive-audit-'+version+'.json'),result);print(json.dumps(result['counts']))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();audit(a.output_dir)
