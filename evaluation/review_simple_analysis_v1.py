"""Deterministic accounting; labels frozen before prediction, human reading separate."""
import json
from collections import Counter,defaultdict
from datetime import datetime
from evaluation.public_review_validation_trial_v1 import read,write
from agents.verification_contract_v14 import MARKER


def assessment(rationale):
    for marker in (MARKER,' [source-support-relation-v6] '):
        if marker in rationale:return json.loads(rationale.split(marker,1)[1])
    return None


def union_ms(intervals):
    total=0;end=None
    for a,b in sorted(intervals):
        total+=max(0,b-max(a,end if end is not None else a));end=max(b,end if end is not None else b)
    return round(total*1000,3)


def analyze(local,public):
    s=read(local/'batch/summary.json');m=read(local/'materials.json');fixed=[];invalid=[];lines=defaultdict(Counter);branches=[]
    for c in s['control']:
        rid=c.get('accepted',{}).get('run_id');spec=c.get('accepted',{}).get('spec',{});r=s['outputs'].get(rid)
        if r is None:continue
        line=spec['line']+'/'+spec['variant'];metric=lines[line];metric['accepted']+=1
        if r['state']=='unexecuted':metric['dependent_unexecuted']+=1;continue
        metric['executed']+=1;metric['execution_complete']+=not bool(r.get('execution_issues')) and r['state']!='failed'
        records=r.get('model_records',[]);initial=[x for x in records if not x['correction']]
        metric['all_initial_valid_tasks']+=all(not x.get('validation_error') for x in initial)
        metric['duration_ms_sequential_harness_sum']+=r.get('duration_ms',0)
        metric['revisions']+=len(r.get('revision_outputs',[]))
        for rec in records:
            metric['calls']+=1;metric['corrections']+=rec['correction'];metric['initial']+=not rec['correction'];metric['initial_valid']+=not rec['correction'] and not rec.get('validation_error')
            stage=rec.get('component');metric['revision_calls']+=stage=='revision';metric['rereview_calls']+=stage in ('claim_extraction','evidence_verification','power_domain_review') and (rec.get('answer_version') or 1)>1
            metric['model_duration_ms_not_wallclock']+=rec['duration_ms']
            for key in ('input_tokens','output_tokens','total_tokens','cache_hit_tokens','cache_miss_tokens'):metric[key]+=(rec.get('usage') or {}).get(key) or 0
            if rec.get('validation_error'):
                d=rec['validation_error'];invalid.append(dict(id=c['case_id'],call=rec['call_number'],prompt_version=rec['prompt_version'],correction=rec['correction'],constraints=sorted({e['constraint'] for e in d.get('errors',[d])}),diagnostic=d))
        intervals=defaultdict(list)
        for e in r.get('trace',{}).get('events',[]):
            component=e['component'];version=e.get('answer_version') or 1
            bucket='retrieval' if component.startswith('retrieval_') else 'generation' if component=='generation' else 'revision' if component=='revision' else 'rereview' if version>1 and component in ('claim_extraction','evidence_verification','power_domain_review') else 'initial_audit' if component in ('claim_extraction','evidence_verification','power_domain_review') else None
            if bucket:
                end=datetime.fromisoformat(e['timestamp_utc']).timestamp();intervals[bucket].append((end-e['duration_ms']/1000,end))
        branches.append(dict(id=c['case_id'],state=r['state'],duration_ms=r.get('duration_ms'),root_stage_union_ms={k:union_ms(v) for k,v in intervals.items()},revision_count=len(r.get('revision_outputs',[]))))
        if spec['line']!='A' or not r.get('verification_output'):continue
        v=r['verification_output']
        for i,(f,cit,ref) in enumerate(zip(v['findings'],v['citation_reviews'],m['A'][spec['case']]['reference'])):
            part=f['component_reviews'][0];a=assessment(part['rationale']);ca=assessment(cit['rationale'])
            executed=part.get('origin')!='execution_incomplete';ce=not cit['rationale'].startswith('model_execution_incomplete')
            fixed.append(dict(id=c['case_id'],unit=i,reference=ref,fact_executed=executed,fact_raw=part.get('raw_support_status') if executed else None,fact_effective=part['status'],fact_assessment=a,citation_executed=ce,citation_raw=ca['raw_model_status'] if ca and ce else None,citation_effective=cit['status'],citation_assessment=ca,fact_reference_aligned=executed and part['status']==ref,citation_reference_aligned=ce and cit['status']==ref))
    result=dict(plan=Counter(x['input']['line'] for x in s['planned']),accepted=len(s['control']),actually_executed=sum(v['executed'] for v in lines.values()),not_submitted_after_stop=s['unexecuted'],dependent_unexecuted=[c['case_id'] for c in s['control'] if s['outputs'].get(c.get('accepted',{}).get('run_id'),{}).get('state')=='unexecuted'],lines=dict(lines),fixed_units=fixed,invalid_attempts=invalid,root_constraint_request_counts=dict(Counter(k for x in invalid for k in set(x['constraints']))),branches=branches,invoice_cost=None,timing_method='Union of root-stage finish-minus-duration intervals; model request times and Harness totals are separate, not additive. No browser paint.')
    write(public/'evaluation.json',result)
    return result
