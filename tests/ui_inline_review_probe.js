/* Real main HTML + real renderer + real client; no invented diagnostic DOM. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let document;
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.style={};this.value='';this._text='';this.hidden=false;this.attrs={};}
 set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 set innerHTML(v){throw Error('unsafe HTML');}get options(){return this.children;}
 append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this._text='';}
 addEventListener(e,f){this.listeners[e]=f;}setAttribute(k,v){this.attrs[k]=v;}scrollIntoView(){}
 focus(){document.activeElement=this;this.listeners.focus?.();}
 querySelector(s){return find(this,e=>e.id===s.slice(1));}
}
const find=(e,f)=>f(e)?e:e.children.map(x=>find(x,f)).find(Boolean);
const all=(e,f)=>[...(f(e)?[e]:[]),...e.children.flatMap(x=>all(x,f))];
const html=fs.readFileSync('backend/static/index.html','utf8'),ids=[...html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)];
const elements=Object.fromEntries(ids.map(([,tag,id])=>[id,new Element(tag)])),copies=[];
document={getElementById:id=>elements[id]||find(elements.answers,e=>e.id===id)||null,createElement:t=>new Element(t)};
const response=v=>({ok:true,status:200,json:async()=>v});
const context={document,window:{addEventListener(){}},navigator:{clipboard:{writeText:async t=>copies.push(t)}},URL,AbortController,setTimeout:()=>1,clearTimeout(){},console,
 fetch:async p=>response(p==='/health'?{profile:'synthetic_fixture',status:'ready',configuration_ready:true,service_lifecycle:{accepting_work:true}}:{items:[],next_offset:null})};
vm.runInNewContext(fs.readFileSync('backend/static/inline_review.js','utf8'),context);
const source=fs.readFileSync('backend/static/app.js','utf8').replace(/restoreConnection\(\)\.catch\(e=>tell\(errorText\(e\),true\)\);/,"window.testClient={renderAnswers};");vm.runInNewContext(source,context);
const a={answer_id:'A',version:2,text:'😀前缀\r\n同一句意见。\n<script>原文</script>',citations:[]},points=Array.from(a.text),start=points.join('').indexOf('同一句意见。')-1,end=start+6;
const opinion=(origin,status='insufficient_evidence')=>({opinion_id:origin,origin,status,reason:origin+'的独立理由',answer_id:'A',answer_version:2,start,end,original_text:'同一句意见。',located:true,evidence_ids:['e']});
const r={execution:{status:'finished',required_stages_complete:true},answer:{final:a,versions:[{...a,version:1,text:'原回答'},a],revisions:[]},decision:{kind:'needs_information'},presentation:{inline_review:{version:'answer-inline-review-v1',offset_unit:'unicode_codepoint',ready:true,answer_id:'A',answer_version:2,opinions:[opinion('fact'),opinion('citation')]}},findings:{},evidence:[]};
const render=()=>context.window.testClient.renderAnswers(r);
const marks=()=>all(elements.answers,e=>e.tag==='mark');
const body=()=>find(elements.answers,e=>e.tag==='pre'&&e.className==='answer-text');
const panel=()=>find(elements.answers,e=>e.className==='review-popover');
const fire=(e,event='click',extra={})=>e.listeners[event]?.({preventDefault(){},...extra});
(async()=>{
 render();assert.equal(marks().length,1);assert.equal(body().textContent,a.text);assert(marks()[0].className.includes('insufficient'));assert(elements.answers.textContent.includes('正文待核实位置：1'));assert(!elements.answers.textContent.includes('已修订'));
 assert(!elements.decision.textContent.includes('未解决句子'));await fire(marks()[0]);assert(!panel().hidden);assert(panel().textContent.includes('fact的独立理由'));assert(panel().textContent.includes('citation的独立理由'));assert(panel().textContent.includes('依据不足'));assert(!panel().textContent.includes('事实错误'));
 await fire(panel(),'keydown',{key:'Escape'});assert(panel().hidden,'Escape reopened focus popup');assert.equal(document.activeElement,marks()[0]);
 await fire(marks()[0],'keydown',{key:'Enter'});assert(!panel().hidden);await fire(find(panel(),e=>e.tag==='button'&&e.textContent==='关闭原因'));assert(panel().hidden);
 await fire(find(elements.answers,e=>e.tag==='button'&&e.textContent==='复制所选正文'));assert.equal(copies.at(-1),a.text);assert.equal(body().textContent,a.text);
 const saved=JSON.stringify(r);marks()[0].focus();render();assert.equal(document.activeElement.id,'review-mark-0');assert.equal(JSON.stringify(r),saved);
 r.presentation.inline_review.opinions[1].status='contradicted';render();assert(marks()[0].className.includes('conflict'));await fire(marks()[0]);assert(panel().textContent.includes('与依据存在冲突（审核判断）'));
 // Offset corruption, nonliteral proposition and foreign version never get guessed.
 for(const mutate of [o=>o.start++,o=>o.answer_version=1,o=>o.original_text='改述',o=>o.start=true]){const p=structuredClone(r.presentation.inline_review);p.opinions=[opinion('fact')];mutate(p.opinions[0]);r.presentation.inline_review=p;render();assert.equal(marks().length,0);assert(elements.answers.textContent.includes('此项未能定位到正文'));assert.equal(body().textContent,a.text);}
 r.presentation.inline_review.opinions=[opinion('fact')];
 const picker=find(elements.answers,e=>e.id==='answer-version');picker.value='1';await fire(picker,'change');assert.equal(marks().length,0);assert(elements.answers.textContent.includes('当前展示历史版本'));assert.equal(body().textContent,'原回答');
 const latest=find(elements.answers,e=>e.id==='answer-version');latest.value='2';await fire(latest,'change');
 for(const [status,complete,noAnswer] of [['running',false,false],['interrupted',false,false],['finished',true,true]]){r.execution={status,required_stages_complete:complete};r.no_substantive_answer=noAnswer;render();assert.equal(marks().length,0);assert.equal(body().textContent,a.text);}
 r.execution={status:'finished',required_stages_complete:true};r.no_substantive_answer=false;
 // Overlap is flattened into nonnested exact segments; untouched prefix/suffix stays literal.
 r.presentation.inline_review.opinions=[opinion('fact'),{...opinion('citation'),start:start+2,end:end+2,original_text:points.slice(start+2,end+2).join('')}];render();assert.equal(marks().length,3);assert.equal(body().textContent,a.text);assert(marks().every(m=>!m.children.some(c=>c.tag==='mark')));assert(elements.answers.textContent.includes('正文待核实位置：1'));
 r.presentation.inline_review.opinions=[];r.decision={kind:'pass',execution_integrity:'complete'};render();
 assert.equal(all(elements.answers,e=>e.className==='badge pass').length,1);assert(!elements.answers.textContent.includes('0处'));assert(!elements.phase.textContent.includes('通过'));assert.equal(elements.decision.textContent,'');
 for(const [status,complete,noAnswer,kind] of [['running',false,false,'pass'],['failed',true,false,'pass'],['finished',false,false,'pass'],['finished',true,true,'pass'],['finished',true,false,'review_required'],['finished',true,false,'needs_information']]){r.execution={status,required_stages_complete:complete};r.no_substantive_answer=noAnswer;r.decision.kind=kind;render();assert.equal(all(elements.answers,e=>e.className==='badge pass').length,0);}
 console.log('PASS inline real DOM: exact Unicode/CRLF/hostile text, merged opinions, conflict labels, version/offset fallback, overlap, copy, focus/Escape, pending and interruption');
})().catch(e=>{console.error(e);process.exitCode=1;});
