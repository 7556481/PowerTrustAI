"""Explicit opt-in; no production factory or v1 batch entry selects this candidate."""
from agents.premise_verification_v1 import PremiseVerificationAgent
from services import premise_review_protocol_v2

class PremiseVerificationAgentV2(PremiseVerificationAgent):
    premise_profile = premise_review_protocol_v2
