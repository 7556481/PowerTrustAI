"""Budget admission for the unique fixed source-first batch; no implicit retry/run."""
import asyncio,json,threading
from dataclasses import replace
from time import monotonic
from backend.config import ROOT
from backend.serialization import wire
from core.models import TaskRequest,GenerationEvidenceSnapshot,ClaimExtractionOutput
from agents.contracts import ReliabilityVerificationInput
from evaluation.archive_replay import restore
from evaluation.source_first_materials_v1 import LOCAL
from evaluation.natural_draft_audit_v1 import save,sha
from model_adapter.contracts import ModelSettings,ModelConnectionError
from model_adapter.runtime import model_scope,ModelBudget
from services.source_first_audit_v1 import SourceFirstReviewAgent,VERSION

PUBLIC=ROOT/'docs/evaluation/source-first-audit-redesign-v1'

def token_reservation(request):
    # No provider tokenizer is installed/frozen for this model. One token cannot
    # encode less than one byte of nonempty content; reserve all UTF-8 bytes plus
    # a generous framing allowance and the complete legal output allowance.
    # This is an upper-bound admission policy, never a measured token estimate.
    return sum(len(m.content.encode('utf-8'))+len(m.role.encode('utf-8')) for m in request.messages)+2048+request.max_output_tokens

class SendLimit:
    def __init__(self,root,clock=monotonic):
        self.root=root;self.clock=clock;self.start=clock();self.calls=0;self.tokens=0;self.chains={};self.lock=threading.Lock();self.stopped=False
    def remaining_seconds(self):return max(.001,5400-(self.clock()-self.start))
    def __call__(self,spec,request,n):
        with self.lock:
            key=f"{spec['case']}-{spec['variant']}";amount=token_reservation(request)
            if self.stopped or request.model_id!='deepseek-flash' or request.max_output_tokens!=8000 or self.calls>=96 or self.chains.get(key,0)>=12 or self.tokens+amount>1200000 or self.remaining_seconds()<=.001:
                self.stopped=True;raise RuntimeError('Frozen global/chain/token/deadline admission rejected; stop all sends')
            row=dict(sequence=self.calls+1,chain=key,token_reservation=amount,total_reserved=self.tokens+amount,
                reservation_policy='UTF8-content-plus2048-framing-plus-max-output; never reclaimed',request_sha256=sha(wire(request)))
            # Durable reservation before mutation/send; persistence failure stops batch.
            try:save(self.root/'reservations'/f'{self.calls+1:04d}.json',row)
            except BaseException:self.stopped=True;raise
            self.calls+=1;self.tokens+=amount;self.chains[key]=self.chains.get(key,0)+1

async def preflight():
    """Construct real initial candidate messages without env, network or index reads.

    Admits only if each chain can reserve its full 12-call allowance using its
    observed initial wire. Later corrections/Revision/extra evidence can be larger;
    therefore a pass still needs the live atomic guard. A rejection sends nothing.
    """
    if (LOCAL/'attempt.json').exists():raise RuntimeError('Unique batch already attempted; never resume')
    m=json.loads((LOCAL/'materials-v1.1.json').read_text(encoding='utf-8'))
    require_identity=json.loads((LOCAL/'materials-v1.1-identity.json').read_text(encoding='utf-8'))
    if sha(m)!=require_identity['sha256']:raise RuntimeError('Frozen material changed')
    rows=[]
    class Capture:
        async def complete(self,r):self.request=r;raise ModelConnectionError()
    from core.models import FactRetrievalBinding,EvidenceBinding
    from harness.fact_retrieval import objects
    for row in m['cases']:
        req=restore(row['request'],TaskRequest);snapshot=restore(row['snapshot'],GenerationEvidenceSnapshot)
        extraction=restore(row['extraction'],ClaimExtractionOutput)
        bindings=tuple(FactRetrievalBinding(req.existing_answer.answer_id,1,c.claim_id,component,category,target,'',VERSION,None,snapshot.knowledge_version,
            'source_scope',delivered_evidence_ids=tuple(e.evidence_id for e in req.provided_evidence)) for c,component,category,target,q in objects(extraction.claims))
        inputs=ReliabilityVerificationInput(req,req.existing_answer,extraction.claims,req.provided_evidence,
            tuple(EvidenceBinding(e.evidence_id,'index_saved_reference','source_fidelity',1) for e in req.provided_evidence),
            snapshot.knowledge_version,tuple(e for e in req.provided_evidence if e.evidence_id in {i for c in req.existing_answer.citations for i in c.evidence_ids}),snapshot,
            fact_retrieval_bindings=bindings)
        capture=Capture();agent=SourceFirstReviewAgent(capture,ModelSettings('deepseek-flash',90,8000,96000))
        try:
            with model_scope(ModelBudget(1)):await agent.run(inputs)
        except ModelConnectionError:pass
        r=capture.request;reservation=token_reservation(r)
        save(LOCAL/'preflight-wire'/f"{row['id']}.json",wire(r))
        rows.append(dict(id=row['id'],message_chars=sum(len(x.content) for x in r.messages),
            content_utf8_bytes=reservation-10048,initial_request_reservation=reservation,
            candidate_12_call_reservation=12*reservation,wire_sha256=sha(wire(r))))
    candidate_total=sum(x['candidate_12_call_reservation'] for x in rows)
    result=dict(version=VERSION,status='budget_not_admitted' if candidate_total>1200000 else 'requires_baseline_and_later_stage_wire_preflight',
        materials_sha256=sha(m),cases=rows,total_token_cap=1200000,candidate_chains_only_48_call_reservation=candidate_total,
        full_pair_calls=96,output_allowance_alone=96*8000,
        method='Conservative UTF-8 reservation, NOT actual provider tokens. Uses frozen initial candidate wires before adjacency/correction/revision growth. Baseline not priced and not treated as same scope.',
        limitation='This conservative admission can reject a batch whose actual usage would fit; no claim that actual provider consumption must exceed cap.',
        project_model_calls=0,actual_tokens=0,env_loaded=False,attempt_started=False,
        stop='Do not lower output limits, shrink cases, omit required re-review, use another tokenizer estimate as hard proof, or start a partial paid batch. No second batch.')
    save(LOCAL/'preflight-v1.1.json',result);save(PUBLIC/'preflight.json',result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':asyncio.run(preflight())
