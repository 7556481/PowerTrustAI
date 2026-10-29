"""Normal service result reads from a small archive copy; no inference."""
import json,sqlite3
from pathlib import Path
from dataclasses import replace
from backend.assembly import ComponentFactory
from backend.service import ApplicationService
from backend.store import RunStore
from evaluation.natural_draft_audit_v1 import save

def check(root,c):
 root=Path(root);summary=json.loads((root/'summary.json').read_text(encoding='utf-8'));dest=root/'ordinary-read.sqlite3'
 if dest.exists():raise RuntimeError('Preserve prior read check')
 with sqlite3.connect((root/'runs.sqlite3').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(dest) as dst:src.backup(dst)
 store=RunStore(dest);rows=[]
 try:
  for entry in summary['control']:
   rid=entry['accepted']['run_id'];spec=entry['accepted']['spec'];cfg=replace(c,run_db=dest,audit_evidence_profile='deferred_subject_v1' if spec['variant']=='candidate' else 'baseline_v1');manifest=ComponentFactory(cfg).manifest(cfg.knowledge_version)
   inp=json.loads((root/rid/'input.json').read_text(encoding='utf-8'))
   with store.tx():store.db.execute('UPDATE runs SET config=?,request=? WHERE id=?',(json.dumps(manifest),json.dumps(inp['request']),rid))
   projected=ApplicationService(cfg,store,factory=ComponentFactory(cfg)).result(rid);raw=summary['outputs'][rid]
   assert projected['answer']['final']==raw.get('answer'),'Ordinary read changed final answer'
   expected=bool(raw.get('review_rounds')) and not raw.get('execution_issues')
   assert projected['execution']['required_stages_complete']==expected,'Incomplete audit mislabeled'
   save(root/rid/'ordinary-result.json',projected);rows.append(dict(slot=entry['case_id'],required_stages_complete=expected,final_equal=True))
 finally:store.close()
 save(root/'ordinary-read-check.json',dict(passed=True,rows=rows));return rows
