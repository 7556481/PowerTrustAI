"""Chinese explanations derived only from persisted structured results."""
TERMINAL={'finished','failed','cancelled','interrupted'}

def explain(result):
    ex=result['execution'];f=result.get('findings',{});answer=result.get('answer',{})
    facts=f.get('model_fact',[]);domain=f.get('domain',[]);rules=f.get('program_rules',[])
    reasons=[];next_steps=[]
    decision=result.get('decision') or {}
    query_failures=[i for i in ex.get('execution_issues',[]) if i.get('component')=='generation_query_conversion']
    if query_failures:
        return {'run_ended':ex.get('status') in TERMINAL,
            'answer_unavailable_reason':'未生成回答：英文补检查询转换执行失败。原中文查询为空，尚不能判断资料是否足以回答；请检查本机模型连接。',
            'reasons':['执行未完成：查询转换失败，未进入生成、提取或双审核；不是事实错误或审核通过。'],
            'next_steps':['检查模型连接后由用户手动发起新任务；本运行不会自动重发。'],
            'saved':'原查询与失败请求记录已保留。'}
    issues=ex.get('execution_issues',[])
    if issues and issues[0].get('component') in {'generation','claim_extraction','evidence_verification','power_domain_review','revision'} and issues[0].get('code') in {'MODEL_CONNECTION_FAILED','MODEL_OUTPUT_ERROR','MODEL_TIMEOUT'}:
        names={'generation':'回答生成','claim_extraction':'主张提取','evidence_verification':'事实审核','power_domain_review':'领域审核','revision':'回答修订'}
        first=issues[0];stage=names.get(first.get('component'),'必要执行阶段')
        code=first.get('code')
        cause={'MODEL_CONNECTION_FAILED':'模型网络连接失败','MODEL_OUTPUT_ERROR':'模型输出未满足结构要求','MODEL_TIMEOUT':'模型请求超时'}.get(code,'该阶段未成功完成')
        return {'run_ended':ex.get('status') in TERMINAL,
            'answer_unavailable_reason':None if answer.get('final') else f'未生成回答：{stage}阶段失败（{cause}）。',
            'reasons':[f'执行未完成：{stage}阶段失败（{cause}），已有回答仍可阅读，但没有完整审核结论。'],
            'next_steps':['查看终端或执行详情的失败阶段；本记录保留，不自动重发。'],
            'saved':'已完成的回答与阶段记录保留；执行失败不是事实矛盾。'}
    if result.get('no_substantive_answer'):
        return {'run_ended':ex.get('status') in TERMINAL,
            'reasons':['待补充：未生成实质回答，后续提取与双审核不适用。'],
            'next_steps':['补充相关依据或问题范围后，手动发起新任务。'],
            'saved':'原检索、补检与生成记录已保留；未审核程序拒答模板。'}
    if decision.get('policy_version','').startswith('product-decision-v1'):
        disposition=decision['kind']
        text={'pass':'通过：本任务适用检查完整且未发现阻断问题。',
            'reject':'不通过：仍有定位明确的错误，或命中经审阅的高严重度规则。',
            'needs_information':'待补充：存在尚未解决的具体依据或输入缺口。',
            'review_required':'人工复核：分类、严重度或审核判断存在不确定性。',
            'execution_incomplete':'执行未完成：检查失败或缺失，不能据此判事实错误。',
            'revise':'正在修订：最多一次，修订后重新提取并完整审核。'}
        reasons=[text.get(disposition,disposition)]+decision.get('reasons',[])
        next_steps=[{'pass':'可在限定任务范围内使用回答；工程安全仍需对应工程验证。',
                    'needs_information':'补齐逐项发现中的证据/输入后，手动发起新任务。',
                    'reject':'查看对应错误和每个回答版本，不自动重复运行。',
                    'execution_incomplete':'查看执行问题；保留已完成结果，不自动重发。'}.get(disposition,'对照原文、组件和版本判断；可追加反馈，不覆盖原结论。')]
        return {'run_ended':ex.get('status') in TERMINAL,'reasons':reasons,'next_steps':next_steps,'unresolved':unresolved_items(result),
                'saved':f"已保存 {len(answer.get('versions',[]))} 个独立回答版本；原版发现与反馈保留。"}
    codes={i.get('code') for i in ex.get('execution_issues',[])}
    if 'REVIEW_MESSAGE_CAPACITY_EXCEEDED' in codes:
        reasons.append('审核的完整消息超出配置容量；对应检查未完成，不能据此判断事实矛盾。')
        next_steps.append('查看执行问题中的引用索引与完整消息容量，人工检查未完成项；有效同级发现保留。')
    if 'REVIEW_WORKLOAD_BUDGET_SHORTFALL' in codes:
        reasons.append('已知剩余审核请求超过本次运行的剩余调用额度；已完成检查保留，其他检查未完成。')
        next_steps.append('查看剩余工作量与实际调用记录；运行保护不保证所有生成或修订输出都能完整审核。')
    if ex.get('execution_issues') or ex.get('status') in ('failed','interrupted','cancelled'):
        reasons.append('执行未完整结束或存在执行问题；已保存输出不等于全部审核完成。')
        next_steps.append('查看阶段事件和执行问题，人工确认已完成的回答版本；不会自动重发任务。')
    if any(x.get('status')=='contradicted' for x in facts) or any(x.get('status')=='warning' for x in rules):
        reasons.append('发现与依据矛盾的主张或程序一致性告警。')
        next_steps.append('对照对应版本的逐项发现、工具依据和修订动作；修订仍需重审。')
    if any(x.get('status')=='insufficient_evidence' for x in facts):
        reasons.append('部分主张缺少足够证据。')
        next_steps.append('回查这些主张的独立依据和原引用，人工核实来源与适用范围。')
    if any(x.get('missing_prerequisites') for x in domain):
        reasons.append('领域检查记录了缺少的工程前提。')
        next_steps.append('查看领域发现中的 missing_prerequisites；此界面没有运行工程仿真。')
    if any(x.get('status')=='not_assessable' for x in facts) or any(x.get('check_status')=='not_assessable' for x in domain) or any(x.get('status')=='incomplete' for x in rules):
        reasons.append('存在无法评估或未完成的必需检查。阶段完成表示已返回有效结果，无法评估表示该结果未给出实质判断，两者可以同时成立。')
    if any(x.get('check_status')=='warning' for x in domain):
        reasons.append('领域审核记录了待处理告警；具体原因见关联发现。')
    if not reasons:
        reasons.append('结构化发现未提供更具体的复核原因；请结合业务决策详情人工检查。' if (result.get('decision') or {}).get('kind')!='pass' else '当前政策未要求进一步处理；pass 不代表工程安全认证。')
    if not next_steps:next_steps.append('下一步无法从结构化发现确定，待人工检查业务决策与逐项发现；不生成工程操作建议。')
    return {'run_ended':ex.get('status') in TERMINAL,'reasons':reasons,'next_steps':next_steps,'unresolved':unresolved_items(result),
        'saved':f"已保存 {len(answer.get('versions',[]))} 个回答版本、{len(facts)} 条当前事实发现、{len(domain)} 条当前领域发现、{len(result.get('evidence',[]))} 条 Evidence；历史轮次与人工意见分别查看。"}


def unresolved_items(result):
    """Read-only current-version projection; no historic judgment rewrite."""
    answer=(result.get('answer') or {}).get('final') or {}
    extraction=(result.get('snapshots') or {}).get('extraction') or {}
    claims={c['claim_id']:c for c in extraction.get('claims',[])}
    rows=[]
    for f in (result.get('findings') or {}).get('model_fact',[]):
        if f.get('status')=='supported':continue
        c=claims.get(f.get('claim_id'),{})
        rows.append({'sentence':c.get('text') or c.get('proposition') or '主张原文绑定未提供',
            'status':f.get('status'),'reason':f.get('rationale','具体原因未提供'),'finding_id':f.get('finding_id')})
    for f in (result.get('findings') or {}).get('original_citations',[]):
        if f.get('status')=='supported':continue
        i=f.get('citation_index');citations=answer.get('citations',[])
        cit=citations[i] if type(i) is int and 0<=i<len(citations) else {}
        rows.append({'sentence':answer.get('text','')[cit.get('start_offset',0):cit.get('end_offset',0)] or '引用原文绑定未提供',
            'status':f.get('status'),'reason':f.get('rationale','具体原因未提供'),'citation_index':i})
    return rows
