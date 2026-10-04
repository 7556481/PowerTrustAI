"""Exact request-scoped IDs. No approximate substitutions; full fragments retained."""
from dataclasses import asdict
import hashlib
import json
from services.quote_candidates import build_candidates
from services.validation_diagnostics import ErrorCollector


class CandidateScope:
    def __init__(self,answer,knowledge_version,purpose,evidence,*,check_id=None,protocol_version="scoped-whole-fragment-v1"):
        candidates=tuple(c for c in build_candidates(evidence) if c.method=="whole_fragment")
        binding={"answer_id":answer.answer_id,"answer_version":answer.version,
            "answer_sha256":hashlib.sha256(answer.text.encode()).hexdigest(),
            "knowledge_version":knowledge_version,"purpose":purpose,"check_id":check_id,"protocol_version":protocol_version,
            "candidate_ids":[c.quote_id for c in candidates]}
        self.scope_id="scope-"+hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()[:24]
        self.binding=binding
        self.candidates=candidates
        self.by_wire={self.scope_id+"-"+str(i):c for i,c in enumerate(candidates)}
        self.evidence_ids={e.evidence_id for e in evidence}
        self.metadata=[{k:v for k,v in asdict(e).items() if k!="text"} for e in evidence]

    def payload(self):
        # Entire literal fragment once. Context equals fragment for this method.
        return {"scope_id":self.scope_id,**{k:v for k,v in self.binding.items() if k!="candidate_ids"},"candidate_count":len(self.candidates),
            "EVIDENCE_METADATA":self.metadata,
            "QUOTE_CANDIDATES":[{"quote_id":wire,"evidence_id":c.evidence_id,"text":c.text,
                "start_offset":c.start_offset,"end_offset":c.end_offset,"warnings":c.warnings}
                for wire,c in self.by_wire.items()]}

    def resolve(self,wire,path,collector=None):
        ec=collector or ErrorCollector()
        if not ec.check(type(wire) is str and wire in self.by_wire,path,"quote_id_must_belong_to_this_request_scope"):
            ec.errors[-1].update(scope_id=self.scope_id,allowed_quote_ids=list(self.by_wire),
                processing_options=["select_an_exact_ID_from_this_request","return_insufficient_evidence_without_basis"])
            if collector is None:ec.finish()
            return None
        return self.by_wire[wire].quote_id
