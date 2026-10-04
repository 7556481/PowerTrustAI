// Execute the real client in a minimal DOM double; no browser/paid requests.
// This exercises uncertain POST handling and plain-text rendering independently
// of the HTTP suite. Actual browser verification is recorded separately.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.value='';this.disabled=false;this.hidden=false;this._text='';}
 set textContent(s){this._text=String(s);this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 set innerHTML(_){throw Error('unsafe HTML rendering');}
 get options(){return this.children;}
 append(...items){this.children.push(...items);if(this.tag==='select'&&!this.value)this.value=this.children[0]?.value||'';}
 replaceChildren(...items){this.children=items;this._text='';if(this.tag==='select')this.value='';}
 addEventListener(name,fn){this.listeners[name]=fn;}
 fire(name){return this.listeners[name]?.({preventDefault(){}});}
}
const html=fs.readFileSync('backend/static/index.html','utf8');
const ids=[...html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)];
const health={profile:'synthetic_fixture',status:'ready',configuration_ready:true,queued:0,queue_capacity:2};
const response=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const malicious='<script>alert(1)</script><style>body{display:none}</style><img src=x onerror=alert(2)>';
const result={execution:{status:'finished',required_stages_complete:true},answer:{original:{answer_id:'a',version:1,text:malicious},final:{answer_id:'a',version:1,text:malicious},versions:[{answer_id:'a',version:1,text:malicious}]},findings:{model_fact:[],domain:[],tools:[]},evidence:[{evidence_id:'e1',source_id:'fixture',text:malicious,provenance:{source_uri:'https://www.nerc.com/a.pdf'}},{evidence_id:'e2',provenance:{source_uri:'javascript:alert(1)'}}],feedback_targets:[],review_rounds:[]};
async function harness(handler){
 const elements=Object.fromEntries(ids.map(([_,tag,id])=>[id,new Element(tag)]));
 elements.mode.value='question_answer';elements['review-action'].value='pending';elements['review-source'].value='user';elements.reviewer.value='test';
 const calls=[];const context={document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},window:{addEventListener(){}},URL,AbortController,setTimeout,clearTimeout,console,
 fetch:async(path,opts)=>{calls.push({path,method:opts.method,body:opts.body});return handler(path,opts);}};
 vm.runInNewContext(fs.readFileSync('backend/static/app.js','utf8'),context);
 elements.token.value='fictional-test-token-not-a-secret';await elements['access-form'].fire('submit');elements.question.value='synthetic_fixture';
 return {elements,calls};
}
function get(path){if(path==='/health')return response(health);if(path.startsWith('/runs/page/'))return response({items:[],next_offset:null});if(path.endsWith('/result'))return response(result);if(path.endsWith('/trace'))return response({events:[]});if(path.endsWith('/reviews'))return response([]);if(path.includes('/evidence/'))return response({evidence_id:'e1',text:malicious});return response({run_id:'r1',status:'finished',profile:'synthetic_fixture'});}
(async()=>{
 let release;const gate=new Promise(r=>release=r);const h=await harness(async(p,o)=>p==='/runs'&&o.method==='POST'?(await gate,response({run_id:'r1'})):get(p));
 const first=h.elements['submit-form'].fire('submit');await Promise.resolve();await h.elements['submit-form'].fire('submit');release();await first;
 assert.equal(h.calls.filter(c=>c.path==='/runs'&&c.method==='POST').length,1,'duplicate click created a second task');
 assert.equal(h.elements.token.value,'','token input not cleared');
 assert.ok(h.elements.answers.textContent.includes(malicious),'model text was not retained literally');
 const anchors=h.elements.evidence.children.flatMap(c=>c.children).filter(c=>c.tag==='a');
 assert.equal(anchors.length,1);assert.equal(anchors[0].href,'https://www.nerc.com/a.pdf');assert.equal(anchors[0].rel,'noopener noreferrer');assert.equal(anchors[0].referrerPolicy,'no-referrer');
 const n=await harness(async(p,o)=>{if(p==='/runs'&&o.method==='POST')throw Error('offline after acceptance');return get(p);});
 await n.elements['submit-form'].fire('submit');await n.elements['submit-form'].fire('submit');
 assert.equal(n.calls.filter(c=>c.method==='POST').length,1);assert.ok(n.elements.submit.disabled);assert.match(n.elements.notice.textContent,/状态未知/);
 const f=await harness(async(p,o)=>o.method==='POST'&&p.endsWith('/reviews')?response({code:'INVALID_RUN_ANSWER_FINDING_BINDING'},409):p==='/runs'&&o.method==='POST'?response({run_id:'r1'}):get(p));
 await f.elements['submit-form'].fire('submit');f.elements['review-note'].value=malicious;await f.elements['review-form'].fire('submit');
 assert.equal(f.elements['review-note'].value,malicious);assert.match(f.elements.notice.textContent,/未确认保存成功/);
 for(const status of [401,409,429,422,503]){const h=await harness(async(p,o)=>p==='/runs'&&o.method==='POST'?response({},status):get(p));await h.elements['submit-form'].fire('submit');assert.equal(h.calls.filter(c=>c.method==='POST').length,1);assert.ok(h.elements.notice.className.includes('error'));}
 console.log('PASS: duplicate click; unknown POST locks retry; literal hostile text; feedback 409 retains input; 401/409/429/422/503 distinguished. No paid calls.');
})().catch(e=>{console.error(e);process.exitCode=1;});
