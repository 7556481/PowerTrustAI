"""Development-only supervised support classification; optional isolated torch runner."""
from collections import Counter
from copy import deepcopy
from pathlib import Path

from evaluation.support_dataset import (LABELS, VERSION, apply_reviews, canonical,
    digest, normalized, read, task_key, validate_sample, write)

CLASSES = LABELS[:3]
TEXT_VERSION = 'support-classifier-complete-pair-v2'


def confirm_template(samples, template, *, event_id, reviewer_id):
    if not event_id or not reviewer_id:
        raise ValueError('explicit local user event and identifier required')
    rows = template['reviews']; byid = {s['sample_id']: s for s in samples}
    if len(byid) != len(samples) or len(rows) != len(samples) or {r['sample_id'] for r in rows} != set(byid):
        raise ValueError('confirmation must cover the explicit primary selection once')
    confirmed=[]
    for row in rows:
        s=byid[row['sample_id']]
        if s['quality_review']['disposition']!='candidate_ready' or row['task_sha256']!=task_key(s['task']):
            raise ValueError('only exact primary frozen tasks may be confirmed')
        label=row['suggestion_label']
        if label not in CLASSES:raise ValueError('this supervised experiment has three classes')
        confirmed.append(dict(sample_id=s['sample_id'],task_sha256=row['task_sha256'],
            status='confirmed',label=label,basis_ids=list(row['suggestion_basis_ids']),
            reviewer_id=reviewer_id,source='ai_assisted_user_supervised',event_id=event_id,
            note='User explicitly confirmed this ID-specific template suggestion; not expert gold.'))
    return apply_reviews(samples,{'reviews':confirmed}), confirmed


def select_materials(samples, permitted_sources):
    included=[];excluded=[]
    for s in samples:
        validate_sample(s)
        sources={q['metadata'].get('source_id') for q in s['task']['evidence']}
        # Every delivered document must be permitted; labels are not inferred here.
        missing=sources-set(permitted_sources)
        if s['supervision']['status']!='confirmed' or not s['eligible_for_baseline'] or s['supervision']['label'] not in CLASSES:
            reason='not_confirmed_three_class_primary'
        elif missing:reason='source_training_permission_unconfirmed'
        elif not sources:reason='no_document_source_in_this_experiment'
        else:
            included.append(deepcopy(s));continue
        excluded.append({'sample_id':s['sample_id'],'reason':reason,'sources':sorted(sources),
            'unconfirmed_sources':sorted(missing)})
    return included,excluded


def text_pair(sample):
    """Keep exact claim/stance/conditions and whole delivered bases; never truncate."""
    t=sample['task']
    claim=deepcopy(t['claim'])
    if claim.get('text')==claim['proposition']:claim.pop('text')
    target={'task_type':t['task_type'],'claim':claim}
    # Remove byte-identical repetitions only, never shorten a claim or a quote.
    if t['answer_excerpt']!=claim['proposition']:target['answer_excerpt']=t['answer_excerpt']
    first=canonical(target)
    second=canonical({'evidence':[{'basis_id':q['basis_id'],'text':q['text'],
        'source_id':q['metadata'].get('source_id'),'source_version':q['metadata'].get('source_version'),
        'locator':q['metadata'].get('locator'),'applicability':q['metadata'].get('applicability'),
        'source_uri':q['metadata'].get('provenance',{}).get('source_uri'),
        'document_title':q['metadata'].get('provenance',{}).get('document_title')}
        for q in t['evidence']], 'other_basis':t['other_basis']})
    return first,second


def check_partition(samples):
    groups={}; parents={s['sample_id']:s for s in samples}
    for s in samples:
        if s['split'] not in ('train','validation','test'):raise ValueError('explicit development split required')
        old=groups.setdefault(s['group_id'],s['split'])
        if old!=s['split']:raise ValueError('family crosses split')
        for o in s['origins']:
            parent=parents.get(o.get('parent_sample_id'))
            if parent and parent['split']!=s['split']:raise ValueError('parent crosses split')
    for i,a in enumerate(samples):
        x=set(normalized(a['task']['claim']['proposition']).split())
        for b in samples[i+1:]:
            if a['task']['task_type']!=b['task']['task_type']:continue
            y=set(normalized(b['task']['claim']['proposition']).split())
            if x|y and len(x&y)/len(x|y)>=.9 and a['split']!=b['split']:
                raise ValueError('near duplicate crosses split')
    return {'splits':dict(Counter(s['split'] for s in samples)),
        'families':len(groups),'labels':dict(Counter(s['supervision']['label'] for s in samples)),
        'independent_test':False}


def development_split(samples, *, seed):
    """New frozen family-only development split, selected before model execution."""
    import random
    families=sorted({s['group_id'] for s in samples})
    if len(families)<3:raise ValueError('need at least three distinct families')
    random.Random(seed).shuffle(families)
    n_train=max(1,int(len(families)*.6)); n_val=max(1,int(len(families)*.2))
    mapping={g:('train' if i<n_train else 'validation' if i<n_train+n_val else 'test') for i,g in enumerate(families)}
    revised=deepcopy(samples)
    for s in revised:
        s['original_split']=s['split'];s['split']=mapping[s['group_id']]
    report=check_partition(revised)
    return revised, {'seed':seed,'family_assignment':mapping,'ratio_rule':'floor 60% train, floor 20% validation, remainder test; minimum one each',
        'reason':'permission-screened original development subset has no test partition',
        'independent_test':False,'report':report}


def classify_metrics(samples, predictions):
    from evaluation.support_baseline import metrics
    return metrics(samples, {'task_hashes':{s['sample_id']:digest(canonical(s['task'])) for s in samples},
        'predictions':predictions}, class_labels=CLASSES)


def train(config_path):
    """One CPU fine-tune; select on validation, test once for each before/after model."""
    import json, random, time, platform, importlib.metadata
    import numpy as np
    import torch
    import psutil
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    cfg=read(config_path); out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=False)
    seed=cfg['seed']; random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.set_num_threads(cfg['threads']);torch.use_deterministic_algorithms(True)
    process=psutil.Process();peak=process.memory_info().rss;started=time.perf_counter()
    samples=read(cfg['dataset'])['samples']; check_partition(samples)
    if any(s['supervision']['status']!='confirmed' for s in samples):raise ValueError('pending labels cannot train')
    tokenizer=AutoTokenizer.from_pretrained(cfg['model_directory'],local_files_only=True)
    encoded={};lengths=[];excluded=[]
    for s in samples:
        a,b=text_pair(s);item=tokenizer(a,b,truncation=False,return_tensors='pt')
        size=item['input_ids'].shape[1]
        lengths.append({'sample_id':s['sample_id'],'tokens':size,'text_sha256':digest(canonical([a,b])),
                        'handling':'complete' if size<=cfg['max_length'] else 'excluded_whole_sample'})
        if size>cfg['max_length']:excluded.append(s);continue
        encoded[s['sample_id']]=item
    usable=[s for s in samples if s['sample_id'] in encoded]
    partitions={k:[s for s in usable if s['split']==k] for k in ('train','validation','test')}
    if any(not v for v in partitions.values()):raise ValueError('material/length screening leaves an empty split')
    if {s['supervision']['label'] for s in partitions['train']}!=set(CLASSES):raise ValueError('training requires all three classes')
    write(out/'lengths.json',{'items':lengths,'excluded_ids':[s['sample_id'] for s in excluded],
        'no_truncation':True,'text_version':TEXT_VERSION})
    model=AutoModelForSequenceClassification.from_pretrained(cfg['model_directory'],
        num_labels=3,id2label=dict(enumerate(CLASSES)),label2id={v:i for i,v in enumerate(CLASSES)},
        local_files_only=True,attn_implementation='eager',use_safetensors=True)
    if cfg['max_length']>model.config.max_position_embeddings:raise ValueError('context exceeds actual model')
    params=sum(p.numel() for p in model.parameters())
    model.save_pretrained(out/'initial-model',safe_serialization=True)
    def predict(rows):
        nonlocal peak
        model.eval();pred=[]
        with torch.no_grad():
            for s in rows:
                scores=model(**encoded[s['sample_id']]).logits[0]
                label=CLASSES[int(scores.argmax())]
                pred.append({'sample_id':s['sample_id'],'label':label,'status':'complete',
                    'basis_ids':[],'rationale':'classifier label only; does not generate audited basis selection',
                    'logits':scores.tolist()})
                peak=max(peak,process.memory_info().rss)
        return pred
    # One before pass on the fixed final evaluation set. Not used to tune config.
    before=predict(partitions['test'])
    write(out/'before-predictions.json',{'predictions':before})
    optimizer=torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    best=-1.;best_epoch=None;history=[]
    for epoch in range(1,cfg['epochs']+1):
        model.train();order=list(partitions['train']);random.shuffle(order);loss_sum=0
        for s in order:
            optimizer.zero_grad(set_to_none=True)
            label=torch.tensor([CLASSES.index(s['supervision']['label'])])
            loss=model(**encoded[s['sample_id']],labels=label).loss
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
            loss_sum+=float(loss.detach());peak=max(peak,process.memory_info().rss)
        val=predict(partitions['validation']);m=classify_metrics(partitions['validation'],val)
        score=m['semantic_metrics']['macro_f1']
        history.append({'epoch':epoch,'train_loss':loss_sum/len(order),'validation':m})
        if score>best:
            best=score;best_epoch=epoch;model.save_pretrained(out/'best-checkpoint',safe_serialization=True)
        print(json.dumps({'epoch':epoch,'validation_macro_f1':score}),flush=True)
    del optimizer,model
    model=AutoModelForSequenceClassification.from_pretrained(out/'best-checkpoint',local_files_only=True,attn_implementation='eager')
    after=predict(partitions['test'])
    write(out/'after-predictions.json',{'predictions':after})
    before_m=classify_metrics(partitions['test'],before);after_m=classify_metrics(partitions['test'],after)
    report={'config':cfg,'seed':seed,'device':'cpu','parameters':params,
        'frameworks':{k:importlib.metadata.version(k) for k in ('torch','transformers','numpy','safetensors','psutil')},
        'python':platform.python_version(),'text_version':TEXT_VERSION,'splits':{k:len(v) for k,v in partitions.items()},
        'families':check_partition(usable)['families'],'training_labels':dict(Counter(s['supervision']['label'] for s in partitions['train'])),
        'best_epoch':best_epoch,'history':history,'elapsed_seconds':time.perf_counter()-started,
        'peak_process_rss_bytes':peak,'before':before_m,'after':after_m,
        'same_test_ids':[s['sample_id'] for s in partitions['test']],
        'excluded_length_ids':[s['sample_id'] for s in excluded],
        'baseline_note':'Same pretrained encoder with seeded random three-class head before supervised tuning; not an NLI-trained classifier.',
        'scope':'Small user-supervised in-document development experiment; no independent generalization claim.',
        'test_evaluations_per_model':1,'classifier_does_not_select_evidence':True}
    write(out/'report.json',report)
    print(canonical({k:report[k] for k in ('elapsed_seconds','peak_process_rss_bytes','splits','best_epoch')}))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True)
    train(p.parse_args().config)
