/* Real app.js; deterministic promise gates and one virtual polling clock. */
const assert=require('node:assert/strict');
const {client,response,answer,fallback,deferred}=require('./ui_async_probe');
const flush=()=>new Promise(setImmediate);
async function poll(h){assert.equal(h.polls.size,1,'expected exactly one polling source');const [id,fn]=[...h.polls][0];h.polls.delete(id);await fn();await flush();}
const tests=[];const test=(n,f)=>tests.push([n,f]);
for(const count of [1,3])test(count+' hanging auxiliaries permit next main cycle and terminal display',async()=>{
 const gates=Array.from({length:count},deferred);let done=false;const counts={};const active={},max={};
 const h=await client(async(p,o)=>{
  counts[p]=(counts[p]||0)+1;
  if(p==='/runs/A')return response({status:done?'finished':'running',run_id:'A'});
  const i=['nli','trace','reviews'].indexOf(p.split('/').at(-1));
  if(p.startsWith('/runs/A/')&&i>=0&&i<count){active[p]=(active[p]||0)+1;max[p]=Math.max(max[p]||0,active[p]);await gates[i].promise;active[p]--;}
  return fallback(p);
 });
 const loading=h.api.selectRun('A');await flush();
 try{assert(h.ui.answers.textContent.includes('answer A'));assert.equal(h.polls.size,1,'slow auxiliary blocked the main schedule');done=true;await poll(h);assert(h.ui.current.textContent.includes('结束'));for(const value of Object.values(max))assert.equal(value,1);}
 finally{for(const g of gates)g.resolve();await loading;await flush();h.api.forgetConnection();}
});
test('feedback save invalidates old auxiliary list without overlapping GET',async()=>{
 const gate=deferred();let saved=false,getCount=0,active=0,max=0;const h=await client(async(p,o)=>{
  if(p==='/runs/A/reviews'&&o.method==='POST'){saved=true;return response({});}
  if(p==='/runs/A/reviews'){getCount++;active++;max=Math.max(max,active);if(getCount===1)await gate.promise;const rows=getCount===1?[]:[{note:'NEW SAVED',run_id:'A'}];active--;return response(rows);}
  return fallback(p);
 });
 const loading=h.api.selectRun('A');await flush();h.ui['review-note'].value='NEW SAVED';const save=h.ui['review-form'].listeners.submit({preventDefault(){}});await flush();
 try{assert(saved);assert.equal(max,1,'feedback readback overlapped auxiliary reviews GET');}
 finally{gate.resolve();await loading;await save;await flush();}
 assert(h.ui.reviews.textContent.includes('NEW SAVED'));assert.equal(getCount,2);h.api.forgetConnection();
});
test('terminal while diagnostics pending converges once, final trace and reviews retained',async()=>{
 let checks=0;const counts={};const h=await client(async p=>{counts[p]=(counts[p]||0)+1;if(p==='/runs/A/nli')return response({pending:++checks<3,records:[],risk_note:'diagnostic '+checks});if(p==='/runs/A/trace')return response({events:[{event:{component:'FINAL TRACE'}}]});if(p==='/runs/A/reviews')return response([{note:'FINAL REVIEW'}]);return fallback(p);});
 await h.api.selectRun('A');await flush();for(let i=0;i<3&&h.polls.size;i++)await poll(h);
 assert.equal(h.polls.size,0);assert.equal(checks,3);assert(h.ui.trace.textContent.includes('FINAL TRACE'));assert(h.ui.reviews.textContent.includes('FINAL REVIEW'));assert.equal(counts['/runs/A/trace'],1);assert.equal(counts['/runs/A/reviews'],1);h.api.forgetConnection();
});
test('three virtual 15s deadlines pause once; manual recovery is bounded',async()=>{
 let fail=true;const counts={};const h=await client(async(p,o)=>{
  if(p==='/runs/A')return response({status:'running',run_id:'A'});
  if(/^\/runs\/A\/(nli|trace|reviews)$/.test(p)){counts[p]=(counts[p]||0)+1;if(fail)await new Promise((resolve,reject)=>o.signal.addEventListener('abort',()=>reject(Error('timeout'))));}return fallback(p);
 },{virtualClock:true});
 await h.api.selectRun('A');await flush();assert.equal(h.deadlines.size,3);for(const [id,d] of [...h.deadlines]){h.deadlines.delete(id);assert.equal(d.ms,15000);d.fn();}await flush();
 await poll(h);assert(Object.values(counts).every(n=>n===1));assert(h.ui.trace.textContent.includes('失败'));
 fail=false;await h.api.load();await flush();assert(Object.values(counts).every(n=>n===2));assert(!h.ui.trace.textContent.includes('失败'));h.api.forgetConnection();
});
for(const ending of ['success','failure','401'])test('late A '+ending+' cannot contaminate B or its connection',async()=>{
 const gate=deferred();const h=await client(async p=>{if(p==='/runs/A/nli'){await gate.promise;if(ending==='failure')throw Error('old offline');return response({risk_note:'STALE A'},ending==='401'?401:200);}return fallback(p);});
 await h.api.selectRun('A');await flush();await h.api.selectRun('B');await flush();const notice=h.ui.notice.textContent;gate.resolve();await flush();assert.equal(h.api.state().selected,'B');assert(h.api.state().connected);assert(!h.ui['local-nli'].textContent.includes('STALE A'));assert.equal(h.ui.notice.textContent,notice);h.api.forgetConnection();
});
test('manual overlap coalesces to one queued refresh per endpoint; main cycle never overlaps',async()=>{
 const main=deferred(),aux=deferred();let primary=0,maxMain=0,slow=false;const active={},max={},counts={};
 const h=await client(async(p,o)=>{
  if(p==='/runs/A'){primary++;maxMain=Math.max(maxMain,primary);if(slow)await main.promise;primary--;return response({status:'running',run_id:'A'});}
  if(/^\/runs\/A\/(nli|trace|reviews)$/.test(p)){active[p]=(active[p]||0)+1;max[p]=Math.max(max[p]||0,active[p]);counts[p]=(counts[p]||0)+1;await aux.promise;active[p]--;}return fallback(p);
 });
 await h.api.selectRun('A');await flush();slow=true;const one=h.api.load();await flush();await Promise.all(Array.from({length:8},()=>h.api.load()));main.resolve();await one;await flush();
 assert.equal(maxMain,1);assert(Object.values(max).every(n=>n===1));aux.resolve();await flush();assert(Object.values(counts).every(n=>n===2));assert(Object.values(max).every(n=>n===1));assert.equal(h.polls.size,1);h.api.forgetConnection();
});
test('terminal NLI pending has ten-check bound; current 401 and primary failures stop',async()=>{
 const h=await client(async p=>p==='/runs/A/nli'?response({pending:true,records:[]}):fallback(p));await h.api.selectRun('A');await flush();let ticks=0;while(h.polls.size&&ticks<15){ticks++;await poll(h);}assert.equal(ticks,9);assert.equal(h.polls.size,0);assert(h.ui['local-nli'].textContent.includes('10次'));h.api.forgetConnection();
 for(const unauthorized of [false,true]){const u=await client(async p=>p==='/runs/A'?response({},unauthorized?401:503):fallback(p));await u.api.selectRun('A');await flush();assert.equal(u.polls.size,0);if(unauthorized)assert(!u.api.state().connected);u.api.forgetConnection();}
});
test('leaving or reconnecting aborts old GETs without a new-page error',async()=>{
 for(const leave of ['pagehide','forget','reconnect']){let aborted=0;const h=await client(async(p,o)=>{if(p==='/runs/A/nli')await new Promise((resolve,reject)=>o.signal.addEventListener('abort',()=>{aborted++;reject(Error('abort'));}));return fallback(p);});
  await h.api.selectRun('A');await flush();if(leave==='pagehide')h.windowEvents.pagehide();else h.api.forgetConnection();await flush();assert.equal(aborted,1);assert.equal(h.polls.size,0);
  if(leave==='reconnect'){await h.api.connect('new_fixture');await flush();assert(h.api.state().connected);h.api.forgetConnection();await flush();}
 }
});
test('identical trace and reviews keep DOM; changes and same-data recovery still render',async()=>{
 let changed=false,fail=false;const h=await client(async p=>{if(p==='/runs/A/trace'){if(fail)throw Error('offline');return response({events:[{event:{component:changed?'CHANGED':'ORIGINAL'}}]});}if(p==='/runs/A/reviews')return response([{note:'SAVED REVIEW'}]);return fallback(p);});
 await h.api.selectRun('A');await flush();const trace=h.ui.trace.children[0],review=h.ui.reviews.children[0];await h.api.load();await flush();assert.equal(h.ui.trace.children[0],trace);assert.equal(h.ui.reviews.children[0],review);
 changed=true;await h.api.load();await flush();assert(h.ui.trace.textContent.includes('CHANGED'));
 fail=true;await h.api.load();await flush();assert(h.ui.trace.textContent.includes('失败'));fail=false;await h.api.load();await flush();assert(h.ui.trace.textContent.includes('CHANGED'));h.api.forgetConnection();
});
(async()=>{let failed=0;for(const [name,fn] of tests){try{await fn();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+': '+e.message);}}if(failed)process.exitCode=1;})().catch(e=>{console.error(e);process.exitCode=1;});
