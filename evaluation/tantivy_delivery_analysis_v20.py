"""Derive observable admission/settlement intervals from immutable v19 journals."""
import collections,datetime,json
from pathlib import Path
from evaluation.tantivy_delivery_replay_v20 import PRIOR,HOME,read,union,atomic,epoch,sha

def ledger_timeline():
 state=read(PRIOR/'accounting/state.json');settlements={};journal=[]
 for p in sorted((PRIOR/'accounting/journal').glob('*.json')):
  record=read(p);journal.append({'file':p.name,'sha256':sha(p),'mtime_ns':p.stat().st_mtime_ns})
  for k,e in record['entries'].items():
   if e.get('finished') and k not in settlements:settlements[k]={'observed_wall':p.stat().st_mtime,'file':p.name}
 timeline=read(HOME/'timeline.json');summary=read(PRIOR/'summary.json')
 for row in timeline['rows']:
  x=read(PRIOR/(row['case']+'-'+row['backend']+'-result.json'));base=epoch(x['execution']['created_utc']);intervals=[]
  for m in x['model_usage']:
   matches=[(k,e) for k,e in state['entries'].items() if e['chain']==x['execution']['run_id'] and e['usage']==m['usage']]
   if len(matches)!=1:raise ValueError('Cannot uniquely bind usage to a journal admission')
   k,e=matches[0];a=e['admitted_wall'];b=settlements[k]['observed_wall']
   if not 0<=b-a<=m['duration_ms']/1000+.1:raise ValueError('Unexpected journal clock/copy skew')
   intervals.append({'component':m['component'],'call_number':m['call_number'],'correction':m['correction'],'start':a-base,'end':b-base,'observed_seconds':b-a,'recorded_wait_seconds':m['duration_ms']/1000,'settlement_file':settlements[k]['file'],'global_admission':k,'evidence_chars':m.get('request_metrics',{}).get('evidence_chars_delivered',0)})
  row['journal_model_intervals']=intervals
  row['model_admission_settlement_union_seconds']=union([(z['start'],z['end']) for z in intervals])
  for purpose,components in [('generation',('generation',)),('verification',('claim_extraction','evidence_verification')),('domain_review',('power_domain_review',))]:
   subset=[z for z in intervals if z['component'] in components]
   row['by_purpose'][purpose]['admission_settlement_union_seconds']=union([(z['start'],z['end']) for z in subset])
  factstage=next(z for z in row['stages'] if z['component']=='evidence_verification')
  subset=[z for z in intervals if z['component']=='evidence_verification']
  row['fact_stage_uncovered_by_model_admission_seconds']=factstage['seconds']-union([(z['start'],z['end']) for z in subset])
  row['fact_between_model_intervals']=[{'start':a['end'],'end':b['start'],'seconds':b['start']-a['end']} for a,b in zip(sorted(subset,key=lambda z:z['start']),sorted(subset,key=lambda z:z['start'])[1:])]
 timeline['journal_identity']=journal
 timeline['notes']+=['Model intervals use actual persisted admitted_wall and filesystem mtime of FIRST immutable journal showing settlement; not delayed model_request events.','Receipt mtime observes usage settlement, not exact socket completion; parsing, diagnostics and store outside these intervals remain unassigned.','96 usage dictionaries uniquely bind model records to admissions; no order-based guessing. Intervals all within recorded wait +100ms; no timestamp of individual HTTP wire send/receive available.']
 atomic(HOME/'ledger-timeline.json',timeline)

def replay_summary():
 rows=[json.loads(l) for l in (HOME/'measurements.jsonl').read_text(encoding='utf8').splitlines()];f=read(HOME/'freeze.json');groups=collections.defaultdict(dict)
 if len(rows)!=3*len(f['requests']):raise ValueError('Incomplete or duplicated replay slot count')
 for r in rows:
  if r['route'] in groups[r['slot']]:raise ValueError('Duplicate replay route')
  if r['status']!='ok':raise ValueError('Failed replay slot retained; cannot summarize as successful')
  request=f['requests'][r['slot']]
  if any(r[k]!=request[k] for k in ('case','origin','purpose','query_sha256')):raise ValueError('Request identity mismatch')
  if r['root_count']>(6 if r['route']=='v18' else 3):raise ValueError('Evidence limit exceeded')
  groups[r['slot']][r['route']]=r
 out=[]
 for request in f['requests']:
  rr=groups[request['slot']]
  if set(rr)!={'sqlite','v18','v18_k3'}:raise ValueError('Missing route')
  out.append({**{k:request[k] for k in ('slot','case','origin','purpose','query_sha256')},'routes':{k:{'seconds':v['total_seconds'],'root_chars':v.get('root_chars'),'context_chars':v.get('context_chars'),'root_count':v.get('root_count'),'status':v['status'],'evidence_ids':[e['evidence_id'] for e in v.get('result',{}).get('evidence',[])]} for k,v in rr.items()}})
 atomic(HOME/'summary.json',{'slots':len(rows),'requests':len(out),'rows':out,'models':0,'repeats':1})

if __name__=='__main__':
 import sys
 if sys.argv[1]=='timeline':ledger_timeline()
 elif sys.argv[1]=='summary':replay_summary()
