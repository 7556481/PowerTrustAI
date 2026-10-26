"""Opt-in small-catalog source routing and bilingual lexical retrieval v1.

No answers, question IDs, target documents or translation dictionary live here.
The original published body store remains the sole Evidence authority.
"""
import asyncio
from dataclasses import dataclass
import json
import re

from core.validation import require, validate_types
from core.models import ExecutionIssue, ExecutionStatus
from rag.bm25 import tokenize, score_corpus
from rag.contracts import RetrievalRequest, RetrievalResult, RetrievalHit
from rag.storage import KnowledgeStore, canonical, digest
from rag.corpus_index import seal
from rag.context import read_adjacent_context
from rag.retriever import AsyncSQLiteBM25Retriever
from services.generation_query import chinese_query, english_corpus

PROFILE = 'chinese_first_cross_language_v1'
SCORING = 'catalog-lexical-v1;RRF(k=60,depth=20,equal-weight,stable-fragment-id)'
STOP = frozenset('a an the and or of in on at for with by from is are was were be as how what why does do please explain describe according which these this'.split())


def lexical(text):
    return tokenize(text) + tuple(w.casefold() for w in re.findall(r'[\u0370-\u03ff]+|[=+*/^<>≤≥−]', text))


def query_body(text, aliases):
    for alias in sorted(aliases, key=len, reverse=True):
        pattern = re.escape(alias)
        if re.fullmatch(r'[A-Za-z0-9-]+', alias):
            pattern = r'(?<![A-Za-z0-9])'+pattern+r'(?![A-Za-z0-9])'
        text = re.sub(pattern, ' ', text, flags=re.I)
    # Generic lexical stop words; uppercase technical abbreviations survive.
    upper = set(re.findall(r'\b[A-Z][A-Z0-9]+\b', text))
    return ' '.join(w for w in lexical(text) if w not in STOP or w.upper() in upper)


def language(text):
    cjk = len(re.findall(r'[\u3400-\u9fff]', text))
    latin = len(re.findall(r'[A-Za-z]', text))
    if cjk and latin:
        return 'mixed' if min(cjk, latin)/max(cjk, latin) >= .05 else ('chinese' if cjk>latin else 'english')
    return 'chinese' if cjk else 'english' if latin else 'unknown'


def match_alias(text, alias):
    pattern = re.escape(alias)
    if re.fullmatch(r'[A-Za-z0-9-]+', alias):
        pattern = r'(?<![A-Za-z0-9])'+pattern+r'(?![A-Za-z0-9])'
    return bool(re.search(pattern, text, re.I))


@dataclass(frozen=True)
class Scope:
    status: str
    members: tuple
    aliases: tuple
    english: bool
    message: str


class Catalog:
    def __init__(self, rows):
        require(len(rows)<=10000, 'Catalog fragment limit exceeded')
        require(sum(len(canonical(dict(r)).encode()) for r in rows)<=100*1024*1024, 'Catalog byte limit exceeded')
        self.rows = tuple(dict(r) for r in rows)
        grouped = {}
        for row in self.rows:
            grouped.setdefault((row['document_id'], row['version']), []).append(row)
        require(len(grouped)<=12, 'Catalog document limit exceeded')
        self.documents=[]
        for (doc, version), fragments in sorted(grouped.items()):
            meta=json.loads(fragments[0]['metadata']); title=meta.get('document_title') or ''
            publisher=meta.get('publisher') or ''
            title_alias={title} if title else set()
            if ': ' in title:title_alias.add(title.split(': ',1)[1])
            identifier=re.match(r'^([A-Z][A-Z0-9]+-\d+(?:-\d+)*)\b',title)
            if identifier:title_alias.add(identifier[1])
            org_alias={publisher} if publisher else set()
            org_alias.update(re.findall(r'[（(]([A-Z][A-Z0-9-]{1,15})[）)]',publisher))
            # Only literal publisher components, never document/body keywords.
            for part in re.split(r'[；;]',publisher):
                stem=re.split(r'[（(《]',part)[0].strip()
                if len(stem)>=3:org_alias.add(stem)
            text='\n'.join(r['raw_text'] for r in fragments)
            self.documents.append(dict(document_id=doc,version=version,title=title,publisher=publisher,
                title_aliases=sorted(title_alias),institution_aliases=sorted(org_alias),
                language=language(text),english_body_available=any(english_corpus([r]) for r in fragments),
                fragments=len(fragments),text_sha256=digest(text.encode())))
        self.identity=digest(canonical(self.documents).encode())
        self.tokens={r['fragment_id']:lexical(r['search_text']) for r in self.rows}

    def resolve(self, question):
        quoted=re.findall(r'《([^》]+)》',question)
        titles=[d for d in self.documents if any(match_alias(question,a) for a in d['title_aliases'])]
        # An explicitly named absent title must not fall back to its institution.
        absent=[q for q in quoted if not any(q.casefold()==a.casefold() for d in self.documents for a in d['title_aliases'])]
        if absent:
            return Scope('source_not_found',(),(),False,'未找到所指资料：'+'、'.join(absent)+'；可检查当前目录标题。')
        institutions=[d for d in self.documents if any(match_alias(question,a) for a in d['institution_aliases'])]
        if titles and institutions and not any(d in institutions for d in titles):
            return Scope('source_conflict',(),(),False,'所指标题与机构目录身份冲突，未擅自选择或更正来源。')
        selected=titles or institutions
        if not selected:return Scope('unspecified',(),(),False,'未指定目录可识别来源，沿原路径。')
        aliases=tuple(sorted({a for d in selected for a in d['title_aliases']+d['institution_aliases'] if match_alias(question,a)}))
        members=tuple((d['document_id'],d['version']) for d in selected)
        return Scope('title' if titles else 'institution',members,aliases,
            any(d['english_body_available'] for d in selected),
            '保留全部匹配文献/版本；'+str(len(members))+'项，未擅选唯一资料。')

    def rank(self, question, scope, english=None):
        members=set(scope.members); rows=[r for r in self.rows if (r['document_id'],r['version']) in members]
        lanes=[]
        for query in (question,) if english is None else (question,english):
            body=query_body(query,scope.aliases)
            # score_corpus uses the existing generic tokenizer. Greek/math
            # tokens are retained in the lexical plan and do not erase numbers.
            scores=score_corpus(body,[self.tokens[r['fragment_id']] for r in rows],query_tokens=lexical(body))
            lane=sorted(((r['fragment_id'],s) for r,s in zip(rows,scores) if s>0),key=lambda p:(-p[1],p[0]))[:20]
            lanes.append(dict(query=query,body_query=body,candidates=lane))
        if english is None:
            ranked=lanes[0]['candidates']
        else:
            fused={}
            for lane in lanes:
                for rank,(fid,_) in enumerate(lane['candidates'],1):fused[fid]=fused.get(fid,0)+1/(60+rank)
            ranked=sorted(fused.items(),key=lambda p:(-p[1],p[0]))
        return ranked,lanes


class ChineseFirstRetriever(AsyncSQLiteBM25Retriever):
    """Same bounded worker/interface and original body verification; opt-in only."""
    manages_query_conversion = True
    def __init__(self,path,knowledge_version,converter=None,*,bilingual=True,catalog=None):
        super().__init__(path,execution_profile='topic_v4_subject_v1')
        self.execution_profile=PROFILE if bilingual else PROFILE+'-original-only'
        self.cache_identity=('bm25',self.execution_profile)
        self.knowledge_version=knowledge_version;self.converter=converter;self.bilingual=bilingual
        self.catalog=catalog;self.plans={};self.converted={};self.last_results={}

    def _load(self):
        with KnowledgeStore(self.path,readonly=True,validated_pdf_cache=True) as store:
            s=seal(store,self.knowledge_version)
            base=self.knowledge_version if s is None else s['base_knowledge_version']
            self.catalog=Catalog(store.rows(base))

    async def prepare(self):
        if self.catalog is None:
            import functools
            await asyncio.get_running_loop().run_in_executor(self._executor,self._load)
        return self.catalog

    async def retrieve(self,request):
        require(request.knowledge_version==self.knowledge_version,'Candidate knowledge mismatch')
        catalog=await self.prepare();scope=catalog.resolve(request.query)
        if self.bilingual and scope.members and scope.english and chinese_query(request.query):
            require(self.converter is not None,'Triggered profile requires converter')
            # A plan may be replayed for validation, never translated twice.
            require(request not in self.converted,'One translation per request; no retrieval resubmit')
            self.converted[request]=await self.converter.run(request.query)
        output=await self._submit(request)
        self.last_results[request]=output
        return output

    def _work(self,request,result,validate):
        if validate=='saved_evidence':return super()._work(request,result,validate)
        scope=self.catalog.resolve(request.query)
        if scope.status=='unspecified':
            # Ordinary Chinese uses the exact original profile/certificate.
            return super()._work(request,result,validate)
        with KnowledgeStore(self.path,readonly=True,validated_pdf_cache=True) as store:
            seal(store,request.knowledge_version)
            if scope.status in ('source_not_found','source_conflict'):
                expected=RetrievalResult((),request.knowledge_version,execution_issues=(
                    ExecutionIssue('retrieval_source',ExecutionStatus.FAILED,scope.status.upper(),scope.message),))
                plan=dict(scope=scope.__dict__,lanes=[],english_query=None)
            else:
                ranked,lanes=self.catalog.rank(request.query,scope,self.converted.get(request))
                evidence=tuple(store.evidence(fid,request.knowledge_version) for fid,_ in ranked[:request.max_results])
                hits=tuple(RetrievalHit(e.evidence_id,e.provenance.fragment_id,i,float(score),SCORING)
                    for i,(e,(_,score)) in enumerate(zip(evidence,ranked),1))
                context=None if request.context_options is None else read_adjacent_context(store,evidence,request.knowledge_version,request.context_options)
                expected=RetrievalResult(evidence,request.knowledge_version,hits=hits,context=context)
                plan=dict(scope=scope.__dict__,lanes=lanes,english_query=self.converted.get(request),catalog_identity=self.catalog.identity)
            self.plans[request]=plan
            if validate:
                validate_types(result,RetrievalResult);require(result==expected,'Scoped result differs from fixed index/query plan')
                return None
            return expected
