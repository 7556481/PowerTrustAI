"""Optional extractor for public-review premise candidate, one normal request."""
from dataclasses import asdict
import json
from services.claim_extractor import ModelClaimExtractor
from services.claim_obligations import DAILY_SYSTEM
from services.answer_anchors import anchors
from services.structured_model import structured_request
from services.task_premises_v1 import catalog, parse_extraction, EXTRACTION_INSTRUCTION as V1_INSTRUCTION
from services.premise_review_protocol_v2 import PROFILE

EXTRACTION_INSTRUCTION = V1_INSTRUCTION + """
OBJECT BOUNDARY v2: classify the actual component proposition, never the paragraph.
A conditional rule such as `at least 50 permits P` and a score-independent rule
`regardless of score P is never mandatory` are literature with premise_ids [].
`This stipulated score is 55, so P is permitted` is scenario_application and selects
only the relevant task premise IDs. Sharing an anchor with an application does not
make every rule clause an application. Split independently expressed rule and instance
components without inventing missing assertions. Unrelated premises are not selected.
Keep an incorrect explicit instance application an application; do not relabel it as
literature to avoid checking the actual task. Mixed/unclear objects remain uncertain.
"""
from model_adapter.contracts import ModelMessage


class PremiseClaimExtractorV2(ModelClaimExtractor):
    def __init__(self, adapter, settings, *, diagnostic_dir=None):
        super().__init__(adapter, settings, diagnostic_dir=diagnostic_dir,
                         typed_components=True, protocol_version=7, daily_guidance=True)

    async def extract(self, answer):
        raise ValueError('Premise candidate requires actual task via extract_for_task')

    async def extract_for_task(self, answer, request):
        payload = {'answer_id': answer.answer_id, 'answer_version': answer.version,
                   'ANSWER_ANCHORS': anchors(answer), 'assumptions': answer.assumptions,
                   'missing_information': answer.missing_information,
                   'CURRENT_TASK': {'task_id': request.task_id, 'question': request.question, 'user_context': request.user_context},
                   'TASK_PREMISES': [asdict(p) for p in catalog(request)]}
        path = None if self.diagnostics is None else self.diagnostics.save_scope(payload)
        result, _ = await structured_request(self.client,
            (ModelMessage('system', DAILY_SYSTEM + EXTRACTION_INSTRUCTION), ModelMessage('user', json.dumps(payload, ensure_ascii=False))),
            PROFILE + '-extraction', lambda v: parse_extraction(v, answer, request), diagnostics=self.diagnostics,
            response_contract_version=PROFILE + '-extraction', candidate_catalog_path=path)
        return result
