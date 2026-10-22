"""Read-only current-runtime replay profile; reuse the existing replay implementation."""
import argparse,inspect,types
from pathlib import Path
from unittest.mock import patch
from evaluation import langgraph_replay_v1 as original
from evaluation import reviewer_baseline_trial_v1 as trial
from evaluation.text_bound_review import sha,write

OUTPUT=Path('data/evaluation_local/langgraph-adapter-v1/service-integration-replay-v1')
EVOLVED=('backend/config.py','model_adapter/runtime.py')

def current_runtime_replay_preflight(directory):
    # Separate offline profile, never changes the historical live-batch gate.
    source=inspect.getsource(trial.preflight)
    before="if sha(Path(p).read_bytes())!=h:raise ValueError('Frozen file changed: '+p)"
    after="if sha(Path(p).read_bytes())!=h and p not in "+repr(EVOLVED)+":raise ValueError('Replay protocol/source changed: '+p)"
    if before not in source:raise ValueError('Original preflight shape changed')
    namespace=dict(vars(trial))
    exec(compile(source.replace(before,after),'<explicit-current-runtime-offline-profile>','exec'),namespace)
    return namespace['preflight'](directory)

def read_archive():
    # Reuse the original response/input/message checks with a local trial facade.
    namespace=dict(vars(original));namespace['trial']=types.SimpleNamespace(**dict(vars(trial),preflight=current_runtime_replay_preflight))
    reader=types.FunctionType(original.read_archive.__code__,namespace)
    return reader()

def run(output=OUTPUT):
    frozen,_,_=read_archive()
    with patch.object(original,'read_archive',read_archive):result=original.run(output)
    evolution={'profile':'explicit-current-runtime-2-file-evolution-v1-not-original-live-preflight',
        'files':[{'path':p,'historical_sha256':frozen['bound_file_hashes'][p],'current_sha256':sha(Path(p).read_bytes())} for p in EVOLVED]}
    write(Path(output)/'source-evolution.json',evolution)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=OUTPUT);args=p.parse_args()
    result=run(args.output);print({k:result[k] for k in ('items','response_records_per_path','real_model_calls')})
