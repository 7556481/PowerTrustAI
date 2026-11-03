"""Bounded continuation after the existing build controller, using its supervisor.
No model calls, quality approval, service mutation or automatic retries.
"""
import json,time,sys,psutil
from pathlib import Path
from rag.tantivy_build import atomic,owner
from evaluation.tantivy_full_build_v1 import ROOT
from evaluation.tantivy_full_controller_v1 import idle
from evaluation.tantivy_supervision_v3 import supervise
from evaluation.tantivy_full_accept_v1 import audited_history

def alive(identity):
 try:return abs(psutil.Process(identity['pid']).create_time()-identity['created'])<.001
 except psutil.NoSuchProcess:return False

def main():
 folder=ROOT/'postbuild';folder.mkdir(exist_ok=True)
 with owner(folder):
  identity=json.loads((ROOT/'controller-v3-identity.json').read_text());ledger=json.loads((ROOT/'construction-ledger.json').read_text());deadline=ledger['deadline']
  if (folder/'result.json').exists():raise RuntimeError('Postbuild receipt exists; inspect, do not repeat')
  atomic(folder/'identity.json',{'pid':psutil.Process().pid,'created':psutil.Process().create_time(),'watching_controller':identity,'global_deadline':deadline})
  try:
   with (folder/'waiting-heartbeats.jsonl').open('a',encoding='utf8') as log:
    while alive(identity):
     if time.time()>=deadline:raise TimeoutError('Original96h absolute deadline reached')
     try:
      root=psutil.Process(identity['pid'])
      if abs(root.create_time()-identity['created'])>=.001:break
      procs=[psutil.Process(),root,*root.children(recursive=True)]
     except psutil.NoSuchProcess:break
     seen={};cpu={}
     for p in procs:
      try:m=p.memory_info();seen[p.pid]=max(m.rss,getattr(m,'private',m.rss));cpu[str(p.pid)]=sum(p.cpu_times()[:2])
      except psutil.NoSuchProcess:pass
     # Account this waiting companion too. It exits instead of causing an uncounted overrun.
     if sum(seen.values())>ledger['memory_limit']:raise MemoryError('Combined controller plus companion exceeds frozen memory')
     log.write(json.dumps({'wall':time.time(),'combined_memory':sum(seen.values()),'cpu_seconds':cpu,'available':psutil.virtual_memory().available})+'\n');log.flush();time.sleep(2)
   ledger=json.loads((ROOT/'construction-ledger.json').read_text());audited_history(ROOT,ledger)
   if not (ROOT/'built-complete.json').exists():raise RuntimeError('Controller exited without completed build; no retries')
   if (ROOT/'acceptance-complete.json').exists() or (ROOT/'full-measurements.jsonl').exists():raise RuntimeError('Existing acceptance/comparison requires inspection')
   for phase,module in [('accept','evaluation.tantivy_full_accept_v1'),('measure','evaluation.tantivy_full_measure_v1')]:
    if time.time()>=deadline:raise TimeoutError('No original96h budget remains')
    control=folder/phase;control.mkdir(exist_ok=False);logs=folder/(phase+'-logs');plan={'deadline':min(deadline,time.time()+4*3600),'grace_seconds':45,'kill_on_supervisor_exit':True,'cwd':str(Path.cwd()),'data_root':str(ROOT),'memory_limit':ledger['memory_limit'],'disk_limit':157*1024**3,'min_free':30*1024**3,'pressure_available':512*1024**2}
    location=ROOT/'native-location-v7.json'
    if location.exists():plan['extra_data_roots']=[json.loads(location.read_text())['build_root']]
    atomic(control/'plan.json',plan)
    args=[sys.executable,'-X','utf8','-m',module]+([str(control/'plan.json')] if phase=='accept' else [])
    atomic(folder/'phase.json',{'phase':phase,'started':time.time(),'deadline':plan['deadline'],'models':0})
    rc=supervise(control/'plan.json',args,logs,idle)
    if rc or (logs/'INVALID.json').exists():raise RuntimeError('Postbuild phase failed; inspect preserved artifacts, no retry')
    if phase=='accept' and not (ROOT/'acceptance-complete.json').exists():raise RuntimeError('Missing full acceptance receipt')
   atomic(folder/'result.json',{'status':'offline_outputs_ready_for_in_task_semantic_review','ended':time.time(),'models':0,'automatic_paid_or_release':False})
  except BaseException as e:
   atomic(folder/'result.json',{'status':'stopped_requires_inspection','error':type(e).__name__,'ended':time.time(),'models':0});raise
if __name__=='__main__':main()
