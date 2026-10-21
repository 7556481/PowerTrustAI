"""Offline allowlisted inputs; never reads evaluator-only files or creates a client."""
import json
from pathlib import Path

from evaluation import premise_bound_review_v5 as protocol
from evaluation.text_bound_review import write, sha
from evaluation.text_bound_review_v2 import build_units, UNIT_VERSION

CARD_IDS = ('H-EIA-001', 'H-NRC-001')


def build_task(card, answer):
    if card['card_id'] not in CARD_IDS or answer['question_id'] != card['card_id']:
        raise ValueError('Unrecognized question binding')
    if set(answer) != {'question_id', 'candidate_id', 'answer'}:
        raise ValueError('Only candidate identity and answer fields allowed')
    if card['scenario_premises']:
        raise ValueError('These cards have no hypothetical premises')
    e = card['evidence']
    context = []
    # NRC full paragraph is definition + two context sentences. No reference
    # decomposition, expected labels or case-specific rationale is consulted.
    if e['paragraph_context'].startswith(e['selected_definition']):
        tail=e['paragraph_context'][len(e['selected_definition']):].strip()
        if tail:
            context=[{'text':tail,'url':e['url'],'locator':e['locator'],
                      'text_basis':'saved_official_paragraph_context'}]
    task={'sample_id':answer['candidate_id'],'question':card['question'],
          'requirements':[{'requirement_id':r['id'],'description':r['description']}
                          for r in card['requirements']],
          'scenario_premises':[], 'answer':answer['answer'],
          'answer_units':build_units(answer['candidate_id'],answer['answer']),
          'unit_version':UNIT_VERSION,
          'evidence':[{'evidence_id':card['source_group']+'-X1',
                       'text':e['selected_definition'],'url':e['url'],
                       'locator':{'title':e['title'],'version':e['version'],
                                  'source_sha256':e['snapshot_sha256'],
                                  'description':e['locator']},
                       'text_basis':'confirmed_official_excerpt_whitespace_normalized',
                       'scope_context':context}]}
    protocol.basis_catalog(task)
    return task


def prepare(cards_dir, answers_file, output):
    # Explicit three-file read allowlist, not a recursive directory reader.
    card_paths=[cards_dir/(cid+'.json') for cid in CARD_IDS]
    cards={cid:json.loads(path.read_text(encoding='utf-8'))
           for cid,path in zip(CARD_IDS,card_paths)}
    answers=json.loads(answers_file.read_text(encoding='utf-8'))['answers']
    if len(answers)!=8 or len({a['candidate_id'] for a in answers})!=8:
        raise ValueError('Eight distinct candidate answers required')
    tasks=[build_task(cards[a['question_id']],a) for a in answers]
    output.mkdir(parents=True,exist_ok=False)
    write(output/'input-preview.json',tasks)
    write(output/'messages-preview.json',[[{'role':m.role,'content':m.content}
          for m in protocol.messages(t)] for t in tasks])
    write(output/'preparation-manifest.json',{
        'status':'offline_preview_not_execution_or_order_freeze','api_calls':0,
        'read_allowlist':{str(p):sha(p.read_bytes()) for p in [*card_paths,answers_file]},
        'builder_sha256':sha(Path(__file__).read_bytes()),
        'prompt_sha256':sha(protocol.PROMPT.encode()),
        'outputs':{p.name:sha(p.read_bytes()) for p in output.iterdir()},
        'reference_labels_loaded':False,'reference_units_loaded':False,
        'mechanical_answer_units_only':True})
    return tasks
