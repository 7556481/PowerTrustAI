"""Small fixed plan over the existing freezer, run_fixed and isolated run library."""
import json,re,hashlib
from collections import Counter
from dataclasses import replace
from evaluation import production_review_v2 as base
from evaluation.answer_review_net_benefit_v1 import batch as shared_batch
from evaluation.public_review_validation_trial_v1 import read,write
from backend.config import ROOT
from services.review_simple_v1 import PROMPT,CONTRACT

PUBLIC=ROOT/'docs/evaluation/review-contract-simple-v1'
LOCAL=ROOT/'data/retrieval_local/review-contract-simple-v1'
request=base.request
fixed_input=base.fixed_input
task_runner=base.task_runner


def materials():
    # Reuse frozen A verbatim, not a regenerated approximation or changed labels.
    old=read(ROOT/'data/retrieval_local/production-review-net-benefit-v2/materials.json')
    result={**old,'version':'review-contract-simple-v1-materials','B':[old['B'][i] for i in (0,1,2,5)]}
    result['allowed']='Equivalent source-supported paraphrases; no exact wording score. Four natural questions retain all pre-fixed requirements.'
    result['unjudgeable_boundary']='Source silence is insufficient, not opposite truth. Unknown plant inputs cannot establish capacity or guarantee. Runtime syntax failure is execution, not semantic insufficiency.'
    result['stop_contract_recurrence']='Two consecutive candidate cases with the same final structural constraint/path, excluding ordinary semantic judgments, stop later sends with exact diagnostics. No midbatch fix or replay.'
    return result


def order():
    return [dict(id=r['id'].replace('scope_v2','simple_v1'),input={**r['input'],'variant':r['input']['variant'].replace('scope_v2','simple_v1')}) for r in base.order() if r['input']['line']=='A' or r['input']['case']<4]


def variants(c,v):return replace(c,fact_review_contract=v)


class ContractRecurrence:
    """Bounded stop evidence, not a semantic classifier or a second controller."""
    def __init__(self):self.previous=None
    def __call__(self,spec,raw):
        if spec['variant']!='simple_v1':return None
        # A bad intermediate attempt corrected successfully does not trigger this stop.
        if not raw.get('execution_issues'):self.previous=None;return None
        errors=[]
        for r in raw.get('model_records',[]):
            if r['prompt_version']!=PROMPT or not r.get('validation_error'):continue
            d=r['validation_error'];errors.extend(d.get('errors',[d]))
        keys={(e['constraint'],re.sub(r'\[\d+\]','[]',e['field_path'])) for e in errors if e.get('stage')==CONTRACT}
        current=dict(case=(spec['line'],spec['case']),constraints=keys,diagnostics=errors)
        prior=self.previous;self.previous=current
        repeated=keys.intersection(prior['constraints']) if prior and prior['case']!=current['case'] else set()
        if not repeated:return None
        return dict(component='evidence_verification',code='SERVICE_EXECUTION_FAILED',message='Frozen candidate contract repeatedly fails across consecutive cases; stop all later sends, no paid probing.',contract_stop_evidence=dict(previous_case=list(prior['case']),current_case=list(current['case']),repeated_constraints=[list(x) for x in sorted(repeated)],previous_diagnostics=prior['diagnostics'],current_diagnostics=errors))


async def batch(*args,**kwargs):
    return await shared_batch(*args,**kwargs,result_guard=ContractRecurrence())


def freeze():
    return base.freeze(public=PUBLIC,local=LOCAL,materials_factory=materials,order_factory=order,version='review-contract-simple-v1')


def execute():
    return base.execute(public=PUBLIC,local=LOCAL,order_factory=order,variants_factory=variants,result_guard=ContractRecurrence())


def audit_previous():
    """Read every prior raw response/message; never translate it into new success."""
    p=ROOT/'data/retrieval_local/production-review-net-benefit-v2/batch';s=read(p/'summary.json');entries=[];identities=[]
    for folder in ('messages','responses'):
        for f in sorted((p/folder).glob('*.json')):identities.append(dict(path=f.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    for control in s['control']:
        rid=control['accepted']['run_id'];out=s['outputs'][rid];sends=[r for r in s['send_log'] if r['run_id']==rid]
        records=sorted(out.get('model_records',[]),key=lambda r:r['call_number']);assert len(sends)==len(records)
        for sent,record in zip(sends,records):
            assert sent['prompt_version']==record['prompt_version'] and sent['correction']==record['correction']
            n=sent['sequence'];msg=read(p/'messages'/f'{n:04d}.json');response=read(p/'responses'/f'{n:04d}.json')
            try:json.loads(response['text']);json_valid=True
            except ValueError:json_valid=False
            d=record.get('validation_error');constraints=sorted({x['constraint'] for x in d.get('errors',[d])}) if d else []
            mechanisms=[]
            if 'literal_local_subject_condition_conclusion_required' in constraints:mechanisms.append('model_literal_retranscription')
            if not json_valid:mechanisms.append('json_serialization')
            if any(c in ('condition_id_must_be_selected_in_this_scope','known_source_kind_required','condition_must_be_in_evaluated_answer_body','truth_existence_transcription_targets_must_not_be_interchanged','explicit_actual_task_scope_required') for c in constraints):mechanisms.append('basis_or_scope_selection')
            if constraints and not mechanisms:mechanisms.append('other_contract_obligation')
            entries.append(dict(id=control['case_id'],sequence=n,call=record['call_number'],valid_structure=not bool(d),constraints=constraints,mechanisms=mechanisms,primary_mechanism=mechanisms[0] if mechanisms else None,diagnostic=d,message_sha256=hashlib.sha256((p/'messages'/f'{n:04d}.json').read_bytes()).hexdigest(),response_sha256=hashlib.sha256((p/'responses'/f'{n:04d}.json').read_bytes()).hexdigest()))
    invalid=[x for x in entries if not x['valid_structure']];assert len(invalid)==47
    oldeval=read(ROOT/'docs/evaluation/production-review-net-benefit-v2/evaluation.json')
    report=dict(response_count=len(entries),invalid_request_count=len(invalid),primary_mechanism_request_counts=dict(Counter(x['primary_mechanism'] for x in invalid)),mechanism_request_counts=dict(Counter(k for x in invalid for k in set(x['mechanisms']))),root_constraint_request_counts=dict(Counter(k for x in invalid for k in set(x['constraints']))),all_requests=entries,immutable_files=identities,legal_peer_and_semantic_results=oldeval['fixed_units'],projection_defect=oldeval['postrun_projection_replay'],compatibility='Old scope_v2 wire requires literal fields and cannot be replayed as simple_v1 model output. No old output converted into a claimed new success. New synthetic tests only exercise proven mechanisms.',prompt_consistency='Old initial/example/parser all required literal fields; repeated transcription is a contract burden, not evidence of missing instructions. Old required=true/no-condition/preserved mapping is a confirmed incompatible projection. Old prompts and actual corrections inspected and immutable. Support mistakes only scored from legal judgments, never invalid replies.')
    PUBLIC.mkdir(parents=True,exist_ok=True)
    (PUBLIC/'prior-mechanisms.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['audit']:audit_previous()
    elif sys.argv[1:]==['freeze']:freeze()
    elif sys.argv[1:]==['execute']:execute()
    else:raise SystemExit('audit | freeze | execute')
