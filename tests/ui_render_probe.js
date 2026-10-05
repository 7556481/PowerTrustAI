/* Public synthetic_fixture: execute the actual client, no network/browser secrets. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.listeners={};this.textContent='';}
 append(...items){this.children.push(...items);if(this.tag==='select'&&!this.value&&items[0])this.value=items[0].value;}
 replaceChildren(...items){this.children=items;this.textContent='';if(this.tag==='select')this.value='';}
 addEventListener(name,fn){this.listeners[name]=fn;}
 scrollIntoView(options){this.lastScroll=options;}
 get options(){return this.children;}
 set innerHTML(v){throw Error('Unsafe HTML rendering');}
}
const ids=new Map();const element=id=>{if(!ids.has(id))ids.set(id,new Element(id.startsWith('review-')?'select':'div'));return ids.get(id);};
const answer={answer_id:'synthetic-answer',version:1,text:'synthetic_fixture',citations:[{evidence_ids:['cited-e1']}]};
const result={execution:{status:'finished',required_stages_complete:true},answer:{original:answer,final:answer,versions:[answer]},
 decision:{kind:'review_required'},presentation:{reasons:['synthetic_fixture'],next_steps:[],saved:'saved'},
 configuration:{retrieval_mode:'hybrid',fact_retrieval_strategy:'per_claim_v1',knowledge_version:'synthetic-k',embedding_profile:{model_id:'synthetic_fixture'},scoring_method:'synthetic-RRF'},
 retrieval:[{query:'<script>throw Error("untrusted")</script>'}],findings:{},evidence:[
 {evidence_id:'cited-e1',source_id:'cited_source',locator:'synthetic paragraph'},
 {evidence_id:'uncited-e2',source_id:'uncited_source',locator:'synthetic paragraph'}],feedback_targets:[],limitations:[]};
const requests=[];
const context={document:{getElementById:element,createElement:tag=>new Element(tag)},window:{addEventListener(){}},
 AbortController,URL,setTimeout,clearTimeout,JSON,Map,console,
 fetch:async(path,opts)=>{requests.push({path,method:opts.method});const body=path==='/health'?{profile:'synthetic_fixture',status:'ready',configuration_ready:true,queued:0,queue_capacity:2}:
 path.includes('/page/')?{items:[],next_offset:null}:path.endsWith('/result')?result:path.endsWith('/trace')?{events:[]}:path.endsWith('/reviews')?[]:{run_id:'synthetic',status:'finished'};
 return {ok:true,json:async()=>body};}};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),context);
function texts(e){return e.textContent+e.children.map(texts).join(' ');}
(async()=>{
 element('token').value='synthetic_fixture_not_a_secret';await element('access-form').listeners.submit({preventDefault(){}});
 element('run-id').value='synthetic';await element('lookup-form').listeners.submit({preventDefault(){}});
 await new Promise(setImmediate); // drain async GET/render chain started by the event listener
 const usage=texts(element('usage'));
 assert(usage.includes('事实检索模式、知识版本、逐主张交付与省略'),texts(element('notice')));
 assert(usage.includes('hybrid')&&usage.includes('synthetic-k')&&usage.includes('per_claim_v1'));
 assert(usage.includes('<script>'));assert(texts(element('notice')).includes('已查询'));
 assert(requests.every(r=>r.method==='GET'));assert(texts(element('reviews')).includes('暂无反馈'));
 assert.equal(element('answers').lastScroll.block,'start');
 assert(texts(element('answers')).includes('cited_source'));
 assert(!texts(element('answers')).includes('uncited_source'));
 assert(texts(element('evidence')).includes('uncited_source')); // retained in technical detail
 console.log('Actual client render, saved configuration, text safety and GET-only restoration passed.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
