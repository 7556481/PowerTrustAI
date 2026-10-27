/* Same-origin plain-text client. Opt-in local connection memory; no POST retries. */
'use strict';
(() => {
const $ = id => document.getElementById(id);
const diagnostic=Boolean($('access-form'));
const on=(id,event,fn)=>$(id)?.addEventListener(event,fn);
const labels = {skipped:'跳过',production_not_assessable:'原事实对象无法评估，不执行NLI',explicit_component_delivery_missing_or_ambiguous:'缺少明确逐组件交付证明',mixed_component_literal_binding_missing:'混合组件缺少独立原文绑定',shared_parent_anchor_without_component_literal_binding:'共享原文锚点，无法唯一绑定组件',over_context_no_truncation:'超出模型上下文，未截断',unsupported_basis_target:'此依据类型不支持正文NLI',unsupported_assertion_role:'此立场类型尚不支持NLI',verification_execution_incomplete:'事实审核执行未完成',incomplete:'未完成',reject:'不通过',rejected:'不通过',needs_information:'待补充',execution_incomplete:'执行未完成',low:'低风险（限定任务）',medium:'中风险',high:'高风险',unknown:'风险未知',complete:'完整',partial:'部分',unable_to_answer:'无法回答',queued:'排队',running:'运行中',finished:'结束',failed:'执行失败',cancelled:'已取消',interrupted:'中断',supported:'有依据支持（限定范围）',contradicted:'与依据矛盾',insufficient_evidence:'证据不足',not_assessable:'无法评估',pass:'通过（当前任务，非安全认证）',revise:'需修订',review_required:'需人工复核',succeeded:'执行成功',timed_out:'执行超时',pending:'待查',confirm:'确认',disagree:'反对',note:'说明',question_answer:'问答',assess_existing:'已有回答审核',generation:'生成',claim_extraction:'主张提取',evidence_verification:'事实审核',power_domain_review:'领域审核',revision:'修订',verifying:'双重审核',extracting:'提取主张',completed:'完成',generating:'生成回答',index_core_hit:'索引核心命中',index_adjacent_context:'索引相邻上下文',generation_input:'生成输入',original_citation:'原引用绑定',user_reference:'用户参考（未核实）'};
const tr = v => v == null ? '未提供' : typeof v === 'boolean' ? (v ? '是' : '否') : labels[v] || String(v);
let answerFocused=false;let answerVersion=null;let inlineRendered=null;
const reviewDrafts=new Map();let draftNeedsSelection=false;
let auxiliaryPaused=new Set(), renderedAnswerKey='', renderedDetailsKey='', restoreDraftPending=false;
function draftValue(){return {note:$('review-note').value,action:$('review-action').value,source:$('review-source').value,answer:$('review-answer').value,finding:$('review-finding').value,needsSelection:draftNeedsSelection};}
function rememberDraft(){if(!$('review-form'))return;if(selected)reviewDrafts.set(selected,draftValue());}
function resetDraft(){if(!$('review-form'))return;draftNeedsSelection=false; $('review-note').value='';$('review-action').value='pending';$('review-source').value='user';$('review-draft-status').textContent='';}
function restoreDraft(){if(!$('review-form'))return;const draft=reviewDrafts.get(selected);if(!draft)return;draftNeedsSelection=Boolean(draft.needsSelection);
 $('review-note').value=draft.note;$('review-action').value=draft.action;$('review-source').value=draft.source;
 const valid=[...$('review-answer').options].some(o=>o.value===draft.answer);
 if(valid)$('review-answer').value=draft.answer;else{draftNeedsSelection=true;$('review-answer').value='';$('review-draft-status').textContent='草稿回答版本已不可用，请重新选择版本与关联发现。';}
 reviewFindings();
 if(valid&&[...$('review-finding').options].some(o=>o.value===draft.finding))$('review-finding').value=draft.finding;
 else if(draft.finding){draftNeedsSelection=true;$('review-finding').value='';$('review-draft-status').textContent='草稿关联发现已不可用，请重新选择；不会静默改挂。';}
 controls();
}
let connected = false, sessionConnected = false;
const hasConnection=()=>Boolean(token||sessionConnected);
const connectionMemory=window.PowerTrustConnectionMemory?.create()||{load:()=>null,save:()=>false,forget:()=>true};
let token = '', selected = '', profile = null, result = null, timer = null, epoch = 0, reading = false, posting = false, uncertainPost = false, feedbackPosting = false, cancelPosting = false, historySerial = 0, nextOffset = null;
let serviceStatus={kind:'unknown',allowed:null,code:null,latest:null},serviceRevision=0,healthSerial=0,healthOwner=null;
const pendingStopped=s=>s?.pending_terminal_status==='interrupted'&&s.persistence_confirmed===false;
function setServiceStatus(kind,allowed,code=null,latest=serviceStatus.latest){
 if(kind!==serviceStatus.kind||allowed!==serviceStatus.allowed||code!==serviceStatus.code)serviceRevision++;
 serviceStatus={kind,allowed,code,latest};
 const messages={ready:'服务已确认可接收新任务。',legacy_ready:'旧版服务报告就绪且配置可用，但未提供工作循环接单字段；最终以提交受理为准。',
  lifecycle:'服务工作循环或资源状态不允许接收新任务。',closing:'服务正在关闭，不接收新任务。',configuration:'服务配置未就绪，不接收新任务。',
  storage:'运行存储报告故障，不接收新任务；历史查询与反馈保存也可能失败。',queue_full:'等待队列已满，暂不提交新任务；稍后可手动重新检查。',
  unavailable:'服务已明确拒绝新任务。',unreachable:'服务不可达或检查超时，当前接单状态未知。',unauthorized:'连接鉴权已失效；历史读取需要重新连接。',unknown:'服务接单状态尚未确认。'};
 const text=messages[kind]+(allowed===true?' 可按需查询历史。':' 已读结果和输入保留；可尝试查询已保存结果，是否可读以实际查询为准。');
 if($('service-status').textContent!==text)$('service-status').textContent=text;
 $('service-status').className='notice'+(allowed===true?'':' error');controls();
}
function applyServiceHealth(h){
 const life=h.service_lifecycle;
 if(h.configuration_ready===false||h.reason==='CONFIGURATION_UNAVAILABLE')setServiceStatus('configuration',false,'CONFIGURATION_UNAVAILABLE',h);
 else if(h.storage_healthy===false||h.reason==='RUN_STORAGE_FAILED')setServiceStatus('storage',false,'RUN_STORAGE_FAILED',h);
 else if(life?.accepting_work===false)setServiceStatus(life.closing?'closing':'lifecycle',false,life.fault_code||h.reason||'WORKER_UNAVAILABLE',h);
 else if(h.status==='degraded')setServiceStatus('unavailable',false,h.reason||null,h);
 else if(Number(h.queue_capacity)>0&&Number(h.queued)>=Number(h.queue_capacity))setServiceStatus('queue_full',false,'QUEUE_FULL',h);
 else if(h.status==='ready'&&life?.accepting_work===true)setServiceStatus('ready',true,null,h);
 else if(h.status==='ready'&&h.configuration_ready===true&&life?.accepting_work===undefined)setServiceStatus('legacy_ready',true,null,h);
 else setServiceStatus('unknown',null,null,h);
}
function renderRunStatus(s){
 if(s.service_fault_code)setServiceStatus('lifecycle',false,s.service_fault_code);
 const note=$('run-status-note');note.hidden=false;
 if(pendingStopped(s)){
  note.textContent='服务已停止处理此任务，中断状态尚未确认保存。数据库原状态仍为'+tr(s.status)+'；不再按排队状态持续轮询，可手动查询。下方只展示实际读取到的记录。';
  $('phase').textContent='已停止处理；中断状态尚未确认保存。';
 }else if(s.persistence_confirmed===false)note.textContent=(s.persisted_result_available?'已保存的答案和审核结果仍可读取；部分状态或元数据保存未确认。':'任务状态或元数据保存未确认；下方仅展示实际读取到的记录。')+' 不能保证全部保存成功，服务故障不改变原业务处置。';
 else if(s.service_fault_code)note.textContent='服务当前不接收新任务；下方正文、版本和业务处置按已保存记录展示，不因服务故障改判答案。';
 else{note.hidden=true;note.textContent='';}
}
const getControllers=new Set();let auxiliary=null;
function abandonReads(){for(const ctl of getControllers)ctl.abort();getControllers.clear();auxiliary=null;}
function auxiliaryContext(){if(!auxiliary||auxiliary.stamp!==epoch||auxiliary.rid!==selected)auxiliary={stamp:epoch,rid:selected,slots:new Map(),known:false,running:false,stopped:false,nliPending:false,nliChecks:0};return auxiliary;}
function ownsAuxiliary(ctx){return auxiliary===ctx&&ctx.stamp===epoch&&ctx.rid===selected&&!ctx.stopped&&hasConnection();}
function schedulePoll(ctx){if(!ownsAuxiliary(ctx)||timer||reading||!ctx.known)return;
 if(ctx.running||ctx.nliPending&&ctx.nliChecks<10)timer=setTimeout(()=>load(false),1800);
 else if(ctx.nliPending&&!ctx.slots.get('nli')?.inflight&&!ctx.limitShown){ctx.limitShown=true;$('local-nli').append(node('p','诊断仍未结束，已达10次终态查询上限；自动查询暂停，可手动查询状态。','hint'));}
}
function requestAuxiliary(path,fresh=false){
 const ctx=auxiliaryContext();if(!ownsAuxiliary(ctx))return;
 let slot=ctx.slots.get(path);if(!slot){slot={revision:0,inflight:null,terminal:false,paused:false};ctx.slots.set(path,slot);}
 if(fresh){slot.paused=false;slot.terminal=false;slot.revision++;if(slot.inflight){slot.queued=true;return slot.inflight;}}
 if(slot.inflight||slot.paused||!ctx.running&&slot.terminal&&!(path==='nli'&&ctx.nliPending))return slot.inflight;
 const owner={revision:slot.revision,terminal:!ctx.running};const area={nli:'local-nli',trace:'trace',reviews:'reviews'}[path];
 const render={nli:renderLocalNLI,trace:renderTrace,reviews:renderReviews}[path];
 if(path==='nli'&&owner.terminal)ctx.nliChecks++;
 const task=(async()=>{
  try{const data=await api(`/runs/${encodeURIComponent(ctx.rid)}/${path}`);
   if(!ownsAuxiliary(ctx)||slot.revision!==owner.revision)return;
   slot.terminal=owner.terminal;if(path==='nli')ctx.nliPending=Boolean(data.pending);
   const key=path==='trace'||path==='reviews'?JSON.stringify(data):null;
   if(key===null||key!==slot.renderedKey){render(data);slot.renderedKey=key;}
  }catch(e){
   if(!ownsAuxiliary(ctx)||slot.revision!==owner.revision)return;
   slot.paused=true;slot.renderedKey=null;auxiliaryPaused.add(path);if(path==='nli')ctx.nliPending=false;clear(area);
   $(area).append(node('p','此项读取失败，已暂停自动读取；主状态与回答仍可更新。点击“查询状态”手动恢复。','hint'));
   if(path==='trace')$('progress').textContent='阶段详情读取失败；主任务状态见上方。';
  }finally{
   if(!ownsAuxiliary(ctx)||slot.inflight!==task)return;slot.inflight=null;
   if(!slot.paused&&(slot.queued||!ctx.running&&!owner.terminal)){const queued=slot.queued;slot.queued=false;if(queued)slot.terminal=false;requestAuxiliary(path);}
   schedulePoll(ctx);
  }
 })();slot.inflight=task;return task;
}
function node(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=String(text);if(cls)n.className=cls;return n;}
function clear(id){$(id)?.replaceChildren();}
function tell(text,error=false){$('notice').textContent=text;$('notice').className='notice'+(error?' error':'');}
function jsonBox(value){return node('pre',JSON.stringify(value,null,2),'json');}
function fields(parent,items){const dl=node('dl');for(const [key,value] of items){dl.append(node('dt',key),node('dd',value==null?'未提供':typeof value==='object'?JSON.stringify(value):tr(value)));}parent.append(dl);}
function badge(value){return node('span',tr(value),'badge'+(['contradicted','failed','timed_out','reject','rejected','execution_incomplete'].includes(value)?' issue':['insufficient_evidence','needs_information','not_assessable','interrupted','review_required','unknown'].includes(value)?' warning':''));}
class ApiError extends Error {constructor(status,data){super('API error');this.status=status;this.code=data?.code||data?.detail?.code;}}
async function api(path,body,owns=()=>true){const ctl=new AbortController();if(body===undefined)getControllers.add(ctl);const timeout=setTimeout(()=>ctl.abort(),15000);try{const headers={};const requestToken=token;const requestEpoch=epoch;if(requestToken)headers.Authorization='Bearer '+requestToken;if(body!==undefined)headers['Content-Type']='application/json';const r=await fetch(path,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body),signal:ctl.signal,cache:'no-store',credentials:'same-origin',redirect:'error'});const data=await r.json();if(!r.ok){if(r.status===401&&token===requestToken&&epoch===requestEpoch&&owns())invalidateConnection();throw new ApiError(r.status,data);}return data;}finally{getControllers.delete(ctl);clearTimeout(timeout);}}
function errorText(e,write=false){if(!(e instanceof ApiError))return !write?'只读查询失败或超时；未提交新任务。已暂停自动查询，可手动查询状态或刷新运行列表。':'网络中断或请求超时：状态未知。任务可能已被服务接收；不会自动重新提交，请用已有 run_id 或运行列表查询。';const byCode={CONFIGURATION_UNAVAILABLE:'真实模型配置或固定知识库缺失，未接受任务；不会切换演示组件。',RUN_STORAGE_FAILED:'运行存储不可用，保存未确认。请检查服务端存储。',SERVICE_UNAVAILABLE:'服务当前不接受任务。',SAME_ORIGIN_REQUIRED:'请求来源不符合本机同源要求。'};return byCode[e.code]||({401:'令牌无效或已失效；已清除页面连接与浏览器记忆，请核对本机固定令牌后重新连接。',409:'回答版本或 finding 关联冲突，未保存意见。请刷新后选择实际版本。',429:'等待队列已满，未接受本次任务。请等待后手动提交。',422:'输入验证失败，请检查必填项、长度与实际版本。',404:'该运行或关联记录未找到；仅在收到明确 404 时作此判断。',503:'服务不可用，未确认接受或保存。',403:'仅允许本机同源访问。'}[e.status]||`HTTP ${e.status}：操作未确认成功。`);}
function controls(){ $('connection-state').textContent=connected?'已连接 · 仅本机':'未连接';$('service-check').disabled=Boolean(healthOwner);$('history-refresh').disabled=!connected||!hasConnection(); if(diagnostic)$('lookup').disabled=!connected||!hasConnection()||reading; $('submit').disabled=!connected||!hasConnection()||profile===null||serviceStatus.allowed!==true||Boolean(healthOwner)||posting||uncertainPost;$('refresh').disabled=!connected||!hasConnection()||!selected||reading;$('cancel').disabled=!connected||!hasConnection()||!selected||cancelPosting||pendingStopped(result?.execution)||!['queued','running'].includes(result?.execution?.status);if(diagnostic)$('review-submit').disabled=!connected||!hasConnection()||!selected||!$('review-answer').value||feedbackPosting||draftNeedsSelection;}
function stop(){clearTimeout(timer);timer=null;}
async function health(){
 const owner={stamp:epoch,serial:++healthSerial,revision:serviceRevision};healthOwner=owner;controls();
 const owns=()=>healthOwner===owner&&owner.stamp===epoch&&owner.serial===healthSerial&&owner.revision===serviceRevision;
 try{
  const h=await api('/health',undefined,owns);if(!owns())return;
  profile=['synthetic_fixture','real'].includes(h.profile)?h.profile:null;
  if(diagnostic){$('nli-enabled').disabled=!h.local_nli?.available;if(!h.local_nli?.available)$('nli-enabled').checked=false;
  $('nli-availability').textContent=h.local_nli?.note||'本地NLI不可用';}const demo=profile==='synthetic_fixture';
  $('service-mode').className='mode-banner'+(demo?' demo':'');
  $('service-mode').textContent=demo?'演示模式 · 无模型调用':profile==='real'?'DeepSeek · 真实付费调用':'服务模式未确认';
  if(diagnostic)$('connection').textContent=`最近服务检查：${h.status==='ready'?'就绪':h.status==='degraded'?'降级':'状态未知'} · 单活动运行 · 等待 ${h.queued??'未知'}/${h.queue_capacity??'未知'}`;
  applyServiceHealth(h);return h;
 }catch(e){if(!owns())return;setServiceStatus('unreachable',null);$('service-mode').textContent='服务不可达 · 接单状态未知';throw e;}
 finally{if(healthOwner===owner){healthOwner=null;controls();}}
}
function current(s){if(!diagnostic){$('phase').textContent=['queued','running'].includes(s.status)?'正在处理：'+tr(s.harness_state||s.status):'任务'+tr(s.status);renderRunStatus(s);return;}$('phase').textContent=['queued','running'].includes(s.status)?'当前阶段：'+tr(s.harness_state||s.status)+'（以实际阶段为准）':'任务'+tr(s.status)+'，回答与处置见下方。';clear('current');const parent=$('current');parent.className='';parent.append(badge(s.status),node('span',s.profile==='synthetic_fixture'?'synthetic_fixture 演示记录':'真实运行记录','badge'));fields(parent,[['run_id',s.run_id],['当前阶段',s.harness_state],['创建时间 UTC',s.created_utc],['结束时间 UTC',s.ended_utc],['结果持久化',s.persistence_confirmed],['错误代码',s.error_code],['固定知识版本',s.knowledge_version]]);const copy=node('button','复制运行ID','quiet');copy.type='button';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(s.run_id);copy.textContent='已复制运行ID';}catch(_){copy.textContent='复制失败，请手动选择运行ID';}});parent.append(copy);fields(parent,[['数据库原状态',s.status],['待保存的终态',s.pending_terminal_status],['服务故障代码',s.service_fault_code]]);const raw=node('details');raw.append(node('summary','原始执行与保存状态字段（只读）'),jsonBox({status:s.status,pending_terminal_status:s.pending_terminal_status,persistence_confirmed:s.persistence_confirmed,persisted_result_available:s.persisted_result_available,service_fault_code:s.service_fault_code}));parent.append(raw);renderRunStatus(s);if(s.cancel_requested)parent.append(node('p','已请求取消，以下状态以服务确认结果为准。','hint'));}
function renderTrace(trace){if(!$('trace'))return;clear('progress');clear('trace');const events=trace.events||[];if(!events.length)$('progress').append(node('p','阶段信息未提供，无进度百分比。','hint'));for(const item of events){const e=item.event;const card=node('div',null,'stage');card.append(node('strong',tr(e.component)+' · '+tr(e.state||e.status||e.kind)));card.append(jsonBox(e));$('trace').append(card);}if(events.length){const e=events.at(-1).event;$('progress').append(node('p',`最近阶段：${tr(e.component)} · 已记录 ${events.length} 个事件。`,'hint'));}}
function renderAnswers(r){
 const focusedMark=document.activeElement?.id;const previousInline=inlineRendered;
 clear('answers');clear('decision');clear('usage');const a=r.answer||{};const final=a.final;const shown=(a.versions||[]).find(v=>v.version===answerVersion)||final;
 const running=['queued','running'].includes(r.execution?.status);const complete=r.execution?.required_stages_complete===true;const versions=a.versions||[];$('phase').textContent=running?(final?'回答已生成，正在审核；尚未获得最终认可。':'任务处理中，尚无已保存回答。'):r.no_substantive_answer?(complete?'资料不足，未生成实质回答；后续审核不适用，不能当作审核通过。':'执行未完成，已有资料不足生成记录保留；不是审核通过。'):!complete?(final?'执行未完成，已有草稿保留；不是审核通过。':'执行未完成，尚无可用回答。'):'审核执行完整；最终处置：'+tr(r.decision?.kind||'unknown')+'。';if(['cancelled','interrupted','failed'].includes(r.execution?.status))$('phase').textContent=tr(r.execution.status)+'；'+$('phase').textContent;if(versions.length>1)$('phase').textContent+=' 已保留原回答及修订版本；最新版是否认可仍看最终处置。';
 if(pendingStopped(r.execution))$('phase').textContent='已停止处理；中断状态尚未确认保存。';
 const c=node('div',null,'card');const adopted=!running&&complete&&r.decision?.kind==='pass';
 const historyVersion=shown&&shown.version!==final?.version;
 const heading=historyVersion?'原回答／历史版本':running?'回答（审核中）':!complete?'回答草稿（审核未完成）':r.no_substantive_answer?'资料不足，暂无实质回答':adopted?'回答（本轮审核通过）':r.decision?.kind==='needs_information'?'回答（部分内容待核实）':'回答（存在待核实意见）';
 c.append(node('h3',diagnostic?(historyVersion?'初稿／历史版本（当前处置针对最新版）':adopted?'审核认可回答':'未认可回答'):heading),node('pre',shown?.text||r.presentation?.answer_unavailable_reason||'尚未生成可供阅读的回答，请查看下方具体原因。','answer-text'));const tools=node('div',null,'answer-tools');
 const label=node('label','查看回答版本');label.htmlFor='answer-version';
 const picker=node('select');picker.id='answer-version';
 for(const v of versions){const item=node('option',`v${v.version} · ${v.version===final?.version?'当前稿':'初稿／历史稿'}`);item.value=String(v.version);picker.append(item);}
 picker.value=String(shown?.version||'');picker.disabled=versions.length<2;
 picker.addEventListener('change',()=>{answerVersion=Number(picker.value);renderAnswers(r);$('answer-version')?.focus?.();});
 const copy=node('button','复制所选正文','quiet');copy.type='button';copy.disabled=!shown?.text;
 copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(shown.text);copy.textContent='已复制所选正文';}catch(_){copy.textContent='复制失败，请选中正文手动复制';}});
 if(versions.length>1||diagnostic)tools.append(label,picker);tools.append(copy);const answerText=c.children[1];c.replaceChildren(c.children[0],tools,answerText);
 if(!diagnostic&&shown?.text&&window.PowerTrustInlineReview){
  const projection=r.presentation?.inline_review||{answer_id:final?.answer_id,answer_version:final?.version,ready:true,offset_unit:'unicode_codepoint',opinions:(r.presentation?.unresolved||[]).map((o,i)=>({opinion_id:'legacy:'+i,origin:'legacy',status:o.status,reason:o.reason,located:false}))};
  const view=window.PowerTrustInlineReview.render({answer:shown,final,projection,execution:r.execution,noAnswer:r.no_substantive_answer,revisions:{versions,records:a.revisions},node,lookupEvidence});
  c.replaceChildren(c.children[0],tools,view.element);
  inlineRendered={key:JSON.stringify([selected,shown.answer_id,shown.version,shown.text]),view};
 }else inlineRendered=null;
 if(diagnostic)c.append(node('p',versions.length>1?'发生过修订；此选择仅切换保存的版本，不重算审核。':'正文未发生修订；不表示已修复错误。','hint'));
 if(!adopted&&diagnostic)c.append(node('p','此文字尚未获审核认可，请先看处置与具体警告，勿直接采用。','hint'));for(const s of r.operational_safety||[]){if(s.verdict==='dangerous'||s.verdict==='uncertain')c.append(node('p',(s.verdict==='dangerous'?'危险建议，禁止采用：':'安全疑点：')+s.original_text+' — '+s.reason+'（领域模型判断，非工程认证）',s.verdict==='dangerous'?'danger-warning':'safety-warning'));for(const b of s.source_bindings||[]){let u;try{u=new URL(b.url);}catch(_){}if(u?.protocol==='https:'&&!u.username&&!u.password){const link=node('a','安全规则来源（非答案引用）：'+b.section);link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';c.append(link,node('span',' '));}}}$('answers').append(c);
 if(previousInline&&inlineRendered&&previousInline.key===inlineRendered.key&&focusedMark?.startsWith('review-mark-')){
  const old=previousInline.view.model.segments[Number(focusedMark.slice(12))];const index=inlineRendered.view.model.segments.findIndex(s=>old&&s.start===old.start&&s.end===old.end);
  if(index>=0)$('review-mark-'+index)?.focus?.();
 }
 const sources=node('div',null,'answer-sources');sources.append(node('h3','回答引用的来源'));sources.append(node('p',`对应所选版本 v${shown?.version??'未提供'}；原引用与独立审核依据分别保留。`,'hint'));
 const cited=new Set((shown?.citations||[]).flatMap(x=>x.evidence_ids||[]));if((r.evidence||[]).some(e=>cited.has(e.evidence_id)&&e.source_type==='industry_corpus_unverified'))sources.append(node('p','行业语料原出处未核实；概念参考不等于规范或工程保证。','hint'));
 const groups=new Map();for(const e of r.evidence||[]){if(!cited.has(e.evidence_id))continue;const key=e.source_id+'|'+e.source_version;let g=groups.get(key);if(!g){g={e,pages:new Set()};groups.set(key,g);}if(e.provenance?.file_page)g.pages.add(e.provenance.file_page);}
 for(const {e,pages} of groups.values()){const item=node('div');item.append(node('span',(e.provenance?.document_title||e.source_id)+(pages.size?' · 第'+[...pages].sort((a,b)=>a-b).join('、')+'页':' · 原文定位见证据详情')));let u;try{u=new URL(e.provenance?.source_uri);}catch(_){}if(u?.protocol==='https:'&&!u.username&&!u.password){const link=node('a',' 打开来源');link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';link.referrerPolicy='no-referrer';item.append(link);}sources.append(item);}
 for(const id of cited){const button=node('button',diagnostic?'查看引用 '+id:'查看依据 ['+([...cited].indexOf(id)+1)+']','quiet evidence-link');button.type='button';button.addEventListener('click',()=>lookupEvidence(id,button));sources.append(button);}
 if(!cited.size)sources.append(node('p','本回答没有引用来源；检索命中不等于答案引用。','hint'));$('answers').append(sources);
 const d=$('decision');d.className='';d.append(badge(r.decision?.kind));if(r.decision?.risk_level)d.append(node('p','风险：'+tr(r.decision.risk_level)+'；问题解决程度：'+tr(r.decision.resolution)));
 for(const t of (r.presentation?.reasons||[]).filter(x=>!/[A-Za-z]{3}/.test(x)).slice(0,2))d.append(node('p',t));
 const codes=r.decision?.reason_codes||[];const reasons={FACT_ASSESSMENT_UNCERTAIN:'事实支持或依据条件不确定；不等于提取不忠实。',MODEL_BOUND_OPERATIONAL_HAZARD:'领域模型依据注册来源识别操作危险，禁止采用；不作工程认证。',OPERATIONAL_HAZARD_UNCERTAIN:'操作安全判断尚不确定，暂勿采用，请核对具体警告。',FACT_BASIS_MISSING:'部分主张或引用的依据不足。',REQUIRED_INPUT_MISSING:'必要工程输入或分析尚缺。',SOURCE_BOUND_REPAIR:'存在有原文依据的可定位缺陷，执行一次修订并完整重审。',REPAIRABLE_ERROR:'存在可定位的错误，需要有限修订并重审。',UNRESOLVED_ORDINARY_ERROR:'修订后仍有错误。',COMPONENT_CLASSIFICATION_UNCERTAIN:'主张分类或原文绑定不确定。',NO_SUBSTANTIVE_ANSWER:'未生成实质回答，后续审核不适用。',REQUIRED_EXECUTION_FAILED:'必需检查执行失败。',NONCLAIM_CLASSIFICATION_UNCERTAIN:'回答文本是否已完整覆盖存在疑问。',ANSWER_DECLARED_MISSING_INFORMATION:'回答明确保留了缺失信息。',REQUIRED_ANSWER_INFORMATION_MISSING:'当前问题所必需的信息仍缺失。',MISSING_INFORMATION_SCOPE_UNCERTAIN:'缺口是否影响当前问题尚不确定。',DOMAIN_JUDGMENT_DISPUTE:'领域判断仍有争议。',TASK_SCOPE_UNKNOWN:'任务适用范围尚不明确。'};
 for(const code of codes)if(reasons[code])d.append(node('p',reasons[code]));
 if(diagnostic)for(const u of r.presentation?.unresolved||[]){const box=node('div',null,'card');box.append(node('strong','未解决句子：'),node('p',u.sentence),node('p',tr(u.status)+'：'+u.reason.split(' [source-support-relation-')[0]));d.append(box);}
 for(const [i,gap] of (final?.missing_information||[]).entries()){const scope=(r.presentation?.scope_note_indexes||[]).includes(i);const reviewed=(r.presentation?.missing_information_review||[]).find(x=>x.index===i);d.append(node('p',(scope?'回答的范围说明：':reviewed?.applicability==='required'?'必要回答缺口：':'回答保留信息（影响尚待确认）：')+gap));}
 const detail=node('details');detail.append(node('summary','审核详情／技术详情：执行、版本及原始原因'),jsonBox({execution:r.execution,decision:r.decision,presentation:r.presentation,answer:final}));
 for(const v of a.versions||[])detail.append(node('h4',`回答版本 v${v.version}`),node('pre',v.text));if(a.revisions?.length)detail.append(jsonBox(a.revisions));if(diagnostic)d.append(detail);
 $('usage')?.append(jsonBox({budget_usage:r.budget_usage,model_usage:r.model_usage,limitations:r.limitations}));
}
function findingCard(f,version,category,claimMap){const c=node('div',null,'card');c.append(badge(f.status||f.check_status||f.severity),node('span',category,'badge'),node('span',`v${version??'未提供'}`,'badge'));if(f.origin)c.append(node('span',`origin: ${f.origin}`,'badge'));const claim=claimMap?.get(f.claim_id);if(claim)c.append(node('p','主张：'+(claim.proposition||claim.text)));c.append(node('p',f.reason||f.rationale||tr(f.status||f.check_status||f.severity)+'；具体理由和适用范围见原始详情。'));const original=f.original_text||claim?.text;if(original)c.append(node('blockquote',original));for(const id of f.evidence_ids||[]){const button=node('button','查看依据 '+id,'quiet evidence-link');button.type='button';button.addEventListener('click',()=>lookupEvidence(id,button));c.append(button);}fields(c,[['finding / check / tool ID',f.finding_id||f.check_id||f.result_id],['依据类型',f.assessment_basis],['检查方法',f.check_method||f.method_version],['关联 Evidence',f.evidence_ids],['关联主张',f.claim_id||f.claim_ids]]);const detail=node('details');detail.append(node('summary','完整字段与引用定位'),jsonBox(f));c.append(detail);return c;}
function renderFindings(r){if(!$('findings'))return;clear('findings');$('findings').className='';const rounds=[...(r.review_rounds||[])];if(!rounds.some(x=>x.answer?.version===r.answer?.final?.version))rounds.push({answer:r.answer?.final,verification:{findings:r.findings?.model_fact,citation_reviews:r.findings?.original_citations,consistency_checks:r.findings?.program_rules},domain_review:{findings:r.findings?.domain},extraction:r.snapshots?.extraction});for(const round of rounds){const version=round.answer?.version;const claimMap=new Map((round.extraction?.claims||round.verification?.claims||[]).map(c=>[c.claim_id,c]));for(const [title,rows] of [['事实审核 · 独立核验',round.verification?.findings],['事实审核 · 原引用核验',round.verification?.citation_reviews],['领域审核 · 模型或执行占位',round.domain_review?.findings?.filter(f=>f.origin!=='program_rule')],['程序规则 · 事实一致性',round.verification?.consistency_checks],['程序规则 · 领域前提与边界',round.domain_review?.findings?.filter(f=>f.origin==='program_rule')]]){const group=node('div');group.append(node('h3',title+` / v${version??'未提供'}`));if(!rows?.length)group.append(node('p','未提供','hint'));for(const f of rows||[])group.append(findingCard(f,version,title,claimMap));$('findings').append(group);}}const tools=node('div');tools.append(node('h3','工具结果（不证明工程可行性）'));for(const f of r.findings?.tools||[])tools.append(findingCard(f,null,'工具'));if(!r.findings?.tools?.length)tools.append(node('p','未提供','hint'));$('findings').append(tools);}
function renderEvidence(r){if(!$('evidence'))return;clear('evidence');$('evidence').className='';for(const e of r.evidence||[]){const b=(r.evidence_bindings||[]).filter(b=>b.evidence_id===e.evidence_id);const roles=b.length?b.map(b=>`${tr(b.origin)} / ${b.purpose||'用途未提供'}`).join('；'):'来源角色未提供';const card=node('div',null,'card');card.append(node('h3',e.evidence_id),node('p',roles,'hint'));fields(card,[['来源',e.provenance?.document_title||e.source_id],['来源类型',e.source_type],['定位',e.locator],['文件页',e.provenance?.file_page],['字符区间（提取文本）',e.provenance?`${e.provenance.start_offset}–${e.provenance.end_offset}`:null],['质量告警',e.provenance?.quality_warnings]]);const uri=e.provenance?.source_uri;let valid=false;try{const u=new URL(uri);valid=u.protocol==='https:'&&!u.username&&!u.password;}catch(_){}if(valid){const link=node('a','打开公开 HTTPS 来源');link.href=uri;link.target='_blank';link.rel='noopener noreferrer';link.referrerPolicy='no-referrer';card.append(link);}else card.append(node('p','公开来源链接：未提供','hint'));const btn=node('button','回查原文','quiet');btn.type='button';btn.addEventListener('click',()=>lookupEvidence(e.evidence_id,btn));card.append(btn);$('evidence').append(card);}if(!r.evidence?.length)$('evidence').append(node('p','未提供','hint'));}
async function lookupEvidence(id,button){
 const rid=selected;const stamp=epoch;button.disabled=true;
 try{
  const value=await api(`/runs/${encodeURIComponent(rid)}/evidence/${encodeURIComponent(id)}`);
  if(stamp!==epoch)return;
  clear('evidence-detail');const card=node('div',null,'card');
  card.append(node('h3',diagnostic?'运行作用域内 Evidence 回查':'来源原文'),node('pre',value.text));
  if(diagnostic)fields(card,[['Evidence ID',value.evidence_id],['来源',value.source_id],['来源版本',value.source_version],['定位',value.locator],['文件页',value.provenance?.file_page],['印刷页',value.provenance?.printed_page],['提取文本依据',value.provenance?.text_basis],['质量告警',value.provenance?.quality_warnings],['切分告警',value.provenance?.split_warnings]]);
  const detail=node('details');detail.append(node('summary','原文对象与完整身份'),jsonBox(value));if(diagnostic)card.append(detail);else fields(card,[['来源',value.provenance?.document_title||value.source_id],['版本',value.source_version],['定位',value.locator]]);
  $('evidence-detail').append(card);$('evidence-panel').open=true;$('evidence-panel').hidden=false;$('evidence-detail').scrollIntoView({block:'start'});
 }catch(e){if(stamp===epoch)tell(errorText(e),true);}
 finally{button.disabled=false;}
}
function options(select,items,old){if(select.options.length===items.length&&items.every(([v,t],i)=>select.options[i].value===v&&select.options[i].textContent===t))return;select.replaceChildren();for(const [value,text] of items){const o=node('option',text);o.value=value;select.append(o);}if([...select.options].some(o=>o.value===old))select.value=old;}
function reviewFindings(){if(!$('review-finding'))return;const answer=JSON.parse($('review-answer').value||'null');const old=$('review-finding').value;options($('review-finding'),[['','整个回答'],...(result?.feedback_targets||[]).filter(f=>answer&&f.answer_id===answer.answer_id&&f.answer_version===answer.version).map(f=>[f.finding_id,f.finding_id])],old);controls();}
function reviewOptions(r){if(!$('review-answer'))return;const old=$('review-answer').value;options($('review-answer'),(r.answer?.versions||[]).map(a=>[JSON.stringify({answer_id:a.answer_id,version:a.version}),`v${a.version} · ${a.answer_id}`]),old);reviewFindings();}
function renderReviews(reviews){if(!$('reviews'))return;clear('reviews');$('reviews').append(node('h3','已保存的追加意见'));for(const f of reviews){const c=node('div',null,'card');c.append(badge(f.action),node('pre',f.note||'无说明'));fields(c,[['run_id',f.run_id],['回答版本',`${f.answer_id} / v${f.answer_version}`],['关联 finding',f.finding_id],['来源',f.source],['复核者声明',f.reviewer_id],['创建时间 UTC',f.created_utc]]);c.append(node('p','已追加保存；不改变模型判断，不是专家金标准。','hint'));$('reviews').append(c);}if(!reviews.length)$('reviews').append(node('p','暂无反馈','hint'));}
function renderLocalNLI(value){if(!$('local-nli'))return;clear('local-nli');const area=$('local-nli');area.append(node('p',value.risk_note,'hint'));if(value.pending)area.append(node('p','本地NLI诊断处理中，原审核已经独立结束。','hint'));if(!value.records?.length&&!value.pending)area.append(node('p',value.enabled?'本次没有已保存诊断；缺少可安全转换的交付时跳过，历史查询不会补算。':'本次未选择本地NLI，不执行推理；服务可复用此前已加载模型。','hint'));for(const r of value.records||[]){const c=node('div',null,'card');c.append(node('h3',`v${r.answer_version??'未知'} · ${r.component_id||'无支持组件'}`),badge(r.status));fields(c,[['NLI三类诊断',r.nli_three_class_result],['原事实判断',r.comparison_source==='fact_agent'?r.production_status:'未提供（比较项为已有用户监督，不是事实Agent）'],['已见用户监督',r.comparison_source==='user_supervision_replay'?r.production_status:null],['分歧',r.disagreement===null?'无法比较':r.disagreement?'有分歧':'无分歧'],['跳过/失败原因',tr(r.reason)],['完整输入token',r.tokens],['输入身份',r.input_id]]);const d=node('details');d.append(node('summary','模型版本、原始logits及实际输入（诊断详情）'),jsonBox(r));c.append(d);area.append(c);}if(value.error_code)area.append(node('p',value.error_code,'notice'));}
async function load(manual=true){
 if(!hasConnection()||!selected||reading)return;
 const ctx=auxiliaryContext();if(manual){auxiliaryPaused.clear();ctx.stopped=false;ctx.nliChecks=0;ctx.limitShown=false;}
 stop();const owner={};reading=owner;controls();
 const stamp=epoch;const rid=selected;
 try{
  const status=await api('/runs/'+encodeURIComponent(rid));
  if(stamp!==epoch)return;current(status);
  const value=await api(`/runs/${encodeURIComponent(rid)}/result`);
  if(stamp!==epoch)return;result=value;
  if(value.answer){
   const answerKey=JSON.stringify([value.answer,value.execution?.status,value.execution?.required_stages_complete,value.execution?.pending_terminal_status,value.execution?.persistence_confirmed,value.execution?.service_fault_code,value.no_substantive_answer,value.decision,value.presentation,value.answer_adoption,value.operational_safety,value.evidence]);
   if(answerKey!==renderedAnswerKey){const focused=document.activeElement?.id;renderAnswers(value);if(focused==='answer-version')$('answer-version')?.focus?.();renderedAnswerKey=answerKey;}
   else{clear('usage');$('usage')?.append(jsonBox({budget_usage:value.budget_usage,model_usage:value.model_usage,limitations:value.limitations}));}
   renderFactDelivery(value);
   if(!answerFocused&&value.answer.final?.text){answerFocused=true;$('answers').scrollIntoView({block:'start'});}
   const detailsKey=JSON.stringify([value.review_rounds,value.findings,value.evidence,value.snapshots?.extraction]);
   if(detailsKey!==renderedDetailsKey){renderFindings(value);renderEvidence(value);renderedDetailsKey=detailsKey;}reviewOptions(value);
   if(restoreDraftPending){restoreDraft();restoreDraftPending=false;}
  }else{clear('decision');$('decision').append(node('p','尚无阶段结果，未提供业务结论。','hint'));}
  const effective={...status,...value.execution};renderRunStatus(effective);
  ctx.known=true;ctx.running=['queued','running'].includes(status.status)&&!pendingStopped(effective);
  for(const path of diagnostic?['nli','trace','reviews']:[])requestAuxiliary(path,Boolean(manual));
  tell(diagnostic?`已查询 ${rid} · ${tr(status.status)}。`:'已读取保存结果。'+(auxiliaryPaused.size?' 部分辅助详情读取已暂停，可手动恢复。':''));
 }catch(e){
  if(stamp===epoch){ctx.stopped=true;abandonReads();tell(errorText(e),true);if(diagnostic)$('progress').textContent='只读查询失败；保留最近确认结果。自动轮询已暂停，可手动查询。';}
 }finally{
  if(reading===owner){reading=false;controls();schedulePoll(ctx);}
 }
}
async function selectRun(rid){
 if(!/^[A-Za-z0-9_-]{1,150}$/.test(rid)){tell('run_id 格式无效。',true);return;}
 rememberDraft();resetDraft();stop();const stamp=++epoch;healthSerial++;healthOwner=null;abandonReads();auxiliaryPaused=new Set();renderedAnswerKey='';renderedDetailsKey='';restoreDraftPending=true;reading=false;selected=rid;answerVersion=null;answerFocused=false;result=null;if(diagnostic)$('run-id').value=rid;const link=$('diagnostics-link');if(link)link.href='/ui/diagnostics.html#'+encodeURIComponent(rid);for(const button of $('history').children)button.className='history-item'+(button.title===rid?' selected':'');
 for(const id of ['current','progress','trace','decision','answers','usage','findings','evidence','evidence-detail','reviews','local-nli','run-status-note'])clear(id);$('run-status-note').hidden=true;
 $('review-answer')?.replaceChildren();reviewFindings();await load();
 if(stamp===epoch&&result?.answer)$('answers').scrollIntoView({block:'start'});
}
async function history(page=0){
 const stamp=epoch;const request=++historySerial;let data;
 try{data=await api('/runs/page/'+page);}catch(e){if(stamp!==epoch||request!==historySerial)return;throw e;}
 if(stamp!==epoch||request!==historySerial)return;
 nextOffset=data.next_offset;clear('history');
 for(const row of data.items){
  const btn=node('button',null,'history-item'+(selected===row.run_id?' selected':''));btn.title=row.run_id;btn.append(node('strong',row.question_summary||tr(row.mode)),node('span',`${tr(row.status)} · ${new Date(row.created_utc).toLocaleString('zh-CN')} · ${row.profile}`),node('small',row.run_id.length>16?row.run_id.slice(0,12)+'…':row.run_id));
  btn.type='button';btn.addEventListener('click',()=>selectRun(row.run_id));$('history').append(btn);
 }
 $('history-next').hidden=nextOffset===null;
 if(!data.items.length)$('history').append(node('p','暂无运行','hint'));
}
function forgetConnection(message='已忘记连接：浏览器保存项与页面内存均已清除。'){
 stop();epoch++;abandonReads();historySerial++;reading=false;connected=false;sessionConnected=false;token='';healthSerial++;healthOwner=null;setServiceStatus('unknown',null,null,null);const deleted=connectionMemory.forget();if(diagnostic)$('remember-connection').checked=false;if(diagnostic){$('token').value='';$('token').required=true;}tell(deleted?message:'页面连接已清除，但浏览器拒绝删除保存项；请在浏览器站点设置中手动清除此地址的数据。',!deleted);controls();
}
function invalidateConnection(){forgetConnection('连接已失效：已清除页面记忆。请双击启动入口重新自动连接，或展开高级手动连接。');$('notice').className='notice error';setServiceStatus('unauthorized',false);}
async function connect(value){
 stop();const stamp=++epoch;abandonReads();reading=false;connected=false;token=value;healthSerial++;healthOwner=null;setServiceStatus('unknown',null,null,null);if(diagnostic){$('token').value='';$('token').required=!token;}
 try{await health();if(stamp!==epoch||token!==value)return;if(diagnostic)await history();if(stamp!==epoch||token!==value)return;connected=true;uncertainPost=false;
  if($('remember-connection')?.checked){if(connectionMemory.save(token))tell('已连接，并记住此浏览器的本机连接。');else{if(diagnostic)$('remember-connection').checked=false;connectionMemory.forget();tell('已连接，但浏览器存储不可用；本次仅在内存保存。');}}
  else{connectionMemory.forget();tell('已连接。令牌仅保存在页面内存。');}
  if(selected)await load();
 }catch(err){if(stamp===epoch)tell(errorText(err),true);}finally{controls();}
}
on('service-check','click',async()=>{
 if(healthOwner)return;const stamp=epoch;
 try{const h=await health();if(stamp!==epoch||!h)return;tell(uncertainPost?'已检查服务；此前提交受理仍未知，提交锁定保持。请先核对运行列表。':!connected?'已只读检查服务，但当前页面尚未连接；历史读取及提交仍需有效连接。未启动或重放任务。':'服务状态已更新；本次仅GET检查，未启动服务、提交或重放任务。');}
 catch(e){if(stamp===epoch)tell('服务检查失败或超时；已读结果和输入保留，可手动重新检查。',true);}
});
on('access-form','submit',async e=>{e.preventDefault();const value=$('token').value.trim()||token;if(value)await connect(value);});
on('disconnect','click',async()=>{const stamp=epoch;let revoked=true;try{await api('/session/logout',{});}catch(_){revoked=false;}if(stamp!==epoch)return;forgetConnection(revoked?'已忘记连接：本机会话已注销，浏览器保存项与页面内存已清除。':'页面记忆已清除，但本机会话注销未确认；请在服务恢复后再注销，或清除此站点的浏览器数据。');});
on('remember-connection','change',()=>{
  if(!$('remember-connection').checked){const deleted=connectionMemory.forget();if(!deleted){tell('记忆开关已关闭，但浏览器拒绝删除保存项；请手动清除此地址的站点数据。',true);return;}tell(sessionConnected?'已删除旧令牌记忆；本机会话仍有效，需注销时请点“忘记连接”。':connected?'记忆已关闭并删除保存项；当前连接仅在页面内存使用。':'记忆已关闭，连接成功后仅在页面内存使用。');}
 else if(connected&&token){if(connectionMemory.save(token))tell('已按你的选择记住当前本机连接。');else{if(diagnostic)$('remember-connection').checked=false;tell('浏览器存储不可用，当前连接仅在内存使用。');}}
});
on('submit-form','submit',async e=>{
 e.preventDefault();if(posting||uncertainPost||healthOwner||serviceStatus.allowed!==true||!hasConnection()||profile===null)return;
 const payload=diagnostic?window.PowerTrustDiagnosticInput.payload($):{mode:'question_answer',question:$('question').value.trim(),engineering_context:{goal:'conceptual'}};
 if(!payload){tell('请检查问题、已有回答及回答要求长度。',true);return;}
 const stamp=epoch;posting=true;controls();tell('正在提交一次任务，请勿重复提交。');let accepted;let sent=false;
 try{const before=profile;const checked=await health();if(stamp!==epoch||!checked)return;if(serviceStatus.allowed!==true){tell('服务当前不能接受新任务；未发送提交，可查看服务状态说明。',true);}else if(profile!==before){tell('服务模式已变化，请核对页面模式标识后再次手动提交。',true);}else{sent=true;accepted=await api('/runs',payload);}}catch(err){
   if(stamp!==epoch)return;
   if(err instanceof ApiError&&[429,503].includes(err.status)){setServiceStatus(err.status===429?'queue_full':err.code==='CONFIGURATION_UNAVAILABLE'?'configuration':err.code==='RUN_STORAGE_FAILED'?'storage':'unavailable',false,err.code||null);}
   if(!(err instanceof ApiError)&&sent){uncertainPost=true;tell(errorText(err,true)+' 提交已锁定，请重新连接并核对运行列表后再决定。',true);}else tell(!sent&&!(err instanceof ApiError)?'提交前服务检查失败或超时，未发送新任务；已读结果与输入保留，可重新检查服务。':errorText(err),true);
 }finally{posting=false;controls();}
 if(accepted&&stamp===epoch){if(diagnostic)$('run-id').value=accepted.run_id;tell(diagnostic?`任务已接受：${accepted.run_id}`:'问题已提交，正在生成回答。');await selectRun(accepted.run_id);const readStamp=epoch;try{if(diagnostic)await history();}catch(err){if(readStamp===epoch)tell(`任务已接受：${accepted.run_id}，运行列表暂时无法查询。`+errorText(err),true);}}
});
on('lookup-form','submit',e=>{e.preventDefault();selectRun($('run-id').value.trim());});
on('refresh','click',load);
on('cancel','click',async()=>{
 if(cancelPosting||!selected)return;
 cancelPosting=true;controls();const rid=selected;const stamp=epoch;
 try{await api(`/runs/${encodeURIComponent(rid)}/cancel`,{});if(stamp!==epoch)return;tell('已请求取消，等待服务确认实际状态。');await load();}
 catch(err){if(stamp===epoch)tell(errorText(err,true),true);}
 finally{cancelPosting=false;controls();}
});
on('history-refresh','click',()=>history(0).catch(e=>tell(errorText(e),true)));
on('history-next','click',()=>{if(nextOffset!==null)history(nextOffset).catch(e=>tell(errorText(e),true));});
on('review-answer','change',()=>{draftNeedsSelection=false;$('review-draft-status').textContent='';reviewFindings();});
on('review-finding','change',()=>{draftNeedsSelection=false;$('review-draft-status').textContent='';controls();});
on('review-form','submit',async e=>{
 e.preventDefault();if(feedbackPosting||draftNeedsSelection||!hasConnection()||!selected||!$('review-answer').value)return;
 const a=JSON.parse($('review-answer').value);const rid=selected;const stamp=epoch;const note=$('review-note').value;
 const payload={answer_id:a.answer_id,answer_version:a.version,finding_id:$('review-finding').value||null,action:$('review-action').value,source:$('review-source').value,reviewer_id:$('reviewer').value,note};
 const submitted=draftValue();reviewDrafts.set(rid,submitted);
 feedbackPosting=true;controls();let saved=false;
 try{await api(`/runs/${encodeURIComponent(rid)}/reviews`,payload);saved=true;
  const latest=selected===rid?draftValue():reviewDrafts.get(rid);
  if(JSON.stringify(latest)===JSON.stringify(submitted)){reviewDrafts.delete(rid);if(selected===rid)resetDraft();}
  if(stamp!==epoch)return;tell('复核意见已追加保存；模型判断保持原样。');}
 catch(err){if(stamp===epoch)tell(errorText(err,true)+' 输入已保留；未确认保存成功，请先查询已有反馈再决定是否重试。',true);}
 finally{feedbackPosting=false;controls();}
 if(saved&&stamp===epoch&&selected===rid)requestAuxiliary('reviews',true);
});
function renderFactDelivery(r){if(!$('usage'))return;const d=node("details");d.append(node("summary","事实检索模式、知识版本、逐主张交付与省略（详情）"),jsonBox({mode:r.configuration?.retrieval_mode,strategy:r.configuration?.fact_retrieval_strategy,knowledge_version:r.configuration?.knowledge_version,embedding_profile:r.configuration?.embedding_profile,scoring_method:r.configuration?.scoring_method,records:r.retrieval}));$("usage").append(d);}
on('example-question','click',()=>{$('question').value='无功功率和电压有什么关系？请作概念解释。';$('question').focus?.();tell('示例已填入，尚未提交；可以先修改问题。');});
window.addEventListener('pagehide',()=>{stop();epoch++;healthSerial++;healthOwner=null;abandonReads();reading=false;token='';sessionConnected=false;connected=false;});
async function restoreConnection(){
 try{const r=await fetch('/session',{method:'GET',credentials:'same-origin',cache:'no-store',redirect:'error'});if(r.ok){sessionConnected=true;connected=true;await health();tell('已通过本机会话自动连接，无需复制令牌。');if(diagnostic)if(diagnostic)await history();if(diagnostic&&window.location?.hash)await selectRun(decodeURIComponent(window.location.hash.slice(1)));else if(selected)await load();return;}}catch(_){}
 const remembered=connectionMemory.load();
 if(remembered){if(diagnostic)$('remember-connection').checked=true;await connect(remembered);if(connected){try{const upgraded=await api('/session/remember',{});if(upgraded.version==='localhost-launch-session-v1'){sessionConnected=true;token='';connectionMemory.forget();if(diagnostic)$('remember-connection').checked=false;tell('已将主动记住的连接升级为本机会话，无需再复制令牌。');}}catch(_){/* Old services keep the existing opt-in fallback. */}}}else{await health();tell('尚未连接：请使用当前服务启动器的本机会话入口，或展开高级手动连接。');}
}
on('history-panel','toggle',()=>{if($('history-panel').open)history().catch(e=>tell(errorText(e),true));});
on('history-open','click',()=>{$('history-panel').open=true;});
restoreConnection().catch(e=>tell(errorText(e),true));
})();
