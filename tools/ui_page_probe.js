/* Measurement hooks served only by tools.ui_page_performance, never production. */
const fixtureMetrics={records:[],runs:[],pending:0,current:null,usage:false,tick:0};
const fixtureFetch=window.fetch.bind(window);
window.fetch=async(...args)=>{
 if(!String(args[0]).startsWith('/runs')&&String(args[0])!=='/health')return fixtureFetch(...args);
 fixtureMetrics.pending++;
 try{const response=await fixtureFetch(...args);return {ok:response.ok,status:response.status,json:async()=>{
  const start=performance.now();try{const value=await response.json();const end=performance.now();
   if(fixtureMetrics.current){fixtureMetrics.current.json_ms+=end-start;
    if(String(args[0]).endsWith('/result')){fixtureMetrics.current.result_received=end;fixtureMetrics.current.visible=new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(performance.now()-end))));}
   }
   if(fixtureMetrics.usage&&String(args[0]).endsWith('/result'))value.budget_usage={...value.budget_usage,fixture_tick:++fixtureMetrics.tick};
   return value;
  }finally{fixtureMetrics.pending--;}
 }};}catch(e){fixtureMetrics.pending--;throw e;}
};
const fixtureFrame=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
async function fixtureIdle(){const deadline=performance.now()+10000;while(fixtureMetrics.pending){if(performance.now()>deadline)throw Error('fixture read did not settle');await new Promise(r=>setTimeout(r,0));}await fixtureFrame();}
async function fixtureMeasure(rid,scene){
 await selectRun(rid);await fixtureIdle();
 const values=[];
 for(let i=-1;i<5;i++){
  const record={run_id:rid,scene,json_ms:0,sync_ms:{}};fixtureMetrics.current=record;
  fixtureMetrics.usage=scene==='usage';const start=performance.now();
  if(scene==='open-details'){
   const details=[...document.querySelectorAll('main details')].filter(x=>!x.closest('#submit-form'));
   for(const d of details)d.open=false;await fixtureFrame();const begin=performance.now();for(const d of details)d.open=true;await fixtureFrame();record.open_to_two_frames_ms=performance.now()-begin;
  }else if(scene==='initial'){await selectRun(rid);await fixtureIdle();}
  else{await load();await fixtureIdle();}
  record.total_to_settled_two_frames_ms=performance.now()-start;
  if(record.visible)record.result_json_to_two_frames_ms=await record.visible;
  delete record.visible;delete record.result_received;
  record.dom_nodes=document.querySelectorAll('*').length;record.answer_visible=Boolean($('answers').textContent.trim());
  if(i>=0)values.push(record);fixtureMetrics.current=null;fixtureMetrics.usage=false;
 }
 fixtureMetrics.runs.push({run_id:rid,scene,values});
 $('fixture-metrics').textContent=JSON.stringify(fixtureMetrics.runs);
}
window.addEventListener('DOMContentLoaded',()=>{
 const panel=document.createElement('section');panel.id='fixture-measurements';panel.className='panel';panel.append(node('h2','隔离页面测量 · 1次预热/5次计时'));
 for(const rid of ['page-normal-v3','page-large-v3'])for(const scene of ['initial','refresh','usage','open-details']){
  const button=node('button',rid+' / '+scene);button.type='button';button.id='fixture-'+rid+'-'+scene;button.addEventListener('click',async()=>{button.disabled=true;button.dataset.complete='false';try{await fixtureMeasure(rid,scene);}catch(e){$('fixture-metrics').textContent='ERROR '+e.message;}finally{button.disabled=false;button.dataset.complete='true';}});panel.append(button);
 }
 const out=node('pre','尚未测量');out.id='fixture-metrics';panel.append(out);document.body.prepend(panel);
});
