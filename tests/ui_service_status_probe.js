/* Actual client with v4 API-shaped data; no server/models or wall-clock sleeps. */
const assert=require('node:assert/strict');
const {client,response,answer,fallback,deferred}=require('./ui_async_probe');
const flush=()=>new Promise(setImmediate);
const healthy={profile:'synthetic_fixture',status:'ready',configuration_ready:true,storage_healthy:true,queued:0,queue_capacity:2,service_lifecycle:{accepting_work:true,worker_running:true}};
const unavailable={...healthy,status:'degraded',reason:'RESOURCE_CLOSE_FAILED',service_lifecycle:{accepting_work:false,worker_running:false,fault_code:'RESOURCE_CLOSE_FAILED'}};
const pending={run_id:'A',status:'queued',pending_terminal_status:'interrupted',persistence_confirmed:false,service_fault_code:'RESOURCE_CLOSE_FAILED'};
const tests=[];const test=(name,fn)=>tests.push([name,fn]);
function prepare(h){h.ui.question.value='synthetic';h.ui.mode.value='question_answer';h.ui.requirements.value='';}
test('reachable non-accepting health disables submit but keeps history GET available',async()=>{
 let posts=0;const h=await client(async(p,o)=>{if(o.method==='POST')posts++;return p==='/health'?response(unavailable):fallback(p);});
 try{assert.equal(h.ui.submit.disabled,true);assert(h.api.state().connected);assert.equal(h.ui['history-refresh'].disabled,false);await h.api.history();assert.equal(posts,0);}
 finally{h.api.forgetConnection();}
});
test('pre-submit health says unavailable: no POST /runs is sent',async()=>{
 let blocked=false,posts=0;const h=await client(async(p,o)=>{if(p==='/runs'&&o.method==='POST'){posts++;return response({run_id:'A'});}return p==='/health'?response(blocked?unavailable:healthy):fallback(p);});
 try{prepare(h);blocked=true;await h.ui['submit-form'].listeners.submit({preventDefault(){}});assert.equal(posts,0,'non-accepting health still sent POST');assert(h.ui.submit.disabled);}
 finally{h.api.forgetConnection();}
});
test('pending interrupted and unconfirmed state is explained without changing stored status',async()=>{
 const h=await client(async p=>p==='/health'?response(unavailable):p==='/runs/A'?response(pending):p==='/runs/A/result'?response({execution:pending,result_available:false}):fallback(p));
 try{await h.api.selectRun('A');await flush();assert((h.ui.phase.textContent+h.ui.current.textContent).includes('中断状态尚未确认保存'));assert(h.ui.current.textContent.includes('排队'));assert(h.ui.current.textContent.includes('interrupted')||h.ui.current.textContent.includes('中断'));}
 finally{h.api.forgetConnection();}
});
test('explicit stopped processing converges instead of polling queued forever',async()=>{
 const counts={};const h=await client(async p=>{counts[p]=(counts[p]||0)+1;return p==='/runs/A'?response(pending):p==='/runs/A/result'?response({execution:pending,result_available:false}):fallback(p);});
 try{await h.api.selectRun('A');await flush();assert.equal(h.polls.size,0,'pending interruption kept polling');assert.equal(counts['/runs/A'],1);for(const endpoint of ['nli','trace','reviews'])assert.equal(counts['/runs/A/'+endpoint],1);}
 finally{h.api.forgetConnection();}
});
test('completed saved answer stays approved while service fault blocks new work',async()=>{
 const ex={status:'finished',required_stages_complete:true,persisted_result_available:true,persistence_confirmed:true,service_fault_code:'RESOURCE_CLOSE_FAILED'};
 const saved={...answer('A'),execution:ex,decision:{kind:'pass'}};
 const h=await client(async p=>p==='/runs/A'?response({...ex,run_id:'A'}):p==='/runs/A/result'?response(saved):fallback(p));
 try{await h.api.selectRun('A');await flush();assert.equal(h.ui.submit.disabled,true);assert(h.ui.answers.textContent.includes('answer A'));assert(h.ui.decision.textContent.includes('通过'));assert.equal(h.polls.size,0);}
 finally{h.api.forgetConnection();}
});
test('manual service check uses only health GET, restores availability and keeps draft/answer',async()=>{
 let blocked=true;const calls=[];const h=await client(async(p,o)=>{calls.push([p,o.method]);return p==='/health'?response(blocked?unavailable:healthy):fallback(p);});
 await h.api.selectRun('A');await flush();h.ui['review-note'].value='keep draft';const rendered=h.ui.answers.children[0];blocked=false;const before=calls.length;
 await h.ui['service-check'].listeners.click();assert.deepEqual(calls.slice(before),[['/health','GET']]);assert.equal(h.ui.submit.disabled,false);assert.equal(h.ui['review-note'].value,'keep draft');assert.equal(h.ui.answers.children[0],rendered);assert.equal(h.polls.size,0);h.api.forgetConnection();
});
test('unreachable check leaves confirmed content and draft, blocks submit without losing readable history',async()=>{
 let fail=false,posts=0;const h=await client(async(p,o)=>{if(o.method==='POST')posts++;if(p==='/health'){if(fail)throw Error('offline');return response(healthy);}return fallback(p);});
 await h.api.selectRun('A');await flush();h.ui['review-note'].value='offline draft';fail=true;await h.ui['service-check'].listeners.click();
 assert(h.ui['service-status'].textContent.includes('不可达'));assert(h.ui.submit.disabled);assert.equal(h.ui['history-refresh'].disabled,false);assert(h.ui.answers.textContent.includes('answer A'));assert.equal(h.ui['review-note'].value,'offline draft');await h.api.history();prepare(h);await h.ui['submit-form'].listeners.submit({preventDefault(){}});assert.equal(posts,0);h.api.forgetConnection();
});
test('health check does not clear uncertain POST lock or automatically resend',async()=>{
 let posts=0;const h=await client(async(p,o)=>{if(p==='/runs'&&o.method==='POST'){posts++;throw Error('unknown acceptance');}return p==='/health'?response(healthy):fallback(p);});
 prepare(h);await h.ui['submit-form'].listeners.submit({preventDefault(){}});assert(h.api.state().uncertainPost);await h.ui['service-check'].listeners.click();assert(h.api.state().uncertainPost);assert(h.ui.submit.disabled);assert(h.ui.notice.textContent.includes('锁定'));await h.ui['submit-form'].listeners.submit({preventDefault(){}});assert.equal(posts,1);h.api.forgetConnection();
});
for(const status of [503,429])test('health-to-POST '+status+' race blocks another write until checked, no retry',async()=>{
 let posts=0;const h=await client(async(p,o)=>{if(p==='/runs'&&o.method==='POST'){posts++;return response({code:status===503?'SERVICE_UNAVAILABLE':'QUEUE_FULL'},status);}return p==='/health'?response(healthy):fallback(p);});
 prepare(h);await h.ui['submit-form'].listeners.submit({preventDefault(){}});assert.equal(posts,1);assert(h.ui.submit.disabled);assert.equal(h.ui['history-refresh'].disabled,false);await h.ui['submit-form'].listeners.submit({preventDefault(){}});assert.equal(posts,1);await h.ui['service-check'].listeners.click();assert.equal(h.ui.submit.disabled,false);assert.equal(posts,1);h.api.forgetConnection();
});
for(const outcome of ['success','failure','401'])test('older health '+outcome+' cannot replace newer fault or invalidate connection',async()=>{
 let count=0;const gate=deferred();const h=await client(async p=>{if(p==='/health'){count++;if(count===2){await gate.promise;if(outcome==='failure')throw Error('old offline');return response(healthy,outcome==='401'?401:200);}return response(count>=3?unavailable:healthy);}return fallback(p);});
 const old=h.api.health();await flush();await h.api.health();gate.resolve();await old;await flush();assert(h.ui.submit.disabled);assert(h.api.state().connected);assert(h.ui['service-status'].textContent.includes('不允许'));h.api.forgetConnection();
});
test('a run-reported new fault also invalidates an older health ready in the same epoch',async()=>{
 let fault=false,count=0;const gate=deferred();const h=await client(async p=>{if(p==='/health'){if(++count===2)await gate.promise;return response(healthy);}if(p==='/runs/A')return response({run_id:'A',status:'finished',service_fault_code:fault?'RESOURCE_CLOSE_FAILED':null});return fallback(p);});
 await h.api.selectRun('A');await flush();const old=h.api.health();await flush();fault=true;await h.api.load();gate.resolve();await old;await flush();assert(h.ui.submit.disabled);assert(h.ui['service-status'].textContent.includes('不允许'));h.api.forgetConnection();
});
test('current 401 differs from reachable refusal and a public health GET cannot authenticate',async()=>{
 let unauthorized=false;const h=await client(async p=>p==='/health'?response(healthy):p==='/runs/A'&&unauthorized?response({},401):fallback(p));
 unauthorized=true;await h.api.selectRun('A');await flush();assert(!h.api.state().connected);assert(h.ui['service-status'].textContent.includes('鉴权'));assert(h.ui['history-refresh'].disabled);await h.ui['service-check'].listeners.click();assert(!h.api.state().connected);assert(h.ui.submit.disabled);h.api.forgetConnection();
});
for(const [label,value,enabled] of [
 ['legacy ready',{profile:'synthetic_fixture',status:'ready',configuration_ready:true},true],
 ['unknown',{profile:'synthetic_fixture',status:'unknown'},false],
 ['configuration',{...healthy,configuration_ready:false},false],
 ['storage',{...healthy,storage_healthy:false},false],
 ['queue full',{...healthy,queued:2},false]
])test('health mapping '+label+' preserves compatibility without claiming unknown ready',async()=>{
 const h=await client(async p=>p==='/health'?response(value):fallback(p));assert.equal(h.ui.submit.disabled,!enabled);assert.equal(h.ui['history-refresh'].disabled,false);if(label==='legacy ready')assert(h.ui['service-status'].textContent.includes('旧版'));h.api.forgetConnection();
});
test('only a service fault does not stop a task still genuinely running',async()=>{
 let finished=false;const h=await client(async p=>p==='/runs/A'?response({run_id:'A',status:finished?'finished':'running',service_fault_code:'RESOURCE_CLOSE_FAILED'}):fallback(p));
 await h.api.selectRun('A');await flush();assert(h.ui.submit.disabled);assert.equal(h.polls.size,1);finished=true;const [id,fn]=[...h.polls][0];h.polls.delete(id);await fn();await flush();assert.equal(h.polls.size,0);h.api.forgetConnection();
});
test('saved business result with metadata unconfirmed is preserved and explained separately',async()=>{
 const ex={status:'finished',required_stages_complete:true,persistence_confirmed:false,persisted_result_available:true};const saved={...answer('A'),execution:ex,decision:{kind:'pass'}};
 const h=await client(async p=>p==='/runs/A'?response({run_id:'A',...ex}):p==='/runs/A/result'?response(saved):fallback(p));await h.api.selectRun('A');await flush();
 assert(h.ui['run-status-note'].textContent.includes('元数据保存未确认'));assert(h.ui['run-status-note'].textContent.includes('已保存'));assert(h.ui.decision.textContent.includes('通过'));assert(h.ui.answers.textContent.includes('answer A'));assert.equal(h.polls.size,0);h.api.forgetConnection();
});
test('stopped task still settles pending diagnostic under the original finite mechanism',async()=>{
 let calls=0,trace=0;const h=await client(async p=>p==='/runs/A'?response(pending):p==='/runs/A/result'?response({execution:pending,result_available:false}):p==='/runs/A/nli'?response({pending:++calls<3,records:[]}):p==='/runs/A/trace'?(trace++,fallback(p)):fallback(p));
 await h.api.selectRun('A');await flush();let ticks=0;while(h.polls.size&&ticks++<12){const [id,fn]=[...h.polls][0];h.polls.delete(id);await fn();await flush();}assert.equal(calls,3);assert.equal(trace,1);assert.equal(h.polls.size,0);h.api.forgetConnection();
});
test('manual check double click has one in-flight health GET and no polling source',async()=>{
 let held=false,calls=0;const gate=deferred();const h=await client(async p=>{if(p==='/health'){calls++;if(held)await gate.promise;return response(healthy);}return fallback(p);});
 held=true;const checking=h.ui['service-check'].listeners.click();await flush();assert(h.ui['service-check'].disabled);await h.ui['service-check'].listeners.click();assert.equal(calls,2);gate.resolve();await checking;assert.equal(h.ui['service-check'].disabled,false);assert.equal(h.polls.size,0);h.api.forgetConnection();
});
test('pending raw status fields remain inspectable and saved feedback can still be written',async()=>{
 let posts=0;const h=await client(async(p,o)=>{if(o.method==='POST'){posts++;return response({});}return p==='/health'?response(unavailable):p==='/runs/A'?response(pending):p==='/runs/A/result'?response({...answer('A'),execution:{...pending,required_stages_complete:false}}):fallback(p);});
 await h.api.selectRun('A');await flush();assert(h.ui.current.textContent.includes('"status": "queued"'));assert(h.ui.current.textContent.includes('"pending_terminal_status": "interrupted"'));assert(h.ui.submit.disabled);assert.equal(h.ui['review-submit'].disabled,false);h.ui['review-note'].value='keep binding';await h.ui['review-form'].listeners.submit({preventDefault(){}});assert.equal(posts,1);h.api.forgetConnection();
});
test('version switching after a metadata-only interruption never restores running text',async()=>{
 let stopped=false;const v1={answer_id:'A',version:1,text:'original'},v2={answer_id:'A',version:2,text:'revised'};
 const state=()=>({run_id:'A',status:'queued',pending_terminal_status:stopped?'interrupted':null,persistence_confirmed:!stopped,service_fault_code:stopped?'RESOURCE_CLOSE_FAILED':null});
 const h=await client(async p=>p==='/runs/A'?response(state()):p==='/runs/A/result'?response({answer:{original:v1,final:v2,versions:[v1,v2]},execution:{...state(),required_stages_complete:false},findings:{},evidence:[]}):fallback(p));
 await h.api.selectRun('A');await flush();stopped=true;await h.api.load();await flush();assert(h.ui.phase.textContent.includes('中断状态尚未确认保存'));
 const all=e=>[e,...e.children.flatMap(all)];const picker=all(h.ui.answers).find(e=>e.tag==='select');picker.value='1';picker.listeners.change();assert(h.ui.phase.textContent.includes('中断状态尚未确认保存'));assert(h.ui.answers.textContent.includes('original'));h.api.forgetConnection();
});
(async()=>{let failed=0;for(const [name,fn] of tests){try{await fn();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+': '+e.message);}}if(failed)process.exitCode=1;})().catch(e=>{console.error(e);process.exitCode=1;});
