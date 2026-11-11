"""Post-run read-only paired analysis; never calls a model or resumes a batch."""
import json,statistics,collections,hashlib,difflib,sqlite3
from pathlib import Path
from evaluation.fact_domain_overlap_run_v23 import HOME,read
OUT=Path('docs/evaluation/fact-domain-overlap-v23')
def main():
 h=HOME/'real';records=read(h/'summary.json');assert len(records)==16;rows=[];allqueue=[];rawissues=[]
 frozen=read(h/'full-identity-before-admission.json')
 for p,digest in frozen['sources'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,('frozen source changed',p)
 for case in dict.fromkeys(r['case'] for r in records):
  rr={r['route']:r for r in records if r['case']==case};items={route:read(h/case/route/'result.json') for route in rr};events={route:read(h/case/route/'events.json') for route in rr}
  assert items['serial']['answer']['versions'][0]==items['overlap']['answer']['versions'][0]
  variants={}
  for route,x in items.items():
   initial=x['answer']['versions'][0];final=x['answer']['final'];assert initial==final
   (h/case/route/'answer-diff.txt').write_text(''.join(difflib.unified_diff(initial['text'].splitlines(True),final['text'].splitlines(True),fromfile='historical-draft',tofile='final')),encoding='utf8')
   # Store objects independently replay full answer and source bindings.
   db=sqlite3.connect('file:'+str(h/case/route/'runs.sqlite3')+'?mode=ro',uri=True);raw=json.loads(db.execute('select result from runs where id=?',(rr[route]['run_id'],)).fetchone()[0]);db.close();assert raw['answer']==final
   ev=events[route];zero=next(e['time'] for e in ev if e['kind']=='draft_entered');ds=next(e['time'] for e in ev if e['kind']=='retrieval_start' and e.get('purpose')=='domain_review');de=next(e['time'] for e in ev if e['kind']=='retrieval_end' and e.get('purpose')=='domain_review');fs=next(e['time'] for e in ev if e['kind']=='request_dispatch' and e.get('component')=='evidence_verification');http=next(e['time'] for e in ev if e['kind']=='http_worker_begin' and e.get('component')=='evidence_verification')
   if route=='overlap':assert ds<fs<de and ds<http<de
   queue=[]
   pending=collections.defaultdict(list)
   for e in sorted(ev,key=lambda e:e['time']):
    if e['kind']=='request_dispatch':pending[e['component']].append(e['time'])
    elif e['kind']=='http_worker_begin' and pending[e['component']]:queue.append(e['time']-pending[e['component']].pop(0))
   allqueue+=queue
   usage=x['model_usage'];roles={component:{'calls':len(mm:=[m for m in usage if m['component']==component]),'corrections':sum(m['correction'] for m in mm),'request_ms_sum':sum(m['duration_ms'] or 0 for m in mm),'input_tokens':sum((m.get('usage') or {}).get('input_tokens',0) for m in mm),'output_tokens':sum((m.get('usage') or {}).get('output_tokens',0) for m in mm),'evidence_chars':sum((m.get('request_metrics') or {}).get('evidence_chars_delivered',0) for m in mm)} for component in ('claim_extraction','evidence_verification','power_domain_review','revision')}
   finishes={component:max((e['time']-zero for e in ev if e['kind']=='review_complete' and e['component']==component),default=None) for component in ('evidence_verification','power_domain_review')}
   variants[route]=dict(seconds=rr[route]['post_draft_seconds'],complete=rr[route]['complete'],decision=x['decision']['kind'],calls=len(usage),corrections=sum(m['correction'] for m in usage),tokens=sum((m.get('usage') or {}).get('total_tokens',0) for m in usage),retrieval_seconds={purpose:sum(r['duration_ms'] for r in x['retrieval'] if r['purpose']==purpose)/1000 for purpose in ('verification','domain_review')},roles=roles,relative_events=dict(fact_dispatch=fs-zero,http_worker_begin=http-zero,domain_retrieve_start=ds-zero,domain_retrieve_return=de-zero,**finishes,answer_readable=rr[route]['post_draft_seconds']),queue_envelope_seconds=queue,rate_limit_429_observed=sum((m.get('network_diagnostic') or {}).get('http_status')==429 for m in usage),final_equals_draft=True,final_object_equals_store=True)
  rows.append(dict(case=case,routes=variants,complete_pair=all(v['complete'] for v in variants.values()),saved_seconds=variants['serial']['seconds']-variants['overlap']['seconds'],body_difference=False))
 good=[r for r in rows if r['complete_pair']];base=statistics.median(r['routes']['serial']['seconds'] for r in good);cand=statistics.median(r['routes']['overlap']['seconds'] for r in good)
 state=read(h/'accounting/state.json');assert all(e.get('finished') and not e.get('inflight') and e.get('usage') is not None for e in state['entries'].values())
 counts={route:sum(r['routes'][route]['complete'] for r in rows) for route in ('serial','overlap')}
 gate=len(good)>=6 and counts['overlap']>=counts['serial'] and base-cand>=3 and (base-cand)/base>=.15
 summary=dict(rows=rows,complete_pairs=len(good),complete_chains=counts,serial_median=base,overlap_median=cand,saving_seconds=base-cand,saving_fraction=(base-cand)/base,speed_and_integrity_gate=gate,body_quality_review='All final objects equal the same initial draft, so no new text error/condition deletion/misrevision. Shared existing defects remain; disposition and reviewer rationales vary; not expert gold or safety certification.',calls=state['calls'],trusted_tokens=state['trusted_tokens'],unknown_usage=0,pending=0,queue_envelope_median=statistics.median(allqueue),queue_envelope_max=max(allqueue),source_identity_after_equal=True)
 (h/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');OUT.mkdir(parents=True,exist_ok=True);(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
 print('Gate',gate,'complete',len(good),'medians',base,cand,'queue envelope median/max',statistics.median(allqueue),max(allqueue))
if __name__=='__main__':main()
