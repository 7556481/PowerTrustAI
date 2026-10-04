"""Chinese explanations derived only from persisted structured results."""
TERMINAL={'finished','failed','cancelled','interrupted'}

def explain(result):
    ex=result['execution'];f=result.get('findings',{});answer=result.get('answer',{})
    facts=f.get('model_fact',[]);domain=f.get('domain',[]);rules=f.get('program_rules',[])
    reasons=[];next_steps=[]
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
    return {'run_ended':ex.get('status') in TERMINAL,'reasons':reasons,'next_steps':next_steps,
        'saved':f"已保存 {len(answer.get('versions',[]))} 个回答版本、{len(facts)} 条当前事实发现、{len(domain)} 条当前领域发现、{len(result.get('evidence',[]))} 条 Evidence；历史轮次与人工意见分别查看。"}
