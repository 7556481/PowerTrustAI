"""Development-only diagnostics revision; unchanged v4 prompt and acceptance rules.

No paid entry point. Never repairs predictions or reinterprets historical results.
"""
from evaluation import premise_bound_review_v4 as previous
from services.validation_diagnostics import ErrorCollector

VERSION = 'typed-premise-field-diagnostics-eval-v5-dev'
PROMPT = previous.PROMPT
messages = previous.messages
model_input = previous.model_input
basis_catalog = previous.basis_catalog


def parse(value, task):
    # Validate outer identities exactly as before when their shape is invalid.
    # Only replace the misleading unit field-set error with precise diagnostics.
    previous.basis_catalog(task)
    if not (isinstance(value, dict) and
            set(value) == {'sample_id', 'requirements', 'units', 'rationale'} and
            isinstance(value['units'], list)):
        return previous.parse(value, task)
    errors = ErrorCollector(VERSION)
    for i, unit in enumerate(value['units']):
        path = '$.units[' + str(i) + ']'
        if errors.fields(unit, {'unit_id', 'judgments', 'rationale'}, set(), path):
            errors.check(isinstance(unit['rationale'], str) and
                         bool(unit['rationale'].strip()),
                         path + '.rationale', 'nonempty_unit_rationale_required')
    errors.finish()
    # All original ID, typed basis, scope, judgment and requirement checks remain.
    return previous.parse(value, task)
