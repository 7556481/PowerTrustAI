"""Reject internal identifier leakage; no text deletion or truncation."""
import re
from services.validation_diagnostics import StructuredValidationError

VERSION='answer-body-no-internal-evidence-ids-v1'
def validate(answer,*,stage='generation'):
    if re.search(r'\b(?:e-[0-9a-f]{64}|user-[0-9a-f]{32})\b',answer.text,re.I):
        error=StructuredValidationError(stage,'$.answer_units','internal_evidence_id_in_answer_body')
        error.diagnostic.update(constraint_version=VERSION,correction_instruction='Rewrite the COMPLETE same answer with technical clauses and necessary conditions intact. Put internal IDs ONLY in evidence_ids, never body text. Do not truncate/delete substantive content to hide the identifier.')
        raise error
    return answer
