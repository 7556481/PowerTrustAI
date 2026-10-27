/* Only the diagnostic page owns engineering and existing-answer inputs. */
'use strict';
window.PowerTrustDiagnosticInput={payload($){
const mode=$('mode').value,requirements=$('requirements').value.split('\n').map(s=>s.trim()).filter(Boolean);
if(!$('question').value.trim()||mode==='assess_existing'&&!$('existing').value.trim()||requirements.length>10||requirements.some(s=>s.length>4000))return null;
const p={local_nli_enabled:$('nli-enabled').checked,engineering_context:{goal:$('task-scope').value},mode,question:$('question').value.trim(),user_context:$('context').value,answer_requirements:requirements};
if(mode==='assess_existing')p.existing_answer=$('existing').value;
if($('reference').value.trim())p.references=[{label:$('reference-label').value||'用户参考（未核实）',text:$('reference').value}];return p;}};
document.getElementById('mode').addEventListener('change',()=>{const existing=document.getElementById('mode').value==='assess_existing';document.getElementById('existing-group').hidden=!existing;document.getElementById('existing').required=existing;document.getElementById('submit').textContent=existing?'审核已有回答（诊断）':'生成并审核';});
