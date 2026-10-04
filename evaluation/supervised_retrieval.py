"""Offline supervised-label import and saved-rank evaluation, no retrieval/API."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/retrieval_local/semantic/blind-review"
ADAPTER_VERSION = "supervised-pool-evaluation-v1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def keys(value, allowed, path, inventory):
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    extra = set(value) - set(allowed)
    if extra:
        raise ValueError(f"{path}: unadapted fields {sorted(extra)}; update adapter explicitly")
    inventory[path] = sorted(value)


def validate(data, mapping, dataset, comparison):
    """Explicit field inventories; keep complete imported bytes separately."""
    inventory, diagnostics = {}, []
    keys(data, ("schema_version","knowledge_version","query_set_sha256","status","coverage","questions",
                "annotation_provenance","user_feedback_history"), "$", inventory)
    if data["schema_version"] != "blind-annotations-v1":
        raise ValueError("$.schema_version: unsupported annotation format")
    for name in ("knowledge_version", "query_set_sha256"):
        if data[name] != mapping[name] or data[name] != dataset[name]:
            raise ValueError(f"$.{name}: frozen source binding mismatch")
    p = data["annotation_provenance"]
    keys(p, ("reviewer","human_confirmed","ranking_mapping_seen","prior_answer_suggestions_seen","visual_pages_checked",
        "limitations","input_sha256","subsequent_batch","batch_a11_a18","batch_d01_d12","core_judgment_count"), "$.annotation_provenance", inventory)
    for name, allowed in {
        "subsequent_batch": ("question_ids","candidate_count","visual_pages_checked","human_confirmed","supervision_authorized"),
        "batch_a11_a18": ("candidate_count","visual_pages_checked","human_confirmed"),
        "batch_d01_d12": ("candidate_count","visual_review_package_pages","human_confirmed")}.items():
        if name in p:
            keys(p[name], allowed, "$.annotation_provenance."+name, inventory)
    page_pairs = {(r["document_id"], r["original_file_page"]):r["review_package_page"] for r in mapping["pdf_pages"]}
    for i,page in enumerate(p.get("visual_pages_checked", [])):
        keys(page,("document_id","file_page","review_package_page"),f"$.annotation_provenance.visual_pages_checked[{i}]",inventory)
        if page_pairs.get((page["document_id"],page["file_page"])) != page["review_package_page"]:
            raise ValueError("Visual page mapping mismatch")
    for name, expected in p.get("input_sha256",{}).items():
        if name not in ("questions.md","evidence-pool.md","review-pages.pdf","annotations-template.json"):
            raise ValueError("Unknown provenance input file")
        if sha((BASE/name).read_bytes()) != expected:
            raise ValueError("Provenance input hash mismatch: "+name)
    for i,f in enumerate(data["user_feedback_history"]):
        keys(f,("scope","feedback","individual_candidate_scores_confirmed","does_not_imply_unseen_labels_human_confirmed"),
             f"$.user_feedback_history[{i}]",inventory)
    qs = data["questions"]
    ids = [q["question_id"] for q in qs]
    if len(set(ids)) != len(ids) or set(ids) != {q["id"] for q in dataset["queries"]}:
        raise ValueError("Question IDs duplicate or missing/foreign")
    global_blind = {bid:v for qm in mapping["questions"].values() for role in ("candidates","contexts") for bid,v in qm[role].items()}
    eids = {v["evidence_id"] for v in global_blind.values()}
    core_count = 0
    nested = {"answerability":("status","value","reason"), "reference_answer":("status","text","evidence_ids"),
        "necessary_evidence_combinations":("status","groups"), "qualifying_conditions":("status","items"),
        "applicability_scope":("status","regions","document_authority","notes"),
        "candidate_pool_coverage":("status","all_candidates_judged","exhaustive_relevant_evidence","missing_materials"),
        "annotation_provenance":("human_confirmed","supervision_authorized","classification")}
    for q in qs:
        qid = q["question_id"]
        path = "$.questions["+qid+"]"
        keys(q,("question_id","status","answerability","reference_answer","fragment_relevance","necessary_evidence_combinations",
            "qualifying_conditions","applicability_scope","candidate_pool_coverage","reviewer","reviewed_at","annotation_provenance",
            "evidence_combination_completeness","supplementary_reference_evidence"),path,inventory)
        for name,allowed in nested.items():
            if name in q:
                keys(q[name],allowed,path+"."+name,inventory)
        if q.get("evidence_combination_completeness") not in (None,"partial_not_sufficient","scope_limited_sufficient"):
            raise ValueError(path+".evidence_combination_completeness: unadapted value")
        if q["answerability"]["value"] not in ("answerable_with_scope_limits","partially_answerable","insufficient_evidence","not_assessable",None):
            raise ValueError(path+".answerability.value: unadapted value")
        qm = mapping["questions"][qid]
        own = {**qm["candidates"], **qm["contexts"]}
        seen = set()
        for f in q["fragment_relevance"]:
            bid = f["blind_id"]
            keys(f,("blind_id","fragment_id","role","status","relevance","support_relation","reason","conditions","scope","visual_checked"),path+".fragment_relevance["+bid+"]",inventory)
            if bid not in own or bid in seen or f["fragment_id"] != own[bid]["fragment_id"]:
                raise ValueError(path+".fragment_relevance: ID/fragment binding mismatch "+bid)
            seen.add(bid)
            expected_role = "candidate" if bid in qm["candidates"] else "adjacent_context"
            if f["role"] != expected_role:
                raise ValueError(path+".fragment_relevance: role mismatch")
            value = f["relevance"]
            if value is not None and (type(value) is not int or not 0 <= value <= 3):
                raise ValueError(path+".fragment_relevance: grade must be integer 0..3 or null")
            if f["status"] == "unreviewed" and value is not None:
                raise ValueError(path+".fragment_relevance: unreviewed cannot have a numeric grade")
            if f["status"] not in ("unreviewed","ai_proposed","reviewed","proposed_pending_human"):
                raise ValueError(path+".fragment_relevance.status: unadapted status")
            core_count += expected_role == "candidate" and value is not None
        if seen != set(own):
            raise ValueError(path+".fragment_relevance: missing blind candidates/contexts")
        for group in q["necessary_evidence_combinations"]["groups"]:
            if not isinstance(group,list) or not group or len(set(group)) != len(group) or not set(group) <= set(own):
                raise ValueError(path+".necessary_evidence_combinations: nonlocal/empty/duplicate group")
        for i,s in enumerate(q.get("supplementary_reference_evidence",[])):
            keys(s,("source_blind_id","fragment_id","evidence_id","counts_as_retrieval_hit"),path+f".supplementary_reference_evidence[{i}]",inventory)
            original = global_blind.get(s["source_blind_id"])
            if not original or (s["fragment_id"],s["evidence_id"]) != (original["fragment_id"],original["evidence_id"]):
                raise ValueError(path+".supplementary_reference_evidence: binding mismatch")
            if s["counts_as_retrieval_hit"] is not False:
                raise ValueError(path+".supplementary_reference_evidence: cannot create retrieval credit")
        unknown = set(q["reference_answer"]["evidence_ids"]) - eids
        if unknown:
            diagnostics.append({"question_id":qid,"field":"reference_answer.evidence_ids","issue":"unknown_evidence_id","ids":sorted(unknown)})
        if q["candidate_pool_coverage"]["exhaustive_relevant_evidence"] is True:
            diagnostics.append({"question_id":qid,"issue":"exhaustive_claim_not_accepted_for_full_corpus_metrics"})
    if p.get("core_judgment_count") != core_count:
        raise ValueError("Declared core_judgment_count mismatch")
    # Verify saved rankings exactly rather than trusting mapping in isolation.
    for saved in comparison["results"]:
        qm = mapping["questions"][saved["id"]]
        for method,hits in qm["original_methods"].items():
            original = saved["methods"]["hybrid" if method=="rrf" else method]["result"]["hits"]
            if [(qm["candidates"][h["blind_id"]]["fragment_id"],h["rank"]) for h in hits] != [(h["fragment_id"],h["rank"]) for h in original]:
                raise ValueError("Saved rank/mapping mismatch")
    return inventory,diagnostics


def score_question(question, ranking, candidates):
    labels = {f["blind_id"]:f for f in question["fragment_relevance"]}
    def grade(bid):
        item = labels[bid]
        return None if item["status"] == "unreviewed" else item["relevance"]
    top = ranking[:5]
    unknown_top = [bid for bid in top if grade(bid) is None]
    judged = {bid:grade(bid) for bid in candidates if grade(bid) is not None}
    positives = {bid for bid,g in judged.items() if g>=2}
    direct = {bid for bid,g in judged.items() if g==3}
    def hit_rr(target):
        first = next((rank for rank,bid in enumerate(top,1) if bid in target),None)
        if unknown_top:
            return (None,None)
        return (int(first is not None),0.0 if first is None else 1.0/first)
    hit,rr = hit_rr(positives)
    dhit,drr = hit_rr(direct)
    recall = None if unknown_top or not positives else len(set(top)&positives)/len(positives)
    dcg = lambda grades: sum((2**g-1)/math.log2(i+2) for i,g in enumerate(grades))
    ideal = dcg(sorted(judged.values(),reverse=True)[:5])
    ndcg = None if unknown_top or ideal==0 else dcg([grade(bid) for bid in top])/ideal
    groups = question["necessary_evidence_combinations"]["groups"]
    group_details = [{"required_ids":g,"covered_ids":[bid for bid in g if bid in top],
        "missing_ids":[bid for bid in g if bid not in top], "coverage":len(set(g)&set(top))/len(g),
        "unknown_label_ids":[bid for bid in g if grade(bid) is None]} for g in groups]
    coverage = max((g["coverage"] for g in group_details),default=None)
    group_complete = None if not groups else any(not g["missing_ids"] for g in group_details)
    declared = question.get("evidence_combination_completeness")
    eligible = question["answerability"]["value"] == "answerable_with_scope_limits" and declared != "partial_not_sufficient" and bool(groups)
    answer_complete = bool(group_complete) and eligible
    failures = []
    if not top:failures.append("empty_saved_ranking")
    if unknown_top:failures.append("unjudged_top5_unknown")
    if hit==0:failures.append("no_grade2_hit_at5")
    if not positives:failures.append("no_grade2_in_judged_core_pool")
    if direct and dhit==0:failures.append("grade3_direct_basis_missed")
    if group_complete is False:failures.append("necessary_combination_incomplete")
    if declared=="partial_not_sufficient" or question["answerability"]["value"]=="partially_answerable":
        failures.append("annotation_declares_partial_or_limited_inference")
    if question["answerability"]["value"]=="insufficient_evidence":failures.append("insufficient_evidence_question")
    if top:
        reason=labels[top[0]].get("reason") or ""
        if any(word in reason for word in ("目录","图题","标题","链接","脚注","页眉")):failures.append("rank1_structural_noise_from_annotation")
        if any(word in reason for word in ("旧版","另一个标准","版本不同","不同标准")):failures.append("rank1_version_or_standard_mismatch_from_annotation")
        if grade(top[0])==1:failures.append("rank1_background_only")
    return {"top5_ids":top,"hit_ge2_at5":hit,"mrr_ge2_at5":rr,"direct_grade3_hit_at5":dhit,"direct_grade3_mrr_at5":drr,
        "recall_ge2_judged_core_pool_at5":recall,"ndcg_graded_judged_core_pool_at5":ndcg,
        "judged_core_count":len(judged),"grade2_pool_count":len(positives),"grade3_pool_count":len(direct),
        "unknown_top5_ids":unknown_top,"unknown_context_count":sum(f["role"]=="adjacent_context" and f["relevance"] is None for f in labels.values()),
        "combination_max_member_coverage_at5":coverage,"any_necessary_group_covered_at5":group_complete,
        "scope_limited_answer_basis_eligible":eligible,"scope_limited_answer_basis_complete_at5":answer_complete,
        "combination_details":group_details,"supplementary_reference_hit_credit":0,"failure_classes":failures}


METRICS = ("hit_ge2_at5","mrr_ge2_at5","direct_grade3_hit_at5","direct_grade3_mrr_at5",
    "recall_ge2_judged_core_pool_at5","ndcg_graded_judged_core_pool_at5","combination_max_member_coverage_at5",
    "any_necessary_group_covered_at5","scope_limited_answer_basis_complete_at5")


def aggregate(rows):
    output={"questions":len(rows),"methods":{}}
    for method in ("bm25","dense","rrf"):
        values={}
        for name in METRICS:
            present=[r["methods"][method][name] for r in rows if r["methods"][method][name] is not None]
            values[name]={"mean":sum(present)/len(present) if present else None,"n":len(present)}
        eligible=[r["methods"][method] for r in rows if r["methods"][method]["scope_limited_answer_basis_eligible"]]
        values["scope_limited_answer_basis_complete_eligible_only"]={"mean":sum(v["scope_limited_answer_basis_complete_at5"] for v in eligible)/len(eligible) if eligible else None,"n":len(eligible)}
        output["methods"][method]=values
    return output


def evaluate(data,mapping,dataset):
    qs={q["question_id"]:q for q in data["questions"]}
    rows=[]
    for query in dataset["queries"]:
        qid=query["id"];q=qs[qid];qm=mapping["questions"][qid]
        row={**query,"answerability":q["answerability"],"reference_answer":q["reference_answer"],
            "original_annotation_status":q["status"],"annotation_provenance":q.get("annotation_provenance"),
            "reviewer":q["reviewer"],"reviewed_at":q["reviewed_at"],"candidate_pool_coverage":q["candidate_pool_coverage"],
            "evidence_combination_completeness":q.get("evidence_combination_completeness","not_explicitly_provided"),
            "qualifying_conditions":q["qualifying_conditions"],"applicability_scope":q["applicability_scope"],
            "supplementary_reference_evidence":q.get("supplementary_reference_evidence",[]),"methods":{}}
        for method,ranking in qm["original_methods"].items():
            row["methods"][method]=score_question(q,[h["blind_id"] for h in ranking],qm["candidates"])
            annotation_by_id={f["blind_id"]:f for f in q["fragment_relevance"]}
            row["methods"][method]["top5_judgments"]=[annotation_by_id[h["blind_id"]] for h in ranking[:5]]
        row["changes_vs_bm25"]={}
        for method in ("dense","rrf"):
            deltas={name:row["methods"][method][name]-row["methods"]["bm25"][name]
                for name in METRICS if row["methods"][method][name] is not None and row["methods"]["bm25"][name] is not None}
            up=[name for name,value in deltas.items() if value>1e-12]
            down=[name for name,value in deltas.items() if value < -1e-12]
            row["changes_vs_bm25"][method]={"deltas":deltas,"improved_metrics":up,"regressed_metrics":down,
                "category":"mixed" if up and down else "improved" if up else "regressed" if down else "unchanged",
                "not_complete_answer_despite_metric_improvement":bool(up) and not row["methods"][method]["scope_limited_answer_basis_complete_at5"]}
        rows.append(row)
    groups={"all":rows,"development":[r for r in rows if r["split"]=="development"],
        "frozen_family_partition":[r for r in rows if r["split"]=="frozen_acceptance_candidate"],
        "english_natural":[r for r in rows if r["language"]=="en"],
        "chinese_natural":[r for r in rows if r["language"]=="zh"],
        "keyword_acronym":[r for r in rows if r["language"]=="acronym"],
        "all_natural":[r for r in rows if r["language"]!="acronym"]}
    families=sorted({r["family"] for r in rows})
    families_report={family:aggregate([r for r in rows if r["family"]==family]) for family in families}
    macro={method:{name:sum(v)/len(v) if (v:=[f["methods"][method][name]["mean"] for f in families_report.values()
        if f["methods"][method][name]["mean"] is not None]) else None for name in METRICS} for method in ("bm25","dense","rrf")}
    return {"groups":{name:aggregate(values) for name,values in groups.items()},"families":families_report,
        "family_macro_means":macro,"per_question":rows,
        "special_questions":{
            "insufficient_evidence":[r["id"] for r in rows if r["answerability"]["value"]=="insufficient_evidence"],
            "limited_inference_or_partial":[r["id"] for r in rows if r["answerability"]["value"]=="partially_answerable"],
            "no_grade2_in_pool":[r["id"] for r in rows if r["methods"]["bm25"]["grade2_pool_count"]==0],
            "no_grade3_in_pool":[r["id"] for r in rows if r["methods"]["bm25"]["grade3_pool_count"]==0]},
        "failure_counts":{method:dict(Counter(f for r in rows for f in r["methods"][method]["failure_classes"])) for method in ("bm25","dense","rrf")}}


def render(report):
    lines=["# AI 辅助、用户监督标注：三方法离线对照", "",
        "采用用户授权的监督标注进行本轮计算。不是独立专家金标准，不把 ai_proposed 或 human_confirmed:false 改写成逐项人工确认。",
        "原反馈批次完整保留。来源记录 prior_answer_suggestions_seen=true，因此冻结家族分组不代表严格独立盲审验收。", "",
        "## 统计定义", "",
        "- Hit@5/MRR@5：相关性 >=2；3 分直接依据命中单列。全题 Hit/MRR 无正例记 0，并单列无正例题。",
        "- Recall@5：命中的 >=2 核心候选 / 本题所有已评分核心候选中的 >=2 数量；无正例时未定义，不纳入该平均。不是完整语料 Recall。",
        "- nDCG@5：gain=2^grade-1，discount=log2(rank+1)，IDCG 来自已评分核心候选池；无非零评分时未定义。1分背景可贡献 nDCG，不表示答案支持。",
        "- 必要组合：groups 视为可替代组合；每组成员全部需要。报告最大成员覆盖与任一组完整覆盖，不能将部分命中算完整。",
        "- 范围限定完整答案依据：还要求 answerable_with_scope_limits、非 partial_not_sufficient、存在组合；这个指标仅按标注声明，不证明答案事实正确。",
        "- 相邻上下文未标注保留 unknown，不记 0；跨题补充参考不加入任何方法的排名或评分分母。",
        "- 各指标展示有效分母；同族题相关，另附整族与 family-macro 结果。排名未重跑或调整。", "",
        "## 分组结果", "", "| 分组 / 题数 | 方法 | Hit@5 >=2 | MRR@5 >=2 | 3分 Hit@5 | 池内 Recall@5 | 池内 nDCG@5 | 任一必要组全覆盖 | 范围完整依据/全部题 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    def fmt(value):
        return "未定义" if value["mean"] is None else f"{value['mean']:.4f} (n={value['n']})"
    for group,summary in report["evaluation"]["groups"].items():
        for method,values in summary["methods"].items():
            names=("hit_ge2_at5","mrr_ge2_at5","direct_grade3_hit_at5","recall_ge2_judged_core_pool_at5",
                "ndcg_graded_judged_core_pool_at5","any_necessary_group_covered_at5","scope_limited_answer_basis_complete_at5")
            lines.append(f"| {group} / {summary['questions']} | {method} | "+" | ".join(fmt(values[n]) for n in names)+" |")
    lines += ["", "## 问题族结果与同族宏平均", "",
        "| 家族 / 题数 | 方法 | Hit>=2 | MRR>=2 | 3分命中 | 任一必要组全覆盖 |", "|---|---|---:|---:|---:|---:|"]
    for family,summary in report["evaluation"]["families"].items():
        for method,values in summary["methods"].items():
            lines.append(f"| {family} / {summary['questions']} | {method} | "+" | ".join(fmt(values[n]) for n in
                ("hit_ge2_at5","mrr_ge2_at5","direct_grade3_hit_at5","any_necessary_group_covered_at5"))+" |")
    lines += ["", "family-macro（各族等权，不把相近题当独立样本）：", "", "```json",
        json.dumps(report["evaluation"]["family_macro_means"],ensure_ascii=False,indent=2), "```", "",
        "## 组合覆盖的有效分母", "",
        "28 题提供非空必要组合；各组成员覆盖仅是标注定义的材料覆盖。21 题的标注允许范围内完整回答，单列这些题的条件覆盖率：", "",
        "| 方法 | 完整依据 / 全部30题 | 完整依据 / 可完整回答21题 |", "|---|---:|---:|"]
    for method,values in report["evaluation"]["groups"]["all"]["methods"].items():
        lines.append(f"| {method} | {fmt(values['scope_limited_answer_basis_complete_at5'])} | {fmt(values['scope_limited_answer_basis_complete_eligible_only'])} |")
    unknown_count=sum(r["methods"]["bm25"]["unknown_context_count"] for r in report["evaluation"]["per_question"])
    lines += ["", f"相邻上下文 unknown：{unknown_count} 条按题标注记录，未转换成 0。完整组合并不自动证明限定条件/语义判断正确。", ""]
    lines += ["", "## 无答案、有限推论及证据不完整", "", "```json",json.dumps(report["evaluation"]["special_questions"],ensure_ascii=False,indent=2),"```", "",
        "A04 的 answerability 被标为范围内可回答，但问题要求缺工程数据时给具体安全设定；参考答案实际是否定能计算。原标签保留，需区分可回答澄清与可提供设定。",
        "A09/A17 及 D01/D02/D05/D06/D09/D12 的部分答案不能凭组覆盖升级为完整；D05/D06/D12 的跨题参考不获得检索命中信用。", "",
        "## 逐题与变化", ""]
    for row in report["evaluation"]["per_question"]:
        lines += [f"### {row['id']} / {row['family']} / {row['split']} / {row['language']}", "",row["query"],"",
            "可回答性："+str(row["answerability"]["value"])+"；组合充分性："+row["evidence_combination_completeness"],
            "参考答案（来自标注，未另作事实审核）："+str(row["reference_answer"]["text"]), "",
            "| 方法 | Hit>=2 | MRR>=2 | 3分命中 | 最大组合覆盖 | 组全覆盖 | 范围完整依据 | 缺失组合成员 |", "|---|---:|---:|---:|---:|---|---|---|"]
        for method,v in row["methods"].items():
            missing="; ".join(",".join(g["missing_ids"]) or "完整" for g in v["combination_details"]) or "无已标组合"
            lines.append(f"| {method} | {v['hit_ge2_at5']} | {v['mrr_ge2_at5']} | {v['direct_grade3_hit_at5']} | {v['combination_max_member_coverage_at5']} | {v['any_necessary_group_covered_at5']} | {v['scope_limited_answer_basis_complete_at5']} | {missing} |")
        for method,v in row["methods"].items():
            lines += ["",f"{method} 失败/限制分类："+", ".join(v["failure_classes"]), ""]
            for rank,label in enumerate(v["top5_judgments"],1):
                lines += [f"{method} rank {rank}：{label['blind_id']}；相关性 {label['relevance']}；{label['support_relation']}；{label['reason']}。", ""]
        for method,change in row["changes_vs_bm25"].items():
            lines += [f"{method} 对 BM25：{change['category']}；改善指标 {change['improved_metrics']}；退步指标 {change['regressed_metrics']}。", ""]
            if change["not_complete_answer_despite_metric_improvement"]:
                lines += ["这里的指标改善仍未获得标注所声明的完整答案依据，尤其背景 nDCG 提高不代表可回答。", ""]
        lines += ["关键条件："+"；".join(row["qualifying_conditions"]["items"]),
            "范围："+json.dumps(row["applicability_scope"],ensure_ascii=False),
            "跨题补充参考（信用恒为0）："+json.dumps(row["supplementary_reference_evidence"],ensure_ascii=False), ""]
    lines += ["## 字段适配与审计", "",
        "显式适配 annotation_provenance/user_feedback_history（完整保留），question.annotation_provenance（保留监督属性），",
        "evidence_combination_completeness（阻止部分组合被称完整），supplementary_reference_evidence（校验来源且禁止补算命中）。",
        "未知字段会报字段路径并拒绝导入，不静默删除。原 JSON 按字节存档，标准化评测视图另存，不改原标签状态。",
        "所有引用、blind ID、fragment ID、角色、问题集/知识哈希、评分范围及保存排名映射经过校验。",
        "本次数据绑定诊断："+json.dumps(report["diagnostics"],ensure_ascii=False), "",
        "模型评分的语义准确性仍未由独立专家核定；小样本、同族依赖、先前建议曝光与视觉检查不全限制结论外推。"]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True)
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    target=Path(args.output_dir)
    if target.exists():raise FileExistsError("New version directory required; no overwrites")
    raw=Path(args.input).read_bytes();data=json.loads(raw.decode("utf-8-sig"))
    mapping=load(BASE/"mapping.json");dataset=load(BASE.parent/"dataset-v1.json");comparison=load(BASE.parent/"comparison-v2.json")
    for name,digest in mapping["source_files"].items():
        if sha((BASE.parent/name).read_bytes())!=digest:raise ValueError("Original archive changed: "+name)
    inventory,diagnostics=validate(data,mapping,dataset,comparison)
    target.mkdir(parents=True)
    (target/"annotations-30-supervised-v3.json").write_bytes(raw)
    evaluation=evaluate(data,mapping,dataset)
    report={"evaluation_version":ADAPTER_VERSION,"annotation_version":"annotations-30-supervised-v3",
        "imported_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":sha(raw),
        "knowledge_version":data["knowledge_version"],"query_set_sha256":data["query_set_sha256"],
        "label_usage":"AI-assisted user-supervised, explicitly authorized for this evaluation; not expert gold",
        "original_status":data["status"],"annotation_provenance":data["annotation_provenance"],
        "user_feedback_history":data["user_feedback_history"],"field_inventory":inventory,"diagnostics":diagnostics,
        "mapping_sha256":sha((BASE/"mapping.json").read_bytes()),"saved_ranking_sha256":sha((BASE.parent/"comparison-v2.json").read_bytes()),
        "evaluation":evaluation,"paid_api_calls":0,"retrieval_calls":0}
    for name,value in (("evaluation.json",report),("import-manifest.json",{k:v for k,v in report.items() if k!="evaluation"})):
        (target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    (target/"evaluation.md").write_text(render(report),encoding="utf-8")
    print(json.dumps({"output_dir":str(target),"overall":evaluation["groups"]["all"],"diagnostics":diagnostics},ensure_ascii=False,indent=2))


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
