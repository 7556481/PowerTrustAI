"""One confirmed SW-001-D trial, unchanged scoped prompt and source inputs."""
import argparse
import json
from pathlib import Path
import subprocess

from evaluation import scoped_requirement_review_v1 as protocol
from evaluation import requirement_trial_v3 as trial
from evaluation.text_bound_review import canonical, sha, write


def prepare(root, output):
    card_path = root/'SW-001.owner-confirmed-v1.json'
    label_path = root/'SW-001.synonym-merged-owner-confirmed-v1.json'
    card = json.loads(card_path.read_text(encoding='utf-8'))
    labels = json.loads(label_path.read_text(encoding='utf-8'))
    assert labels['status'] == 'owner_confirmed_synonym_development_labels'
    assert labels['parent_card_sha256'] == sha(card_path.read_bytes())
    assert labels['sample_id'] == 'SW-001-D'
    source = json.loads((root/card['source_manifest']).read_text(encoding='utf-8'))
    task = protocol.model_input(card, {'id':labels['sample_id'], 'answer':labels['answer']}, source)
    prior = root/'batch-sw001-scoped-v1'
    old_freeze = json.loads((prior/'freeze.json').read_text(encoding='utf-8'))
    assert sha(protocol.PROMPT.encode()) == old_freeze['prompt_sha256']
    assert sha((prior/'input.json').read_bytes()) == old_freeze['input_sha256']
    original = json.loads((prior/'input.json').read_text(encoding='utf-8'))[0]
    changed = {'sample_id','answer','answer_units'}
    assert {k:v for k,v in task.items() if k not in changed} == {
        k:v for k,v in original.items() if k not in changed}
    assert ''.join(u['text'] for u in task['answer_units']) == labels['answer']
    output.mkdir(parents=True, exist_ok=False)
    write(output/'input.json', [task])
    write(output/'expectations-private.json', labels)
    write(output/'messages-preview.json', [[{'role':m.role,'content':m.content}
                                           for m in protocol.messages(task)]])
    paths = [Path(__file__), Path(protocol.__file__), Path(protocol.base.__file__),
             Path(trial.__file__), Path('evaluation/text_bound_review_v2.py'),
             Path('evaluation/text_bound_review.py'), Path('services/validation_diagnostics.py')]
    manifest = {'version':protocol.VERSION,'planned_items':1,'api_calls':0,
                'status':'offline_prepared_no_execution',
                'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'working_tree_hashes':{str(p):sha(p.read_bytes()) for p in paths},
                'card_sha256':sha(card_path.read_bytes()),
                'confirmed_labels_sha256':sha(label_path.read_bytes()),
                'prompt_sha256':sha(protocol.PROMPT.encode()),
                'same_prompt_and_nonanswer_inputs_as_prior_batch':True}
    for filename,key in [('input.json','input_sha256'),
                         ('expectations-private.json','expectations_sha256'),
                         ('messages-preview.json','messages_preview_sha256')]:
        manifest[key] = sha((output/filename).read_bytes())
    write(output/'offline-manifest.json',manifest)
    return manifest


def verify_single(output):
    tasks = json.loads((output/'input.json').read_text(encoding='utf-8'))
    assert len(tasks)==1 and tasks[0]['sample_id']=='SW-001-D'


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('prepare','freeze','run'))
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='prepare':
        print(canonical(prepare(Path('data/evaluation_local/evidence-bound-v1'),args.output)))
    elif args.action=='freeze':
        verify_single(args.prepared)
        print(canonical(trial.freeze(args.prepared,args.output,protocol=protocol,expected_items=1)))
    else:
        verify_single(args.output)
        trial.run(args.output,protocol=protocol,expected_items=1)
