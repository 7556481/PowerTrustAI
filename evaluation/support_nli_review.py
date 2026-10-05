"""Receive pending review and propose leakage-aware groups; no model calls."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import zipfile
from evaluation.support_dataset import task_key, validate_sample, normalized, canonical, digest


def read_review_archive(path):
    names=('review-analysis-78.json','review-labels-ready-69.json','review-summary.json','review-report-78.md','README.md')
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist()
        if len({i.filename for i in entries}) != len(entries):
            raise ValueError('Duplicate archive member')
        if set(i.filename for i in entries)!=set(names):
            raise ValueError('Unexpected archive members; never extract or execute')
        if any(i.file_size>4_000_000 for i in entries):
            raise ValueError('Oversized review member')
        payload={name:archive.read(name) for name in names}
    return payload, {name:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for name,b in payload.items()}


def receive_pending(samples, analysis, template):
    byid={s['sample_id']:s for s in samples}
    reviews=analysis['reviews'];ready=template['reviews']
    if len(byid)!=len(samples) or len(reviews)!=len(samples) or len({r['sample_id'] for r in reviews})!=len(reviews) or {r['sample_id'] for r in reviews}!=set(byid):
        raise ValueError('Review must cover each original ID once')
    primary={r['sample_id']:r for r in ready}
    expected={r['sample_id'] for r in reviews if r['disposition']=='candidate_ready'}
    if len(primary)!=len(ready) or set(primary)!=expected:
        raise ValueError('Primary template selection mismatch')
    result=[];changes=[]
    for row in reviews:
        old=byid[row['sample_id']];validate_sample(old);task=old['task']
        if row['task_sha256']!=task_key(task):raise ValueError('Review task hash changed')
        if row['family']!=old['group_id'] or row['future_allocation']!=old['split']:
            raise ValueError('Review lineage or future document allocation changed')
        if row['claim']!=task['claim']['proposition'] or row['evidence_text']!='\n\n'.join(e['text'] for e in task['evidence']):
            raise ValueError('Reviewed delivery changed')
        if len(task['evidence'])!=1 or row['document_id']!=task['evidence'][0]['metadata']['source_id'] or row['file_page']!=task['evidence'][0]['metadata']['provenance']['file_page']:
            raise ValueError('Reviewed source page changed')
        basis={e['basis_id'] for e in task['evidence']}|{b['basis_id'] for b in task['other_basis']}
        if not set(row['basis_ids'])<=basis:raise ValueError('Review basis out of delivery scope')
        if row['original_suggestion']!=old['supervision']['suggestion_label']:
            raise ValueError('Original suggestion mismatch')
        if row['status']!='pending':raise ValueError('Review is not a confirmation event')
        disposition=row['disposition'];label=row['proposed_label']
        if disposition not in ('candidate_ready','auxiliary_only','hold'):
            raise ValueError('Unknown disposition')
        if disposition=='hold':
            if label is not None:raise ValueError('Hold cannot have a primary label')
        elif label not in ('supported','contradicted','insufficient_evidence'):
            raise ValueError('Unsupported proposed class')
        if disposition=='candidate_ready':
            t=primary[row['sample_id']]
            if t['task_sha256']!=row['task_sha256'] or t['suggestion_label']!=label or t['suggestion_basis_ids']!=row['basis_ids'] or t['note']!=row['rationale']:
                raise ValueError('Primary template contradicts detailed review')
            if t['status']!='pending' or t['label'] is not None or t['reviewer_id'] is not None or t['basis_ids']:
                raise ValueError('New labels must remain pending')
        s=deepcopy(old)
        s['supervision_history']=s.get('supervision_history',[])+[deepcopy(old['supervision'])]
        s['quality_review']=deepcopy(row)
        s['quality_review']['version']='nli-review-received-v2'
        s['quality_review']['basis_scope'] = (
            'evidence_metadata_fields' if task['claim'].get('basis_target')=='metadata'
            else 'source_attribution_auxiliary' if disposition=='auxiliary_only'
            else 'delivered_document_prose')
        s['supervision'].update(status='pending',label=None,reviewer_id=None,basis_ids=[],
            suggestion_label=label,suggestion_basis_ids=list(row['basis_ids']),
            suggestion_method='received_exact_delivery_review_v1',rationale=row['rationale'])
        s['training_eligible']=False
        s['eligible_for_baseline']=disposition=='candidate_ready'
        validate_sample(s);result.append(s)
        if label is not None and label!=row['original_suggestion']:
            changes.append(deepcopy(row))
    return result,changes


def merge_groups(samples, concept_links=()):
    """Union original families/parents/concepts/near duplicates/shared passages.

    Only exact normalized semantic deliveries are deduplicated; all IDs and
    lineage stay in the returned report. No labels or model scores used.
    """
    parent={s['sample_id']:s['sample_id'] for s in samples};edges=[]
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    def join(a,b,reason):
        if a==b:return
        ra,rb=find(a),find(b)
        if ra!=rb:parent[max(ra,rb)]=min(ra,rb)
        edges.append({'first':a,'second':b,'reason':reason})
    groups={}
    for s in samples:groups.setdefault(s['group_id'],[]).append(s['sample_id'])
    for ids in groups.values():
        for sid in ids[1:]:join(ids[0],sid,'original_concept_family')
    for a,b in concept_links:
        if a not in groups or b not in groups:raise ValueError('Unknown explicit concept link')
        join(groups[a][0],groups[b][0],'audited_same_concept')
    for s in samples:
        for o in s['origins']:
            p=o.get('parent_sample_id')
            if p in parent:join(s['sample_id'],p,'parent_lineage')
    duplicates=[];seen={}
    for i,a in enumerate(samples):
        words=set(normalized(a['task']['claim']['proposition']).split())
        bodies=[normalized(e['text']) for e in a['task']['evidence']]
        sig=canonical({'type':a['task']['task_type'],'claim':a['task']['claim'],
            'bodies':bodies,'other_basis':a['task']['other_basis']})
        if sig in seen:duplicates.append({'retained':seen[sig],'duplicate':a['sample_id']})
        else:seen[sig]=a['sample_id']
        for b in samples[i+1:]:
            other=set(normalized(b['task']['claim']['proposition']).split())
            if words|other and len(words&other)/len(words|other)>=.85:
                join(a['sample_id'],b['sample_id'],'near_duplicate_claim_0.85')
            # A contained full quotation also leaks evidence; page alone does not.
            shared=any(min(len(x),len(y))>=40 and (x in y or y in x)
                for x in bodies for y in [normalized(e['text']) for e in b['task']['evidence']])
            if shared:join(a['sample_id'],b['sample_id'],'shared_or_contained_evidence')
    members={}
    for s in samples:members.setdefault(find(s['sample_id']),[]).append(s['sample_id'])
    allocation={sid:'merged-'+digest('|'.join(sorted(ids)))[:16] for ids in members.values() for sid in ids}
    return {'input_count':len(samples),'exact_duplicates_removed':len(duplicates),
        'deduplicated_count':len(samples)-len(duplicates),'duplicates':duplicates,
        'families':len(members),'groups':allocation,'edges':edges,
        'rule':'Unions label-blind; exact duplicate only removed, near-duplicate kept in same family'}


def propose_split(samples, grouping, *, seed):
    """Deterministic family-only ~20% validation, never uses labels or scores."""
    sizes=Counter(grouping['groups'][s['sample_id']] for s in samples)
    ranked=sorted(sizes,key=lambda gid:digest(str(seed)+'|'+gid))
    target=max(1,round(len(samples)*.2));validation=set();count=0
    for gid in ranked:
        if len(validation)<len(sizes)-1 and (not validation or abs(count+sizes[gid]-target)<abs(count-target)):
            validation.add(gid);count+=sizes[gid]
    if len(sizes)<2:raise ValueError('Not enough independent merged families for validation')
    return {s['sample_id']:'validation' if grouping['groups'][s['sample_id']] in validation else 'train' for s in samples}
