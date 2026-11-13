"""Frozen v28 continuous-source excerpts; evaluation-only, no default routing change."""
import hashlib,json,re,time
from dataclasses import replace
from evaluation.fast_overlap_v27 import enable_v18,query_tokens
VERSION='conservative-contiguous-paragraph-v28'
# Grammar classes, not answers/numbers/identifiers. Any scope-bearing root is whole.
SCOPE=re.compile(r'\d|\b(?:if|when|unless|except|not|no|only|must|shall|should|may|means|defined|because|therefore|however|this|these|such)\b|条件|定义|是指|称为|由于|因此|但是|其中|不得|不应|不能|无须|必须|应当|仅|除外|例外|否则|至少|至多|额定|单位',re.I)
PREFIX=';pta-span-v28='
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def make_span(parent,start,end):
    if not 0<=start<end<=len(parent.text):raise ValueError('Invalid source interval')
    if (start,end)==(0,len(parent.text)):return parent
    p=parent.provenance
    if p is None:raise ValueError('Missing original provenance')
    stamp=f'{start}:{end}:{digest(parent.text)}'
    locator=parent.locator+PREFIX+stamp
    ident='ex-'+digest(json.dumps([VERSION,parent.evidence_id,parent.source_version,stamp],separators=(',',':')))
    return replace(parent,evidence_id=ident,locator=locator,text=parent.text[start:end],provenance=replace(p,start_offset=p.start_offset+start,end_offset=p.start_offset+end,start_line=p.start_line+parent.text[:start].count('\n'),end_line=p.start_line+parent.text[:end].count('\n')))
def verify_span(evidence,parent):
    if PREFIX not in evidence.locator:
        if evidence!=parent:raise ValueError('Original source mismatch')
        return parent
    original,stamp=evidence.locator.rsplit(PREFIX,1)
    start,end,bodyhash=stamp.split(':');start,end=int(start),int(end)
    if original!=parent.locator or bodyhash!=digest(parent.text):raise ValueError('Parent source/hash mismatch')
    expected=make_span(parent,start,end)
    if expected!=evidence:raise ValueError('Excerpt identity/text/version/range mismatch')
    return expected

def select_span(query,parent):
    started=time.perf_counter();text=parent.text;start,end=0,len(text);reason='whole_unreliable_boundary'
    if parent.provenance and parent.provenance.text_basis=='dataset_record_original_text' and not SCOPE.search(text):
        pieces=[];cursor=0
        for match in re.finditer(r'\n[ \t]*\n+',text):
            if text[cursor:match.start()].strip():pieces.append((cursor,match.start()))
            cursor=match.end()
        if text[cursor:].strip():pieces.append((cursor,len(text)))
        # Whole sentences and paragraph context on both sides, one continuous hull.
        if len(pieces)>=5 and all(text[a:b].strip().endswith(('.','。','!','！','?','？')) for a,b in pieces):
            from rag.chinese_terms import terms
            target=query_tokens(query);matches=[i for i,(a,b) in enumerate(pieces) if set(terms(text[a:b]))&target]
            if matches:
                lo=max(0,min(matches)-1);hi=min(len(pieces)-1,max(matches)+1)
                start,end=pieces[lo][0],pieces[hi][1];reason='matched_paragraph_hull_plus_adjacent_paragraphs'
    selected=make_span(parent,start,end)
    return selected,dict(parent_id=parent.evidence_id,selected_id=selected.evidence_id,start=start,end=end,parent_chars=len(text),selected_chars=len(selected.text),reason=reason,seconds=time.perf_counter()-started)

class CandidateRetriever:
    def __init__(self,native):
        self.native=native;self.execution_profile=native.execution_profile;self.cache_identity=(VERSION,native.cache_identity);self._certificate=None;self.parents={};self.last_trace={}
    def __getattr__(self,name):return getattr(self.native,name)
    async def retrieve(self,request):
        started=time.perf_counter();pool=await self.native.retrieve(replace(request,max_results=6,context_options=None));roots=[];trace=[];ids={}
        for e in pool.evidence:
            excerpt,row=select_span(request.query,e);roots.append(excerpt);trace.append(row);ids[e.evidence_id]=excerpt.evidence_id;self.parents[excerpt.evidence_id]=e
        context=None if request.context_options is None else await self.native.source_context(pool.evidence,request.knowledge_version,request.context_options)
        if context is not None:context=replace(context,items=tuple(replace(item,links=tuple(replace(link,core_evidence_id=ids[link.core_evidence_id]) for link in item.links)) for item in context.items))
        hits=tuple(replace(hit,evidence_id=root.evidence_id,scoring_method=hit.scoring_method+';'+VERSION) for hit,root in zip(pool.hits,roots))
        result=replace(pool,evidence=tuple(roots),hits=hits,context=context);self._certificate=(request,result);self.last_trace={'version':VERSION,'excerpts':trace,'total_seconds':time.perf_counter()-started};return result
    async def validate_evidence(self,evidence,knowledge_version):
        originals=[]
        for e in evidence:
            if PREFIX in e.locator:
                parent=self.parents.get(e.evidence_id)
                if parent is None:
                    # Reconstruct by original fragment through existing read-only worker.
                    from rag.contracts import ContextOptions
                    from evaluation.fast_overlap_replay_v27 import SourceCatalog
                    catalog=SourceCatalog(self.native.path)
                    try:parent=catalog.evidence(e.provenance.fragment_id,knowledge_version)
                    finally:catalog.close()
                verify_span(e,parent);originals.append(parent)
            else:originals.append(e)
        await self.native.validate_evidence(tuple(originals),knowledge_version)
    async def validate_result(self,request,result):
        if self._certificate!=(request,result):raise ValueError('Uncertified candidate result')
        await self.validate_evidence(result.evidence+(() if result.context is None else tuple(i.evidence for i in result.context.items)),request.knowledge_version)
    def close(self):self.native.close()
