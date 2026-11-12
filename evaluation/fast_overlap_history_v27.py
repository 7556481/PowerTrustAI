from pathlib import Path
import json,sqlite3,hashlib,statistics,collections
HOME=Path('D:/PowerTrustAI/data/runtime_local/fast-overlap-v27');BASE=HOME.parent;P19=BASE/'tantivy-product-v19';P20=BASE/'tantivy-delivery-replay-v20';P23=BASE/'fact-domain-overlap-v23/real'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def request_at(dbpath,rid):
 db=sqlite3.connect(Path(dbpath).as_uri()+'?mode=ro',uri=True)
 try:return json.loads(db.execute('select request from runs where id=?',(rid,)).fetchone()[0])
 finally:db.close()
def options(v):
 return {k:v.get(k) for k in ('scenario_id','max_results','context_options','execution_profile')}
def main():
 freeze=read(P20/'freeze.json');measures=[json.loads(line) for line in (P20/'measurements.jsonl').read_text(encoding='utf-8').splitlines()];mm={(r['slot'],r['route']):r for r in measures};cases=read(P19/'summary.json')['pairs'];questions={}
 for pair in cases:
  for origin in ('baseline','fast'):
   result=read(P19/(pair['case']+'-'+origin+'-result.json'));rid=result['execution']['run_id'];request=request_at(P19/origin/'runs.sqlite3',rid);questions[(pair['case'],origin)]=request['question']
 qrecords=[]
 for r in freeze['requests']:
  qrecords.append(dict(r,question_sha256=sha(questions[(r['case'],r['origin'])]),batch='v19-real8',options=options(r['options'])))
 v23=read(P23/'summary.json');timeline=read(P20/'timeline.json')['rows'];out=[];supplement=[]
 for case in [p['case'] for p in cases]:
  row=next(r for r in v23 if r['case']==case and r['route']=='overlap');folder=P23/case/'overlap';raw=read(folder/'result.json');request=request_at(folder/'runs.sqlite3',row['run_id']);question=request['question'];assert question==questions[(case,'baseline')]
  events=read(folder/'events.json');t0=next(e['time'] for e in events if e['kind']=='draft_entered');pending={};intervals=[]
  for e in events:
   if e['kind']=='retrieval_start':pending[e['purpose']]=e['time']
   elif e['kind']=='retrieval_end':
    begin=pending.pop(e['purpose']);intervals.append({'purpose':e['purpose'],'start':begin-t0,'end':e['time']-t0,'seconds':e['time']-begin})
  for v in intervals:v['seconds']=v['end']-v['start']
  records=[r for r in raw['retrieval'] if r.get('reused_from_retrieval_id') is None and r['purpose'] in ('verification','domain_review')]
  links=[];by_purpose=collections.defaultdict(list)
  for r in records:by_purpose[r['purpose']].append(r)
  for purpose,rs in by_purpose.items():
   ii=[v for v in intervals if v['purpose']==purpose]
   assert len(ii)==len(rs),(case,purpose,len(ii),len(rs))
   for record,interval in zip(rs,ii):
    qh=sha(record['query']);matched=[r for r in qrecords if r['origin']=='baseline' and r['question_sha256']==sha(question) and r['purpose']==purpose and r['query_sha256']==qh and r['knowledge_version']==record['knowledge_version'] and r['options']==options(record['request_options'])]
    link=dict(batch='v23-overlap-real8',question_sha256=sha(question),purpose=purpose,query_sha256=qh,knowledge_version=record['knowledge_version'],options=options(record['request_options']),historical_sqlite=interval,matched_slots=[r['slot'] for r in matched],record_duration_ms=record['duration_ms'])
    if matched:
     # Frozen duplicate slots refer to identical request bytes; report all identities, first observation only.
     item=mm[(matched[0]['slot'],'v18')];link['v20_native6_seconds']=item['total_seconds'];link['match_status']='exact question/purpose/query/config'
    else:
     link['match_status']='unknown; needs only this zero-model candidate request';supplement.append({'case':case,'question_sha256':sha(question),'query':record['query'],'query_sha256':qh,'purpose':purpose,'knowledge_version':record['knowledge_version'],'options':record['request_options']})
    links.append(link)
  f=next(e['time']-t0 for e in reversed(events) if e['kind']=='review_complete' and e['component']=='evidence_verification');d=next(e['time']-t0 for e in reversed(events) if e['kind']=='review_complete' and e['component']=='power_domain_review');vr=sum(x['seconds'] for x in intervals if x['purpose']=='verification');dr=sum(x['seconds'] for x in intervals if x['purpose']=='domain_review');last=max(f,d);zero=max(f-vr,d-vr-dr);upper=last-zero
  old=next(r for r in timeline if r['case']==case and r['backend']=='baseline');gen=[r for r in qrecords if r['case']==case and r['origin']=='baseline' and r['purpose']=='generation'];assert gen
  gen_sql=old['by_purpose']['generation']['retrieval_seconds'];gen_fast=sum(mm[(r['slot'],'v18')]['total_seconds'] for r in gen);gen_replays_sql=sum(mm[(r['slot'],'sqlite')]['total_seconds'] for r in gen)
  result=read(P19/(case+'-baseline-result.json'));generation_stage=[v for v in old['stages'] if v['component']=='generation'];generation_stage_end=max((v['end'] for v in generation_stage),default=None)
  out.append(dict(case=case,batch='v19-real8/v23-overlap-real8',question_sha256=sha(question),generation={'v19_sql_read_seconds':gen_sql,'v20_sql_replay_seconds':gen_replays_sql,'v20_native6_seconds':gen_fast,'optimistic_retrieval_zero_seconds_saved':gen_sql,'matched_native6_model_unchanged_estimated_seconds_saved':gen_sql-gen_fast,'server_generation_stage_end_seconds':generation_stage_end,'first_readable_observation':'historical stage end only; browser first visibility unavailable','requests':[r['slot'] for r in gen]},post_draft_sqlite_overlap_seconds=row['post_draft_seconds'],fact_finished=f,domain_finished=d,last_role='fact' if f>d else 'domain',verification_read_seconds=vr,domain_read_seconds=dr,optimistic_zero_read_seconds_saved=upper,optimistic_zero_read_terminal_seconds=row['post_draft_seconds']-upper,complete=row['complete'],issues=row['issues'],retrieval_links=links,model_assumption='hold every role model/queue/correction/store tail duration unchanged; optimistic retrieval only, not product measurement'))
 complete=[r for r in out if r['complete']];base=statistics.median(r['post_draft_sqlite_overlap_seconds'] for r in complete);optimistic=statistics.median(r['optimistic_zero_read_terminal_seconds'] for r in complete)
 report=dict(rows=out,requests56=len(qrecords),measurement_slots=len(measures),matched_audit_requests=sum(bool(r['matched_slots']) for row in out for r in row['retrieval_links']),unmatched_audit_requests=len(supplement),complete_pairs_for_historical_bound=len(complete),complete_baseline_median=base,complete_optimistic_zero_read_median=optimistic,optimistic_median_seconds_saved=base-optimistic,optimistic_fraction_saved=(base-optimistic)/base,optimistic_gate_pass=base-optimistic>=3 and (base-optimistic)/base>=.15,notes=['Different question batches never joined by Q label.','No multiplication of1.87 and29.20.','Model response/evidence changes may erase modeled saving.','Q3 failure retained; no prediction of successful terminal.'])
 (HOME/'history-bound.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');(HOME/'supplement-requests.json').write_text(json.dumps(supplement,ensure_ascii=False,indent=2),encoding='utf-8');(HOME/'question-association-private.json').write_text(json.dumps(qrecords,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False));print([(r['case'],round(r['generation']['matched_native6_model_unchanged_estimated_seconds_saved'],3),round(r['optimistic_zero_read_seconds_saved'],3),r['last_role'],r['complete']) for r in out])
if __name__=='__main__':main()
