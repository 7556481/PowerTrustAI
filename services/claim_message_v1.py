"""One v7 message shape; unchanged parser and semantic obligations."""
import json
from services.answer_anchors import SYSTEM as V5
from services.answer_basis_targets import SYSTEM as V6
from services.claim_obligations import SYSTEM as V7, DAILY_SYSTEM

VERSION = 'atomic-claims-v7-unified-message-v1'
PROFILE = 'unified_v1'


def system(daily=True):
    # Keep the existing semantic instructions verbatim. Only obsolete shape
    # declarations/examples are replaced with the current parser's one shape.
    anchor = V5.split('Legal example:')[0]
    anchor = anchor.replace('Root EXACT claims,non_claims. Choose existing anchor_id; never copy source quotes, IDs, versions or offsets.',
                            'Choose existing anchor_id; never copy source quotes, IDs, versions or offsets.')
    anchor = anchor.replace('Each claim EXACT anchor_id,proposition,claim_type,components,assertion_role,semantic_qualifiers.\n', '')
    anchor = anchor.replace('components: 1..8 EXACT {category,proposition}; categories', 'Component categories:')
    anchor = anchor.replace('non_claims: EXACT anchor_id,reason, [] legal. Only whole entirely nonfactual paragraphs;',
                            'Nonclaims are only whole entirely nonfactual paragraphs;')
    target = V6[len(V5):].split('Full legal example:')[0]
    target = target.replace('CURRENT V6 COMPONENT SHAPE: each component EXACT category,proposition,basis_target.\n', '')
    obligation = V7[len(V6):].split('Full component example:')[0]
    obligation = obligation.replace('CURRENT V7: every component ALSO requires verification_obligation.\n', '')
    obligation += 'Retain grouped numeric strings; the program owns numeric parsing. Do not invent tool evidence.\n'
    clarity = DAILY_SYSTEM[len(V7):] if daily else ''
    return anchor + target + obligation + clarity + '\n' + contract()


def contract():
    example = dict(claims=[dict(anchor_id='supplied-anchor',
        proposition='The supplied input states Q=30 MW.', claim_type='input_report',
        assertion_role='input_report', semantic_qualifiers=[], components=[dict(
            category='input_evidence_coverage', proposition='The supplied input states Q=30 MW.',
            basis_target='input_snapshot', verification_obligation='input_provided')])], non_claims=[])
    return ('ONE CURRENT V7 OUTPUT SHAPE (initial and correction):\n'
        'Root EXACT required keys claims, non_claims; neither may be omitted.\n'
        'claims: nonempty array, at most32. Each item EXACT required keys '
        'anchor_id, proposition, claim_type, components, assertion_role, semantic_qualifiers.\n'
        'Each component EXACT required keys category, proposition, basis_target, verification_obligation.\n'
        'non_claims: array, at most64; [] is allowed only when your classification warrants it. '
        'Each item EXACT required keys anchor_id, reason. No additional fields.\n'
        'Example is synthetic shape data, not a classification of this answer:\n' +
        json.dumps(example, ensure_ascii=False))


def correction_instruction():
    return ('Return the complete v7 extraction in the original field meanings. '
            'Choose existing anchor IDs; the program binds literal text and positions. '
            'Preserve actual quantities, negation, qualifiers and obligation strength; '
            'do not repair assertions or invent missing semantic fields.\n' + contract())
