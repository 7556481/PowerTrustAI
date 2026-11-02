"""Segmented full-build controller around the existing isolated supervisor."""
import json,time,socket,sqlite3,sys,urllib.request,psutil
from pathlib import Path
from evaluation.tantivy_full_build_v1 import ROOT,SOURCE,K
from evaluation.tantivy_supervision_v3 import supervise,Expired
from rag.tantivy_build import atomic,owner

def idle():
 try:
  with socket.create_connection(('127.0.0.1',8765),timeout=.15):pass
 except OSError:
  p=Path('D:/PowerTrustAI/data/runtime_local/runs.sqlite3')
  if not p.exists():return True
  c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
  try:return c.execute("select count(*) from runs where status in ('queued','running')").fetchone()[0]==0
  finally:c.close()
 try:
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open('http://127.0.0.1:8765/health',timeout=.5) as response:d=json.load(response)
  return d.get('status')=='ready' and not d.get('active_run') and d.get('queued',0)==0
 except Exception:return False

def main():
 ROOT.mkdir(exist_ok=True)
 with owner(ROOT):
  ledger_file=ROOT/'construction-ledger.json'
  if ledger_file.exists():ledger=json.loads(ledger_file.read_text())
  else:
   available=psutil.virtual_memory().available
   ledger={'start_wall':time.time(),'deadline':time.time()+96*3600,'memory_limit':min(available//2,2*1024**3),'initial_available':available,'segments':[],'total_budget_seconds':96*3600};atomic(ledger_file,ledger)
  if ledger['segments'] and ledger['segments'][-1]['status']=='running':raise RuntimeError('Interrupted segment requires PID/creation-time and checkpoint audit before resume')
  atomic(ROOT/'controller-identity.json',{'pid':psutil.Process().pid,'created':psutil.Process().create_time()})
  while not (ROOT/'built-complete.json').exists():
   if time.time()>=ledger['deadline']:break
   index=len(ledger['segments']);control=ROOT/'controls'/str(index);control.mkdir(parents=True,exist_ok=False);logs=ROOT/'segments'/str(index);logs.parent.mkdir(exist_ok=True)
   plan={'deadline':min(ledger['deadline'],time.time()+4*3600),'grace_seconds':45,'cwd':str(Path.cwd()),'data_root':str(ROOT),'memory_limit':ledger['memory_limit'],'disk_limit':160*1024**3-3*1024**3,'min_free':30*1024**3,'pressure_available':512*1024**2,'gap_seconds':5}
   atomic(control/'plan.json',plan);segment={'index':index,'start':time.time(),'status':'running','control':str(control)};ledger['segments'].append(segment);atomic(ledger_file,ledger)
   try:rc=supervise(control/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_full_build_v1',str(control/'plan.json')],logs,idle)
   except Expired:rc=0 # Paused before launch; no worker exists, global deadline unchanged.
   segment.update(end=time.time(),exit_code=rc,status='complete' if rc==0 else 'failed-needs-proof');ledger['wall_elapsed']=time.time()-ledger['start_wall'];atomic(ledger_file,ledger)
   if rc!=0 or (logs/'INVALID.json').exists():break
  atomic(ROOT/'controller-result.json',{'built':(ROOT/'built-complete.json').exists(),'ledger':str(ledger_file),'ended':time.time(),'models':0})
if __name__=='__main__':main()
