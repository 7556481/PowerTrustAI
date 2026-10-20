"""Explicit once-only RC-001 v4 recheck; reuse existing bounded trial controls."""
import argparse
import json
from pathlib import Path
import subprocess

from evaluation import premise_bound_review_v4 as protocol
from evaluation import requirement_trial_v3 as trial
from evaluation.text_bound_review import canonical, sha, write


def verify_items(directory):
    tasks=json.loads((directory/'input.json').read_text(encoding='utf-8'))
    assert [t['sample_id'] for t in tasks]==['RC-001-A','RC-001-B','RC-001-C-v2']
    for task in tasks:
        protocol.basis_catalog(task)
        assert task['evidence'][1]['scope_context']


def stage(offline, root, output):
    manifest=json.loads((offline/'offline-manifest.json').read_text(encoding='utf-8'))
    assert manifest['protocol']==protocol.VERSION
    assert manifest['prompt_sha256']==sha(protocol.PROMPT.encode())
    assert manifest['input_sha256']==sha((offline/'input.json').read_bytes())
    for path,h in manifest['working_tree_hashes'].items():
        assert sha(Path(path).read_bytes())==h
    card_path=root/'RC-001.offline-card-v2.json'
    labels_path=root/'RC-001.synthetic-confirmed-v2.json'
    assert sha(card_path.read_bytes())==manifest['card_sha256']
    assert sha(labels_path.read_bytes())==manifest['labels_sha256']
    card=json.loads(card_path.read_text(encoding='utf-8'))
    labels=json.loads(labels_path.read_text(encoding='utf-8'))
    tasks=json.loads((offline/'input.json').read_text(encoding='utf-8'))
    assert tasks==[protocol.model_input(card,e) for e in labels['examples']]
    verify_items(offline)
    previous=json.loads((root/'batch-rc001-v1/input.json').read_text(encoding='utf-8'))
    for old,new in zip(previous,tasks):
        for key in ('sample_id','question','answer','answer_units','evidence'):
            assert old[key]==new[key]
    output.mkdir(parents=True,exist_ok=False)
    write(output/'input.json',tasks)
    write(output/'expectations-private.json',labels)
    write(output/'messages-preview.json',[[{'role':m.role,'content':m.content}
        for m in protocol.messages(t)] for t in tasks])
    extra=[Path(__file__),Path(trial.__file__),Path('evaluation/text_bound_review.py'),
           Path('services/validation_diagnostics.py')]
    frozen=dict(manifest,version=protocol.VERSION,
        status='explicitly_authorized_recheck_preparation',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        working_tree_hashes=dict(manifest['working_tree_hashes'],
            **{str(p):sha(p.read_bytes()) for p in extra}),
        same_inputs_as_offline_v4=True,original_answers_evidence_labels_unchanged=True)
    for filename,key in [('input.json','input_sha256'),
                         ('expectations-private.json','expectations_sha256'),
                         ('messages-preview.json','messages_preview_sha256')]:
        frozen[key]=sha((output/filename).read_bytes())
    write(output/'offline-manifest.json',frozen)
    return frozen


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('stage','freeze','run'))
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='stage':
        print(canonical(stage(args.prepared,Path('data/evaluation_local/evidence-bound-v1'),args.output)))
    elif args.action=='freeze':
        verify_items(args.prepared)
        print(canonical(trial.freeze(args.prepared,args.output,protocol=protocol)))
    else:
        verify_items(args.output)
        trial.run(args.output,protocol=protocol)
