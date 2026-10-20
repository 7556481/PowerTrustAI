"""RC development inputs; unchanged v3 prompt, parser and bounded controller."""
import argparse
import json
from pathlib import Path
import subprocess

from evaluation import requirement_review_v3 as base
from evaluation import requirement_trial_v3 as trial
from evaluation.text_bound_review import canonical, sha, write

VERSION = base.VERSION
PROMPT = base.PROMPT
messages = base.messages
parse = base.parse


def model_input(card, example):
    evidence=[]
    for e in card['evidence']:
        row={k:e[k] for k in ('id','text','url','locator','text_basis')}
        row['evidence_id']=row.pop('id')
        row['scope_context']=[{k:s[k] for k in ('text','url','locator','text_basis')}
                              for s in e.get('scope_context',[])]
        evidence.append(row)
    return {'sample_id':example['id'],'question':card['question'],
            'requirements':[{'requirement_id':r['id'],
                             'description':r['model_visible_task_requirement']}
                            for r in card['requirements']],
            'answer':example['answer'],
            'answer_units':base.build_units(example['id'],example['answer']),
            'unit_version':base.UNIT_VERSION,'evidence':evidence}


def verify_items(directory):
    tasks=json.loads((directory/'input.json').read_text(encoding='utf-8'))
    assert [t['sample_id'] for t in tasks]==['RC-001-A','RC-001-B','RC-001-C-v2']


def prepare(root,output):
    card_path=root/'RC-001.owner-confirmed-v1.json'
    labels_path=root/'RC-001.synthetic-confirmed-v2.json'
    card=json.loads(card_path.read_text(encoding='utf-8'))
    labels=json.loads(labels_path.read_text(encoding='utf-8'))
    assert labels['status']=='owner_confirmed_revised_samples_before_execution'
    assert labels['parent_card_sha256']==sha(card_path.read_bytes())
    for e in card['evidence']:
        for s in [e]+e.get('scope_context',[]):
            path=root/'sources/RC-001'/s['local_text_file']
            assert sha(path.read_bytes())==s['local_file_sha256']
            assert path.read_text(encoding='utf-8').rstrip('\n')==s['text']
            assert sha(s['text'].encode())==s['text_sha256_utf8']
    tasks=[model_input(card,e) for e in labels['examples']]
    assert len(tasks)==3
    for t in tasks:
        assert ''.join(u['text'] for u in t['answer_units'])==t['answer']
        assert {r['requirement_id'] for r in t['requirements']}=={'R1','R2'}
        assert t['evidence'][1]['scope_context']
    output.mkdir(parents=True,exist_ok=False)
    write(output/'input.json',tasks);write(output/'expectations-private.json',labels)
    write(output/'messages-preview.json',[[{'role':m.role,'content':m.content}
        for m in messages(t)] for t in tasks])
    verify_items(output)
    files=[Path(__file__),Path(base.__file__),Path(trial.__file__),
           Path('evaluation/text_bound_review.py'),Path('evaluation/text_bound_review_v2.py'),
           Path('services/validation_diagnostics.py')]
    manifest={'version':VERSION,'input_builder':'rule-chain-input-v1',
        'status':'offline_prepared_no_execution','planned_items':3,'api_calls':0,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'working_tree_hashes':{str(p):sha(p.read_bytes()) for p in files},
        'card_sha256':sha(card_path.read_bytes()),
        'confirmed_labels_sha256':sha(labels_path.read_bytes()),
        'prompt_sha256':sha(PROMPT.encode()),'prompt_unchanged_v3':True}
    for filename,key in [('input.json','input_sha256'),
                         ('expectations-private.json','expectations_sha256'),
                         ('messages-preview.json','messages_preview_sha256')]:
        manifest[key]=sha((output/filename).read_bytes())
    write(output/'offline-manifest.json',manifest)
    return manifest


if __name__=='__main__':
    import sys
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('prepare','freeze','run'))
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();protocol=sys.modules[__name__]
    if args.action=='prepare':
        print(canonical(prepare(Path('data/evaluation_local/evidence-bound-v1'),args.output)))
    elif args.action=='freeze':
        verify_items(args.prepared)
        print(canonical(trial.freeze(args.prepared,args.output,protocol=protocol)))
    else:
        verify_items(args.output)
        trial.run(args.output,protocol=protocol)
