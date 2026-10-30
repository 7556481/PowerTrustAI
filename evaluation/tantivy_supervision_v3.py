"""Isolated evaluation supervision: expiry survives sleep/restart; no product imports."""
import json,time,os,sys,subprocess,shutil
from pathlib import Path
import psutil

class Expired(RuntimeError):pass
class Guard:
 def __init__(self,path,wall=time.time,mono=time.monotonic,sleep=time.sleep):
  self.path=Path(path);self.plan=json.loads(self.path.read_text());self.wall=wall;self.mono=mono;self.sleep=sleep;self.start=mono();self.cleanup=False
 def event(self,kind,**fields):
  with self.path.with_name('events.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(kind=kind,wall=self.wall(),monotonic_elapsed=self.mono()-self.start,**fields))+'\n')
 def check(self,stage,pause_action=None,refresh=None):
  if self.wall()>=self.plan['deadline'] or self.path.with_name('stop.json').exists():
   self.cleanup=True;self.event('expired',stage=stage);raise Expired(stage)
  paused_once=False
  while self.path.with_name('pause.json').exists():
   if refresh and refresh():self.path.with_name('pause.json').unlink(missing_ok=True);break
   if pause_action and not paused_once:pause_action();paused_once=True
   self.event('paused',stage=stage);self.sleep(.2)
   if self.wall()>=self.plan['deadline'] or self.path.with_name('stop.json').exists():
    self.cleanup=True;raise Expired(stage+' while paused')
  if getattr(self,'last_stage',None)!=stage:self.event('admitted',stage=stage);self.last_stage=stage

class Writer:
 """Close owns the native writer once; cleanup errors never replace the primary."""
 def __init__(self,inner,guard):self.inner=inner;self.guard=guard;self.closed=False;self.committed=False
 def add_document(self,*a,**kw):self.guard.check('feed',pause_action=self.inner.commit);self.committed=False;return self.inner.add_document(*a,**kw)
 def commit(self):
  if self.closed or self.committed:return None
  if not self.guard.cleanup:self.guard.check('commit')
  result=self.inner.commit();self.committed=True;return result
 def wait_merging_threads(self):
  if self.closed:return None
  if not self.guard.cleanup:self.guard.check('merge')
  self.closed=True
  try:return self.inner.wait_merging_threads()
  except Exception as e:self.guard.event('native_close_error',error=repr(e));raise
 def close(self,primary=None):
  failures=[];self.guard.cleanup=True
  self.guard.event('primary_error',error=repr(primary) if primary else None)
  if not self.closed:
   try:self.commit()
   except Exception as e:failures.append(repr(e))
   try:self.wait_merging_threads()
   except Exception as e:failures.append(repr(e))
  self.guard.event('cleanup',primary=repr(primary) if primary else None,errors=failures)
  return failures

def terminate_verified(identities):
 """Only pre-recorded descendants, matched by PID AND creation time."""
 for pid,created in reversed(list(identities.items())):
  try:
   p=psutil.Process(int(pid))
   if abs(p.create_time()-created)<.001:p.kill()
  except psutil.NoSuchProcess:pass

def supervise(plan_path,command,directory,service_idle):
 g=Guard(plan_path);directory=Path(directory)
 roster=g.path.with_name('process-identities.json')
 if roster.exists():
  ids=json.loads(roster.read_text());alive={}
  for pid,created in ids.items():
   try:
    proc=psutil.Process(int(pid))
    if abs(proc.create_time()-created)<.001:alive[pid]=created
   except psutil.NoSuchProcess:pass
  if alive:
   g.path.with_name('stop.json').write_text('supervisor restarted; prior stage invalid')
   g.event('restart_found_live_stage',identities=alive)
   until=time.monotonic()+g.plan['grace_seconds']
   while time.monotonic()<until and any(psutil.pid_exists(int(pid)) for pid in alive):time.sleep(.1)
   terminate_verified(alive);directory.mkdir(exist_ok=True);directory.joinpath('INVALID.json').write_text('supervisor restart with orphaned stage');return 1
 def idle():
  try:return service_idle()
  except Exception as e:g.event('service_health_unavailable',error=type(e).__name__);return False
 if idle():g.path.with_name('pause.json').unlink(missing_ok=True)
 else:g.path.with_name('pause.json').write_text('service not idle or health unavailable')
 g.check('process admission',refresh=idle);directory.mkdir(exist_ok=False)
 with (directory/'stdout.log').open('w',encoding='utf8') as out,(directory/'stderr.log').open('w',encoding='utf8') as err,(directory/'heartbeats.jsonl').open('w') as log:
  p=subprocess.Popen(command,stdout=out,stderr=err,cwd=g.plan['cwd'],creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
  root=psutil.Process(p.pid);ids={p.pid:root.create_time()};last=g.wall();stopping=None;peak=0;disk=0;disk_tick=0
  while p.poll() is None:
   now=g.wall();gap=now-last
   if gap>g.plan.get('gap_seconds',5):g.event('observation_gap',seconds=gap,unobserved_resources=True)
   last=now;rows=[]
   for proc in [psutil.Process(),root,*root.children(recursive=True)]:
    try:
     created=proc.create_time();m=proc.memory_info()
     if proc.pid!=os.getpid():ids[proc.pid]=created
     rows.append(dict(pid=proc.pid,created=created,rss=m.rss,private=getattr(m,'private',m.vms)))
    except psutil.Error:pass
   memory=max(sum(x['rss'] for x in rows),sum(x['private'] for x in rows));peak=max(peak,memory)
   g.path.with_name('process-identities.json').write_text(json.dumps(ids))
   if now-disk_tick>2:
    disk=sum(x.stat().st_size for x in Path(g.plan['data_root']).rglob('*') if x.is_file());disk_tick=now
   expired=now>=g.plan['deadline'];hard=memory>g.plan['memory_limit'] or disk>g.plan['disk_limit'] or shutil.disk_usage(directory).free<g.plan['min_free']
   if expired or hard:
    if stopping is None:
     stopping=now;g.path.with_name('stop.json').write_text(json.dumps(dict(reason='deadline' if expired else 'memory',wall=now)));g.event('stop_requested',identities=ids)
    if now-stopping>=g.plan['grace_seconds']:
     directory.joinpath('INVALID.json').write_text(json.dumps(dict(reason='grace exhausted',identities=ids)));terminate_verified(ids);g.event('terminated_verified_tree');break
   busy=not idle() or psutil.virtual_memory().available<g.plan['pressure_available'];pause=g.path.with_name('pause.json')
   if busy:pause.write_text('resource/service pressure')
   elif pause.exists():pause.unlink()
   log.write(json.dumps(dict(wall=now,mono_elapsed=g.mono()-g.start,processes=rows,memory=memory,disk=disk,system_available=psutil.virtual_memory().available,service_busy=busy))+'\n');log.flush();g.sleep(.2)
  rc=p.wait()
  if g.wall()>=g.plan['deadline'] and stopping is None:stopping=g.wall()
  g.event('exit',code=rc,peak=peak)
  if rc or stopping is not None:directory.joinpath('INVALID.json').write_text(json.dumps(dict(exit_code=rc,stop_requested=stopping)))
  return rc if stopping is None else (rc or 1)
