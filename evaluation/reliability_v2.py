"""Targeted offline diagnosis then one immutable v2 batch, no automatic reruns."""
import argparse
import asyncio
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
from uuid import uuid4
from evaluation.reliability_trial import ROOT,load,save_new,digest,live

SOURCE=ROOT/'data/retrieval_local/deepseek/reliability-v1-followup2'
DEFAULT=ROOT/'data/retrieval_local/deepseek/reliability-v2'

def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    old=load(SOURCE/'plan-v1.json');ledger=load(SOURCE/'all-request-ledger-v1.json')
    cases=[deepcopy(c) for c in old['cases'] if c['name'] in ('quantity','missing_engineering')]
    q=next(c for c in cases if c['name']=='quantity')
    # Existing successful generation is an explicitly frozen input, not a new API output.
    for c in cases:
        c['request']['task_id']=uuid4().hex
    variants=(('direct_count','There are four equipment ratings: stator winding rating, field current rating, terminal voltage rating, and active power output.'),
              ('refuted_count','The proposal describes four equipment ratings, but that description is inconsistent: stator winding rating, field current rating and terminal voltage rating are the three rating categories; active power output affects capability rather than constituting another rating.'),
              ('grouped_conversion','230 kV equals 230,000.0 V.'))
    for name,text in variants:
        row=deepcopy(q);row.update(name=name,component_variant=True,expected_development_checkpoints='Developer regression only; never sent as model labels.')
        row['request'].update(task_id=uuid4().hex,question='Review the supplied statement for factual and numerical consistency.',engineering_context={**row['request']['engineering_context'],'quantities':[]})
        row['frozen_answer'].update(answer_id=uuid4().hex,text=text,citations=[])
        cases.append(row)
    diagnosis=[]
    # Targeted inspection only; do not replay all 135 calls.
    inputs=[(p,load(p)['input']) for p in (SOURCE/'actual-inputs-v1').glob('agent-input-verification-*.json')]
    from agents.contracts import EvidenceVerificationInput
    from agents import verification_contract_v9 as joint
    from agents.verification_contract_v9_scoped import model_wire
    from evaluation.archive_replay import restore
    for row in ledger:
        if row['batch']!=SOURCE.name or not any(a['scenario'] in ('quantity','missing_engineering') for a in row['association']):continue
        record=row['record'];path=Path(record['diagnostic_path']);raw=load(path)
        entry={'association':row['association'],'response_path':str(path),'sha256':digest(path),
               'prompt_version':raw['prompt_version'],'correction':raw['correction'],'historical_validation':raw['validation_error'],
               'historical_state_unchanged':True,'candidate_catalog_path':record.get('candidate_catalog_path')}
        if raw['prompt_version'].startswith('evidence-verification-v9.2'):
            payload=load(record['candidate_catalog_path']);match=next(((p,v) for p,v in inputs if v['answer']['answer_id']==payload['answer']['answer_id'] and v['answer']['version']==payload['answer']['version']),None)
            if match:
                inp=restore(match[1],EvidenceVerificationInput);scopes=joint.catalog(inp,'evidence-verification-output-v9.2');wire,_=model_wire(inp)
                response=json.loads(raw['response_text'])
                try:
                    if payload.get('original_citation'):
                        index=payload['original_citation']['citation_index'];wire['citation_reviews'][index]=response['citation_reviews'][0]
                    else:wire['findings']=response['findings']
                    joint.parse(wire,inp,scopes,prompt_version=raw['prompt_version']);entry['offline_replay']='structurally_valid_only'
                except Exception as exc:entry.update(offline_replay='failed',replay_error=getattr(exc,'diagnostic',{'type':type(exc).__name__,'reason':str(exc)}))
                entry['actual_input_path']=str(match[0])
            else:entry['offline_replay']='not_replayed_missing_matching_actual_input'
        else:entry['offline_replay']='inspected_not_replayed_other_stage'
        diagnosis.append(entry)
    save_new(out/'targeted-diagnosis-v2.json',diagnosis)
    files=set(old['source_sha256'])
    files.update(str(ROOT/p) for p in ('services/claim_obligations.py','services/review_fidelity.py','tools/scalar_numbers.py',
        'evaluation/reliability_v2.py','tests/test_review_reliability_v2.py','tests/test_scalar_numbers_v2.py'))
    # Also protect original artifacts used here; old statuses/results are never edited.
    history={str(p):digest(p) for p in SOURCE.rglob('*') if p.is_file()}
    plan={**old,'version':'review-reliability-v2','cases':cases,'global_model_cap':60,
        'claim_protocol':7,'verification_protocol':11,'domain_protocol':4,'unit_tool_version':'scalar-si-conversion-v2',
        'max_revision_citations':6,'each_revision_and_full_rereview_worst':14,
        'initial_worst_requests':32,'all_cases_full_worst':60,
        'budget_policy':'Two initial reviews <=7 each; three no-citation variants <=6 each; two repairs <=14 each (revision2 + full extraction2/domain2/independent1/citations<=6/one correction1). Total60. No repeated scene. No changes within batch.',
        'versions':{'claim':'atomic-claims-v7','verification':'evidence-verification-output-v9.3','domain':'power-domain-review-output-v3.1',
            'generation':3,'revision':2,'rules':'power-demo-rules-v1.1','tool':'scalar-si-conversion-v2'},
        'source_sha256':{p:digest(p) for p in sorted(files)},'historical_sha256':history}
    assert all(len((c.get('frozen_answer') or load(c['reuse_generation_json'])['answer'])['citations'])<=1 for c in cases)
    save_new(out/'plan-v1.json',plan)
    print(json.dumps({'targeted_records':len(diagnosis),'worst_requests':60,'plan':str(out/'plan-v1.json')}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','live'));parser.add_argument('--output-dir',default=str(DEFAULT));args=parser.parse_args()
    if args.phase=='prepare':return prepare(args.output_dir)
    from harness.deepseek_trial import load_project_env
    from model_adapter.contracts import ModelSettings
    from model_adapter.deepseek import create_adapter
    load_project_env();model=os.environ.get('DEEPSEEK_MODEL_ID')
    if not model:raise ValueError('Explicit configured model required')
    settings=ModelSettings(model,90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')
    adapter=create_adapter(settings);domain=create_adapter(settings)
    try:asyncio.run(live(args.output_dir,adapter,domain,settings))
    finally:adapter.close();domain.close()

if __name__=='__main__':main()
