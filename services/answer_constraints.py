"""Versioned explicit character limit; reject complete output, never truncate it."""
import re
from services.validation_diagnostics import StructuredValidationError

VERSION = 'explicit-answer-character-limit-v1'

def character_limit(question, requirements=()):
    # Only explicit Arabic-digit upper bounds in user answer instructions.
    # No limit is inferred from retrieved documents or from the generated answer.
    values = []
    for text in (question, *requirements):
        for match in re.finditer(r'(?:控制在|不超过|不多于|最多|限)\s*([0-9]{1,5})\s*(?:个)?(?:字|字符)(?:以内|以下)?', text):
            value = int(match[1])
            if value > 0:values.append(value)
    return min(values) if values else None

def validate_length(answer, question, requirements=(), *, stage='generation', path='$.answer_units'):
    limit = character_limit(question, requirements)
    if limit is not None and len(answer.text) > limit:
        error = StructuredValidationError(stage, path,
            'explicit_answer_character_limit_exceeded_no_truncation')
        error.diagnostic.update(max_characters=limit, actual_characters=len(answer.text),
            counting_method='unicode_code_points_in_complete_joined_answer_including_punctuation_and_whitespace',
            correction_instruction='Rewrite a complete concise answer within the original limit; preserve necessary conditions and valid citation bindings. Never cut text or weaken evidence requirements.')
        raise error
    return answer
