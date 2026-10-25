"""Read-only old refusal/compatibility audit. Real projections only go to ignored data."""
import json,hashlib
from dataclasses import asdict
from backend.config import ROOT
from backend.serialization import wire
from agents.contracts import RevisionInput,LiteralVerificationOutput,PowerDomainReviewOutput
from core.models import TaskRequest,AnswerDraft,Evidence
from core.validation import ContractError
from evaluation.archive_replay import restore
from services.structured_model import strict_json
from services.literal_review_v1 import parse_revision as old_parse
from services.local_revision_v2 import plan,parse,system,VERSION
OLD=ROOT/'data/retrieval_local/literal-review-stage1-v1'
LOCAL=ROOT/'data/retrieval_local/local-revision-offline-redesign-v1'
PUBLIC=ROOT/'docs/evaluation/local-revision-offline-redesign-v1'
SEQUENCES=(10,11,15,16,37,38,42,43)
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(data):return hashlib.sha256(data).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(wire(v),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def old_input(sequence):
    """Known archived business fields only; never headers, credentials or env."""
    m=load(OLD/'batch/messages'/f'{sequence:04d}.json')
    data=next(json.loads(x['content']) for x in m['messages'] if x['role']=='user' and 'verification' in json.loads(x['content']))
    req=restore(load(OLD/'batch'/m['run_id']/'input.json')['request'],TaskRequest)
    inp=RevisionInput(req,restore(data['answer'],AnswerDraft),restore(data['verification'],LiteralVerificationOutput),
        restore(data['domain_review'],PowerDomainReviewOutput),tuple(restore(e,Evidence) for e in data['sources']),())
    return inp,m,data,load(OLD/'batch/responses'/f'{sequence:04d}.json')['text']


def independent_old_errors(value,inp):
    issues=[];defs={d.finding_id:d for d in inp.verification.literal_defects};opinions=set(defs)|{f.finding_id for f in inp.domain_review.findings}
    for k in set(value)-{'replacements','finding_actions'}:issues.append(dict(path='$',constraint='extra_root_field',field_name_json=json.dumps(k[:80],ensure_ascii=True)))
    for i,e in enumerate(value['replacements']):
        for j,k in enumerate(e['finding_ids']):
            if k not in defs:issues.append(dict(path=f'$.replacements[{i}].finding_ids[{j}]',constraint='opinion_id_is_not_source_authority' if k in opinions else 'unknown_authorization_id'))
            elif e['relation']=='dependent' and defs[k].anchor_id==e['anchor_id']:issues.append(dict(path=f'$.replacements[{i}].relation',constraint='v1_dependent_with_own_defect'))
    ids=[x['finding_id'] for x in value['finding_actions']]
    return dict(independently_observable=issues,opinion_accounting_complete=len(ids)==len(set(ids)) and set(ids)==opinions,unknown_accounting_ids=sorted(set(ids)-opinions))


def inspect_history():
    public={x['send']['sequence']:x for x in load(ROOT/'docs/evaluation/literal-review-stage1-v1/predictions.json')}
    frozen=load(OLD/'freeze.json');old_source=next(x for x in frozen['sources'] if x['path']=='services/literal_review_v1.py')
    assert sha((ROOT/old_source['path']).read_bytes())==old_source['sha256'],'Frozen old parser changed'
    rows=[];projections=[];identities={}
    for n in SEQUENCES:
        inp,m,data,text=old_input(n);raw=strict_json(text);p=plan(inp)
        for kind in ('messages','responses'):
            file=OLD/'batch'/kind/f'{n:04d}.json';identities[str(file.relative_to(ROOT))]=sha(file.read_bytes())
        expected=public[n]['record']['validation_error']
        try:old_parse(raw,inp)
        except ContractError as exc:
            d=exc.diagnostic;assert d['constraint']==expected['constraint'] and d['field_path']==expected['field_path']
        else:raise AssertionError('Old refusal unexpectedly accepted')
        try:parse(raw,p)
        except ContractError as exc:new_errors=exc.diagnostic['errors']
        else:raise AssertionError('Old response silently converted')
        row=dict(sequence=n,task=m['task'],message_file_sha256=identities[str((OLD/'batch/messages'/f'{n:04d}.json').relative_to(ROOT))],
            response_file_sha256=identities[str((OLD/'batch/responses'/f'{n:04d}.json').relative_to(ROOT))],
            message_identity_matches_public=m['messages_sha256']==public[n]['send']['messages_sha256'],text_matches_public=text==public[n]['prediction_text'],
            old_first_error=d,old_diagnostic=independent_old_errors(raw,inp),new_contract='incompatible_not_a_prediction',new_contract_errors=new_errors)
        assert row['message_identity_matches_public'] and row['text_matches_public'];rows.append(row)
        if n in (10,15,37,42):
            def count(v,text):
                if isinstance(v,list):return sum(count(x,text) for x in v)
                if isinstance(v,dict):return sum(1 if k=='text' and x==text else count(x,text) for k,x in v.items())
                return 0
            required={q.evidence_id for d in inp.verification.literal_defects for q in d.sources}|{e for c in inp.answer.citations for e in c.evidence_ids}|{q.evidence_id for r in inp.verification.literal_reviews for q in r.sources}
            assert required<={e.evidence_id for e in p.sources.values()}
            projections.append(dict(sequence=n,old_message_characters=sum(len(x['content']) for x in m['messages']),
                new_message_characters=len(system())+len(json.dumps(p.payload,ensure_ascii=False)),
                counting='system+initial user Unicode chars, not tokens; equal complete source text fields, not paraphrases',
                old_allowed_evidence=len(inp.allowed_evidence),new_unique_sources=len(p.sources),necessary_sources_preserved=sorted(required),
                source_counts=[dict(evidence_id=e.evidence_id,text_sha256=sha(e.text.encode()),old_exact_body_text_fields=count(data,e.text),new_exact_body_text_fields=count(p.payload,e.text)) for e in p.sources.values()]))
            save(LOCAL/f'projection-{n:04d}.json',p.payload) # Real complete input stays private.
    assert all(sha((ROOT/path).read_bytes())==v for path,v in identities.items())
    save(PUBLIC/'historical-contract-audit.json',dict(origin='Unchanged old refusal replay and raw compatibility, not new model scores',rows=rows))
    save(PUBLIC/'projection-verification.json',dict(protocol=VERSION,real_project_model_requests=0,env_loaded=False,projections=projections))
    save(LOCAL/'old-identities.json',identities)
    return rows,projections


if __name__=='__main__':
    rows,projections=inspect_history()
    print(json.dumps(dict(old_refusals_reproduced=len(rows),raw_old_incompatible=len(rows),real_projections=len(projections),real_project_model_requests=0,env_loaded=False)))
