"""Negative output constraints are not affirmative evidence obligations."""
import re
VERSION='task-requirements-v2-negative-constraints'
INSTRUCTION='''
Task obligations v2: distinguish facts actually asserted by the answer, user
instructions NOT to assert a conclusion, and information genuinely needed for
requested topics. A prohibition is not a request to prove the forbidden universal
claim or its negation. Comply by not asserting it; do not list that unrequested
proof as missing_information. If the answer DOES assert the guarantee, review
it strictly even if prohibited. Necessary conditions of the actual explanation
remain necessary; never suppress them. Actual missing topics remain gaps.
'''
def prohibited_spans(question):
    return [{'start_offset':m.start(),'end_offset':m.end(),'kind':'negative_output_constraint'} for m in re.finditer(r'(?:不要|请勿|不得|避免)(?:说|声称|宣称|断言|作出|做出|认为)[^。；;!?！？]*',question)]
