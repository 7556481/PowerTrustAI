"""Versioned explicit character limit; reject complete output, never truncate it."""
import re
from services.validation_diagnostics import StructuredValidationError

VERSION = 'explicit-answer-character-limit-v2'
PLANNING_VERSION='answer-length-planning-v1'

def planning_target(limit):
    """Advisory 75% budget includes punctuation/separators; never validated."""
    return max(1,limit*3//4)

def correction_guidance(response,diagnostic):
    if diagnostic.get('constraint')!='explicit_answer_character_limit_exceeded_no_truncation':return {}
    maximum=diagnostic['max_characters'];actual=diagnostic['actual_characters']
    return {'version':PLANNING_VERSION,'actual_characters':actual,'strict_maximum_characters':maximum,
        'advisory_target_characters':planning_target(maximum),'target_is_not_an_extra_acceptance_condition':True,
        'instruction':'Rewrite the COMPLETE answer, not a cut substring. The previous joined answer has '+str(actual)+' characters and exceeds the strict '+str(maximum)+' maximum. Aim near '+str(planning_target(maximum))+' characters to leave room for punctuation and separators. Directly answer every requested part; preserve necessary conditions/formulas/negation and valid evidence_ids attached to each rewritten unit. Remove repetition, not obligations. Assumptions/reviewer notes cannot replace conditions in the answer. No front-end hiding, string deletion, citation dropping or extra retry.'}

def character_limit(question, requirements=()):
    # Only explicit Arabic-digit upper bounds in user answer instructions.
    # No limit is inferred from retrieved documents or from the generated answer.
    values = []
    for text in (question, *requirements):
        for match in re.finditer(r'(?:控制在|不超过|不多于|最多|限)\s*([0-9]{1,5})\s*(?:个)?(?:字|字符)(?:以内|以下)?', text):
            value = int(match[1])
            if value > 0:values.append(value)
        for match in re.finditer(r'([0-9]{1,5})\s*(?:个)?(?:字|字符)\s*(?:以内|以下)', text):
            value = int(match[1])
            if value > 0:values.append(value)
    return min(values) if values else None

def validate_length(answer, question, requirements=(), *, stage='generation', path='$.answer_units', default_limit=None):
    limit = character_limit(question, requirements)
    if limit is None:limit=default_limit
    if limit is not None and len(answer.text) > limit:
        error = StructuredValidationError(stage, path,
            'explicit_answer_character_limit_exceeded_no_truncation')
        error.diagnostic.update(max_characters=limit, actual_characters=len(answer.text),
            counting_method='unicode_code_points_in_complete_joined_answer_including_punctuation_and_whitespace',
            correction_instruction='Rewrite a complete concise answer within the original limit; preserve necessary conditions and valid citation bindings. Never cut text or weaken evidence requirements.')
        raise error
    return answer


def product_default_limit(request):
    """Bound the already-declared concise Chinese concept UX; no evidence truncation."""
    context=getattr(request,'engineering_context',None)
    return 300 if context is not None and context.goal in ('conceptual','plant_assessment') and re.search(r'[\u4e00-\u9fff]',request.question) else None
