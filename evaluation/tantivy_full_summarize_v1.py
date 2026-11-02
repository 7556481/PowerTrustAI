"""Mechanical metrics only. Never emits semantic approval or a release switch."""
import json,statistics
from pathlib import Path
from rag.tantivy_build import atomic
from evaluation.tantivy_full_build_v1 import ROOT

def offline():
 freeze=json.loads((ROOT/'offline-freeze.json').read_text(encoding='utf8'));rows=[json.loads(x) for x in (ROOT/'full-measurements.jsonl').read_text(encoding='utf8').splitlines()];out=[]
 for q in freeze['queries']:
  entry={'id':q['id'],'category':q.get('category'),'question':q['query'],'semantic_review':'unknown','backends':{}}
  for name in ('baseline','fast'):
   allrows=[r for r in rows if r['query']==q['id'] and r['backend']==name];ok=[r for r in allrows if r['status']=='ok'];delivered=[([e['provenance']['fragment_id'] for e in r['roots']],[e['provenance']['fragment_id'] for e in r['neighbors']]) for r in ok];entry['backends'][name]={'submitted_reads':len(allrows),'complete':len(ok),'errors':[r.get('error') for r in allrows if r['status']!='ok'],'first_access_seconds':next((r['total_seconds'] for r in allrows if r['round']==0 and r['status']=='ok'),None),'later_seconds':[r['total_seconds'] for r in ok if r['round']>0],'median_seconds':statistics.median(r['total_seconds'] for r in ok) if len(ok)==3 else None,'delivery_stable':all(x==delivered[0] for x in delivered) if delivered else None,'root_chars':[sum(len(e['text']) for e in r['roots']) for r in ok],'neighbor_chars':[sum(len(e['text']) for e in r['neighbors']) for r in ok]}
  b=entry['backends']['baseline']['median_seconds'];f=entry['backends']['fast']['median_seconds'];entry['ratio']=b/f if b is not None and f is not None and f>0 else None;out.append(entry)
 wide=[r for r in out if r['category']=='wide'];ratios=[r['ratio'] for r in wide if r['ratio'] is not None];speed=statistics.median(ratios) if wide and len(ratios)==len(wide) else None
 summary={'queries':out,'records':len(rows),'expected_records':144,'wide_median_ratio':speed,'wide_speed_gate':speed is not None and speed>=1.5,'quality_gate':'unreviewed; requires actual text review, not ID equality','first_access_is_cold_disk':False,'models':0};atomic(ROOT/'offline-metrics.json',summary);return summary

def product():
 root=Path('D:/PowerTrustAI/data/runtime_local/tantivy-full-fast-v1/comparison');f=json.loads((root/'freeze.json').read_text(encoding='utf8'));totals=json.loads((root/'totals.json').read_text(encoding='utf8'));rows=totals['rows'];pairs=[]
 for case in f['cases']:
  by={r['backend']:r for r in rows if r['case']==case['id']};pair={'case':case['id'],'backends':by,'semantic_review':'unknown'}
  if all(name in by and by[name]['complete'] for name in ('baseline','fast')):
   b=by['baseline']['terminal_observed_seconds'];c=by['fast']['terminal_observed_seconds'];pair.update(both_complete=True,saved_seconds=b-c,fraction_saved=(b-c)/b)
  else:pair['both_complete']=False
  pairs.append(pair)
 comparable=[p for p in pairs if p['both_complete']];b=statistics.median(p['backends']['baseline']['terminal_observed_seconds'] for p in comparable) if comparable else None;c=statistics.median(p['backends']['fast']['terminal_observed_seconds'] for p in comparable) if comparable else None
 complete={name:sum(r['complete'] for r in rows if r['backend']==name) for name in ('baseline','fast')};summary={'pairs':pairs,'complete':complete,'complete_pairs':len(comparable),'baseline_terminal_median':b,'fast_terminal_median':c,'median_terminal_saved_seconds':b-c if b is not None else None,'median_terminal_fraction_saved':(b-c)/b if b is not None else None,'formula':'same set of complete pairs: difference between backend terminal medians; also disclose each pair savings','quality_gate':'unreviewed; honest insufficiency not automatically useful; no speed credit for new insufficiency or critical regression','calls_admitted':totals['admissions'],'trusted_tokens':totals['trusted_tokens'],'billing_amount':None};atomic(root/'metrics.json',summary);return summary
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['offline','product']);a=p.parse_args();print(json.dumps(offline() if a.kind=='offline' else product(),ensure_ascii=False))
