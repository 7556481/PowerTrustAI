"""Read-only historical critical-path envelope; no scheduling or model changes."""
import json,statistics,hashlib
from pathlib import Path
SOURCE=Path('D:/PowerTrustAI/data/runtime_local/tantivy-delivery-replay-v20/ledger-timeline.json')
HOME=SOURCE.parent.parent/'schema13-front-overlap-v22'
OUT=Path('docs/evaluation/schema13-front-overlap-v22')
def main():
 x=json.loads(SOURCE.read_text(encoding='utf8'));rows=[]
 for r in x['rows']:
  if r['backend']!='baseline':continue
  stages={s['component']:s for s in r['stages']};fact=stages['evidence_verification'];domain=stages['power_domain_review'];gen=stages['generation']
  mm=[m for m in r['journal_model_intervals'] if m['component']=='evidence_verification'];ind=mm[:2] if len(mm)>1 and mm[1]['correction'] else mm[:1]
  ready=max(z['end'] for z in r['retrievals'] if z['purpose'] in ('verification','domain_review'))
  wall=r['server_to_audit_seconds']-gen['end'];tail=r['server_to_audit_seconds']-max(fact['end'],domain['end'])
  # Optimistic superset: zero all construction/parse gaps, zero ALL citation work.
  # Independent initial+its correction remain causal, domain remains one unchanged lane.
  minimum_fact_end=ready+sum(min(m['observed_seconds'],m['recorded_wait_seconds']) for m in ind)
  upper=max(0,wall-(max(minimum_fact_end,domain['end'])+tail-gen['end'])) if len(mm)>len(ind) else 0
  calls=[]
  for i,m in enumerate(mm):
   category='independent' if i<len(ind) else 'original_citation'
   calls.append(dict(call=m['call_number'],category=category,correction=m['correction'],input_ready_interval=[ind[0]['end'],m['start']] if m['correction'] else [ready,mm[0]['start']],admission=m['start'],settlement_observation=m['end'],recorded_wait=m['recorded_wait_seconds'],observed_span=m['observed_seconds']))
  rows.append(dict(case=r['case'],post_draft_seconds=wall,ready_interval=[ready,mm[0]['start']],fact_stage=fact,domain_stage=domain,terminal=r['server_to_audit_seconds'],unchanged_terminal_tail=tail,upper_saving_seconds=upper,saving_interval=[0,upper],optimistic_post_draft_seconds=wall-upper,upper_fraction=upper/wall,calls=calls,complete=r['case'] not in ('Q3','Q7')))
 baseline=statistics.median(r['post_draft_seconds'] for r in rows);best=statistics.median(r['optimistic_post_draft_seconds'] for r in rows)
 summary=dict(rows=rows,baseline_median=baseline,optimistic_median=best,median_seconds_reduction=baseline-best,median_fraction_reduction=(baseline-best)/baseline,paired_fraction_median=statistics.median(r['upper_fraction'] for r in rows),model_calls=0,gate=False,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),assumption='Historical durations fixed; no prediction or mathematical bound on new provider latencies. Current prepare_review boundary unchanged; no retrieval/model pipelining.')
 HOME.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 (HOME/'bound.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
 report=['# v22：独立事实与首条原引用重叠的乐观终态上界','', '**按事前规则在估算阶段结束，不改调度、不付费。** 原8条SQLite初稿审核链，保留失败Q3/Q7，不挑完整链计算主表。','',f"原初稿后审核终态中位{baseline:.3f}秒；比双通道更宽松的乐观中位{best:.3f}秒，减少{baseline-best:.3f}秒/{100*(baseline-best)/baseline:.2f}%，未达同时15%且3秒。逐对比例中位{100*summary['paired_fraction_median']:.2f}%也未达15%。这里是固定历史延迟的推演，不是新模型等待实测。",'', '|题|历史初稿后终态秒|可节省区间秒|乐观终态秒|最大节省比例|','|---|---:|---:|---:|---:|']
 for r in rows:report.append(f"|{r['case']}|{r['post_draft_seconds']:.3f}|0—{r['upper_saving_seconds']:.3f}|{r['optimistic_post_draft_seconds']:.3f}|{100*r['upper_fraction']:.2f}%|")
 report+=['','## 依赖与时间精度','', 'prepare_review先完成事实检索（含原预检主体补检）、领域检索，再构造v_input/d_input；review_pair随后并行两个角色。事实catalog、baseline wire、原引用分组、条件候选/transport构造均在事实Agent内部。独立事实请求和每条原引用初检均不依赖彼此模型输出，最早可在同一个事实输入对象具备后准备；独立纠正依赖其初检响应/诊断；引用纠正还必须等待全部更早逻辑项的纠正资格确定。预算不足时原回退串行规则保留。原引用引用的是生成快照，不可借独立新证据改绑定。','', '输入齐备时刻没有独立打点：初检统一给出[最后审核检索完成观测，首次事实准入]区间。纠正给出[前置初检结算观测，纠正准入]区间；结算mtime是保存usage的观测，不是精确响应/解析结束，真实齐备位置未知。模型事件集中记录，不能用event减duration伪造HTTP起点。阶段端点为实际event，起点由毫秒duration推导；journal准入/首次结算提供请求包络，存在本地处理/文件观测误差。原始ledger-timeline由原预算journal/mtime派生，输入SHA留私有bound.json。','', '领域审核已经并行，因此终态使用max(事实完成,领域完成)+原merge/Store尾部，不相加两个角色。各请求持续时间只用于独立因果链，不能把请求节省直接相加当用户收益。初稿边界为generation阶段完成，不是点击提交或浏览器首绘。Q3/Q7本来事实合同失败，不能把它们的终态叫完整审核通过。','', '为了得到足够宽松的否决上界，本计算甚至把全部原引用请求及其解析/间隔都归零，独立请求构造、纠正间隙也归零，只保留历史独立初检与其纠正的较短观测耗时和既有领域阶段完成；末端merge/存储尾部保持。这个假想优于最多两路的实际调度，也优于仅提前首条原引用。Q10没有原引用模型请求，因此调度节省为0。新并发下HTTP/限流/响应/纠正可能变化，记录不能给出正的保证节省，故逐题下界是0。','', '不把事实检索后到领域检索后的等待算进本候选：当前代码尚未构造v_input，提前跨过prepare_review并和检索交错是另一种Harness检索—审核流水线改动，不是复用事实双通道的本轮初检调度。也不将引用正文在初稿完成时已存在等同于当前完整审核请求已可发送。若改变该阶段边界，应另行冻结估算，不能套用本表。','', '## 每个事实请求的输入齐备区间与观测','', '时间均为各历史run创建后的秒数；引用按实际请求序列而非引用条数计。完整模型scope、usage与原始数据保持忽略存储，不导出正文。','', '|题/调用|职责|纠正|输入齐备区间|准入→结算观测|','|---|---|---|---|---|']
 for r in rows:
  for c in r['calls']:report.append(f"|{r['case']}/{c['call']}|{c['category']}|{c['correction']}|{c['input_ready_interval'][0]:.3f}—{c['input_ready_interval'][1]:.3f}|{c['admission']:.3f}—{c['settlement_observation']:.3f}|")
 report+=['','## 处置','', '只新增只读分析与报告，复用旧双通道实现作依赖核对，不修改waves/CorrectionOrder/Factory/生产配置、不创建付费预算、不加载.env、不发Flash。旧1462全套不重复：本轮无业务代码变更，验证8行唯一性、非负节省、终态不早于领域结束、全部调用唯一及原始输入身份；学习站检查另记。检索、一次修订、完整重审及取消策略保持；没有离线通过后跳过真实验收的采用结论。']
 (OUT/'report.md').write_text('\n'.join(report)+'\n',encoding='utf8')
 assert len(rows)==8 and all(0<=r['upper_saving_seconds']<=r['post_draft_seconds'] for r in rows)
 print(baseline,best,(baseline-best)/baseline)
if __name__=='__main__':main()
