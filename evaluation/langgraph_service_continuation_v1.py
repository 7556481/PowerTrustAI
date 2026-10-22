"""New authorization for only the five unsent items; old batch stays immutable.

Reuse the fixed collector and normal Factory/worker/API, never resume its attempt.
"""
import argparse
import hashlib
import os
from contextlib import ExitStack
from unittest.mock import patch
from evaluation import langgraph_service_trial_v1 as trial

ROOT=trial.ROOT
PUBLIC=ROOT/'docs/evaluation/langgraph-service-continuation-v1'
LOCAL=ROOT/'data/evaluation_local/langgraph-service-continuation-v1/batch-v1'
PRIVATE=ROOT/'data/retrieval_local/langgraph-service-continuation-v1/batch-v1'
OLD=ROOT/'data/evaluation_local/langgraph-service-integration-v1/batch-v1'
OLD_FREEZE=ROOT/'docs/evaluation/langgraph-service-integration-v1/execution-freeze-v1.json'
ORDER=trial.ORDER[1:]
ENGINEERING={
    'evaluation/langgraph_service_trial_v1.py',
    'tests/test_langgraph_service_trial_v1.py',
    'tests/test_langgraph_service_integration_v1.py',
    'backend/static/app.js',
}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def compatibility(old,c,manifest):
    """Exact configuration and production sources, with explicit engineering deltas."""
    if trial.config_identity(c)!=old['configuration']:raise ValueError('Business configuration changed')
    if manifest!=old['manifest']:raise ValueError('Agent/knowledge/model/prompt manifest changed')
    if os.environ.get('DEEPSEEK_MODEL_ID')!=old['model_id']:raise ValueError('Model changed')
    if [{ 'id':i,'task_id':t,'execution_path':p,'payload_sha256':trial.sha(trial.tasks()[t])} for i,t,p in ORDER]!=old['order'][1:]:
        raise ValueError('Only original five unsent inputs allowed')
    changes=[]
    for f in old['bound_files']:
        current=digest(ROOT/f['path'])
        if current!=f['sha256']:
            if f['path'] not in ENGINEERING:raise ValueError('Unapproved production source change: '+f['path'])
            changes.append({**f,'current_sha256':current})
    return changes

def prepare():
    if LOCAL.exists() or (PUBLIC/'execution-freeze-v1.json').exists():raise ValueError('Fresh continuation only')
    old=trial.read(OLD_FREEZE)
    summary=trial.read(OLD/'summary.json')
    if [b['status'] for b in summary['branches']]!=['execution_failed']+['unexecuted']*5:
        raise ValueError('Old unsent set changed')
    reference=OLD/'LSI-01-S/recovered-readonly-after-stop.json'
    recovered=trial.read(reference)
    if recovered['result']['execution_issues'] or recovered['result']['state']!='completed':
        raise ValueError('First historical service result not complete')
    c=trial.ServiceConfig.from_environment();factory=trial.ComponentFactory(c)
    manifest=factory.manifest(factory.preflight())
    changes=compatibility(old,c,manifest)
    paths={ROOT/f['path'] for f in old['bound_files']}
    paths.update((__file__,ROOT/'tests/test_langgraph_service_continuation_v1.py'))
    from pathlib import Path
    frozen={**old,'version':'langgraph-service-continuation-v1',
        'source_base_commit':'2c75ba038011c07a6bb92a6b7bd7b19f17dfc5a5',
        'authorization':'User authorized only five previously unsent service items; no first-item resend, no retry or resume.',
        'order':old['order'][1:],'manifest':manifest,
        'linked_old_batch':{'freeze_sha256':digest(OLD_FREEZE),'summary_sha256':digest(OLD/'summary.json'),
            'reference_run_id':'a83c9966ad034532954127b6958b075b','reference_sha256':digest(reference)},
        'engineering_changes':changes,
        'bound_files':[{'path':Path(p).relative_to(ROOT).as_posix(),'sha256':digest(Path(p))} for p in sorted(paths,key=str)]}
    trial.write(PUBLIC/'execution-freeze-v1.json',frozen)
    trial.write(LOCAL/'freeze.json',frozen);trial.write(LOCAL/'payloads.json',trial.tasks())
    print('Only original five unsent service runs frozen; business identities unchanged',flush=True)

def execute():
    f=trial.read(PUBLIC/'execution-freeze-v1.json')
    if f['order']!=trial.read(OLD_FREEZE)['order'][1:]:raise ValueError('Wrong remaining order')
    for path,key in ((OLD_FREEZE,'freeze_sha256'),(OLD/'summary.json','summary_sha256'),
                     (OLD/'LSI-01-S/recovered-readonly-after-stop.json','reference_sha256')):
        if digest(path)!=f['linked_old_batch'][key]:raise ValueError('Old record changed')
    with ExitStack() as s:
        for name,value in (('PUBLIC',PUBLIC),('LOCAL',LOCAL),('PRIVATE',PRIVATE),('ORDER',ORDER)):
            s.enter_context(patch.object(trial,name,value))
        trial.execute()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','execute'));a=p.parse_args()
    prepare() if a.action=='prepare' else execute()
