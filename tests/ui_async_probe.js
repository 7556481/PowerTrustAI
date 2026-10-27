/* Actual app.js with controlled GET delays. No server, credentials or models. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.value='';this.disabled=false;this.hidden=false;this._text='';}
 set textContent(v){this._text=String(v);this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join(' ');}
 set innerHTML(_){throw Error('unsafe model HTML');}
 get options(){return this.children;}
 append(...items){this.children.push(...items);if(this.tag==='select'&&!this.value)this.value=this.children[0]?.value||'';}
 replaceChildren(...items){this.children=items;this._text='';if(this.tag==='select')this.value='';}
 addEventListener(n,fn){this.listeners[n]=fn;}
 scrollIntoView(){}
}
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const response=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const answer=id=>({execution:{status:'finished',required_stages_complete:true},answer:{final:{answer_id:id,version:1,text:'answer '+id},versions:[{answer_id:id,version:1,text:'answer '+id}]},findings:{},evidence:[],review_rounds:[]});
const fallback=p=>p==='/health'?response({profile:'synthetic_fixture',status:'ready',configuration_ready:true,queued:0,queue_capacity:2}):p.includes('/page/')?response({items:[],next_offset:null}):p.endsWith('/result')?response(answer(p.split('/')[2])):p.endsWith('/nli')?response({enabled:false,records:[],risk_note:'diagnostic '+p.split('/')[2]}):p.endsWith('/trace')?response({events:[]}):p.endsWith('/reviews')?response([]):response({run_id:p.split('/')[2],status:'finished',profile:'synthetic_fixture'});
async function client(handler,settings={}){
 const ids=[...fs.readFileSync('backend/static/index.html','utf8').matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)];
 const elements=Object.fromEntries(ids.map(([,tag,id])=>[id,new Element(tag)]));
 const copied=[];const polls=new Map(),deadlines=new Map();let tick=0;
 const schedule=(fn,ms)=>ms===1800?(polls.set(++tick,fn),tick):settings.virtualClock?(deadlines.set(++tick,{fn,ms}),tick):setTimeout(fn,ms);
 const unschedule=id=>polls.has(id)?polls.delete(id):deadlines.has(id)?deadlines.delete(id):clearTimeout(id);
 const windowEvents={};const context={document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},navigator:{clipboard:{writeText:async t=>copied.push(t)}},window:{addEventListener(n,f){windowEvents[n]=f;}},URL,AbortController,setTimeout:schedule,clearTimeout:unschedule,console,fetch:handler};
 const source=fs.readFileSync(settings.sourcePath||'backend/static/app.js','utf8').replace(/restoreConnection\(\)\.catch\(e=>tell\(errorText\(e\),true\)\);/,"window.testClient={selectRun,forgetConnection,history,connect,api,errorText,renderAnswers,load,state:()=>({reading,selected,connected})};");
 vm.runInNewContext(source,context);await context.window.testClient.connect('synthetic_fixture_not_a_secret');return {ui:elements,api:context.window.testClient,copied,polls,deadlines,windowEvents};
}
const tests=[];const test=(name,fn)=>tests.push([name,fn]);
test('disconnect rejects delayed NLI',async()=>{
 const arrived=deferred(),gate=deferred();const h=await client(async p=>{if(p==='/runs/A/nli'){arrived.resolve();await gate.promise;return response({records:[],enabled:false,risk_note:'STALE A'});}return fallback(p);});
 const a=h.api.selectRun('A');await arrived.promise;h.api.forgetConnection();gate.resolve();await a;assert(!h.ui['local-nli'].textContent.includes('STALE A'));
});
test('rapid A to B selection and old finally cannot unlock B',async()=>{
 const aArrived=deferred(),bArrived=deferred(),aGate=deferred(),bGate=deferred();const h=await client(async p=>{
  if(p==='/runs/A/nli'){aArrived.resolve();await aGate.promise;return response({records:[],risk_note:'STALE A'});}
  if(p==='/runs/B'){bArrived.resolve();await bGate.promise;}return fallback(p);
 });
 const a=h.api.selectRun('A');await aArrived.promise;const b=h.api.selectRun('B');
 // Flush promises; no deadline sleeps and no waiting forever on the broken client.
 await new Promise(setImmediate);assert.equal(h.api.state().selected,'B');
 aGate.resolve();await a;assert(h.api.state().reading,'old finally released the newer read');
 bGate.resolve();await b;assert(h.ui.answers.textContent.includes('answer B'));assert(!h.ui['local-nli'].textContent.includes('STALE A'));
});
test('latest history refresh owns list and page offset',async()=>{
 let active=false;const gate=deferred();const h=await client(async p=>{
  if(active&&p==='/runs/page/20'){await gate.promise;return response({items:[{run_id:'old-page',mode:'question_answer'}],next_offset:40});}
  if(active&&p==='/runs/page/0')return response({items:[{run_id:'new-page',mode:'question_answer'}],next_offset:null});return fallback(p);
 });
 active=true;const old=h.api.history(20);await h.api.history(0);gate.resolve();await old;assert(h.ui.history.textContent.includes('new-page'));assert(!h.ui.history.textContent.includes('old-page'));assert(h.ui['history-next'].hidden);
});
test('old unauthorized read cannot revoke reconnected session',async()=>{
 const gate=deferred();const h=await client(async p=>{if(p==='/old'){await gate.promise;return response({},401);}return fallback(p);});
 const old=h.api.api('/old').catch(()=>{});h.api.forgetConnection();await h.api.connect('synthetic_fixture_not_a_secret');gate.resolve();await old;assert(h.api.state().connected);
});
test('GET failure does not imply task acceptance or resubmission',async()=>{
 const h=await client(async p=>fallback(p));assert(!/任务可能已被服务接收/.test(h.api.errorText(Error('offline'))));
});
test('version selection copies only selected plain text and scopes citations',async()=>{
 const h=await client(async p=>fallback(p));
 const v1={answer_id:'versioned',version:1,text:'<script>original only</script>',citations:[{evidence_ids:['old-source']}]};
 const v2={answer_id:'versioned',version:2,text:'current only',citations:[{evidence_ids:['current-source']}]};
 h.api.renderAnswers({execution:{status:'finished',required_stages_complete:true},answer:{original:v1,final:v2,versions:[v1,v2]},decision:{kind:'pass'},evidence:[]});
 const all=e=>[e,...e.children.flatMap(all)];
 let nodes=all(h.ui.answers);await nodes.find(x=>x.tag==='button'&&x.textContent==='复制所选正文').listeners.click();assert.equal(h.copied[0],'current only');
 const picker=nodes.find(x=>x.tag==='select');picker.value='1';picker.listeners.change();nodes=all(h.ui.answers);
 assert(nodes.some(x=>x.tag==='pre'&&x.textContent===v1.text));assert(nodes.some(x=>x.tag==='button'&&x.textContent==='查看引用 old-source'));assert(!nodes.some(x=>x.tag==='button'&&x.textContent==='查看引用 current-source'));
 await nodes.find(x=>x.tag==='button'&&x.textContent==='复制所选正文').listeners.click();assert.deepEqual(h.copied,['current only',v1.text]);
});
test('feedback draft belongs to run including action and source; return restores payload',async()=>{
 const writes=[];const h=await client(async(p,o)=>{if(o.method==='POST'){writes.push([p,JSON.parse(o.body)]);return response({});}return fallback(p);});
 await h.api.selectRun('A');h.ui['review-note'].value='A draft';h.ui['review-action'].value='disagree';h.ui['review-source'].value='ai_assisted_user_supervised';
 await h.api.selectRun('B');assert.equal(h.ui['review-note'].value,'');assert.equal(h.ui['review-action'].value,'pending');assert.equal(h.ui['review-source'].value,'user');
 h.ui['review-note'].value='B draft';await h.api.selectRun('A');assert.equal(h.ui['review-note'].value,'A draft');
 await h.ui['review-form'].listeners.submit({preventDefault(){}});assert.equal(writes[0][0],'/runs/A/reviews');assert.equal(writes[0][1].note,'A draft');assert.equal(writes[0][1].answer_id,'A');assert.equal(writes[0][1].action,'disagree');
 await h.api.selectRun('B');assert.equal(h.ui['review-note'].value,'B draft');
});
test('saved A readback error cannot replace B notice or input',async()=>{
 let saved=false;const arrived=deferred(),gate=deferred();const h=await client(async(p,o)=>{
  if(p==='/runs/A/reviews'&&o.method==='POST'){saved=true;return response({});}
  if(saved&&p==='/runs/A/reviews'){arrived.resolve();await gate.promise;throw Error('readback offline');}return fallback(p);
 });
 await h.api.selectRun('A');h.ui['review-note'].value='saved A';const save=h.ui['review-form'].listeners.submit({preventDefault(){}});await arrived.promise;
 await h.api.selectRun('B');h.ui['review-note'].value='B editing';const notice=h.ui.notice.textContent;gate.resolve();await save;assert.equal(h.ui.notice.textContent,notice);assert.equal(h.ui['review-note'].value,'B editing');
});
test('pending A save clears only unchanged A draft while B edited',async()=>{
 const arrived=deferred(),gate=deferred();const writes=[];const h=await client(async(p,o)=>{if(o.method==='POST'){writes.push(JSON.parse(o.body));arrived.resolve();await gate.promise;return response({});}return fallback(p);});
 await h.api.selectRun('A');h.ui['review-note'].value='A submitted';const save=h.ui['review-form'].listeners.submit({preventDefault(){}});await arrived.promise;
 await h.api.selectRun('B');h.ui['review-note'].value='B editing';gate.resolve();await save;assert.equal(h.ui['review-note'].value,'B editing');await h.api.selectRun('A');assert.equal(h.ui['review-note'].value,'');assert.equal(writes.length,1);
});
for(const item of ['trace','reviews'])test(item+' failure is bounded and does not stop running to finished; manual recovers',async()=>{
 let done=false,fail=true,calls=0;const h=await client(async p=>{if(p==='/runs/A')return response({status:done?'finished':'running',run_id:'A'});if(p==='/runs/A/'+item){calls++;if(fail)throw Error('aux offline');}return fallback(p);});
 await h.api.selectRun('A');await new Promise(setImmediate);assert.equal(h.polls.size,1,'aux failure stopped main polling');assert(h.ui[item==='trace'?'trace':'reviews'].textContent.includes('失败'));
 done=true;const fn=[...h.polls.values()][0];await fn();assert(h.ui.current.textContent.includes('结束'));assert.equal(calls,1,'failed aux repeated');
 fail=false;await h.api.load();await new Promise(setImmediate);assert.equal(calls,2);assert(!h.ui[item==='trace'?'trace':'reviews'].textContent.includes('失败'));
});
test('unchanged polling preserves answer picker and feedback DOM focus target',async()=>{
 const h=await client(async p=>fallback(p));await h.api.selectRun('A');const picker=h.ui['review-answer'];const first=picker.children[0];const rendered=h.ui.answers.children[0];await h.api.load();assert.equal(picker.children[0],first);assert.equal(h.ui.answers.children[0],rendered);
});
test('old submit rejection cannot lock or overwrite a reconnected client; POST once',async()=>{
 const arrived=deferred(),gate=deferred();let writes=0;const h=await client(async(p,o)=>{if(p==='/runs'&&o.method==='POST'){writes++;arrived.resolve();await gate.promise;throw Error('unknown acceptance');}return fallback(p);});
 h.ui.question.value='synthetic';h.ui.requirements.value='';h.ui.mode.value='question_answer';const save=h.ui['submit-form'].listeners.submit({preventDefault(){}});await arrived.promise;
 h.api.forgetConnection();await h.api.connect('synthetic_fixture_not_a_secret');const notice=h.ui.notice.textContent;gate.resolve();await save;assert.equal(h.ui.notice.textContent,notice);assert.equal(h.ui.submit.disabled,false);assert.equal(writes,1);
});
test('old logout cannot revoke a newly connected page',async()=>{
 const arrived=deferred(),gate=deferred();const h=await client(async(p,o)=>{if(p==='/session/logout'){arrived.resolve();await gate.promise;}return fallback(p);});
 const logout=h.ui.disconnect.listeners.click();await arrived.promise;await h.api.connect('new_fixture');const notice=h.ui.notice.textContent;gate.resolve();await logout;assert(h.api.state().connected);assert.equal(h.ui.notice.textContent,notice);
});
test('pagehide rejects delayed primary result and schedules no poll',async()=>{
 const arrived=deferred(),gate=deferred();const h=await client(async p=>{if(p==='/runs/A/result'){arrived.resolve();await gate.promise;}return fallback(p);});
 const load=h.api.selectRun('A');await arrived.promise;h.windowEvents.pagehide();gate.resolve();await load;assert.equal(h.ui.answers.textContent,'');assert.equal(h.polls.size,0);
});
test('changed action since submission retains draft; unknown write stays one request',async()=>{
 const arrived=deferred(),gate=deferred();let calls=0;const h=await client(async(p,o)=>{if(o.method==='POST'){calls++;arrived.resolve();await gate.promise;return response({});}return fallback(p);});
 await h.api.selectRun('A');h.ui['review-note'].value='unchanged text';h.ui['review-action'].value='note';const saving=h.ui['review-form'].listeners.submit({preventDefault(){}});await arrived.promise;h.ui['review-action'].value='disagree';gate.resolve();await saving;assert.equal(h.ui['review-note'].value,'unchanged text');assert.equal(calls,1);
 const u=await client(async(p,o)=>{if(o.method==='POST')throw Error('unknown');return fallback(p);});await u.api.selectRun('A');u.ui['review-note'].value='keep';await u.ui['review-form'].listeners.submit({preventDefault(){}});assert.equal(u.ui['review-note'].value,'keep');assert(u.ui.notice.textContent.includes('输入已保留'));
});
test('missing restored finding requires explicit selection, never silently entire answer',async()=>{
 let hasFinding=true;const h=await client(async p=>{if(p==='/runs/A/result')return response({...answer('A'),feedback_targets:hasFinding?[{answer_id:'A',answer_version:1,finding_id:'f1'}]:[]});return fallback(p);});
 await h.api.selectRun('A');h.ui['review-finding'].value='f1';h.ui['review-note'].value='finding note';await h.api.selectRun('B');hasFinding=false;await h.api.selectRun('A');assert(h.ui['review-draft-status'].textContent.includes('重新选择'));assert(h.ui['review-submit'].disabled);
});
test('draft restoration finishes with main result before slow auxiliary read',async()=>{
 let slow=false;const arrived=deferred(),gate=deferred();const h=await client(async p=>{if(slow&&p==='/runs/A/nli'){arrived.resolve();await gate.promise;}return fallback(p);});
 await h.api.selectRun('A');h.ui['review-note'].value='older A';await h.api.selectRun('B');slow=true;const load=h.api.selectRun('A');await arrived.promise;h.ui['review-note'].value='edited during auxiliary wait';gate.resolve();await load;assert.equal(h.ui['review-note'].value,'edited during auxiliary wait');
});
test('usage updates do not rebuild an unchanged answer version picker',async()=>{
 let calls=1;const h=await client(async p=>p==='/runs/A/result'?response({...answer('A'),model_usage:[{calls}]}):fallback(p));
 await h.api.selectRun('A');const rendered=h.ui.answers.children[0];calls=2;await h.api.load();assert.equal(h.ui.answers.children[0],rendered);assert(h.ui.usage.textContent.includes('2'));
});
if(require.main===module)(async()=>{let failed=0;for(const [name,fn] of tests){try{await fn();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+': '+e.message);}}if(failed)process.exitCode=1;})().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={client,response,answer,fallback,deferred};
