"""Summarize paired final-boundary recordings; no model or new retrieval."""
import json,collections
from evaluation.audit_tantivy_boundary_v21 import HOME,read
from pathlib import Path
OUT=Path('docs/evaluation/audit-tantivy-v21')

def main():
 x=read(HOME/'summary.json');groups=collections.defaultdict(list)
 for r in x['requests']:groups[(r['slot'],r['category'],r['route'])].append(r)
 pairs=[]
 for (slot,cat,route),rr in groups.items():
  if route!='sqlite':continue
  cc=groups[(slot,cat,'candidate')];assert len(rr)==len(cc)
  for ordinal,(b,c) in enumerate(zip(rr,cc)):
   assert all(b[k]==c[k] for k in ('answer_id','snapshot_id','case','origin','question'))
   pairs.append(dict(slot=slot,category=cat,ordinal=ordinal,case=b['case'],origin=b['origin'],conditional_supplement=b['conditional_supplement'],sqlite=b['metrics'],candidate=c['metrics'],extra=c['metrics']['evidence_chars_delivered']-b['metrics']['evidence_chars_delivered']))
 assert len(pairs)==70 and len({p['slot'] for p in pairs})==36
 totals={}
 for route in ('sqlite','candidate'):
  totals[route]={cat:{'requests':len(rr:=[p for p in pairs if p['category']==cat]),'evidence_chars':sum(p[route]['evidence_chars_delivered'] for p in rr),'message_chars':sum(p[route]['message_chars'] for p in rr)} for cat in ('independent','original_citation','domain')}
 primary={route:sum(p[route]['evidence_chars_delivered'] for p in pairs if p['origin']=='baseline') for route in ('sqlite','candidate')}
 corrections=sum(r['metrics']['evidence_chars_delivered'] for r in x['historical_corrections']);primary_corrections=sum(r['metrics']['evidence_chars_delivered'] for r in x['historical_corrections'] if r['origin']=='baseline')
 summary=dict(totals=totals,primary_sqlite_drafts=primary,paired_initial_extra=sum(p['extra'] for p in pairs),historical_correction_requests=len(x['historical_corrections']),historical_correction_evidence_chars=corrections,primary_historical_correction_evidence_chars=primary_corrections,primary_conservative_excess=primary['candidate']-primary['sqlite']-primary_corrections,pairs=pairs,models_real=0,paid_gate=False,correction_pairing='Old corrections can be boundary-replayed exactly only with old scope and old response; no prediction of new candidate corrections.',measurement='Actual adapter ModelRequest after normal auditors, review_transport, optional v21 sharing and ModelClient. Recorder raises ModelOutputError to stop response/correction inference.')
 OUT.mkdir(exist_ok=True);(OUT/'boundary-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
 (HOME/'pairs.json').write_text(json.dumps(pairs,ensure_ascii=False,indent=2),encoding='utf8')
 lines=['# v21 最终模型边界逐请求配对','', '每行一个实际模型请求对；slot是原检索槽，不是模型调用序号。B/C起源分别为SQLite/v18自然初稿，各行两路初稿、快照、历史审核时点相同。supp表示基于已冻结历史状态的条件性主体补检。原引用分组由正常合同决定，未固定为一检索一模型。','','|slot|题/起源|模型职责|组内序号|条件补检|SQLite证据字|候选证据字|多字|SQLite全消息字|候选全消息字|','|---|---|---|---:|---|---:|---:|---:|---:|---:|']
 for p in pairs:lines.append(f"|{p['slot']}|{p['case']}/{p['origin']}|{p['category']}|{p['ordinal']}|{p['conditional_supplement']}|{p['sqlite']['evidence_chars_delivered']}|{p['candidate']['evidence_chars_delivered']}|{p['extra']:+}|{p['sqlite']['message_chars']}|{p['candidate']['message_chars']}|")
 (OUT/'boundary-results.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 print('Paired70 model requests /36 retrieval slots; primary conservative excess',summary['primary_conservative_excess'])
if __name__=='__main__':main()
