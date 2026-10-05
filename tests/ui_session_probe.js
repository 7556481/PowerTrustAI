/* Public cookie fixture, actual client; no real credential or paid request. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class E{constructor(){this.children=[];this.value='';this.checked=false;this.textContent='';this.listeners={};}append(...x){this.children.push(...x);}replaceChildren(...x){this.children=x;this.textContent='';}addEventListener(n,f){this.listeners[n]=f;}get options(){return this.children;}}
let session=true;const calls=[];
function page(){const ids=new Map();const el=id=>{if(!ids.has(id))ids.set(id,new E);return ids.get(id);};const ctx={document:{getElementById:el,createElement:()=>new E},window:{addEventListener(){},PowerTrustConnectionMemory:{create:()=>({load:()=>null,forget:()=>true,save:()=>false})}},URL,AbortController,setTimeout,clearTimeout,JSON,Map,console,fetch:async(url,opts)=>{
 calls.push({url,method:opts.method||'GET'});assert.equal(opts.credentials,'same-origin');assert(!opts.headers?.Authorization);
 const ok=url==='/health'||session;if(url==='/session/logout')session=false;
 return {ok,status:ok?200:401,json:async()=>url==='/health'?{profile:'synthetic_fixture',status:'ready',configuration_ready:true,queued:0,queue_capacity:2}:url==='/session'?{connected:true,version:'localhost-launch-session-v1'}:{items:[],next_offset:null}};}};
 vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),ctx);return el;}
const flush=()=>new Promise(setImmediate);
(async()=>{let el=page();await flush();await flush();assert(!el('submit').disabled);assert(el('notice').textContent.includes('自动连接'));el=page();await flush();await flush();assert(!el('submit').disabled);assert(calls.every(c=>c.method==='GET'));await el('disconnect').listeners.click();assert(el('submit').disabled);assert(el('notice').textContent.includes('注销'));el=page();await flush();await flush();assert(el('submit').disabled);assert(!calls.some(c=>c.url==='/runs'&&c.method==='POST'));console.log('Cookie reload, no bearer exposure, acknowledged logout and no task resubmission passed.');})().catch(e=>{console.error(e.message);process.exitCode=1;});
