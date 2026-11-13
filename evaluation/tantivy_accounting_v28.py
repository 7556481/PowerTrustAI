"""Durable Flash admission: trusted usage plus retained conservative reservations.
Does not assert an absolute provider billing-token upper bound.
"""
import json,threading,time
from dataclasses import asdict
from pathlib import Path
import os
def atomic(path,value):
 path=Path(path);pending=path.with_suffix(path.suffix+".pending")
 with pending.open("w",encoding="utf8") as f:json.dump(value,f,ensure_ascii=False,sort_keys=True);f.flush();os.fsync(f.fileno())
 os.replace(pending,path)
class BudgetStop(RuntimeError):pass
class FullBudget:
 def __init__(self,root,cap=240,threshold=4000000):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock();p=self.root/'state.json'
  journal=sorted((self.root/'journal').glob('*.json'))
  self.state=json.loads(journal[-1].read_text(encoding='utf8')) if journal else json.loads(p.read_text(encoding='utf8')) if p.exists() else {'calls':0,'trusted_tokens':0,'entries':{},'cap':cap,'threshold':threshold}
  if self.state['cap']!=cap or self.state['threshold']!=threshold:raise BudgetStop('Budget identity mismatch')
 def save(self):
  journal=self.root/'journal';journal.mkdir(exist_ok=True)
  self.state['sequence']=self.state.get('sequence',0)+1
  target=journal/('%08d.json'%self.state['sequence'])
  with target.open('x',encoding='utf8') as f:json.dump(self.state,f,ensure_ascii=False,sort_keys=True);f.flush();os.fsync(f.fileno())
  atomic(self.root/'state.json',self.state)
 def held(self):return sum(e['reserved'] for e in self.state['entries'].values() if e.get('usage') is None)
 def reserve(self,chain,request):
  with self.lock:
   if request.model_id!='deepseek-flash':raise BudgetStop('Flash only')
   active=[e for e in self.state['entries'].values() if e['inflight']]
   if any(e['chain']!=chain for e in active) or len(active)>=2:raise BudgetStop('Prior request not drained or production review-pair limit exceeded')
   amount=sum(len(m.content.encode('utf8')) for m in request.messages)+request.max_output_tokens+4096
   if self.state['calls']>=self.state['cap'] or self.state['trusted_tokens']>=self.state['threshold'] or self.state['trusted_tokens']+self.held()+amount>self.state['threshold']:raise BudgetStop('Global calls/usage/reservations exhausted')
   i=str(self.state['calls']+1);self.state['entries'][i]={'chain':chain,'reserved':amount,'usage':None,'inflight':True,'admitted_wall':time.time(),'basis':'UTF8 bytes + output allowance +4096 conservative reservation; not certified billing upper bound'};self.state['calls']+=1;self.save();return i
 def received(self,i,usage):
  with self.lock:
   e=self.state['entries'][i]
   if e.get('finished'):raise BudgetStop('Duplicate model settlement')
   e['inflight']=False;e['finished']=True
   if usage is not None:
    u=asdict(usage) if not isinstance(usage,dict) else usage;p,c,t=[u.get(k) for k in ('input_tokens','output_tokens','total_tokens')]
    if all(type(v) is int and v>=0 for v in (p,c,t)) and p+c==t:e['usage']=u;self.state['trusted_tokens']+=t
   self.save()
 def failed(self,i,exc,active):
  with self.lock:
   e=self.state['entries'][i];e['error']=type(exc).__name__;e['inflight']=bool(active is not None and not active.done());e['finished']=not e['inflight'];self.save()
 def release_drained_chain(self,chain):
  # Called only after the original service has drained physical model resources.
  with self.lock:
   for e in self.state['entries'].values():
    if e['chain']==chain and e['inflight']:e['inflight']=False;e['finished']=True;e['drain_confirmed']=True
   self.save()
class AccountedFlash:
 def __init__(self,delegate,gate,chain):self.delegate=delegate;self.gate=gate;self.chain=chain
 @property
 def _active(self):return getattr(self.delegate,'_active',None)
 def close(self):return self.delegate.close()
 async def complete(self,request):
  i=self.gate.reserve(self.chain,request)
  try:r=await self.delegate.complete(request)
  except BaseException as e:self.gate.failed(i,e,self._active);raise
  self.gate.received(i,r.usage);return r

_GATES={}
_GATES_LOCK=threading.Lock()
def shared_gate(root):
 key=str(Path(root).resolve())
 with _GATES_LOCK:
  if key not in _GATES:_GATES[key]=FullBudget(key)
  return _GATES[key]
