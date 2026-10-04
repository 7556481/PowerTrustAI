"""Finite scalar SI conversions; not simulation or physical quantity correction."""
import hashlib
import json
import math
import re
from core.models import ExecutionStatus,ExecutionIssue
from tools.contracts import ToolSpec,ToolResult
from services.quantity_checks import UNITS

VERSION='scalar-si-conversion-v1'
PAIRS={u:(kind,scale) for kind,values in UNITS.items() for u,scale in values.items()}
PATTERN=re.compile(r'(?<![\w.])(-?\d+(?:\.\d+)?)\s*(kV|V|MW|kW|W|MVAr|Mvar|kvar|var|MVA|kVA|VA)\b')

def compute(payload):
    if set(payload)!={'value','from_unit','to_unit','claim_id'}:raise ValueError('unit_conversion.input: exact declared fields required')
    value=payload['value'];a,b=payload['from_unit'],payload['to_unit']
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('unit_conversion.value: finite scalar required')
    if a not in PAIRS or b not in PAIRS or PAIRS[a][0]!=PAIRS[b][0]:raise ValueError('unit_conversion.units: known same-dimension units required')
    if type(payload['claim_id']) is not str:raise ValueError('unit_conversion.claim_id: program claim binding required')
    converted=value*PAIRS[a][1]/PAIRS[b][1]
    if not math.isfinite(converted):raise ValueError('unit_conversion.output: finite result required')
    return {'input':dict(payload),'output_value':converted,'output_unit':b,'quantity_kind':PAIRS[a][0],
        'scope':'scalar SI conversion only; user data unverified; no stability, equipment suitability or simulation result',
        'rule_source':'SI prefix scale whitelist in tools/unit_conversion.py; program rule, not an electrical operating standard'}

class UnitConversionTool:
    spec=ToolSpec('scalar_unit_conversion',VERSION,'Whitelist scalar SI conversion',{}, {},('evidence_verification','power_domain_review'))
    def __init__(self, *, version=VERSION):
        if version not in (VERSION,'scalar-si-conversion-v2'):raise ValueError('Unknown scalar conversion version')
        self.spec=ToolSpec('scalar_unit_conversion',version,'Whitelist scalar SI conversion',{}, {},('evidence_verification','power_domain_review'))
    async def execute(self,request):
        try:
            if request.tool_name!=self.spec.name or request.caller_role not in self.spec.allowed_agent_roles:raise ValueError('unit_conversion.caller: unauthorized tool/role')
            value=compute_versioned(request.payload,self.spec.version)
            rid='unit-result-'+hashlib.sha256(json.dumps((request.call_id,value),sort_keys=True).encode()).hexdigest()[:24]
            return ToolResult(rid,request.call_id,self.spec.name,self.spec.version,ExecutionStatus.SUCCEEDED,value)
        except ValueError as exc:
            return ToolResult('unit-failed-'+request.call_id,request.call_id,self.spec.name,self.spec.version,ExecutionStatus.FAILED,dict(request.payload),
                ExecutionIssue(self.spec.name,ExecutionStatus.FAILED,'UNIT_INPUT_ERROR',str(exc)))

def compute_versioned(payload,version):
    if version==VERSION:return compute(payload)
    if version!='scalar-si-conversion-v2':raise ValueError('unit result version mismatch')
    from tools.scalar_numbers import parse_number
    if set(payload)!={'value','from_unit','to_unit','claim_id','numeric_trace'}:raise ValueError('unit_conversion.input: exact v2 fields required')
    trace=payload['numeric_trace']
    if type(trace) is not dict or trace!=parse_number(trace.get('raw')) or trace['value']!=payload['value']:
        raise ValueError('unit_conversion.numeric_trace: normalization/input mismatch')
    value=compute({k:v for k,v in payload.items() if k!='numeric_trace'})
    value['input']=dict(payload)
    value['numeric_trace']=dict(trace)
    return value

def validate_result(result):
    if result.tool_name!='scalar_unit_conversion' or result.tool_version not in (VERSION,'scalar-si-conversion-v2'):raise ValueError('unit result version mismatch')
    if result.status==ExecutionStatus.SUCCEEDED:
        if result.issue is not None or result.payload!=compute_versioned(result.payload['input'],result.tool_version):raise ValueError('unit result payload changed')
        expected='unit-result-'+hashlib.sha256(json.dumps((result.call_id,result.payload),sort_keys=True).encode()).hexdigest()[:24]
        if result.result_id!=expected:raise ValueError('unit result ID mismatch')
    elif result.issue is None:raise ValueError('failed unit result needs execution issue')

def requests_for(claims, *, version=VERSION):
    if version=='scalar-si-conversion-v2':
        from tools.scalar_numbers import quantities
        requests=[]
        for claim in claims:
            try:items=quantities(claim.proposition or claim.text,PAIRS)
            except ValueError:
                # Execute an explicitly invalid request so the existing Harness
                # retains a real tool failure/trace instead of aborting peers.
                requests.append({'value':0.,'from_unit':'V','to_unit':'V','claim_id':claim.claim_id,
                    'numeric_trace':{'raw':claim.proposition or claim.text,'normalized':None,'value':None,'number_format':'ascii-decimal-us-grouping-v1'}})
                continue
            for item in items:
                unit=item['unit'];kind=PAIRS[unit][0]
                trace={k:item[k] for k in ('raw','normalized','value','number_format')}
                payload={'value':item['value'],'from_unit':unit,'to_unit':{'voltage':'V','active_power':'W','reactive_power':'var','apparent_power':'VA'}[kind],
                         'claim_id':claim.claim_id,'numeric_trace':trace}
                if payload not in requests:requests.append(payload)
        return tuple(requests)
    if version!=VERSION:raise ValueError('Unknown scalar conversion version')
    requests=[]
    for claim in claims:
        matches=list(PATTERN.finditer(claim.proposition or claim.text))
        for m in matches:
            unit=m.group(2)
            if unit not in PAIRS:continue
            kind=PAIRS[unit][0];base={'voltage':'V','active_power':'W','reactive_power':'var','apparent_power':'VA'}[kind]
            # Explicit scalar conversion only; never convert MW to Mvar.
            item={'value':float(m.group(1)),'from_unit':unit,'to_unit':base,'claim_id':claim.claim_id}
            if item not in requests:requests.append(item)
    return tuple(requests)

def validate_claim_conversion(proposition,claim_id,result,status,path='$.calculation_result_reference'):
    from core.validation import require
    from core.models import VerificationStatus
    # Closed mathematical grammar, not polarity detection on arbitrary sentences.
    grammar=r'\s*(\d+(?:\.\d+)?)\s*(kV|V|MW|kW|W|MVAr|Mvar|kvar|var|MVA|kVA|VA)\s*(=|equals|is equal to|does not equal|is not equal to)\s*(\d+(?:\.\d+)?)\s*(kV|V|MW|kW|W|MVAr|Mvar|kvar|var|MVA|kVA|VA)\s*[.]?\s*'
    if result.tool_version=='scalar-si-conversion-v2':
        from tools.scalar_numbers import NUMBER,parse_number
        grammar=grammar.replace(r'\d+(?:\.\d+)?',NUMBER)
    match=re.fullmatch(grammar,proposition,re.I)
    require(match is not None,'calculation can support only complete whitelisted scalar equality proposition',path=path)
    a,unit,relation,b,target=match.groups();p=result.payload['input']
    numeric=lambda s:parse_number(s)['value'] if result.tool_version=='scalar-si-conversion-v2' else float(s)
    require(p['claim_id']==claim_id and numeric(a)==p['value'] and unit==p['from_unit'],'calculation claim/input binding mismatch',path=path)
    require(target in PAIRS and PAIRS[target][0]==result.payload['quantity_kind'],'target dimension mismatch',path=path)
    equal=math.isclose(result.payload['output_value']*PAIRS[result.payload['output_unit']][1],numeric(b)*PAIRS[target][1],rel_tol=1e-12)
    truth=(not equal) if relation.lower() in ('does not equal','is not equal to') else equal
    require(status==(VerificationStatus.SUPPORTED if truth else VerificationStatus.CONTRADICTED),'calculation relationship disagrees with exact computed equality',path=path)
