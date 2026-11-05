"""Reopen saved isolated product chains; no index search, no model, no replay."""
import copy,json
from pathlib import Path
from backend.store import RunStore
from backend.service import ApplicationService
from backend.config import ServiceConfig
from backend.answer_annotations import project
from rag.tantivy_build import atomic
ROOT=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-product-v1')
def main():
 out={'real_model_calls':0,'cases':[]}
 for scope in ('million','quality674'):
  folder=ROOT/scope;store=RunStore(folder/'runs-r4.sqlite3');svc=ApplicationService(ServiceConfig(run_db=folder/'runs-r4.sqlite3'),store)
  try:
   assert len(store.list_runs()['items'])==3
   for label in ('ordinary','insufficient','revision'):
    saved=json.loads((folder/(label+'-result-r4.json')).read_text(encoding='utf8'));rid=saved['execution']['run_id'];current=svc.result(rid)
    assert current['answer']['final']==saved['answer']['final'];assert current['execution']['required_stages_complete']
    for e in current['evidence']:
     original=store.evidence(rid,e['evidence_id']);assert original['text']==e['text'];assert original['source_version']==e['source_version'];assert original['provenance']==e['provenance']
    r={'scope':scope,'case':label,'required_complete':True,'evidence_reopened':len(current['evidence']),'history_read':True,'fixture_requests':len(saved['model_usage']),'versions':len(current['answer']['versions']),'rounds':len(current['review_rounds']),'seconds':next(c['seconds'] for c in json.loads((ROOT/'summary.json').read_text())['cases'] if c['scope']==scope and c['case']==label)}
    if label=='revision':
     assert r['versions']==2 and r['rounds']==2
     first=current['review_rounds'][0];v=copy.deepcopy(current);v['answer']['final']=first['answer'];v['snapshots']={'extraction':first['extraction']};v['review_bindings']={'verification':first['verification']};v['findings']['model_fact']=first['verification']['findings'];v['findings']['original_citations']=first['verification']['citation_reviews'];v['findings']['domain']=first['report']['domain_findings'];a=project(v)
     assert a['ready'] and a['regions'],a;r['original_marked_regions']=len(a['regions']);r['final_annotation_version']=project(current)['answer_version'];assert r['final_annotation_version']==2
    out['cases'].append(r)
  finally:store.close()
 out['offline_fixture_request_records']=sum(c['fixture_requests'] for c in out['cases']);atomic(ROOT/'archive-read-checks.json',out);print(json.dumps(out))
if __name__=='__main__':main()
