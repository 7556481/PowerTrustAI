"""One expanded CPU NLI run, then a sealed document-heldout comparison."""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import random
import time

from evaluation.support_dataset import task_key, validate_sample
from evaluation.support_training import confirm_template, check_partition
from evaluation.support_nli import (VERSION, read, write, prepare, semantic_pair,
    load_model, predict, evaluate, Resources)

MODEL_ID='cross-encoder/nli-MiniLM2-L6-H768'
REVISION='b95119ce93d3e065de6214e38cd4a97b0f2f2c6d'
LABELS=('supported','contradicted','insufficient_evidence')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def confirm_authorized(samples, template, *, event_id, reviewer_id):
    """Requires the human's explicit exact-template authorization at call site."""
    output, events=confirm_template(samples,template,event_id=event_id,reviewer_id=reviewer_id)
    byid={r['sample_id']:r for r in template['reviews']}
    events_byid={event['sample_id']:event for event in events}
    for sample in output:
        event=events_byid[sample['sample_id']]
        row=byid[sample['sample_id']]
        if sample['supervision']['basis_ids']!=row['suggestion_basis_ids']:
            raise ValueError('Confirmation must not expand the received basis subset')
        sample['supervision']['rationale']=row['note']
        sample['supervision']['note']=row['note']
        event['note']=row['note'];event['basis_scope']=sample['quality_review'].get('basis_scope')
        sample['review_history'][-1].update(event)
        validate_sample(sample)
    return output,events


def validate_layout(development, heldout, expected=None):
    ids=[s['sample_id'] for s in development+heldout]
    if len(set(ids))!=len(ids):raise ValueError('Repeated ID or document holdout mixed into development')
    check_partition(development)
    for s in development+heldout:
        validate_sample(s);semantic_pair(s)
        if s['supervision']['status']!='confirmed':raise ValueError('Explicit confirmed labels required')
        if s['supervision']['source']!='ai_assisted_user_supervised':raise ValueError('Preserve actual supervision source')
        if s['supervision']['label'] not in LABELS:raise ValueError('Only the confirmed three-class experiment')
    if any(s['split'] not in ('train','validation') for s in development):
        raise ValueError('Development cannot contain test/heldout cases')
    if any(s['split']!='future_document_heldout_evaluation_review' for s in heldout):
        raise ValueError('Document heldout role must remain explicit')
    devdocs={e['metadata']['source_id'] for s in development for e in s['task']['evidence']}
    holddocs={e['metadata']['source_id'] for s in heldout for e in s['task']['evidence']}
    if devdocs & holddocs:raise ValueError('Same document leaked into development and heldout')
    groups={s['group_id']:s['split'] for s in development+heldout}
    byid={s['sample_id']:s for s in development+heldout}
    if len(groups)!=len({s['group_id'] for s in development})+len({s['group_id'] for s in heldout}):
        raise ValueError('Concept group crosses document holdout')
    for s in development+heldout:
        for origin in s['origins']:
            p=byid.get(origin.get('parent_sample_id'))
            if p and (p in heldout)!=(s in heldout):raise ValueError('Parent crosses document holdout')
    counts={'train':sum(s['split']=='train' for s in development),
        'validation':sum(s['split']=='validation' for s in development),'heldout':len(heldout)}
    if not all(counts.values()) or (expected is not None and counts!=expected):
        raise ValueError('Frozen split counts changed or empty')
    return counts


def verify_freeze(cfg):
    if cfg['model_id']!=MODEL_ID or cfg['revision']!=REVISION or cfg['adapter_version']!=VERSION:
        raise ValueError('Fixed original model or semantic adapter changed')
    frozen=read(cfg['freeze_manifest'])
    for path,record in frozen['files'].items():
        if sha(path)!=record['sha256']:raise ValueError('Frozen file changed: '+path)
    acquisition=read(Path(cfg['model_directory'])/'acquisition.json')
    if acquisition['model_id']!=MODEL_ID or acquisition['revision']!=REVISION:
        raise ValueError('Original official model acquisition required')
    for name,record in acquisition['files'].items():
        if sha(Path(cfg['model_directory'])/name)!=record['sha256']:
            raise ValueError('Pinned official model file changed: '+name)
    return frozen


def match_effective(records, frozen_records, ids):
    expected={r['sample_id']:r for r in frozen_records if r['sample_id'] in ids}
    actual={r['sample_id']:r for r in records}
    if actual!=expected:raise ValueError('Actual semantic inputs or token lengths differ from frozen preflight')


def train_expanded(cfg):
    verify_freeze(cfg)
    development=read(cfg['development'])['samples'];heldout=read(cfg['heldout'])['samples']
    counts=validate_layout(development,heldout,cfg['expected_counts'])
    frozen_inputs=read(cfg['preflight'])
    out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=False)
    write(out/'training-started.json',{'counts':counts,'actual_run':1,'heldout_predictions':0})
    import torch
    random.seed(cfg['seed']);torch.manual_seed(cfg['seed']);torch.set_num_threads(cfg['threads'])
    resources=Resources();model,tokenizer,mapping,limit,load_seconds,info=load_model(cfg['model_directory'])
    encoded,records,excluded=prepare(development,tokenizer,limit)
    match_effective(records,frozen_inputs['records'],{s['sample_id'] for s in development})
    partitions={p:[s for s in development if s['split']==p and s['sample_id'] in encoded] for p in ('train','validation')}
    effective={p:[s['sample_id'] for s in rows] for p,rows in partitions.items()}
    if any(effective[p]!=frozen_inputs['effective_ids'][p] for p in partitions):
        raise ValueError('Effective development IDs changed')
    if not all(partitions.values()):raise ValueError('No effective training or validation')
    inverse={label:i for i,label in mapping.items()}
    optimizer=torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    started=time.perf_counter();history=[];best=-1.;best_epoch=None
    for epoch in range(1,cfg['epochs']+1):
        model.train();rows=list(partitions['train']);random.shuffle(rows);loss_sum=0
        for sample in rows:
            optimizer.zero_grad(set_to_none=True)
            loss=model(**encoded[sample['sample_id']],labels=torch.tensor([inverse[sample['supervision']['label']]])).loss
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss; no automatic restart')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['gradient_clip']);optimizer.step()
            loss_sum+=float(loss.detach());resources.sample()
        predictions,elapsed=predict(model,partitions['validation'],encoded,mapping,resources)
        metrics=evaluate(partitions['validation'],predictions);score=metrics['semantic_metrics']['macro_f1']
        record={'epoch':epoch,'train_loss':loss_sum/len(rows),'validation':metrics,
            'validation_predictions':predictions,'validation_seconds':elapsed}
        history.append(record);write(out/f'epoch-{epoch}.json',record)
        if score>best:
            best=score;best_epoch=epoch;model.save_pretrained(out/'best-checkpoint',safe_serialization=True)
            tokenizer.save_pretrained(out/'best-checkpoint')
        print({'epoch':epoch,'validation_macro_f1':score,'heldout_predictions':0},flush=True)
    training_seconds=time.perf_counter()-started;resources.close()
    checkpoint_files={str(p.resolve()):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((out/'best-checkpoint').iterdir()) if p.is_file()}
    seal={'selection_closed':True,'best_epoch':best_epoch,'validation_macro_f1':best,
        'heldout_predictions_before_selection':0,'checkpoint_files':checkpoint_files,
        'configuration_sha256':sha(cfg['config_path']),'freeze_manifest_sha256':sha(cfg['freeze_manifest'])}
    write(out/'selection-seal.json',seal)
    report={'config':cfg,'counts':counts,'effective_ids':effective,'excluded':excluded,'history':history,
        'best_epoch':best_epoch,'loading_info':info,'mapping':mapping,'parameters':sum(p.numel() for p in model.parameters()),
        'load_seconds':load_seconds,'training_seconds':training_seconds,'peak_rss_bytes':resources.peak,
        'heldout_predictions':0,'training_runs':1,'production_changed':False,'paid_calls':0}
    write(out/'training-report.json',report)
    print({'best_epoch':best_epoch,'training_seconds':training_seconds,'peak_rss_bytes':resources.peak},flush=True)


def heldout_metrics(samples,predictions):
    result=evaluate(samples,predictions)
    predicted_supported=sum(p['label']=='supported' for p in predictions)
    false=result['nli_diagnostics']['false_supported_count']
    result['nli_diagnostics'].update(predicted_supported=predicted_supported,
        wrong_support_among_supported_predictions=false/predicted_supported if predicted_supported else None)
    labels=list(LABELS);truth={s['sample_id']:s['supervision']['label'] for s in samples}
    matrix=[[sum(truth[p['sample_id']]==a and p['label']==b for p in predictions) for b in labels] for a in labels]
    result['three_class_confusion']={'rows':'truth','columns':'prediction','label_order':labels,'matrix':matrix}
    return result


def evaluate_document_holdout(cfg):
    verify_freeze(cfg);out=Path(cfg['output']);seal=read(out/'selection-seal.json')
    if not seal.get('selection_closed') or seal['heldout_predictions_before_selection']!=0:
        raise ValueError('Checkpoint selection must be closed before any document-heldout prediction')
    if seal['configuration_sha256']!=sha(cfg['config_path']) or seal['freeze_manifest_sha256']!=sha(cfg['freeze_manifest']):
        raise ValueError('Configuration changed after selection')
    for path,record in seal['checkpoint_files'].items():
        if sha(path)!=record['sha256']:raise ValueError('Selected checkpoint changed')
    development=read(cfg['development'])['samples'];heldout=read(cfg['heldout'])['samples']
    validate_layout(development,heldout,cfg['expected_counts'])
    write(out/'heldout-started.json',{'selection_seal_sha256':sha(out/'selection-seal.json'),'evaluations_per_model':1})
    import torch
    torch.set_num_threads(cfg['threads']);torch.manual_seed(cfg['seed'])
    frozen_inputs=read(cfg['preflight']);results={}
    for name,directory in [('official_base',cfg['model_directory']),('expanded_best',out/'best-checkpoint')]:
        resources=Resources();model,tokenizer,mapping,limit,load_seconds,info=load_model(directory)
        encoded,records,excluded=prepare(heldout,tokenizer,limit)
        match_effective(records,frozen_inputs['records'],{s['sample_id'] for s in heldout})
        effective=[s for s in heldout if s['sample_id'] in encoded]
        if [s['sample_id'] for s in effective]!=frozen_inputs['effective_ids']['heldout']:
            raise ValueError('Same frozen document-heldout set required for both models')
        predictions,elapsed=predict(model,effective,encoded,mapping,resources);resources.close()
        byrecord={r['sample_id']:r for r in records}
        for p in predictions:p.update(tokens=byrecord[p['sample_id']]['tokens'],task_sha256=p['sample_id'])
        write(out/(name+'-heldout-predictions.json'),predictions)
        metrics=heldout_metrics(heldout,predictions)
        results[name]={'metrics':metrics,'load_seconds':load_seconds,'inference_seconds':elapsed,
            'peak_rss_bytes':resources.peak,'loading_info':info,'mapping':mapping,'excluded':excluded}
        del model,encoded
    report={'best_epoch':seal['best_epoch'],'selection_seal_sha256':sha(out/'selection-seal.json'),
        'same_effective_ids':frozen_inputs['effective_ids']['heldout'],'results':results,
        'evaluations_per_model':1,'scope':'Single SSIAG document, AI-assisted user supervision, small sample single seed; no not_assessable or engineering assurance',
        'production_changed':False,'paid_calls':0}
    write(out/'heldout-report.json',report);print({k:v['metrics']['semantic_metrics']['macro_f1'] for k,v in results.items()},flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['train','heldout']);parser.add_argument('--config',required=True)
    args=parser.parse_args();cfg=read(args.config)
    if Path(cfg['config_path']).resolve()!=Path(args.config).resolve():raise ValueError('Use the frozen configuration path')
    if args.phase=='train':train_expanded(cfg)
    else:evaluate_document_holdout(cfg)

if __name__=='__main__':main()
