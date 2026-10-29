"""Default-off selective MATCH v1. Lexical coverage is never semantic support.

All retained input tokens participate in each MATCH/BM25. Topic constraints add
term occurrences, so these scores intentionally differ from the production SQL.
No DF probes, second scorer, global cross-MATCH score, or broad OR fallback.
"""
import re
import time
from dataclasses import dataclass, field, replace
from rag.chinese_terms import terms, TERMS, ALIASES
from rag.topic_lanes import tagger, GENERIC
from rag.contracts import RetrievalResult, RetrievalHit
from core.validation import require

VERSION = 'selective-match-stage-priority-v1'
STOP = set('a an the of to and or in on at is are be may all only if as by for with from than not no'.split())
STOP.update(GENERIC)
STOP.update(('电力系统','系统','的','时','不能','可以','不要','怎样','它','把','电路'))

def quoted(words):
    return '('+' OR '.join('"'+w+'"' for w in words)+')'

def plan(query):
    text=re.sub(r'\nvoltage_stability_reactive_support\nengineering prerequisites constraints operating limits applicability\s*$','',query)
    text=re.sub(r'(?:请)?用\s*\d+\s*字(?:以内(?:回答|说明)?|回答|说明)','',text)
    raw=tuple(dict.fromkeys(terms(text)))
    expanded=tuple(sorted({v for w in raw for v in (w,*ALIASES.get(w,()))}))
    # Established dictionary concepts take precedence, followed by input-order
    # nouns/entities. This is independent of fixture IDs, DF and target passages.
    topics=[w for w in raw if w in TERMS]
    topics += [t.word.casefold() for t in tagger().cut(text,HMM=False)
               if (t.flag.startswith('n') or t.flag in ('eng','l'))
               and len(t.word)>=2 and t.word.casefold() in raw and t.word.casefold() not in STOP]
    topics=list(dict.fromkeys(topics))[:4]
    groups=[tuple(sorted({w,*ALIASES.get(w,())})) for w in topics]
    qualifiers=tuple(w for w in raw if w in {'不','非','不能','不可','仅','只有','必须','如果','当','超过','not','only','if','may','minutes','mvar','mw'} or any(c.isdigit() for c in w))
    base=quoted(expanded) if expanded else ''
    expr=[]
    if groups:
        expr.append(base+' AND '+' AND '.join(map(quoted,groups)))
        if len(groups)>2:
            expr.append(base+' AND '+quoted(groups[0])+' AND '+quoted(groups[1]))
            expr.append(base+' AND '+quoted(groups[0])+' AND '+quoted(tuple(dict.fromkeys(w for g in groups[2:] for w in g))))
    # One or two topics: no wider fallback. An input without a usable topic
    # remains unknown rather than executing its unrestricted scoring OR.
    return dict(raw_terms=raw, scoring_terms=expanded, groups=groups, qualifiers=qualifiers,
                expressions=tuple(dict.fromkeys(expr)), version=VERSION,
                fallback='at most two selective pair relaxations; never original broad OR')

@dataclass
class Work:
    sql_limit: int = 3
    char_limit: int = 12000
    deadline: float = float('inf')
    calls: int = 0
    chars: int = 0
    bodies: dict = field(default_factory=dict)
    stages: list = field(default_factory=list)
    plan: dict = field(default_factory=dict)
    delivered_facets: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    stop: str = ''

    def check(self):
        if time.perf_counter()>=self.deadline:raise TimeoutError('Selective retrieval original deadline')

def coverage(e, p):
    found=set(terms(e.text))
    return {i for i,g in enumerate(p['groups']) if found.intersection(g)}

def select(pool,p,k):
    # Greedy lexical coverage; ties use stage/local rank only, never BM25
    # values from different expressions. Scores remain local diagnostics.
    chosen=[];covered=set();remaining=list(pool)
    while remaining and len(chosen)<k:
        best=min(remaining,key=lambda x:(-len(coverage(x[0],p)-covered),x[2],x[3]))
        remaining.remove(best);chosen.append(best);covered.update(coverage(best[0],p))
    return chosen

def retrieve(store,request,work):
    from rag.corpus_index import seal,corpus_evidence
    from rag.context import read_adjacent_context
    s=seal(store,request.knowledge_version);require(s is not None,'Selective profile requires sealed corpus')
    p=work.plan=plan(request.query);con=store.connection;pool=[]
    for stage,expression in enumerate(p['expressions']):
        work.check()
        if work.calls>=min(3,work.sql_limit):work.stop='SQL budget';break
        start=time.perf_counter();work.calls+=1
        trace=dict(stage=stage,expression=expression,reason='initial topic conjunction' if stage==0 else 'lexical facet/qualifier gap; selective relaxation',status='running',rowids=[])
        work.stages.append(trace)
        rows=con.execute('SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?',(expression,request.max_results)).fetchall()
        trace['rowids']=[r['rowid'] for r in rows]
        for rank,row in enumerate(rows,1):
            work.check();rid=row['rowid']
            if rid<0:
                r=con.execute('SELECT n.fragment_id,length(f.raw_text) AS size FROM corpus_native n JOIN fragments f ON f.fragment_id=n.fragment_id WHERE n.id=?',(-rid,)).fetchone()
            else:r=con.execute('SELECT fragment_id,end-start AS size FROM corpus_chunks WHERE id=?',(rid,)).fetchone()
            require(r is not None,'Missing selective body identity')
            fid=r['fragment_id']
            if fid in work.bodies:continue
            if work.chars+r['size']>work.char_limit:
                trace['body_budget_omitted']=True;work.stop='character budget';continue
            e=corpus_evidence(store,fid,request.knowledge_version,s)
            require(len(e.text)==r['size'],'Selective body length mismatch')
            work.bodies[fid]=e;work.chars+=len(e.text);pool.append((e,-row['score'],stage,rank))
        chosen=select(pool,p,request.max_results)
        present=set().union(*(coverage(x[0],p) for x in chosen)) if chosen else set()
        texts=set().union(*(set(terms(x[0].text)) for x in chosen)) if chosen else set()
        trace.update(status='ok',seconds=time.perf_counter()-start,lexical_facets=sorted(present),missing_facets=[i for i in range(len(p['groups'])) if i not in present],missing_qualifiers=[w for w in p['qualifiers'] if w not in texts])
        if len(chosen)>=request.max_results and not trace['missing_facets'] and not trace['missing_qualifiers']:
            work.stop='lexical coverage only; semantic review required';break
        if work.stop=='character budget':break
    chosen=select(pool,p,request.max_results)
    evidence=tuple(x[0] for x in chosen)
    work.delivered_facets={str(i):[e.evidence_id for e in evidence if i in coverage(e,p)] for i in range(len(p['groups']))}
    work.missing=[i for i in range(len(p['groups'])) if not work.delivered_facets[str(i)]]
    if not work.stop:work.stop='stages exhausted; unresolved semantic sufficiency'
    work.check()
    # Intermediate unique bodies already consume the same per-call/total limit.
    options=request.context_options
    if options is not None:options=replace(options,max_chars=min(options.max_chars,max(0,work.char_limit-work.chars)))
    context=None if options is None else read_adjacent_context(store,evidence,request.knowledge_version,options)
    work.check()
    hits=tuple(RetrievalHit(e.evidence_id,e.provenance.fragment_id,i,score,VERSION+';local-score-stage-'+str(stage)) for i,(e,score,stage,rank) in enumerate(chosen,1))
    return RetrievalResult(evidence,request.knowledge_version,hits=hits,context=context)
