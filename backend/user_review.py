"""Read-only user reasons. Raw findings and protocol metadata stay in diagnostics."""
import hashlib,json,re

FALLBACK='审核说明暂无法完整展示，可在诊断详情查看。'
TASK=' [task-applicability-v1] '
GAP=' [missing-information-applicability-v1] '
MARKERS=(TASK,GAP)+tuple(' ['+v+'] ' for v in ('source-support-relation-v3','source-support-relation-v4','source-support-relation-v5','source-support-relation-v6','compact-support-assessment-v1'))
FIXED={
 'Input presence checked only; data are user-provided and quality/adequacy are not certified.':'仅检查工程输入是否提供，未认证其质量或充分性。',
 'No structured quantities; this is not a completed free-text unit audit.':'未提供结构化量，未执行相应单位检查。',
 'Current question/answer and domain applicability are conceptual; no plant study inputs required.':'本次为概念解释，不要求厂站研究输入。',
 'Conceptual request contains no structured quantities; actual answer quantity assertions are reviewed separately.':'本次概念输入没有结构化量；回答中的数值另行审核。',
 'simulation_not_run: no engineering computation; conceptual explanation is not a plant feasibility or safety certification. Actual overclaims remain subject to independent analysis_scope review.':'本次未运行工程仿真；仍审核回答是否作出越界保证。'}

def reason(text):
    if not isinstance(text,str) or not text.strip():return '具体原因未提供。'
    found=[(text.find(m),m) for m in MARKERS if m in text]
    if not found:
        # Only reserved protocol signatures trigger fallback; ordinary braces and
        # formulas are user content, never scrubbed with a brace-removal regex.
        if re.search(r'\[(?:task-applicability|missing-information-applicability|source-support-relation|compact-support-assessment)-',text):return FALLBACK
        return FIXED.get(text,text)
    at,_=min(found);natural=text[:at];tail=text[at:]
    try:
        while tail:
            marker=next((m for m in MARKERS if tail.startswith(m)),None)
            if marker is None:raise ValueError('Unknown trailing payload')
            value,end=json.JSONDecoder().raw_decode(tail[len(marker):])
            if marker==TASK:
                if not isinstance(value,dict) or value.get('version')!='task-applicability-v1' or value.get('scope') not in ('conceptual','engineering','uncertain') or not isinstance(value.get('reason'),str):raise ValueError('Invalid task payload')
            elif marker==GAP:
                if not isinstance(value,list) or any(not isinstance(x,dict) or set(x)!=set(('index','applicability','reason')) or type(x['index']) is not int or not isinstance(x['reason'],str) for x in value):raise ValueError('Invalid gap payload')
            elif not isinstance(value,dict):raise ValueError('Invalid relation payload')
            tail=tail[len(marker)+end:]
        return FIXED.get(natural,natural) if natural.strip() else FALLBACK
    except (ValueError,TypeError):return FALLBACK

def task_assessment(result):
    answer=(result.get('answer') or {}).get('final') or {};context=result.get('task_context') or {}
    for f in (result.get('findings') or {}).get('domain',[]):
        text=f.get('rationale','')
        if f.get('category')!='analysis_scope' or TASK not in text:continue
        try:v=json.loads(text.rsplit(TASK,1)[1])
        except (ValueError,TypeError):continue
        if (v.get('version')=='task-applicability-v1' and v.get('answer_id')==answer.get('answer_id') and v.get('answer_version')==answer.get('version')
            and v.get('answer_sha256')==hashlib.sha256(answer.get('text','').encode()).hexdigest()
            and v.get('question_sha256')==hashlib.sha256(context.get('question','').encode()).hexdigest()):return v
    return None

def scope_only(f,result):
    # A display classification only. Never changes the policy or hides a model
    # concern, actual engineering inputs, or an unknown unlocated finding.
    if f.get('origin')!='program_rule':return False
    a=task_assessment(result);goal=(result.get('task_context') or {}).get('structured_goal')
    general=f.get('category') in ('engineering_inputs','input_units:units-input','simulation_boundary')
    return bool(general and a and a.get('scope')!='engineering' and (a.get('scope')=='conceptual' or goal=='conceptual') and f.get('rationale') in FIXED)

def project(opinions):
    rows={}
    for o in opinions:
        o=dict(o);o['reason']=reason(o.get('reason'));o['opinion_ids']=[o['opinion_id']];o['finding_ids']=[o['finding_id']] if o.get('finding_id') else []
        # Exact same role, checked range, kind, reason and sources only.
        key=(o['origin'],o['status'],o.get('answer_id'),o.get('answer_version'),o.get('start'),o.get('end'),o['reason'],tuple(sorted(o['evidence_ids'])),o.get('scope_only',False))
        if key in rows:
            old=rows[key]
            old['opinion_ids']=list(dict.fromkeys(old['opinion_ids']+o['opinion_ids']));old['finding_ids']=list(dict.fromkeys(old['finding_ids']+o['finding_ids']))
        else:rows[key]=o
    for o in rows.values():
        semantic=[o['origin'],o['status'],o['finding_ids'] or o['opinion_ids'],o['reason'],o['evidence_ids']]
        o['display_key']=hashlib.sha256(json.dumps(semantic,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return list(rows.values())
