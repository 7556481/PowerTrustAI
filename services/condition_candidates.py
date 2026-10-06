"""Program-bound literal carriers; no automatic semantic condition extraction."""
import hashlib,json

VERSION='source-condition-carriers-v1'
def catalog(scope):
    metadata={e['evidence_id']:e for e in scope.metadata};result={}
    for wire,parent in scope.by_wire.items():
        # Reconstructing Evidence is unnecessary: whole quotes are already exact,
        # bounded candidates; no new splitting or guessed condition spans.
        binding={'version':VERSION,'scope_id':scope.scope_id,'quote_id':wire,
            'candidate_id':parent.quote_id,'evidence_id':parent.evidence_id,
            'start_offset':parent.start_offset,'end_offset':parent.end_offset,
            'source_version':metadata[parent.evidence_id]['source_version'],
            'locator':metadata[parent.evidence_id]['locator'],
            'provenance':metadata[parent.evidence_id].get('provenance'),
            'text_sha256':hashlib.sha256(parent.text.encode()).hexdigest(),
            'knowledge_version':scope.binding['knowledge_version'],
            'answer_id':scope.binding['answer_id'],'answer_version':scope.binding['answer_version']}
        cid='condition-'+hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()[:24]
        result[cid]={**binding,'condition_id':cid,'text':parent.text,
            'granularity':'whole_existing_quote_carrier','semantic_necessity_not_program_proof':True}
    return result

def payload(scope):return {'version':VERSION,'candidates':[{k:v for k,v in c.items() if k not in ('text','provenance')} for c in catalog(scope).values()],'note':'Exact source body is the corresponding QUOTE_CANDIDATES text. Complete quote carriers, not automatically extracted minimal condition spans; model identifies necessity.'}
