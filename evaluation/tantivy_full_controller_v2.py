"""v2 continuation, same global96h ledger and explicit prior-failure audit."""
import json,time,sys,sqlite3
from pathlib import Path
from evaluation.tantivy_full_build_v1 import ROOT
from evaluation.tantivy_full_controller_v1 import idle
from evaluation.tantivy_supervision_v3 import supervise,Expired
from rag.tantivy_build import atomic,owner
from rag.tantivy_manifest import sha

def main():
 with owner(ROOT):
  import psutil
  atomic(ROOT/'controller-v3-identity.json',{'pid':psutil.Process().pid,'created':psutil.Process().create_time()})
  ledger_file=ROOT/'construction-ledger.json';ledger=json.loads(ledger_file.read_text());audit=json.loads((ROOT/'recovery-audit-1.json').read_text());assert audit['passed'] and audit['committed']==150674
  if ledger['segments'][-1]['status']=='running':raise RuntimeError('Live/orphan segment must be audited first')
  history=ROOT/'driver-revisions-v2.json'
  if not history.exists():atomic(history,{'reason':'Restore validated prepare-before-writer lifecycle; initial failed stream retained','audit':str(ROOT/'recovery-audit-1.json'),'input_schema_unchanged':True,'effective_code':{p:sha(p) for p in ['evaluation/tantivy_full_stages_v2.py','evaluation/tantivy_full_controller_v2.py']}})
  while time.time()<ledger['deadline'] and not (ROOT/'built-complete.json').exists():
   mode='write' if (ROOT/'input-complete.json').exists() else 'prepare';i=len(ledger['segments']);control=ROOT/'controls'/str(i);control.mkdir(exist_ok=False);logs=ROOT/'segments'/str(i)
   p={'deadline':min(ledger['deadline'],time.time()+4*3600),'kill_on_supervisor_exit':True,'grace_seconds':45,'cwd':str(Path.cwd()),'data_root':str(ROOT),'memory_limit':ledger['memory_limit'],'disk_limit':157*1024**3,'min_free':30*1024**3,'pressure_available':512*1024**2}
   location=ROOT/'native-location-v7.json'
   if location.exists():
    extra=Path(json.loads(location.read_text())['build_root']).resolve()
    if not extra.is_relative_to(ROOT.parent.resolve()):raise RuntimeError('Derived build root outside authorized storage')
    p['extra_data_roots']=[str(extra)]
   atomic(control/'plan.json',p)
   segment={'index':i,'phase':mode,'driver':'v2','start':time.time(),'status':'running','control':str(control)};ledger['segments'].append(segment);atomic(ledger_file,ledger)
   try:rc=supervise(control/'plan.json',[sys.executable,'-X','utf8','-m','evaluation.tantivy_full_stages_v2',mode,str(control/'plan.json')],logs,idle)
   except Expired:rc=0
   segment.update(end=time.time(),exit_code=rc,status='complete' if rc==0 else 'failed-needs-proof');ledger['wall_elapsed']=time.time()-ledger['start_wall'];atomic(ledger_file,ledger)
   if rc or (logs/'INVALID.json').exists():break
  atomic(ROOT/'controller-v2-result.json',{'built':(ROOT/'built-complete.json').exists(),'ended':time.time(),'models':0,'ledger':str(ledger_file)})
if __name__=='__main__':main()
