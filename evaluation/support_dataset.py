"""Private support-judgment preparation, never a production protocol adapter."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from html import escape
from services.fact_delivery import FAILED as INCOMPLETE_RETRIEVAL

VERSION='support-judgment-task-v1'
LABELS=('supported','contradicted','insufficient_evidence','not_assessable')
GROUP_VERSION='lineage-question-nearduplicate-union-v1'

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(value.encode('utf8')).hexdigest()
def normalized(text):return ' '.join(re.findall(r'\w+',text.casefold()))
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,value):
    with Path(path).open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

def public_metadata(value):
    """Keep real source/locator fields; never export credential-bearing/file URIs."""
    if isinstance(value,list):return [public_metadata(v) for v in value]
    if not isinstance(value,dict):return value
    out={}
    for key,v in value.items():
        if key.casefold() in ('path','file_path','database_path','request_messages_path','credential','headers','api_key','token','authorization','password'):continue
        if key=='source_uri' and v:
            from backend.serialization import public_https
            v=public_https(v)
        out[key]=public_metadata(v)
    return out

def tags(text):
    rules={'quantity_category':r'number|count|rating|数量|类别|额定|stator|field current',
        'unit_conversion':r'\b(?:kv|volt|ampere)\b|换算|千伏|230|单位',
        'negation_reported':r'\bnot\b|negat|reported|否认|并非|转述|不等于',
        'jurisdiction':r'china|chinese|europe|country|地区|中国|国家',
        'conditions':r'under|when|condition|operating|limit|条件|工况|约束',
        'target_conversion':r'mention|contains|source|原文|提及|核验|引用'}
    return [k for k,p in rules.items() if re.search(p,text,re.I)] or ['technical_support']

def task_key(task):
    # Request-scoped IDs differ between equal deliveries, so exclude them from
    # semantic de-duplication, but retain all original instances as provenance.
    return digest(canonical({'task_type':task['task_type'],'knowledge_version':task.get('knowledge_version'),'claim':task['claim'],
        'answer_excerpt':task['answer_excerpt'],
        'evidence':sorted((e['text_sha256'],canonical(e['metadata'])) for e in task['evidence']),
        'other_basis':[{k:v for k,v in b.items() if k!='basis_id'} for b in task['other_basis']]}))

def validate_sample(s):
    assert s['schema_version']==VERSION and s['sample_id']==task_key(s['task']),'sample identity mismatch'
    t=s['task'];assert t['claim']['proposition'].strip() and t['task_type'],'missing target'
    ids=[]
    for e in t['evidence']:
        assert digest(e['text'])==e['text_sha256'],'evidence text changed'
        assert e['end_offset']-e['start_offset']==len(e['text']),'quote span mismatch'
        ids.append(e['basis_id'])
    ids += [b['basis_id'] for b in t['other_basis']]
    assert len(ids)==len(set(ids)),'duplicate basis ID'
    supervision=s['supervision']
    assert supervision['status'] in ('pending','confirmed','disputed')
    assert supervision['source'] in ('user','ai_assisted_user_supervised')
    if supervision['status']=='confirmed':
        assert supervision['label'] in LABELS and supervision.get('reviewer_id'),'explicit reviewed label required'
        assert set(supervision.get('basis_ids',[]))<=set(ids),'supervision basis out of scope'
    else:assert supervision['label'] is None,'pending is not gold'
    if s['eligible_for_baseline']:
        assert any(o.get('structure_valid') for o in s['observations']) or s['synthetic'],'invalid structure cannot enter baseline'
    return s

def make_sample(task,origin,observation,*,synthetic=False,recipe=None,suggestion=None):
    task=public_metadata(task)
    proposal=suggestion or observation.get('model_status')
    if proposal not in LABELS:
        proposal='insufficient_evidence' if task['task_type'] in ('factual_support','original_citation_support') else 'not_assessable'
        method='target_type_triage_ai_suggestion_no_model_label'
    else:method='controlled_recipe_ai_suggestion' if synthetic else 'archived_model_proposal_unverified'
    s={'schema_version':VERSION,'sample_id':task_key(task),'task':task,'origins':[origin],
       'observations':[observation],'synthetic':synthetic,'recipe':recipe,
       'issue_tags':tags(task['claim']['proposition']),
       'eligible_for_baseline':bool(observation.get('structure_valid') or synthetic) and task['delivery_state'] not in INCOMPLETE_RETRIEVAL|{'capacity_omitted','retrieval_failed'},
       'supervision':{'status':'pending','label':None,'suggestion_label':proposal,
         'suggestion_method':method,
         'source':'ai_assisted_user_supervised','reviewer_id':None,
         'rationale':'建议需依原文、立场、限定与依据类型复核；原模型判断和程序告警均不是正确标签。',
         'checklist':['原核验对象/立场是否忠实','证据是否实际交付且范围匹配','数字/单位/否定/限定是否完整','不能仅凭结构告警认定语义错误']}}
    return validate_sample(s)

def extract(archive_root,*,feedback=(),result_index=None,model_ids=None):
    root=Path(archive_root).resolve();result_index=result_index or {};samples=[];skipped=[]
    for path in sorted(root.rglob('response-*.json')):
        try:
            record=read(path)
            if record.get('scope')!='PRIVATE_MODEL_RESPONSE_DIAGNOSTIC':continue
            if model_ids is not None and record.get('model_id') not in model_ids:
                skipped.append({'file':str(path.relative_to(root)),'reason':'model_not_selected'});continue
            if not record.get('request_messages_path'):
                skipped.append({'file':str(path.relative_to(root)),'reason':'missing_frozen_request_pointer'});continue
            mp=Path(record.get('request_messages_path','')).resolve()
            if not mp.is_relative_to(root):
                skipped.append({'file':str(path.relative_to(root)),'reason':'request outside explicit archive root'});continue
            messages=read(mp);data=json.loads(messages['messages'][1]['content'])
            # Corrections append a message; user message 1 remains frozen input.
            try:response=json.loads(record['response_text'])
            except ValueError:response={}
            assert digest(record['response_text'])==record['response_sha256'],'response hash mismatch'
            request_sha=hashlib.sha256(mp.read_bytes()).hexdigest();structure=record['validation_error'] is None
            answer=data.get('answer') or {};run=path.parent.name if path.parent.parent.name=='service_private' else None
            root_answer=result_index.get(run,{}).get('original_answer') or answer.get('text') or data.get('answer_text','')
            origin={'run_id':run,'archive_group':str(path.parent.relative_to(root)),
                'answer_id':answer.get('answer_id',data.get('answer_id')),'answer_version':answer.get('version',data.get('answer_version')),
                'lineage_root_sha256':digest(normalized(root_answer)) if root_answer else None,
                'question_family':digest(normalized(data.get('question',''))),
                'model_id':record.get('model_id'),'request_sha256':request_sha,'response_sha256':record['response_sha256'],
                'response_file':str(path.relative_to(root)),'prompt_version':record['prompt_version'],'call_number':record['call_number']}
            pools=[]
            if 'QUOTE_CANDIDATES' in data and 'claims' in data:
                byclaim={f['claim_id']:f for f in response.get('findings',[]) if isinstance(f,dict) and 'claim_id' in f}
                delivery={(m['claim_id'],m['component_id']):m for m in data.get('FACT_EVIDENCE_DELIVERY',{}).get('components',[])}
                for claim in data['claims']:
                    finding=byclaim.get(claim['claim_id'],{});reviews=finding.get('component_reviews',[])
                    for n,component in enumerate(claim.get('components',[])):
                        review=next((r for r in reviews if r.get('component_index')==n),{})
                        mapping=delivery.get((claim['claim_id'],component['component_id']))
                        allowed=None if mapping is None else set(mapping['allowed_quote_ids'])
                        if mapping is not None:
                            assert mapping['answer_id']==answer['answer_id'] and mapping['answer_version']==answer['version'],'mapping answer mismatch'
                            assert mapping['knowledge_version']==data['knowledge_version'],'mapping knowledge mismatch'
                            assert allowed<={q['quote_id'] for q in data['QUOTE_CANDIDATES']},'mapping unknown quote'
                        target=(claim.get('component_basis_targets') or ['unknown']*len(claim['components']))[n]
                        kind='factual_support' if target in ('technical_content','document_body') else 'scalar_calculation' if target=='mathematical_relation' else 'engineering_prerequisite' if target=='recommendation' else 'input_or_metadata_support'
                        c={'text':claim['text'],'proposition':component['proposition'],
                           'assertion_role':claim.get('assertion_role'),'qualifiers':claim.get('qualifiers',[])+claim.get('semantic_qualifiers',[]),
                           'category':component['category'],'basis_target':target,'scope':claim.get('qualifiers',[])+claim.get('semantic_qualifiers',[])}
                        pools.append((kind,c,data,allowed,dict(origin,claim_id=claim['claim_id'],component_id=component['component_id']),
                            {'model_status':review.get('status'),'model_rationale':review.get('rationale'),
                             'fidelity':review.get('semantic_review'),'structure_valid':structure,
                             'program_validation':record['validation_error'],'delivery':mapping,'raw_model_review':review,
                             'model_finding_bases':finding.get('bases',[]),'model_applicability_conditions':finding.get('applicability_conditions',[])}))
            for scope in data.get('ORIGINAL_CITATION_SCOPES',[]):
                index=scope['citation_index'];r=next((r for r in response.get('citation_reviews',[]) if r.get('citation_index')==index),{})
                c={'text':scope['answer_text'],'proposition':scope['answer_text'],'assertion_role':'original_bound_answer_substring',
                   'qualifiers':[],'category':'original_citation','basis_target':'original_bound_evidence','scope':[]}
                pools.append(('original_citation_support',c,scope,None,dict(origin,citation_index=index,claim_id=None,component_id=None),
                    {'model_status':r.get('status'),'model_rationale':r.get('rationale'),'structure_valid':structure,
                     'program_validation':record['validation_error'],'delivery':'original_scope_only','raw_model_review':r}))
            for kind,claim,pool,allowed,o,observation in pools:
                metadata={e['evidence_id']:e for e in pool.get('EVIDENCE_METADATA',[])}
                evidence=[{'basis_id':q['quote_id'],'evidence_id':q['evidence_id'],'text':q['text'],
                    'text_sha256':digest(q['text']),'start_offset':q['start_offset'],'end_offset':q['end_offset'],
                    'warnings':q.get('warnings',[]),'metadata':metadata.get(q['evidence_id'],{})}
                    for q in pool['QUOTE_CANDIDATES'] if allowed is None or q['quote_id'] in allowed]
                other=[]
                if kind!='original_citation_support':
                    for tool in data.get('TOOL_RESULTS',[]):other.append({'basis_id':'tool:'+tool['result_id'],'type':'tool_result','value':tool})
                if kind in ('input_or_metadata_support','engineering_prerequisite'):
                    other.append({'basis_id':'answer-text','type':'answer_text','value':data.get('answer',{}).get('text',data.get('answer_text',''))})
                if kind in ('input_or_metadata_support','engineering_prerequisite') and data.get('GENERATION_INPUT_SNAPSHOT'):
                    snap=data['GENERATION_INPUT_SNAPSHOT']
                    other.append({'basis_id':'input-snapshot','type':'input_snapshot','value':public_metadata({k:v for k,v in snap.items() if k in ('question','user_context','engineering_context','evidence','knowledge_version')})})
                task={'task_type':kind,'claim':claim,'answer_excerpt':claim['text'],'evidence':evidence,'other_basis':other,
                    'knowledge_version':pool.get('knowledge_version',data.get('knowledge_version')),
                    'delivery_state':'unknown_historical' if observation.get('delivery') is None else observation['delivery'].get('outcome','original_bound') if isinstance(observation['delivery'],dict) else 'original_bound',
                    'required_evidence_delivery':'delivered' if evidence else 'no_material_delivered'}
                finding_id=result_index.get(run,{}).get('finding_ids',{}).get((o['answer_id'],o['answer_version'],o.get('claim_id')))
                if finding_id is None:
                    matches=[r for r in feedback if r.get('run_id')==run and r['answer_id']==o['answer_id'] and r['answer_version']==o['answer_version']
                        and (r.get('associated_finding') or {}).get('claim_id')==o.get('claim_id') and o.get('claim_id')]
                    if matches:finding_id=matches[0]['finding_id']
                o['finding_id']=finding_id
                observation['human_feedback']=[r for r in feedback if r.get('run_id')==run and r['answer_id']==o['answer_id'] and r['answer_version']==o['answer_version'] and (not r.get('finding_id') or r['finding_id']==finding_id)]
                samples.append(make_sample(task,o,observation))
        except (ValueError,KeyError,TypeError,AssertionError,OSError) as exc:
            skipped.append({'file':str(path.relative_to(root)),'reason':type(exc).__name__})
    return samples,skipped

def deduplicate(samples):
    unique={}
    for s in samples:
        key=s['sample_id']
        if key not in unique:unique[key]=deepcopy(s)
        else:
            for field in ('origins','observations'):
                unique[key][field]+= [x for x in s[field] if x not in unique[key][field]]
            unique[key]['eligible_for_baseline'] |= s['eligible_for_baseline']
    return sorted(unique.values(),key=lambda s:s['sample_id'])

def controlled(samples):
    output=[];used=set()
    for s in samples:
        if not s['eligible_for_baseline'] or s['task']['task_type']!='factual_support' or not s['task']['evidence']:continue
        prop=s['task']['claim']['proposition'];recipes=[]
        if re.search(r'\d+',prop):recipes.append(('quantity_change',re.sub(r'\d+',lambda m:str(int(m[0])+1),prop,count=1),'contradicted'))
        if 'kV' in prop:recipes.append(('unit_change',prop.replace('kV','V',1),'contradicted'))
        if 'field current' in prop:recipes.append(('category_change',prop.replace('field current','stator current',1),'insufficient_evidence'))
        recipes += [('negation','It is not the case that ('+prop+').','contradicted'),
            ('scope_extension',prop+' This holds in every country and at every operating point.','insufficient_evidence')]
        shortened=re.split(r'\b(?:under|when|provided that|if)\b',prop,maxsplit=1,flags=re.I)[0].strip()
        if shortened and shortened!=prop:recipes.append(('condition_removal',shortened,'insufficient_evidence'))
        for name,modified,label in recipes:
            # One substantive example per recipe/question family, not many paraphrases.
            family=s['origins'][0]['question_family'];key=(name,family)
            if key in used:continue
            used.add(key);task=deepcopy(s['task']);task['claim'].update(text=modified,proposition=modified,assertion_role='asserted_synthetic_variant')
            task['answer_excerpt']=modified
            origin=deepcopy(s['origins'][0]);origin['parent_sample_id']=s['sample_id']
            origin['synthetic_recipe']=name
            obs={'structure_valid':True,'model_status':None,'model_rationale':None,'program_validation':None,'human_feedback':[]}
            sample=make_sample(task,origin,obs,synthetic=True,recipe={'method':'deterministic-controlled-edit-v1','operation':name,'before':prop,'after':modified},suggestion=label)
            sample['supervision']['rationale']='受控修改的待审建议；须确认原命题确实被交付证据支持，不能因修改本身直接定矛盾。'
            output.append(sample)
    return output

def group(samples):
    parent=list(range(len(samples)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):parent[find(b)]=find(a)
    seen={};ids={s['sample_id']:i for i,s in enumerate(samples)}
    for i,s in enumerate(samples):
        for o in s['origins']:
            for key in (('answer_lineage',o.get('run_id'),o.get('answer_id')),('root_answer',o.get('lineage_root_sha256')),('question_family',o.get('question_family'))):
                if not key[-1]:continue
                if key in seen:union(i,seen[key])
                else:seen[key]=i
            if o.get('parent_sample_id') in ids:union(i,ids[o['parent_sample_id']])
    # Preserve negation/numbers in normalized token sets; near duplicates still
    # share a group, never a label. Task type guards unrelated evidence tasks.
    for i,a in enumerate(samples):
        ta=set(normalized(a['task']['claim']['proposition']).split())
        for j in range(i):
            b=samples[j];tb=set(normalized(b['task']['claim']['proposition']).split())
            if a['task']['task_type']==b['task']['task_type'] and ta and len(ta&tb)/len(ta|tb)>=.9:union(i,j)
    groups={}
    for i,s in enumerate(samples):groups.setdefault(find(i),[]).append(s)
    for members in groups.values():
        gid='family-'+digest(canonical(sorted(s['sample_id'] for s in members)))[:16]
        split='development_only' if len(groups)<3 else ('train' if int(gid[-4:],16)%100<70 else 'validation' if int(gid[-4:],16)%100<85 else 'test')
        for s in members:s['group_id']=gid;s['split']=split
    evidence_sets={}
    for s in samples:
        for e in s['task']['evidence']:evidence_sets.setdefault(e['text_sha256'],set()).add(s['split'])
    return {'version':GROUP_VERSION,'independent_family_count':len(groups),
        'split_counts':{k:sum(s['split']==k for s in samples) for k in ('development_only','train','validation','test')},
        'shared_evidence_across_splits':{k:sorted(v) for k,v in evidence_sets.items() if len(v)>1},
        'scope':'historical developer cohort; within-document grouping, not an independent or cross-document test set'}

def export_review(samples,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    entries=[];lines=['# 证据支持判断监督复核包 v1','', '来源：AI辅助、用户监督。全部pending不是金标准；建议已预填，审阅后填写confirmed与标签。','']
    for s in samples:
        validate_sample(s);t=s['task'];u=s['supervision']
        proposed=[];allowed={e['basis_id'] for e in t['evidence']}|{b['basis_id'] for b in t['other_basis']}
        for obs in s['observations']:
            review=obs.get('raw_model_review') or {};bases=obs.get('model_finding_bases',[])
            chosen=[bases[i] for i in review.get('basis_indexes',[]) if type(i) is int and 0<=i<len(bases)]
            chosen+=review.get('bases',[])
            proposed += [b['quote_id'] for b in chosen if isinstance(b,dict) and b.get('quote_id') in allowed]
        entries.append({'sample_id':s['sample_id'],'task_sha256':task_key(t),'status':'pending','label':None,
            'suggestion_label':u['suggestion_label'],'suggestion_method':u['suggestion_method'],'suggestion_basis_ids':sorted(set(proposed)),
            'source':'ai_assisted_user_supervised','reviewer_id':None,'note':'','basis_ids':[]})
        lines += ['## '+s['sample_id'][:16], '',f"任务：{t['task_type']}；分组：{s['group_id']}；集合：{s['split']}；synthetic={s['synthetic']}",
            '', '主张：'+escape(t['claim']['proposition']), '','立场/限定：'+escape(canonical({'stance':t['claim']['assertion_role'],'qualifiers':t['claim']['qualifiers'],'scope':t['claim']['scope']})),
            '', '建议：'+str(u['suggestion_label'])+'（pending；'+u['suggestion_method']+'）；'+u['rationale'],'','交付：'+t['required_evidence_delivery']+' / '+t['delivery_state'],'']
        if s['recipe']:lines+=['受控生成方式：'+canonical(s['recipe']),'']
        for e in t['evidence']:
            # Indented text cannot become HTML/scripts in the Markdown package.
            lines+=['依据 '+e['basis_id']+'；原文SHA '+e['text_sha256'],'',*['    '+line for line in e['text'].splitlines()],
                '', '来源与定位（提取文本，未核PDF视觉原文）：'+escape(canonical(e['metadata'])),'']
        for b in t['other_basis']:lines+=['非文献依据 '+b['basis_id']+'：'+canonical(b),'']
        lines+=['原模型/程序/反馈（不等同监督标签）：','',*['    '+line for line in json.dumps(s['observations'],ensure_ascii=False,indent=2).splitlines()],
            '', '来源关系：'+canonical([{k:v for k,v in o.items() if k not in ('response_file','archive_group')} for o in s['origins']]),
            '', '待确认：'+'；'.join(u['checklist']),'']
    write(directory/'review-labels.json',{'schema_version':VERSION,'reviews':entries})
    write(directory/'review-samples.json',{'schema_version':VERSION,'samples':samples})
    (directory/'review.md').write_text('\n'.join(lines)+'\n',encoding='utf8')

def apply_reviews(samples,review_bundle):
    output=deepcopy(samples);byid={s['sample_id']:s for s in output};seen=set()
    for review in review_bundle['reviews']:
        sid=review['sample_id'];assert sid in byid and sid not in seen,'unknown/duplicate sample review';seen.add(sid)
        assert review['task_sha256']==task_key(byid[sid]['task']),'review task mismatch'
        if review['status']=='pending':continue
        assert review['status'] in ('confirmed','disputed') and review['source'] in ('user','ai_assisted_user_supervised')
        ids={e['basis_id'] for e in byid[sid]['task']['evidence']}|{b['basis_id'] for b in byid[sid]['task']['other_basis']}
        assert set(review.get('basis_ids',[]))<=ids,'review basis out of scope'
        old=byid[sid]['supervision'];byid[sid]['supervision']=dict(old,**{k:v for k,v in review.items() if k not in ('sample_id','task_sha256','suggestion_label')})
        byid[sid].setdefault('review_history',[]).append(review);validate_sample(byid[sid])
    return output

def feedback_from_db(path):
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as db:
        values=[json.loads(row[0]) for row in db.execute('SELECT payload FROM reviews ORDER BY created,id')]
        for r in values:
            row=db.execute("SELECT payload FROM objects WHERE run_id=? AND kind='finding' AND id=? AND version=?",
                           (r['run_id'],r.get('finding_id'),r['answer_version'])).fetchone()
            r['associated_finding']=None if row is None else json.loads(row[0])
        return values

def result_lookup(paths):
    lookup={}
    for path in paths:
        result=read(path);rid=result['execution']['run_id'];item={'original_answer':(result['answer']['original'] or {}).get('text'), 'finding_ids':{}}
        for r in result.get('review_rounds',[]):
            for f in r['verification']['findings']:item['finding_ids'][(r['answer']['answer_id'],r['answer']['version'],f['claim_id'])]=f['finding_id']
        lookup[rid]=item
    return lookup

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    b=sub.add_parser('build');b.add_argument('--archives',required=True);b.add_argument('--output',required=True)
    b.add_argument('--feedback-db',action='append',default=[]);b.add_argument('--result',action='append',default=[])
    b.add_argument('--per-topic',type=int,default=4)
    b.add_argument('--model-id',action='append',required=True,help='Explicit archive model allowlist; use synthetic_fixture for fixtures')
    for action in ('validate','export','review'):
        q=sub.add_parser(action);q.add_argument('--dataset',required=True)
        if action!='validate':q.add_argument('--output',required=True)
        if action=='review':q.add_argument('--reviews',required=True)
    a=p.parse_args()
    if a.action=='build':
        directory=Path(a.output);directory.mkdir(parents=True,exist_ok=False)
        feedback=[r for db in a.feedback_db for r in feedback_from_db(db)]
        raw,skipped=extract(a.archives,feedback=feedback,result_index=result_lookup(a.result),model_ids=set(a.model_id));unique=deduplicate(raw)
        write(directory/'candidate-pool.json',{'schema_version':VERSION,'samples':unique,'skipped':skipped})
        write(directory/'feedback-events.json',{'events':feedback,'labels_promoted':0,'rule':'preserved source events; no implicit four-class gold conversion'})
        # Cohort size is an explicit human-review sampling rule, not a call cap.
        selected=[];counts={}
        for s in sorted(unique,key=lambda s:(not s['eligible_for_baseline'],not any(o.get('human_feedback') for o in s['observations']),not any(isinstance(o.get('delivery'),dict) for o in s['observations']),s['sample_id'])):
            if not s['eligible_for_baseline']:continue
            key=(s['task']['task_type'],s['issue_tags'][0])
            if counts.get(key,0)<a.per_topic:selected.append(s);counts[key]=counts.get(key,0)+1
        variants=controlled(selected);cohort=deduplicate(selected+variants);group_report=group(cohort)
        report={'raw_samples':len(raw),'deduplicated_pool':len(unique),'selected_originals':len(selected),'controlled_variants':len(variants),
            'cohort_samples':len(cohort),'feedback_events':len(feedback),'linked_feedback_observations':sum(bool(o.get('human_feedback')) for s in cohort for o in s['observations']),
            'excluded_invalid_structure':sum(not s['eligible_for_baseline'] for s in unique),'archive_skips':skipped,
            'sampling_rule':{'per_task_type_first_issue_topic':a.per_topic,'model_ids':a.model_id,'order':'eligible, feedback-linked, explicit delivery mapping, stable task SHA; not model label'},'groups':group_report}
        write(directory/'dataset.json',{'schema_version':VERSION,'samples':cohort,'report':report})
        write(directory/'source-split-report.json',report);export_review(cohort,directory/'review-package')
        print(canonical({k:v for k,v in report.items() if k not in ('archive_skips','groups')}|{'families':group_report['independent_family_count']}))
    else:
        bundle=read(a.dataset);samples=bundle['samples'];[validate_sample(s) for s in samples]
        if a.action=='export':export_review(samples,a.output)
        elif a.action=='review':write(a.output,dict(bundle,samples=apply_reviews(samples,read(a.reviews))))
        print(canonical({'validated_samples':len(samples),'action':a.action}))
if __name__=='__main__':main()
