"""One frozen million run; all phases share one absolute deadline."""
import sys,json,time,hashlib,psutil,shutil
from pathlib import Path
from evaluation import tantivy_stability_v2 as old
from evaluation.tantivy_supervision_v3 import Guard,supervise
ROOT=old.ROOT
LOCAL=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-supervision-v3')
def main():
 verified=old.read(LOCAL/'spool-verified.json');assert verified['n']==1000000 and verified['complete_source_mapping']
 assert not (LOCAL/'plan.json').exists(),'One run only; preserve old state'
 assert old.health(),'Service not idle'
 available=psutil.virtual_memory().available;budget=min(1024**3,available//2);assert budget>=320*1024**2,'Insufficient memory for reasonable writer budget'
 files=['evaluation/tantivy_supervision_v3.py','evaluation/tantivy_million_v3.py','evaluation/tantivy_campaign_v3.py','evaluation/tantivy_stability_v2.py','evaluation/tantivy_medium_measure_v2.py']
 plan=dict(version='tantivy-supervision-v3',created=time.time(),deadline=time.time()+14400,clock='absolute deadline includes sleep, pause and gaps; monotonic elapsed for diagnostics',grace_seconds=30,gap_seconds=5,cwd=str(ROOT),data_root=str(LOCAL),memory_limit=budget,initial_available=available,pressure_available=max(256*1024**2,available//5),disk_limit=30*1024**3,min_free=30*1024**3,writer_heap=128000000,index_workers=1,input=verified,files={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},model_requests=0,tantivy='0.27.0',query_version='original v1 frozen12 unchanged',restart='prior live stage invalidated, grace then PID/create-time-verified termination')
 assert shutil.disk_usage(LOCAL).free>=plan['min_free'];old.save(LOCAL/'plan.json',plan);old.save(LOCAL/'resource-and-diagnostic-plan.json',dict(writer_heap=128000000,index_threads=1))
 for action in ['build','validate','measure']:
  Guard(LOCAL/'plan.json').check(action+' admission')
  rc=supervise(LOCAL/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_million_v3',action],LOCAL/('supervised-'+action),old.health)
  if rc:
   (LOCAL/'million').mkdir(exist_ok=True);old.save(LOCAL/'million/INVALID.json',dict(stage=action,exit_code=rc));raise SystemExit(action+' failed; no retry')
 old.save(LOCAL/'complete.json',dict(completed=True,finished=time.time(),model_requests=0))
if __name__=='__main__':main()
