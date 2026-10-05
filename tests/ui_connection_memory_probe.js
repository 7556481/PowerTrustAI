/* Actual scripts, synthetic credential only; output never contains a token. */
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const folder=process.argv[2];const secret='synthetic_fixture_connection_token_12345678';
class Element{constructor(tag='div'){this.children=[];this.value='';this.checked=false;this.listeners={};this.textContent='';}append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this.textContent='';}addEventListener(n,fn){this.listeners[n]=fn;}get options(){return this.children;}}
const state=new Map();const storage={getItem:k=>state.get(k)||null,setItem:(k,v)=>state.set(k,v),removeItem:k=>state.delete(k)};let unauthorized=false;
function page(){const ids=new Map();const el=id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);};
 const ctx={document:{getElementById:el,createElement:()=>new Element()},window:{localStorage:storage,addEventListener(){}},AbortController,URL,setTimeout,clearTimeout,JSON,Map,console,fetch:async(url,opts)=>{
 assert(!url.includes(secret));const publicHealth=url==='/health';const ok=publicHealth||!unauthorized&&opts.headers.Authorization==='Bearer '+secret;
 return{ok,status:ok?200:401,json:async()=>publicHealth?{profile:'synthetic_fixture',status:'ready',configuration_ready:true,queued:0,queue_capacity:2}:{items:[],next_offset:null}};
 }};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(folder,'connection_memory.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(folder,'app.js'),'utf8'),ctx);return{el,ctx};}
const flush=()=>new Promise(setImmediate);
(async()=>{
 let p=page();await flush();assert(!p.el('remember-connection').checked);p.el('token').value=secret;await p.el('access-form').listeners.submit({preventDefault(){}});assert.equal(state.size,0);
 p.el('remember-connection').checked=true;p.el('remember-connection').listeners.change();assert.equal(state.size,1);
 p=page();await flush();await flush();assert(p.el('remember-connection').checked);assert(p.el('notice').textContent.includes('已连接'));
 p.el('remember-connection').checked=false;p.el('remember-connection').listeners.change();assert.equal(state.size,0);assert(p.el('notice').textContent.includes('内存'));
 p.el('remember-connection').checked=true;p.el('remember-connection').listeners.change();assert.equal(state.size,1);
 p.el('disconnect').listeners.click();assert.equal(state.size,0);assert.equal(p.el('token').value,'');assert(p.el('submit').disabled);
 p.el('token').value=secret;p.el('remember-connection').checked=true;await p.el('access-form').listeners.submit({preventDefault(){}});assert.equal(state.size,1);
 unauthorized=true;p=page();await flush();await flush();assert.equal(state.size,0);assert(!p.el('remember-connection').checked);assert(p.el('submit').disabled);assert(p.el('notice').textContent.includes('失效'));
 const blocked=p.ctx.window.PowerTrustConnectionMemory.create(()=>{throw new Error('synthetic denied storage');});assert.equal(blocked.save(secret),false);assert.equal(blocked.load(),null);
 console.log('Actual client opt-in, restored auth, unchecked memory-only, forget,401 cleanup and storage failure passed.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
