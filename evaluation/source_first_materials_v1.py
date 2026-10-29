"""Freeze seen development inputs before candidate implementation; never loads env."""
from dataclasses import replace
import json
from backend.config import ROOT
from backend.serialization import wire
from core.models import TaskRequest, ClaimExtractionOutput
from evaluation.archive_replay import restore
from evaluation.natural_draft_audit_v1 import recover, sha, save
from services.evidence_scope import make_snapshot

LOCAL = ROOT/'data/retrieval_local/source-first-audit-redesign-v1'

def prepare():
    path=LOCAL/'materials-v1.1.json'
    if path.exists():raise RuntimeError('Frozen materials already exist')
    generated,origins=recover()
    old=json.loads((ROOT/'data/retrieval_local/natural-draft-audit-v1/batch/summary.json').read_text(encoding='utf-8'))
    rows=[]
    expectations=['Correct modeling explanation: preserve both positions and MW/Mvar.',
        'Correct unconditional need for joint studies to may/important; retain LPF/support points.',
        'Remove unsupported exclusion of N-2 thermal use; retain N-1, stability and extreme disturbances.',
        'Dynamic statement absent from original boundary-load evidence; retrieve dynamic paragraph or remain unresolved. Never imply original citation supports it.']
    for n,i in enumerate((0,1,3,4)):
        g=generated[i];req=restore(origins[i]['request'],TaskRequest)
        req=replace(req,existing_answer=g.answer,provided_evidence=g.evidence)
        snapshot=g.generation_output.evidence_snapshot
        historical=next(r['accepted']['run_id'] for r in old['control'] if r['case_id']==f'N{i+1}')
        extraction=restore(old['outputs'][historical]['extraction_output'],ClaimExtractionOutput)
        origin='Unmodified archived natural C answer and actual generation delivery'
        if n==3:
            # Explicit authored evidence-gap counterfactual. Never called an actual generation.
            from core.models import CitationBinding
            # Keep the body/claims fixed but bind the authored counterfactual to
            # the actually supplied unrelated source. A nonexistent citation ID
            # would test invalid input rather than a semantic evidence gap.
            answer=replace(g.answer,citations=(CitationBinding(0,len(g.answer.text),(generated[0].evidence[0].evidence_id,)),))
            req=replace(req,existing_answer=answer,provided_evidence=generated[0].evidence)
            snapshot=make_snapshot(answer,req.provided_evidence,snapshot.knowledge_version,
                request=req,prompt_version='authored-gap-fixture-v1')
            origin='Authored gap fixture: archived natural N5 text/claims with N1 evidence; not historical generation input'
        from core.validation import validate_answer,validate_extraction
        validate_answer(req.existing_answer,req.provided_evidence);validate_extraction(extraction,req.existing_answer)
        rows.append(dict(id=f'S{n+1}',origin=origin,request=wire(req),snapshot=wire(snapshot),
            extraction=wire(extraction),expected=expectations[n],
            required_reference=f'docs/evaluation/natural-draft-audit-v1/materials-reference.json#N{i+1}'))
    material=dict(version='source-first-materials-v1',selection='N1 correct, N2 modality, N4 exclusion: three unchanged natural drafts; one declared authored N5 evidence gap. Seen development data, AI-assisted/user-supervised, not expert gold.',cases=rows,
        order=[f'S{i+1}-{v}' for i in range(4) for v in (('baseline','candidate') if i%2==0 else ('candidate','baseline'))],
        limits=dict(per_chain_calls=12,total_calls=96,total_tokens=1200000),
        gates=dict(complete_pairs=4,median_reduction=.25,median_saving_seconds=5,error_repairs=2,no_false_edit=True,no_false_gap_pass=True,no_key_loss=True))
    save(path,material)
    save(LOCAL/'materials-v1.1-identity.json',dict(sha256=sha(material),initial_freeze_before_implementation=True,
        correction='Only S4 authored citation now names supplied source; original materials.json retained; no prediction or real request seen'))
    print('Frozen 4 development cases and AB/BA/AB/BA; zero env/index/model access')

if __name__=='__main__':prepare()
