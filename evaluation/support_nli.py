"""Versioned, development-only NLI comparison; never imported by production."""
import argparse
import json
from pathlib import Path
import random
import time

from evaluation.support_dataset import validate_sample, task_key
from evaluation.support_training import check_partition, classify_metrics

LEGACY_VERSION = 'support-nli-semantic-pair-v1'
VERSION = 'support-nli-document-body-pair-v2'
NLI_TO_SUPPORT = {'entailment': 'supported', 'contradiction': 'contradicted',
                  'neutral': 'insufficient_evidence'}


def semantic_pair_v1(sample):
    """Label-blind full delivery, with administrative scope visibly separate."""
    validate_sample(sample)
    task = sample['task']; claim = task['claim']
    if task['task_type'] not in ('factual_support', 'original_citation_support'):
        raise ValueError('NLI experiment cannot evaluate engineering execution')
    if claim.get('assertion_role') not in ('asserted', 'asserted_synthetic_variant'):
        raise ValueError('Unimplemented stance requires explicit new adapter, not silent assertion')
    if task['other_basis']:
        raise ValueError('Non-document bases require a separately audited adapter')
    if not task['evidence']:
        raise ValueError('No delivered evidence')
    bodies = []
    admin = []
    for evidence in task['evidence']:
        bodies.append(evidence['text'])  # Whole delivered text, no label-based selection.
        metadata = evidence['metadata']
        provenance = metadata.get('provenance', {})
        title = provenance.get('document_title')
        if title and title not in admin:
            admin.append('Source attribution recorded by the index: ' + title)
        for scope in metadata.get('applicability') or []:
            statement = 'Index applicability declaration: ' + scope
            if statement not in admin: admin.append(statement)
    premise = '\n\n'.join(bodies)
    if admin:
        premise += '\n\n[Index-maintenance context; these declarations are not official document prose.]\n' + '\n'.join(admin)
    hypothesis = claim['proposition']
    if claim.get('text') and claim['text'] != claim['proposition']:
        hypothesis += '\nOriginal claim wording: ' + claim['text']
    qualifiers = claim.get('qualifiers') or []
    if qualifiers: hypothesis += '\nNecessary task qualifiers: ' + '; '.join(qualifiers)
    if claim.get('scope'):
        hypothesis += '\nTask applicability scope (not a quotation from the document): ' + '; '.join(claim['scope'])
    return {'version': LEGACY_VERSION, 'premise': premise, 'hypothesis': hypothesis,
            'document_bodies': bodies, 'index_declarations': admin,
            'assertion_role': claim['assertion_role'], 'necessary_qualifiers': qualifiers,
            'scope': claim.get('scope', []), 'label_used_for_input': False}


def semantic_pair(sample):
    """Body-only NLI; administrative context is retained outside model premise.

    Claim qualifiers and applicability remain in the hypothesis. Index fields
    describe the delivery, never technical evidence or an official quotation.
    """
    claim = sample['task']['claim']
    target = claim.get('basis_target')
    review = sample.get('quality_review', {})
    if target not in ('literature', 'document_body'):
        raise ValueError('Explicit document-body basis target required; route metadata separately')
    if review.get('disposition') in ('auxiliary_only', 'hold'):
        raise ValueError('Auxiliary attribution and hold tasks cannot enter body NLI')
    if claim.get('category') == 'index-versus-body':
        raise ValueError('Source attribution review requires a separate route')
    pair = semantic_pair_v1(sample)
    pair['version'] = VERSION
    pair['premise'] = '\n\n'.join(pair['document_bodies'])
    pair['document_context'] = {
        'type': 'administrative_source_attribution_and_index_applicability',
        'declarations': pair['index_declarations'],
        'is_official_technical_prose': False,
        'used_as_model_premise': False,
        'sources': [
            {'document_title': e['metadata'].get('provenance', {}).get('document_title'),
             'publisher': e['metadata'].get('provenance', {}).get('publisher'),
             'index_applicability': list(e['metadata'].get('applicability') or []),
             'type': 'index_record_not_technical_prose'}
            for e in sample['task']['evidence']
        ],
    }
    pair['basis_target'] = 'document_body'
    return pair


def output_mapping(config):
    labels = {int(k): v.lower() for k, v in config.id2label.items()}
    if set(labels.values()) != set(NLI_TO_SUPPORT) or set(labels) != {0, 1, 2}:
        raise ValueError('Actual pretrained NLI output order must be explicit')
    return {i: NLI_TO_SUPPORT[label] for i, label in labels.items()}


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


class Resources:
    def __init__(self):
        import psutil, threading
        self.process = psutil.Process(); self.peak = self.process.memory_info().rss
        self.stop_event = threading.Event()
        def sample():
            while not self.stop_event.wait(.05): self.sample()
        self.thread = threading.Thread(target=sample, daemon=True); self.thread.start()
    def sample(self): self.peak = max(self.peak, self.process.memory_info().rss)
    def close(self): self.sample(); self.stop_event.set(); self.thread.join()


def load_model(directory):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    model, info = AutoModelForSequenceClassification.from_pretrained(directory,
        local_files_only=True, output_loading_info=True, attn_implementation='eager')
    if info['missing_keys'] or info['mismatched_keys'] or info['error_msgs']:
        raise ValueError('Checkpoint must load completely without random initialization: ' + str(info))
    mapping = output_mapping(model.config)
    limit = min(tokenizer.model_max_length, model.config.max_position_embeddings - model.config.pad_token_id - 1)
    return model.to('cpu'), tokenizer, mapping, limit, time.perf_counter()-started, info


def prepare(samples, tokenizer, limit):
    encoded = {}; records = []; excluded = []
    for sample in samples:
        pair = semantic_pair(sample)
        tensors = tokenizer(pair['premise'], pair['hypothesis'], truncation=False, return_tensors='pt')
        length = tensors['input_ids'].shape[1]
        record = dict(sample_id=sample['sample_id'], split=sample['split'], group_id=sample['group_id'],
                      task_sha256=task_key(sample['task']), semantic_input=pair, tokens=length, limit=limit,
                      treatment='full_input' if length <= limit else 'excluded_over_context_no_truncation')
        records.append(record)
        if length > limit: excluded.append(record)
        else: encoded[sample['sample_id']] = tensors
    return encoded, records, excluded


def predict(model, samples, encoded, mapping, resources):
    import torch
    model.eval(); started = time.perf_counter(); predictions = []
    with torch.inference_mode():
        for sample in samples:
            key = sample['sample_id']
            if key not in encoded: continue
            tick = time.perf_counter(); logits = model(**encoded[key]).logits[0]
            if not torch.isfinite(logits).all(): raise ValueError('Nonfinite logits')
            predictions.append(dict(sample_id=key, label=mapping[int(logits.argmax())], status='complete',
                                    basis_ids=[], logits=logits.tolist(), seconds=time.perf_counter()-tick))
            resources.sample()
    return predictions, time.perf_counter()-started


def evaluate(samples, predictions):
    result = classify_metrics(samples, predictions)
    byid = {p['sample_id']: p for p in predictions}; truth = {s['sample_id']: s['supervision']['label'] for s in samples}
    completed = [s for s in samples if s['sample_id'] in byid]
    false = sum(byid[s['sample_id']]['label']=='supported' and truth[s['sample_id']]!='supported' for s in completed)
    recalls = {}
    for label in ('supported', 'insufficient_evidence'):
        rows = [s for s in completed if truth[s['sample_id']]==label]
        hits = sum(byid[s['sample_id']]['label']==label for s in rows)
        recalls[label] = {'correct': hits, 'denominator': len(rows), 'recall': hits/len(rows) if rows else None}
    result['nli_diagnostics'] = {'false_supported_count':false,
        'non_supported_completed':sum(truth[s['sample_id']]!='supported' for s in completed),
        'recalls':recalls,'completed':len(completed),'total':len(samples),'coverage':len(completed)/len(samples)}
    return result


def run_comparison(args):
    import torch
    torch.set_num_threads(4); torch.manual_seed(20261005)
    samples = read(args.data)['samples']; check_partition(samples)
    selected = [s for s in samples if s['split'] != 'test']
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    resources = Resources()
    model, tokenizer, mapping, limit, load_seconds, info = load_model(args.model)
    encoded, records, excluded = prepare(selected, tokenizer, limit)
    results = {}
    for split in ('train', 'validation'):
        rows = [s for s in selected if s['split']==split]
        predictions, elapsed = predict(model, rows, encoded, mapping, resources)
        results[split] = {'predictions':predictions,'metrics':evaluate(rows,predictions),'seconds':elapsed}
    # Disposable feasibility probe; never used for quality comparison or as domain checkpoint.
    sample = next(s for s in selected if s['split']=='train' and s['sample_id'] in encoded)
    torch.manual_seed(20261005); model.train(); optimizer = torch.optim.AdamW(model.parameters(),lr=1e-5)
    target = next(i for i,label in mapping.items() if label==sample['supervision']['label'])
    started=time.perf_counter(); optimizer.zero_grad(set_to_none=True)
    loss=model(**encoded[sample['sample_id']],labels=torch.tensor([target])).loss
    loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1); optimizer.step(); resources.sample()
    step_seconds=time.perf_counter()-started
    if not torch.isfinite(loss): raise ValueError('Nonfinite single step')
    resources.close()
    report={'version':VERSION,'parameters':sum(p.numel() for p in model.parameters()),'mapping':mapping,
        'context_limit':limit,'load_seconds':load_seconds,'loading_info':info,'inputs':records,'excluded':excluded,
        'results':results,'probe':{'seconds':step_seconds,'loss':float(loss.detach()),'disposable':True},
        'peak_rss_bytes':resources.peak,'test_results_accessed':False,'device':'cpu'}
    write(out/'report.json',report)
    print(json.dumps({k:report[k] for k in ('parameters','context_limit','load_seconds','probe','peak_rss_bytes','test_results_accessed')}),flush=True)


def run_training(args):
    cfg=read(args.config); out=Path(cfg['output'])
    samples=read(cfg['data'])['samples']; check_partition(samples)
    if any(s['supervision']['status']!='confirmed' for s in samples):
        raise ValueError('Explicit confirmed labels required before loading a training model')
    import torch
    out.mkdir(parents=True,exist_ok=False)
    random.seed(cfg['seed']); torch.manual_seed(cfg['seed']); torch.set_num_threads(cfg['threads'])
    resources=Resources(); model,tokenizer,mapping,limit,load_seconds,info=load_model(cfg['model_directory'])
    encoded,records,excluded=prepare(samples,tokenizer,limit); write(out/'semantic-inputs.json',records)
    partitions={split:[s for s in samples if s['split']==split and s['sample_id'] in encoded] for split in ('train','validation','test')}
    if not all(partitions.values()):raise ValueError('Empty effective split')
    before,seconds_before=predict(model,partitions['test'],encoded,mapping,resources)
    write(out/'before-predictions.json',before)
    inverse={label:i for i,label in mapping.items()}
    optimizer=torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    started=time.perf_counter(); history=[]; best=-1.; best_epoch=None
    for epoch in range(1,cfg['epochs']+1):
        model.train(); rows=list(partitions['train']); random.shuffle(rows); loss_sum=0
        for sample in rows:
            optimizer.zero_grad(set_to_none=True)
            loss=model(**encoded[sample['sample_id']],labels=torch.tensor([inverse[sample['supervision']['label']]])).loss
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['gradient_clip']);optimizer.step()
            loss_sum+=float(loss.detach());resources.sample()
        predictions,elapsed=predict(model,partitions['validation'],encoded,mapping,resources)
        metrics=evaluate(partitions['validation'],predictions);score=metrics['semantic_metrics']['macro_f1']
        history.append({'epoch':epoch,'train_loss':loss_sum/len(rows),'validation':metrics,'validation_predictions':predictions})
        if score>best:
            best=score;best_epoch=epoch;model.save_pretrained(out/'best-checkpoint',safe_serialization=True)
            tokenizer.save_pretrained(out/'best-checkpoint')
        print(json.dumps({'epoch':epoch,'validation_macro_f1':score}),flush=True)
    training_seconds=time.perf_counter()-started
    del optimizer,model
    model,_,_,_,_,_=load_model(out/'best-checkpoint')
    after,seconds_after=predict(model,partitions['test'],encoded,mapping,resources);resources.close()
    write(out/'after-predictions.json',after)
    report={'config':cfg,'version':VERSION,'mapping':mapping,'loading_info':info,'best_epoch':best_epoch,
        'history':history,'before':evaluate(partitions['test'],before),'after':evaluate(partitions['test'],after),
        'effective_splits':{k:len(v) for k,v in partitions.items()},'excluded':excluded,
        'test_ids':[s['sample_id'] for s in partitions['test']],'test_evaluations_per_model':1,
        'timings':{'load':load_seconds,'before':seconds_before,'training':training_seconds,'after':seconds_after},
        'peak_rss_bytes':resources.peak,'parameter_count':sum(p.numel() for p in model.parameters()),
        'scope':'Previously viewed five-item same-document development comparison, not independent acceptance',
        'production_changed':False,'paid_api_calls':0}
    write(out/'report.json',report); print(json.dumps({'best_epoch':best_epoch,'training_seconds':training_seconds,'peak_rss_bytes':resources.peak}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    compare=sub.add_parser('compare');compare.add_argument('--data',required=True);compare.add_argument('--model',required=True);compare.add_argument('--output',required=True)
    train=sub.add_parser('train');train.add_argument('--config',required=True)
    args=parser.parse_args()
    if args.mode=='compare':run_comparison(args)
    else:run_training(args)

if __name__=='__main__':main()
