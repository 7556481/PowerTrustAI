"""Offline-only rationale-layout candidate; same strict v6 acceptance rules."""
import json

from evaluation import premise_bound_review_v6 as previous
from evaluation.text_bound_review import canonical
from model_adapter.contracts import ModelMessage

VERSION = 'explicit-rationale-layout-eval-v7-dev'

# A single final output example, not a second schema competing with v6's example.
# This is prompt layout only: the parser accepts any JSON object key order.
OUTPUT_SHAPE = {
    'sample_id': 'current ID',
    'requirements': [{
        'requirement_id': 'current ID',
        'coverage': 'covered|partially_covered|missing|uncertain',
        'unit_ids': ['current answer unit ID'],
        'rationale': 'independent coverage reason',
    }],
    'units': [{
        'unit_id': 'current answer unit ID',
        'rationale': 'unit-level assertion coverage, decomposition or uncertainty reason',
        'judgments': [{
            'proposition': 'scoped assertion',
            'claim_type': 'premise_restatement|literature_statement|scenario_application|external_claim',
            'support': 'supported|insufficient_evidence|contradicted|not_assessable',
            'basis_ids': ['current premise or evidence ID'],
            'rationale': 'evidence-to-proposition support reason',
        }],
    }],
    'rationale': 'brief overall explanation',
}

_START = 'Return ONLY JSON with exact fields:'
_END = '\nNo extra fields.'
assert previous.PROMPT.count(_START) == 1
_before, _example_and_after = previous.PROMPT.split(_START, 1)
_example, _after = _example_and_after.split(_END, 1)

RATIONALE_ROLES = '''
Required reasons have distinct roles, not interchangeable locations:
- requirements[i].rationale: explain addressedness, not correctness.
- units[i].rationale: explain how judgments cover this original unit's assertions
  and boundaries, or unresolved decomposition. This is a sibling of judgments.
  It is mandatory even for one unit with one judgment; a count is not a reason.
- units[i].judgments[j].rationale: explain the proposition's support label using
  its selected basis and scope, including missing/uncertain support.
- Top-level rationale: brief overall explanation; it replaces no local reason.
All must be nonempty strings. Do not copy a support reason as a unit reason or
invent filler/confidence. Preserve genuine uncertainty, scope and negation.
Before returning, check every requirement, unit and judgment has its own reason.
Missing reasons remain errors; the program does not supply them.
The example describes shape, not item counts: return all original requirements
and units, with as many judgments per unit as necessary. Key order is optional.
Return ONLY JSON with exact fields:
'''
PROMPT = (_before + _END + _after + '\n' + RATIONALE_ROLES +
          json.dumps(OUTPUT_SHAPE, ensure_ascii=False, separators=(',', ':')))

# No repair, default rationale, relaxed field checks, or historical reinterpretation.
model_input = previous.model_input
basis_catalog = previous.basis_catalog
parse = previous.parse


def messages(task):
    basis_catalog(task)
    return (ModelMessage('system', PROMPT), ModelMessage('user', canonical(task)))
