"""Explicitly injected semantic candidate; production factory never selects it."""
from agents.evidence_verification import ModelEvidenceVerificationAgent
from services import premise_review_protocol_v1


class PremiseVerificationAgent(ModelEvidenceVerificationAgent):
    premise_profile = premise_review_protocol_v1

    def __init__(self, adapter, settings, *, diagnostic_dir=None, correction_accounting='invocation_scoped_v1'):
        super().__init__(adapter, settings, diagnostic_dir=diagnostic_dir, schema_version=13,
            support_relation_checks=True, support_relation_version=6, review_message_profile='lossless_v1',
            correction_accounting=correction_accounting)
