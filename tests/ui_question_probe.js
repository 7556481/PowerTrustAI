/* Real main-page DOM only: missing diagnostic elements remain null. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.value='';this._text='';this.hidden=false;}
 set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(c=>c.textContent).join(' ');}
 set innerHTML(v){throw Error('unsafe HTML');}get options(){return this.children;}
 append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;this._text='';}
 addEventListener(e,f){this.listeners[e]=f;}scrollIntoView(){}focus(){}
}
const html=fs.readFileSync('backend/static/index.html','utf8');
const ids=[...html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)];
const answer={answer_id:'a',version:1,text:'<script>plain draft</script>',citations:[{evidence_ids:['e1']}]};
const output={execution:{status:'running',required_stages_complete:false},answer:{final:answer,versions:[answer]},decision:{kind:'review_required'},findings:{},evidence:[{evidence_id:'e1',source_id:'fixture'}]};
async function client({unknown=false,refusal=false}={}){
 const elements=Object.fromEntries(ids.map(([,tag,id])=>[id,new Element(tag)])),calls=[],copies=[];
 const response=(v,status=200)=>({ok:status<400,status,json:async()=>v});
 const context={document:{getElementById:id=>elements[id]||null,createElement:t=>new Element(t)},window:{addEventListener(){}},navigator:{clipboard:{writeText:async t=>copies.push(t)}},URL,AbortController,setTimeout:()=>1,clearTimeout(){},console,
 fetch:async(p,o)=>{calls.push({p,o});if(p==='/health')return response({profile:'synthetic_fixture',status:'ready',configuration_ready:true,service_lifecycle:{accepting_work:!refusal}});
 if(p==='/runs'&&o.method==='POST'){if(unknown)throw Error('offline');return response({run_id:'A'},202);}
 if(p.endsWith('/result'))return response(output);if(p.includes('/evidence/'))return response({evidence_id:'e1',text:'synthetic original'});
 if(p.includes('/page/'))return response({items:[{run_id:'A',question_summary:'history question'}],next_offset:null});return response({run_id:'A',status:output.execution.status});}};
 const source=fs.readFileSync('backend/static/app.js','utf8').replace(/restoreConnection\(\)\.catch\(e=>tell\(errorText\(e\),true\)\);/,"window.testClient={connect,selectRun,load,health};");
 vm.runInNewContext(source,context);await context.window.testClient.connect('synthetic_fixture');return {elements,calls,copies,api:context.window.testClient};
}
const fire=(e,event='click')=>e.listeners[event]?.({preventDefault(){}});
(async()=>{
 for(const id of ['token','access-form','mode','context','requirements','reference','task-scope','nli-enabled','review-form','trace','usage','findings','run-id'])assert(!ids.some(x=>x[2]===id),id+' leaked into main DOM');
 const h=await client();assert(!h.elements.submit.disabled);assert(!h.calls.some(x=>x.p.includes('/page/')),'history loaded before requested');
 h.elements.question.value='Concept question';await fire(h.elements['submit-form'],'submit');
 const payload=JSON.parse(h.calls.find(x=>x.p==='/runs').o.body);assert.deepEqual(payload,{mode:'question_answer',question:'Concept question',engineering_context:{goal:'conceptual'}});
 assert(h.elements.answers.textContent.includes(answer.text));assert(h.elements.phase.textContent.includes('正在审核'));assert(!h.elements.answers.textContent.includes('查看回答版本'));assert(!h.elements.decision.textContent.includes('原始原因'));assert(!h.calls.some(x=>/\/(nli|trace|reviews)$/.test(x.p)));
 const find=(e,fn)=>fn(e)?e:e.children.map(x=>find(x,fn)).find(Boolean);
 await fire(find(h.elements.answers,e=>e.tag==='button'&&e.textContent==='复制所选正文'));assert.equal(h.copies[0],answer.text);
 await fire(find(h.elements.answers,e=>e.tag==='button'&&e.textContent==='查看依据 [1]'));assert(h.elements['evidence-detail'].textContent.includes('synthetic original'));assert(!h.elements['evidence-panel'].hidden);
 output.execution={status:'finished',required_stages_complete:true};output.decision.kind='pass';await h.api.load();assert(h.elements.phase.textContent.includes('审核执行完整'));
 output.no_substantive_answer=true;output.decision.kind='needs_information';await h.api.load();assert(h.elements.phase.textContent.includes('不适用'));output.no_substantive_answer=false;
 output.execution.status='cancelled';output.execution.required_stages_complete=false;await h.api.load();assert(h.elements.phase.textContent.includes('已取消'));
 h.elements['history-panel'].open=true;await fire(h.elements['history-panel'],'toggle');assert(h.calls.some(x=>x.p.includes('/page/')));
 assert.equal(h.elements['diagnostics-link'].href,'/ui/diagnostics.html#A');
 const denied=await client({refusal:true});denied.elements.question.value='x';await fire(denied.elements['submit-form'],'submit');assert(!denied.calls.some(x=>x.p==='/runs'));
 const uncertain=await client({unknown:true});uncertain.elements.question.value='x';await fire(uncertain.elements['submit-form'],'submit');await fire(uncertain.elements['service-check']);await fire(uncertain.elements['submit-form'],'submit');assert.equal(uncertain.calls.filter(x=>x.p==='/runs').length,1);
 console.log('PASS main real DOM: conceptual payload, draft/terminal/no-answer/cancel, copy/citation, demand history, diagnostic link, admission and unknown POST lock');
})().catch(e=>{console.error(e);process.exitCode=1;});
