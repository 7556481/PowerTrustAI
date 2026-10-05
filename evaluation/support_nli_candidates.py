"""Exact private-source anchors and pending candidate review checks; no inference."""
from evaluation.support_dataset import validate_sample, normalized


def exact_anchor(text, start, end):
    """Match whitespace-normalized phrases but return untouched original spans."""
    chars=[]; positions=[]; whitespace=False
    for offset,char in enumerate(text):
        if char.isspace():
            if not whitespace:chars.append(' ');positions.append(offset)
            whitespace=True
        else:chars.append(char);positions.append(offset);whitespace=False
    value=''.join(chars); start=' '.join(start.split()); end=' '.join(end.split())
    if not start or not end or value.count(start)!=1:
        raise ValueError('Missing or ambiguous source start')
    first=value.index(start);last=value.find(end,first)
    if last<0:raise ValueError('Missing source end')
    begin=positions[first];finish=positions[last+len(end)-1]+1
    return begin,finish,text[begin:finish]


def validate_pending(samples, document_pages, existing=()):
    """Keep labels pending and verify real page spans and parent allocations."""
    byid={s['sample_id']:s for s in samples}
    if len(byid)!=len(samples):raise ValueError('Duplicate candidate identity')
    old={s['sample_id'] for s in existing};families={};checked=0
    for sample in samples:
        validate_sample(sample)
        if sample['sample_id'] in old:raise ValueError('Existing task recycled as new candidate')
        if sample['supervision']['status']!='pending' or sample['supervision']['label'] is not None:
            raise ValueError('New candidate must await explicit review')
        if sample.get('training_eligible') is not False:
            raise ValueError('New candidates must not join current training')
        prior=families.setdefault(sample['group_id'],sample['split'])
        if prior!=sample['split']:raise ValueError('Concept family crosses future allocation')
        for origin in sample['origins']:
            parent=byid.get(origin.get('parent_sample_id'))
            if parent and parent['split']!=sample['split']:raise ValueError('Parent lineage crosses allocation')
        for evidence in sample['task']['evidence']:
            metadata=evidence['metadata'];page=metadata['provenance']['file_page']
            text=document_pages[metadata['source_id']][page]
            if text[evidence['start_offset']:evidence['end_offset']]!=evidence['text']:
                raise ValueError('Candidate evidence is not exact extracted page text')
            checked+=1
    warnings=[]
    for i,a in enumerate(samples):
        words=set(normalized(a['task']['claim']['proposition']).split())
        for b in samples[i+1:]:
            other=set(normalized(b['task']['claim']['proposition']).split())
            if words|other and len(words&other)/len(words|other)>=.9:
                warnings.append({'first':a['sample_id'],'second':b['sample_id'],
                                 'same_family':a['group_id']==b['group_id'],'same_allocation':a['split']==b['split']})
                if a['split']!=b['split']:raise ValueError('Near duplicate crosses future allocation')
    return {'candidates':len(samples),'families':len(families),'exact_evidence_spans':checked,
            'pending':len(samples),'near_duplicate_pairs':warnings,'existing_task_reuse':0}
