"""Read-only frozen retrieval delivery replay with original span/neighbor contracts."""
import hashlib,json,time
from pathlib import Path
from dataclasses import replace
from evaluation.archive_replay import restore
from evaluation.fast_overlap_v27 import HOME,select
from core.models import Evidence
from rag.contracts import RetrievalResult,ContextOptions
from rag.storage import KnowledgeStore
from rag.corpus_index import corpus_evidence
from rag.context import read_adjacent_context
from backend.serialization import wire

SOURCE=Path('D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3')
PRIOR=HOME.parent/'tantivy-delivery-replay-v20'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))

class SourceCatalog:
    """Replay exact fragments/identities; no MATCH and no weakening of span hashes.

    Whole-file source seal was accepted by the unchanged production service.
    This replay checks each requested original row/body/span identity; it does not
    claim a new independent whole-file seal or a native-query timing measurement.
    """
    def __init__(self,source=SOURCE):
        self.store=KnowledgeStore(source,readonly=True,validated_pdf_cache=True)
        self.connection=self.store.connection
        self.manifests={k:json.loads(v) for k,v in self.connection.execute('select knowledge_version,manifest from corpus_seal')}
        self.cache={}
    def evidence(self,fragment_id,knowledge_version):
        key=(fragment_id,knowledge_version)
        if key not in self.cache:
            self.cache[key]=corpus_evidence(self,fragment_id,knowledge_version,self.manifests[knowledge_version]) if knowledge_version in self.manifests else self.store.evidence(fragment_id,knowledge_version)
        return self.cache[key]
    def verify_evidence(self,evidence):
        expected=self.evidence(evidence.provenance.fragment_id,evidence.provenance.knowledge_version)
        if expected!=evidence:raise ValueError('Frozen evidence differs from original SQLite span')
        return expected
    def close(self):self.store.close()


def chosen_result(catalog,query,pool,options=None):
    chosen,trace=select(query,pool.evidence)
    started=time.monotonic()
    for e in chosen:catalog.verify_evidence(e)
    context=None if options is None else read_adjacent_context(catalog,chosen,pool.knowledge_version,options)
    trace['context_replay_seconds']=time.monotonic()-started
    hits={h.evidence_id:h for h in pool.hits}
    result=RetrievalResult(chosen,pool.knowledge_version,pool.execution_issues,tuple(replace(hits[e.evidence_id],rank=i+1) for i,e in enumerate(chosen)),context)
    return result,trace


def main():
    freeze=read(PRIOR/'freeze.json');measurements=[json.loads(line) for line in (PRIOR/'measurements.jsonl').read_text(encoding='utf-8').splitlines()];index={(r['slot'],r['route']):r for r in measurements};catalog=SourceCatalog();out=[]
    try:
        for item in freeze['requests']:
            pool=restore(index[(item['slot'],'v18')]['result'],RetrievalResult);opt=item['options'].get('context_options');opt=None if opt is None else restore(opt,ContextOptions)
            result,trace=chosen_result(catalog,item['query'],pool,opt)
            out.append(dict(slot=item['slot'],case=item['case'],origin=item['origin'],purpose=item['purpose'],query_sha256=item['query_sha256'],result=wire(result),selection=trace,historical_native6_seconds=index[(item['slot'],'v18')]['total_seconds'],sqlite_seconds=index[(item['slot'],'sqlite')]['total_seconds']))
        (HOME/'frozen56-candidate-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        root=Path('D:/PowerTrustAI/data/retrieval_local');deliveries=read(root/'tantivy-query-repair-v18/delivery-replay.json')['results'];questions={c['id']:c['query'] for c in read(root/'tantivy-shards-v16/review-materials-v17.json')['cases']};extra=[]
        for record in deliveries:
            evidence=tuple(restore(e,Evidence) for e in record['roots']);pool=RetrievalResult(evidence,evidence[0].provenance.knowledge_version)
            selected,trace=select(questions[record['query']],evidence)
            context=read_adjacent_context(catalog,selected,pool.knowledge_version,ContextOptions())
            delivered=tuple(selected)+tuple(v.evidence for v in context.items)
            extra.append(dict(batch='offline24-v18',case=record['query'],question_sha256=hashlib.sha256(questions[record['query']].encode()).hexdigest(),query=questions[record['query']],pool=wire(evidence),selected=wire(selected),context=wire(context),selection=trace,critical_literal_105_present=any('1.05' in e.text for e in delivered),original_ids_preserved=all(catalog.verify_evidence(e)==e for e in delivered)))
        (HOME/'offline24-candidate-delivery.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8')
        iso=next(r for r in extra if r['case']=='Q10');old=next(e for e in iso['pool'] if '1.05' in e['text']);present={e['evidence_id'] for e in iso['selected']}|{e['evidence']['evidence_id'] for e in iso['context']['items']}
        proof=dict(batch='offline24-v18',case='Q10',question_sha256=iso['question_sha256'],selected_pool_ranks=[r['pool_rank'] for r in iso['selection']['selected']],root_chars=sum(len(e['text']) for e in iso['selected']),context_chars=iso['context']['char_count'],expected_evidence_id=old['evidence_id'],expected_fragment_id=old['provenance']['fragment_id'],expected_source_version=old['source_version'],expected_locator=old['locator'],expected_body_sha256=hashlib.sha256(old['text'].encode()).hexdigest(),expected_full_text=old['text'],expected_original_evidence_present=old['evidence_id'] in present,critical_literal_105_present=iso['critical_literal_105_present'],selection_policy='unchanged frozen v27, no target IDs/numbers in selector',status='confirmed lost if absent in whole source and bounded adjacency')
        (HOME/'iso-directed-review-private.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in proof.items() if k!='expected_full_text'},ensure_ascii=False));print('Frozen requests replayed',len(out),'offline24 existing deliveries',len(extra))
    finally:catalog.close()
if __name__=='__main__':main()
