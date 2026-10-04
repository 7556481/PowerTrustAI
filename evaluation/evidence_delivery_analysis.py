"""Bounded offline paired-delivery diagnostics; no label or historical edits."""
import argparse
from collections import Counter
import json
from pathlib import Path
from evaluation.evidence_delivery_trial import load,save_new
from evaluation.evidence_delivery_report import stage_complete
from harness.evidence_review_demo import restore_answer
from services.claim_extractor import parse_extraction
from services.structured_model import strict_json


def analyze(out,version='v2'):
    out=Path(out);summary=load(out/'summary.json');audit=load(out/'offline-audit.json');replays=[];comparisons=[]
    for path in sorted(out.glob('*-initial.json'))+sorted(out.glob('*-rereview.json')):
        value=load(path)
        for record in value['model_records']:
            if record['prompt_version']!='atomic-claims-v4-explicit-components':continue
            diag=load(record['diagnostic_path']);result={'stage':path.stem,'correction':record['correction'],
                'historical_output_status':record['output_status'],'response_path':record['diagnostic_path']}
            try:
                extracted=parse_extraction(strict_json(diag['response_text']),restore_answer(value['answer']),require_components=True)
                result.update(replayed='valid_structure',claims=len(extracted.claims))
            except Exception as exc:
                diagnostic=getattr(exc,'diagnostic',None)
                if diagnostic is None:raise
                result.update(replayed='invalid_structure',diagnostic=diagnostic)
            assert result['replayed']==record['output_status']
            if record.get('validation_error'):
                assert result['diagnostic']['field_path']==record['validation_error']['field_path']
                assert result['diagnostic']['constraint']==record['validation_error']['constraint']
            replays.append(result)
    scenarios=list(dict.fromkeys(r['scenario'] for r in summary['runs']))
    for name in scenarios:
        runs={r.get('mode'):r for r in summary['runs'] if r['scenario']==name}
        if len(runs)!=2:continue
        left,right=runs['storage_order'],runs['cross_page_next_first']
        row={'scenario':name,'same_frozen_answer':left['frozen_answer']==right['frozen_answer'],
            'same_initial_extraction':bool(left['initial'].get('extraction_output') and left['initial']['extraction_output']==right['initial'].get('extraction_output')),
            'initial_delivery':[],'initial_complete':[stage_complete(left['initial']),stage_complete(right['initial'])],
            'loop_complete':[bool(left.get('loop_execution_complete')),bool(right.get('loop_execution_complete'))]}
        for purpose in ('verification','domain_review'):
            selections=[]
            for r in (left,right):
                selections.append(next((x for x in r['initial']['retrieval_records'] if x['purpose']==purpose),None))
            a,b=selections
            if a and b:row['initial_delivery'].append({'purpose':purpose,'query_equal':a['query']==b['query'],
                'core_equal':a['core_evidence_ids']==b['core_evidence_ids'],'context_equal':a['context_evidence_ids']==b['context_evidence_ids'],
                'context_set_equal':set(a['context_evidence_ids'])==set(b['context_evidence_ids']),
                'baseline_context':a['context_evidence_ids'],'experimental_context':b['context_evidence_ids'],
                'baseline_omissions':a['context_omissions'],'experimental_omissions':b['context_omissions']})
        comparisons.append(row)
    result={'scope':'DEVELOPMENT OFFLINE REPLAY; NO SEMANTIC GOLD OR NEW LABELS',
        'claim_response_replays':replays,'paired_comparisons':comparisons,
        'error_categories':dict(Counter((e['prompt_version']+' / '+e['constraint']) for e in audit['errors'])),
        'initial_complete_by_arm':{m:sum(stage_complete(r.get('initial')) for r in summary['runs'] if r.get('mode')==m) for m in ('storage_order','cross_page_next_first')},
        'loop_complete_by_arm':{m:sum(bool(r.get('loop_execution_complete')) for r in summary['runs'] if r.get('mode')==m) for m in ('storage_order','cross_page_next_first')}}
    save_new(out/('paired-analysis-'+version+'.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('claim_response_replays','paired_comparisons')},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);parser.add_argument('--version',default='v2');a=parser.parse_args();analyze(a.output_dir,a.version)
