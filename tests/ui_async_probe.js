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
async function client(handler){
 const ids=[...fs.readFileSync('backend/static/index.html','utf8').matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)];
 const elements=Object.fromEntries(ids.map(([,tag,id])=>[id,new Element(tag)]));
 const context={document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},window:{addEventListener(){}},URL,AbortController,setTimeout,clearTimeout,console,fetch:handler};
 const source=fs.readFileSync('backend/static/app.js','utf8').replace(/restoreConnection\(\)\.catch\(e=>tell\(errorText\(e\),true\)\);/,"window.testClient={selectRun,forgetConnection,history,connect,api,errorText,state:()=>({reading,selected,connected})};");
 vm.runInNewContext(source,context);await context.window.testClient.connect('synthetic_fixture_not_a_secret');return {ui:elements,api:context.window.testClient};
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
(async()=>{let failed=0;for(const [name,fn] of tests){try{await fn();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+': '+e.message);}}if(failed)process.exitCode=1;})().catch(e=>{console.error(e);process.exitCode=1;});
