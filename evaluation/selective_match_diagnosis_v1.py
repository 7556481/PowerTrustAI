"""Before-code materials and bounded DF/Boolean diagnostics; no env or models."""
import json,re,sqlite3,time,subprocess,hashlib
from pathlib import Path
from backend.config import ROOT
from backend.assembly import ComponentFactory
from evaluation.natural_draft_audit_v1 import save,sha
from evaluation.source_first_modality_v6 import material
from evaluation.source_first_real_v3 import configuration
from evaluation.retrieval_rank_v7 import idle,bounded
from rag.chinese_terms import terms,ALIASES
from rag.topic_lanes import plan
LOCAL=ROOT/'data/retrieval_local/selective-match-retrieval-v1'
DF_TERMS=('无功','无功功率','电网','电力系统','系统','电压','发电机','变压器','电动机','电压稳定','功率因数','补偿','无功补偿','负荷','消耗','供用电','三相','cos','ui','正弦','不可','可控','长距离','容量')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def freeze():
    assert not (LOCAL/'selection-before-code.json').exists(),'No material overwrite'
    old=read(ROOT/'data/maintenance_local/audit-retrieval-final-v1/requests-private.json');m=material();c=configuration(m)
    sql=read(ROOT/'data/retrieval_local/retrieval-rank-and-audit-reference-v7/sql/freeze.json');cases=[];reference={}
    descriptions=[
      ['负荷及网络需无功、远距离全由发电机输送不合理与就地补偿','补偿提高功率因数、减少容量/损耗、改善电压和输电稳定性/能力','三相不平衡时补偿可平衡负载；容量配置须给负荷网络条件，不得凭此算容量'],
      ['持续不可控电压下降/崩溃关系','有载调压低压侧回升但高压侧继续下降；不能当整体改善','低电压电动机电流及无功增大/失稳，无功出力限制加剧缺额'],
      ['功率因数P/S、视在功率有效值UI与周期平均有功定义','cos等同功率因数仅在正弦稳态，非正弦不得直接等同']]
    for i,(row,g,goals) in enumerate(zip(sql['requests'],old['groups'],descriptions),1):
        ids=set(row['record']['core_evidence_ids']+row['record']['context_evidence_ids']);refs=[e for e in g['saved_evidence'] if e['evidence_id'] in ids]
        for e in refs:reference[e['provenance']['fragment_id']]=e
        cases.append(dict(id=f'Q{i}',query=row['query'],kind='seen actual v7 diagnostic; unchanged',reference_fragments=[e['provenance']['fragment_id'] for e in refs],goals=goals,allow_alternative_sources=True,source_required=None,expected='positive',settings=row['record']['request_options'],budget=g['budget'],initial_calls=g['initial_calls'],initial_chars=g['initial_chars']))
    specs=[
      ('TO DP boundary loads modeling MW Mvar high side transformers distribution impedances',0,['边界以MW/Mvar显式负荷表示','建模可高压侧或变压器/等效配电阻抗之后'],True),
      ('GOP TOP voltage controlling device status reactive capability changes longer than 30 minutes',4,['电压控制装置状态及其他因素无功能力变化两种通知','两种均超过30分钟、GOP向TOP通知'],True),
      ('PV pre-contingency all controls post-contingency 3 to 30 minutes only automatic controls',5,['故障前所有控制','故障后3至30分钟仅自动控制，条件归属不得混淆'],True),
      ('QV preselected buses may not reveal wide area voltage stability problems and evaluation speed',7,['须预选代表母线','可能未揭示广域问题，不反转为只适用广域','多次潮流评估较慢及原有QV优点'],True),
      ('Non-synchronous induction generators electronically coupled resources capability additional STATCOM SVC may be required',6,['资源类型与能力可能有无','机组可能不具备时附加资源可能需要、POI设定目的，非一律必须'],True)]
    settings=cases[0]['settings'];budget=cases[0]['budget']
    for i,(query,n,goals,pinned) in enumerate(specs,4):
        es=m['cases'][n]['request']['provided_evidence']
        # Reference fragments are not a unique gold set. For source questions the
        # source identity is mandatory; any delivered passage must cover the goals.
        for e in es:reference[e['provenance']['fragment_id']]=e
        cases.append(dict(id=f'Q{i}',query=query,kind='authored seen source-explanation development query; no prediction yet',reference_fragments=[e['provenance']['fragment_id'] for e in es],goals=goals,allow_alternative_sources=False,source_required='nerc-reactive-planning-2016',expected='positive',settings=settings,budget=budget,initial_calls=0,initial_chars=0))
    extras=[
      ('RLC串谐（串联谐振）时电压电流相位怎样，不能把它说成纯电感电路。',['f-9ff70c2190379ee94d9d3542e86b90676343c2a740be15d35594d62756260233'],['串联谐振电抗抵消、阻抗呈电阻性、电压电流同相；不能与纯感性混淆'],None),
      ('If pre- or post-contingency high voltages may exceed limits, shunt capacitors out-of-service and shunt reactors in-service reduce voltage: explain both actions.',['f-0212dcfba8b930d516c14e1a93a2b52aca61e9a999a467806e97c2a5cf5597f2'],['高电压越限或可能越限的条件','退出并联电容、投入并联电抗这两个方向均保留'],None),
      ('给出SCM_FIXTURE_BUS7390在2050年现场实测的无功缺额及精确补偿容量，不提供负荷、网络或测量数据。',[],['缺少真实设备/现场输入，不能由相关概念片段计算精确容量'],'unknown'),
      ('在指定2016 NERC指南中定位SCM_FIXTURE_UNIT9621于2050年的现场试验数值和强制整定937.13 Mvar条款。',[],['指定旧指南与人工虚构未来现场数据不能形成有据结果'],'unknown')]
    for i,(query,fids,goals,expected) in enumerate(extras,9):
        cases.append(dict(id=f'Q{i}',query=query,kind='authored development fixture before candidate; not holdout/gold',reference_fragments=fids,goals=goals,allow_alternative_sources=expected is None,source_required='nerc-reactive-planning-2016' if i==12 else None,expected=expected or 'positive',settings=settings,budget=budget,initial_calls=0,initial_chars=0))
    # Exact native text is pinned before any candidate code or prediction. Full
    # Evidence/neighbor identities are replayed under the normal seal in diagnose.
    db=sqlite3.connect(c.index_db.resolve().as_uri()+'?mode=ro',uri=True)
    native={fid:dict(zip(('source_id','source_version','raw_text'),db.execute('SELECT document_id,version,raw_text FROM fragments WHERE fragment_id=?',(fid,)).fetchone())) for row in cases for fid in row['reference_fragments'] if fid not in reference};db.close()
    ablations=[]
    for row in cases[:3]:
        expr=plan(row['query'])[0][1];left,_,right=expr.partition(') AND (');score=left+')';groups=re.findall(r'\(([^()]+)\)',right)
        groups=[re.findall(r'"([^\"]+)"',x) for x in groups];original=set(terms(row['query']))
        # Scoring OR is unchanged. Only remove non-original theme alias expansions.
        reduced=[[w for w in g if w in original] or g for g in groups]
        def theme(gs):return '('+' OR '.join('('+' OR '.join('"'+w+'"' for w in g)+')' for g in gs)+')'
        ablations.extend([dict(query=row['id'],kind='theme_alias_only_removed_score_OR_unchanged',expression=score+' AND '+theme(reduced)),dict(query=row['id'],kind='only_one_original_theme_group_score_OR_unchanged',expression=score+' AND '+theme(groups[:1]))])
        row['old_expression']=expr;row['old_boolean_tree']=dict(AND=[dict(scoring_OR=re.findall(r'"([^\"]+)"',left)),dict(theme_OR_groups=groups)]);row['raw_terms']=list(terms(row['query']));row['aliases']=ALIASES
    selection=dict(version='selective-match-materials-v1',base=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases=cases,provided_references=reference,native_references=native,knowledge_version=c.knowledge_version,df_terms=list(DF_TERMS),ablations=ablations,provenance='Seen actual and authored development queries; semantic goals/reference spans frozen before candidate implementation; alternative relevant sources allowed for ordinary concepts, not keyword gold.',gates=dict(slow_median_reduction=.5,slow_median_saving=5,same_direction_rounds=2,other_regression_ratio=.2,other_regression_seconds=1,all_critical_goals=True,no_new_failures=True),schedule=[dict(round=n,query=f'Q{i}',order=['baseline','candidate'] if n in (1,3) else ['candidate','baseline']) for n in (1,2,3) for i in range(1,13)])
    assert len(cases)==12 and len(set(x['query'] for x in cases))==12 and len(ablations)==6
    save(LOCAL/'selection-before-code.json',selection);save(LOCAL/'selection-identity.json',dict(sha256=sha(selection),model_calls=0));print('12 queries/goals/reference text pinned before candidate',sha(selection),flush=True)
def diagnose():
    assert not (LOCAL/'diagnosis').exists(),'Do not resume/repeat diagnostics';assert idle(),'User work active'
    sel=read(LOCAL/'selection-before-code.json');assert sha(sel)==read(LOCAL/'selection-identity.json')['sha256']
    c=configuration(material());f=ComponentFactory(c);start=time.monotonic();f.warm_corpus_index();seal=time.monotonic()-start
    from rag.storage import KnowledgeStore
    with KnowledgeStore(c.index_db,readonly=True) as store:
        es={fid:store.evidence(fid,c.knowledge_version) for row in sel['cases'] for fid in row['reference_fragments']}
        for fid,e in es.items():
            assert store.verify_evidence(e)==e
            if fid in sel['provided_references']:assert e.text==sel['provided_references'][fid]['text']
            else:assert e.text==sel['native_references'][fid]['raw_text']
    from backend.serialization import wire
    save(LOCAL/'materials.json',dict(selection=sel,references={fid:wire(e) for fid,e in es.items()},selection_sha=sha(sel)));save(LOCAL/'materials-identity.json',dict(sha256=sha(read(LOCAL/'materials.json')),model_calls=0))
    db=sqlite3.connect(c.index_db.resolve().as_uri()+'?mode=ro',uri=True);stamp=(c.index_db.stat().st_size,c.index_db.stat().st_mtime_ns)
    save(LOCAL/'diagnosis/freeze.json',dict(seal_seconds=seal,sqlite_version=sqlite3.sqlite_version,main_stamp=stamp,selection_sha=sha(sel),df_cap=24,ablation_cap=6,model_calls=0,temporary_vocab='CREATE VIRTUAL TABLE temp.selective_vocab USING fts5vocab(main,corpus_fts,row)'))
    try:
        db.execute('CREATE VIRTUAL TABLE temp.selective_vocab USING fts5vocab(main,corpus_fts,row)')
        df=[];ab=[]
        for term in sel['df_terms']:
            assert idle(),'User work became active';v=bounded(db,'SELECT doc,cnt FROM temp.selective_vocab WHERE term=?',(term,),30);df.append(dict(term=term,**v));save(LOCAL/'diagnosis/df.json',df);print('DF',term,v['status'],round(v['seconds'],3),flush=True)
        for row in sel['ablations']:
            assert idle(),'User work became active';v=bounded(db,'SELECT count(*) FROM corpus_fts WHERE corpus_fts MATCH ?',(row['expression'],),60);ab.append(dict(**row,**v));save(LOCAL/'diagnosis/ablations.json',ab);print('ABLATION',row['query'],row['kind'],v['status'],round(v['seconds'],3),flush=True)
        assert stamp==(c.index_db.stat().st_size,c.index_db.stat().st_mtime_ns),'Sealed main changed'
        save(LOCAL/'diagnosis/complete.json',dict(df_queries=len(df),ablations=len(ab),main_unchanged=True,seal_seconds=seal,new_model_calls=0));print('Bounded diagnosis complete; no runtime DF/counting',flush=True)
    finally:db.close()
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['freeze']:freeze()
    elif sys.argv[1:]==['diagnose']:diagnose()
    else:raise SystemExit('freeze | diagnose')
