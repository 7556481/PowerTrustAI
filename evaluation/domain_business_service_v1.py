"""Two single-admission candidate services using existing normal collector."""
import json,os
from pathlib import Path
from dataclasses import replace
from contextlib import ExitStack
from unittest.mock import patch
from evaluation import langgraph_service_trial_v1 as shared
from evaluation.domain_business_trial_v1 import PUBLIC,LOCAL
from backend.config import ServiceConfig
REAL_CONFIG=ServiceConfig
ORDER=(('DBS-01','LSI-01','langgraph_v1'),('DBS-02','LSI-02','langgraph_v1'))
def config():return replace(REAL_CONFIG.from_environment(),domain_internal_flow='business_v1')
def freeze():
 c=config();f=shared.ComponentFactory(c);manifest=f.manifest(f.preflight())
 value=dict(version='domain-business-service-v1',configuration=shared.config_identity(c),manifest=manifest,model_id=os.environ.get('DEEPSEEK_MODEL_ID'),budget=shared.wire(c.budget),order=[dict(id=i,task_id=t,execution_path=p,payload_sha256=shared.sha(shared.tasks()[t])) for i,t,p in ORDER],bound_files=[dict(path=str(p.relative_to(shared.ROOT)),sha256=__import__('hashlib').sha256(p.read_bytes()).hexdigest()) for folder in ('agents','backend','core','services','harness','evaluation','tests') for p in (shared.ROOT/folder).glob('*.py')])
 shared.write(PUBLIC/'service-freeze.json',value);shared.write(PUBLIC/'execution-freeze-v1.json',value);shared.write(LOCAL/'service/freeze.json',value);shared.write(LOCAL/'service/payloads.json',shared.tasks())
def execute():
 results=shared.read(PUBLIC/'results.json')
 if results['shared_stop'] or any(r['status']!='complete' for r in results['branches']):
  shared.write(PUBLIC/'service-not-executed.json',{'reason':'component execution gate not met','planned':2});return
 class ConfigProxy:
  @staticmethod
  def from_environment():return config()
 with ExitStack() as stack:
  for name,value in (('PUBLIC',PUBLIC),('LOCAL',LOCAL/'service'),('PRIVATE',LOCAL/'service-private'),('ORDER',ORDER),('ServiceConfig',ConfigProxy)):
   stack.enter_context(patch.object(shared,name,value))
  stack.enter_context(patch.object(shared,'read',side_effect=lambda path:json.loads((PUBLIC/'service-freeze.json' if Path(path)==PUBLIC/'execution-freeze-v1.json' else Path(path)).read_text(encoding='utf-8'))))
  shared.execute()
 shared.write(PUBLIC/'service-results.json',shared.read(LOCAL/'service/summary.json'))
if __name__=='__main__':
 import sys
 freeze() if sys.argv[1:]==['freeze'] else execute() if sys.argv[1:]==['execute'] else None
