"""Explicit smoke-only accounting bridge; ordinary startup never imports this."""
import json
from pathlib import Path
from unittest.mock import patch
from backend.assembly import ComponentFactory
from evaluation.source_first_live_v2 import Accounted
from evaluation.production_supply_v1 import Gate
from evaluation.natural_draft_audit_v1 import save

def acceptance_factory(config,path):
 path=Path(path).resolve();seed=json.loads(path.read_text(encoding='utf-8'))
 if set(seed)!={'version','calls','tokens','pending','cap','threshold'} or seed['version']!='production-supply-smoke-budget-v1' or seed['pending'] or seed['cap']!=240 or seed['threshold']!=4000000:raise ValueError('Unsettled or invalid campaign receipt')
 if any(type(seed[k]) is not int or seed[k]<0 for k in ('calls','tokens')) or seed['calls']>=240 or seed['tokens']>=4000000:raise ValueError('Campaign exhausted')
 root=path.parent/'smoke-accounting'
 if root.exists():raise ValueError('No repeated smoke attempt')
 root.mkdir();gate=Gate(root);gate.calls=seed['calls'];gate.tokens=seed['tokens'];done=path.parent/'smoke-campaign-closed.json'
 from model_adapter.deepseek import create_adapter as provider
 class Factory(ComponentFactory):
  def create(self,rid,observer):
   def build(settings,**opts):
    actual=provider(settings,**opts);accounted=Accounted(actual,gate)
    class Boundary:
     @property
     def _active(self):return getattr(actual,'_active',None)
     def close(self):actual.close()
     async def complete(self,request):
      validate=getattr(actual,'validate_request',None)
      if validate:validate(request)
      if done.exists():return await actual.complete(request)
      gate(dict(case='smoke-'+rid,variant='candidate'),request,gate.calls+1)
      try:return await accounted.complete(request)
      finally:save(path.parent/'smoke-totals.json',dict(calls=gate.calls,tokens=gate.tokens,pending=sorted(gate.pending),stopped=gate.stopped))
    return Boundary()
   with patch('model_adapter.deepseek.create_adapter',side_effect=build):return super().create(rid,observer)
 return Factory(config)
