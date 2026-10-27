/* Read-only code-point marking. Text and clipboard always use the saved version. */
'use strict';
window.PowerTrustInlineReview=(()=>{
const kinds={insufficient_evidence:['依据不足','insufficient'],contradicted:['与依据存在冲突（审核判断）','conflict'],not_assessable:['无法评估','concern'],incomplete:['检查未完成','execution'],failed:['执行失败','execution'],concern:['存在疑点','concern'],warning:['存在疑点','concern']};
const origins={fact:'事实审核',citation:'引用审核',domain:'领域审核',rule:'程序检查'};
const kind=o=>kinds[o.status]||kinds.concern;
const same=(p,a)=>Boolean(a?.answer_id)&&p?.answer_id===a.answer_id&&Number.isInteger(a.version)&&p.answer_version===a.version;
function model(answer,final,projection,execution,noAnswer){
 const text=answer?.text||'',points=Array.from(text),current=answer?.answer_id===final?.answer_id&&answer?.version===final?.version&&text===final?.text;
 const ready=current&&projection?.ready===true&&same(projection,answer)&&projection.offset_unit==='unicode_codepoint'&&execution?.status==='finished'&&execution.required_stages_complete===true&&!noAnswer;
 const opinions=projection?.opinions||[],valid=[],unlocated=[];
 if(ready)for(const o of opinions){
  if(o.located===true&&same(o,answer)&&Number.isInteger(o.start)&&Number.isInteger(o.end)&&o.start>=0&&o.start<o.end&&o.end<=points.length&&typeof o.original_text==='string'&&points.slice(o.start,o.end).join('')===o.original_text)valid.push(o);
  else unlocated.push(o);
 }
 const bounds=[...new Set(valid.flatMap(o=>[o.start,o.end]))].sort((a,b)=>a-b),segments=[];
 for(let i=0;i<bounds.length-1;i++){const start=bounds[i],end=bounds[i+1],active=valid.filter(o=>o.start<=start&&o.end>=end);if(active.length)segments.push({start,end,opinions:active});}
 const regions=[];for(const s of segments){const prev=regions.at(-1);if(prev&&s.start<prev.end||prev&&s.start===prev.end&&prev.opinions.some(o=>s.opinions.includes(o))){prev.end=s.end;for(const o of s.opinions)if(!prev.opinions.includes(o))prev.opinions.push(o);}else regions.push({start:s.start,end:s.end,opinions:[...s.opinions]});}
 return {text,points,current,ready,valid,unlocated,segments,regions};
}
function render({answer,final,projection,execution,noAnswer,revisions,node,lookupEvidence}){
 const m=model(answer,final,projection,execution,noAnswer),area=node('div',null,'inline-review'),summary=node('div',null,'inline-summary'),body=node('pre',null,'answer-text'),reading=node('div',null,'answer-reading');
 const panel=node('section',null,'review-popover');panel.hidden=true;panel.setAttribute?.('aria-label','正文审核意见');
 let owner=null,activeKey=null,returningFocus=false;
 function close(returnFocus=true){panel.hidden=true;panel.replaceChildren();activeKey=null;if(returnFocus){returningFocus=true;owner?.focus?.();returningFocus=false;}}
 function show(opinions,trigger,key){
  owner=trigger;activeKey=key;panel.replaceChildren();panel.hidden=false;
  const closeButton=node('button','关闭原因','quiet');closeButton.type='button';closeButton.addEventListener('click',()=>close());panel.append(closeButton);
  for(const o of opinions){const card=node('div',null,'inline-opinion');card.append(node('strong',kind(o)[0]),node('span',' · '+(origins[o.origin]||'已存审核意见'),'hint'),node('p',o.reason||'具体原因未提供'));
   for(const [i,id] of (o.evidence_ids||[]).entries()){const b=node('button','查看依据 '+(i+1),'quiet');b.type='button';b.addEventListener('click',()=>lookupEvidence(id,b));card.append(b);}panel.append(card);}
  panel.append(node('p','标注是已有审核意见，正文未因标注改变；未标注部分不表示已核实正确。','hint'));
  if(trigger?.getBoundingClientRect&&reading.getBoundingClientRect){const r=trigger.getBoundingClientRect(),base=reading.getBoundingClientRect();panel.style.top=Math.max(0,r.bottom-base.top+8)+'px';}
 }
 panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();close();}});
 function activate(mark,opinions,key){mark.addEventListener('click',()=>show(opinions,mark,key));mark.addEventListener('focus',()=>{if(!returningFocus)show(opinions,mark,key);});mark.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();close();}else if(e.key==='Enter'||e.key===' '){e.preventDefault();show(opinions,mark,key);}});}
 let cursor=0;
 for(const [i,s] of m.segments.entries()){
  if(s.start>cursor)body.append(node('span',m.points.slice(cursor,s.start).join('')));
  const tone=s.opinions.some(o=>o.status==='contradicted')?'conflict':s.opinions.some(o=>o.status==='insufficient_evidence')?'insufficient':s.opinions.some(o=>['incomplete','failed'].includes(o.status))?'execution':'concern';
  const mark=node('mark',m.points.slice(s.start,s.end).join(''),'review-mark '+tone);mark.id='review-mark-'+i;mark.tabIndex=0;mark.setAttribute?.('role','button');mark.setAttribute?.('aria-label',[...new Set(s.opinions.map(o=>kind(o)[0]))].join('；')+'，'+s.opinions.length+'条意见，按Enter查看原因');
  activate(mark,s.opinions,i);body.append(mark);cursor=s.end;
 }
 if(cursor<m.points.length||!m.points.length)body.append(node('span',m.points.slice(cursor).join('')));
 const versions=revisions?.versions||[],changed=versions.some(v=>v.answer_id===final?.answer_id&&v.version!==final?.version&&typeof v.text==='string'&&v.text!==final?.text);
 const modified=changed&&(revisions?.records||[]).some(v=>v.answer?.answer_id===final?.answer_id&&v.answer?.version===final?.version&&v.answer?.text===final?.text);
 const modification=modified?'已有实际修订，所选正文保持保存版本。':changed?'存在内容不同的保存版本，是否修订以原记录为准。':m.valid.length||m.unlocated.length?'正文未修改；本次未自动修改，需核对审核意见。':'正文未修改。';
 const prefix=!m.current?'当前展示历史版本，未叠加最新版审核标注；无高亮不表示通过。':noAnswer?'未生成实质回答，实质审核不适用。':execution?.status==='queued'||execution?.status==='running'?'审核进行中，初稿暂不叠加问题标注。':!execution?.required_stages_complete?'审核未完成，已有草稿保留；未标问题不表示通过。':m.ready?`审核结束：${m.regions.length}处内容需要核实${m.unlocated.length?'，另有'+m.unlocated.length+'条未定位意见':''}。`:'审核结束：暂无可核验的正文标注；无高亮不表示通过。';
 summary.append(node('p',prefix+(m.current?' '+modification:'')));
 for(const [i,region] of m.regions.entries()){const b=node('button',`核实第${i+1}处 · `+[...new Set(region.opinions.map(o=>kind(o)[0]))].join(' / '),'quiet annotation-jump');b.type='button';b.addEventListener('click',()=>{const idx=m.segments.findIndex(s=>s.start===region.start),mark=body.children.find?.(n=>n.id==='review-mark-'+idx)||body.querySelector?.('#review-mark-'+idx);mark?.focus?.();mark?.scrollIntoView?.({block:'center'});if(mark)show(region.opinions,mark,idx);});summary.append(b);}
 for(const o of m.unlocated){const details=node('details',null,'unlocated-opinion');details.append(node('summary','此项未能定位到正文 · '+kind(o)[0]),node('p',(origins[o.origin]||'审核意见')+'：'+(o.reason||'具体原因未提供')));summary.append(details);}
 reading.append(body,panel);area.append(summary,reading);
 return {element:area,body,model:m,close,active:()=>activeKey};
}
return {model,render};
})();
