"""Read-only projection and accounting; never decides answer quality from pass."""
import hashlib
import json
from collections import defaultdict
from evaluation.answer_review_net_benefit_v1 import ROOT, PUBLIC, LOCAL
from evaluation.public_review_validation_trial_v1 import read, write, sha


def review_projection(r):
    rounds=[]
    for rr in r.get('review_rounds',[]):
        v=rr['verification'];d=rr['domain_review']
        rounds.append(dict(answer=rr['answer'],claims=v['claims'],findings=v['findings'],
            citation_reviews=v['citation_reviews'],domain_findings=d['findings'],
            decision=rr['report']['decision'],verification_issues=v['execution_issues'],domain_issues=d['execution_issues']))
    return dict(run_id=r['run_id'],state=r['state'],answer=r.get('answer'),rounds=rounds,
        revisions=[dict(answer=v['answer'],finding_actions=v.get('finding_actions',[]),changes=v.get('changes',[]),
            unresolved_finding_ids=v.get('unresolved_finding_ids',[])) for v in r.get('revision_outputs',[])],
        execution_issues=r.get('execution_issues',[]),
        evidence=[dict(evidence_id=e['evidence_id'],source_id=e['source_id'],source_version=e['source_version'],locator=e['locator'],text_sha256=sha(e['text'])) for e in r.get('evidence',[])])


def audit():
    rows=[]
    for label,path in [('recent-production','data/evaluation_local/langgraph-service-continuation-v1/batch-v1/summary.json'),
                       ('old-collection-failure','data/evaluation_local/langgraph-service-integration-v1/batch-v1/summary.json'),
                       ('historical-revision','data/retrieval_local/deepseek/revision-constructed-v1.json'),
                       ('historical-rereview','data/retrieval_local/deepseek/revision-normal-voltage-v2.json')]:
        p=ROOT/path;s=read(p)
        branches=s.get('branches',s.get('runs',[]))
        for b in branches:
            r=b.get('result')
            if not r:
                rows.append(dict(group=label,archive=path,archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),branch=b.get('id'),status=b.get('status','no_result')))
                continue
            rows.append(dict(group=label,archive=path,archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),branch=b.get('id'),question=b.get('question'),diagnosis=review_projection(r)))
    # Necessary prediction bodies/findings, not full official source bodies.
    write(PUBLIC/'archive-breakpoints.json',rows)
    print('Archive projection saved; no model or historical state mutation.')


def report():
    root=LOCAL/'batch';s=read(root/'summary.json');branches=[];usage=defaultdict(lambda:defaultdict(int))
    for c in s['control']:
        rid=c.get('accepted',{}).get('run_id');spec=c.get('accepted',{}).get('spec',{})
        r=s['outputs'].get(rid)
        if not r:
            branches.append(dict(id=c['case_id'],control=c,status='execution_failed'));continue
        p=review_projection(r) if r.get('answer') else dict(run_id=rid,state=r['state'],execution_issues=r.get('execution_issues',[]),reason=r.get('reason'))
        p.update(id=c['case_id'],task=spec,control=c)
        directory=root/rid
        if (directory/'input.json').exists():
            inp=read(directory/'input.json')
            p['actual_question']=inp['request']['question'];p['initial_answer']=inp['request'].get('existing_answer')
            p['input_sha256']=sha(inp)
            p['generation_snapshot_sha256']=sha(inp['generation_snapshot']) if inp['generation_snapshot'] else None
        if (directory/'observations.json').exists():p['observations']=read(directory/'observations.json')
        p['duration_ms']=r.get('duration_ms');p['call_metrics']=[]
        for rec in r.get('model_records',[]):
            u=rec.get('usage') or {};component=rec.get('component') or rec['prompt_version']
            key=f'{spec["line"]}/{spec["variant"]}/{component}/v{rec.get("answer_version")}'
            a=usage[key];a['calls']+=1;a['corrections']+=int(rec['correction']);a['request_duration_ms_sum_not_wallclock']+=rec['duration_ms']
            for k in ('input_tokens','output_tokens','total_tokens','cache_hit_tokens','cache_miss_tokens'):
                if u.get(k) is not None:a[k]+=u[k]
                else:a[k+'_unknown_records']+=1
            p['call_metrics'].append({k:rec.get(k) for k in ('call_number','component','answer_version','prompt_version','correction','status','duration_ms','usage','output_status','error_code','validation_error')})
        p['stage_events']=[{k:e.get(k) for k in ('component','answer_version','duration_ms','status')} for e in r.get('trace',{}).get('events',[]) if e['component'] in ('generation','claim_extraction','evidence_verification','power_domain_review','revision') or e['component'].startswith('retrieval_')]
        branches.append(p)
    for ident in s['unexecuted']:branches.append(dict(id=ident,status='unexecuted',reason='shared_stop'))
    predictions=[]
    for sent in s['send_log']:
        n=sent['sequence'];p=root/'responses'/f'{n:04d}.json'
        predictions.append(sent | dict(response=read(p) if p.exists() else None))
    write(PUBLIC/'predictions.json',predictions)
    write(PUBLIC/'results.json',branches)
    statistics=dict(planned=dict(A=8,generation=4,B=8),accepted=len(s['control']),unexecuted=s['unexecuted'],actual_sends=len(predictions),
        records=sum(x['calls'] for x in usage.values()),by_stage=dict(usage),invoice_cost=None,
        note='Generation counted once, B independently deducts its calls/time from original shared limits. Parallel/nested durations are not summed as wallclock. No browser paint measurement or pass-rate quality estimate.')
    write(PUBLIC/'statistics.json',statistics)
    print(json.dumps(dict(sends=len(predictions),records=statistics['records'],branches=len(branches)),ensure_ascii=False))


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['audit']:audit()
    elif sys.argv[1:]==['report']:report()
    else:raise SystemExit('audit | report')
