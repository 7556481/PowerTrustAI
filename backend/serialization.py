"""Versioned JSON data; safe API projection excludes private archive paths."""
from dataclasses import fields,is_dataclass
from enum import Enum
from pathlib import Path
import json
import re
import hashlib
import ipaddress
from urllib.parse import urlsplit, parse_qsl

SCHEMA_VERSION='local-review-service-v1'

def wire(value):
    if is_dataclass(value):return {f.name:wire(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,Enum):return value.value
    if isinstance(value,(tuple,list)):return [wire(x) for x in value]
    if isinstance(value,dict):return {k:wire(v) for k,v in value.items()}
    if isinstance(value,Path):return str(value)
    if value is None or type(value) in (str,int,float,bool):return value
    raise TypeError('Unsupported JSON value')

def dumps(value):return json.dumps(wire(value),ensure_ascii=False,allow_nan=False,separators=(',',':'))

PRIVATE={'diagnostic_path','candidate_catalog_path','input_snapshot_path','request_messages_path',
         'authorization','api_key','credential','credentials','headers','request_headers','access_token','token','password','secret'}
LITERAL={'text','question','user_context','proposition','quote','semantic_qualifiers'}

def public_https(value):
    """Projection only: never fetch sources, and never forward credentials."""
    if not isinstance(value,str) or any(c.isspace() or ord(c)<32 for c in value) or '\\' in value:return None
    try:
        u=urlsplit(value)
        if u.scheme!='https' or not u.hostname or u.username is not None or u.password is not None or u.fragment:return None
        if u.port not in (None,443):return None
        host=u.hostname.lower()
        if '.' not in host or host.endswith(('.localhost','.local','.internal')):return None
        try:
            if not ipaddress.ip_address(host).is_global:return None
        except ValueError:pass
        if any(k.lower() in PRIVATE or any(s in k.lower() for s in ('token','secret','password','credential','api_key')) for k,_ in parse_qsl(u.query)):return None
        return value
    except ValueError:return None

def local_path(value):
    return bool(re.search(r'(?<![A-Za-z0-9:/])[A-Za-z]:[\\/]',value)) or value.startswith(('/', '\\\\'))

def safe(value,key=''):
    if isinstance(value,dict):
        result={}
        for k,v in value.items():
            if k.lower() in PRIVATE or k.lower().endswith(('_token','_password','_secret','_api_key')):
                if v and k.endswith('_path'):result[k.removesuffix('_path')+'_ref']='archive-'+hashlib.sha256(str(v).encode()).hexdigest()[:24]
                continue
            result[k]=safe(v,k)
        return result
    if isinstance(value,list):return [safe(x,key) for x in value]
    if isinstance(value,str) and key not in LITERAL:
        if key.lower().endswith(('_uri','_url')) or key.lower() in ('uri','url'):return public_https(value)
        if key=='detail':
            try:return safe(json.loads(value))
            except (ValueError,TypeError):pass
        # URI fields are interpreted structurally; diagnostics with embedded local
        # paths are withheld as a whole instead of rewriting arbitrary substrings.
        if (key.endswith('_path') and key!='field_path') or local_path(value):return '[local-path-hidden]'
    return value

