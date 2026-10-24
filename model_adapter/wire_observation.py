"""Opt-in, header-free wire observations. No raw HTTP errors or opaque envelopes."""
import hashlib,json


def digest(data):return hashlib.sha256(data).hexdigest()


def request_view(body,path,context):
    value=json.loads(body)
    allowed=('model','messages','max_tokens','stream','thinking','tools','tool_choice','response_format')
    return dict(url='https://api.deepseek.com'+path,method='POST',body_sha256=digest(body),body_bytes=len(body),
        field_sha256={k:digest(json.dumps(value[k],ensure_ascii=False).encode()) for k in allowed if k in value},
        unknown_field_count=len(set(value)-set(allowed)),ssl_check_hostname=context.check_hostname,ssl_verify_mode=int(context.verify_mode),proxy_implementation='http.client direct; environment proxy variables not consumed')


def response_view(status,body):
    from model_adapter.deepseek import safe_http_diagnostic
    result=dict(http_status=status,body_sha256=digest(body),body_bytes=len(body))
    if status!=200:
        result['diagnostic']=safe_http_diagnostic(status,body);return result
    try:
        from services.structured_model import strict_json
        data=strict_json(body.decode('utf-8'));choices=data.get('choices')
        if type(choices) is not list or len(choices)!=1:raise ValueError()
        choice=choices[0];msg=choice['message'];calls=msg.get('tool_calls');kept=[]
        if type(calls) is list:
            for call in calls:
                fn=call.get('function') if type(call) is dict else None
                scalar=lambda x:x if type(x) is str else None
                kept.append(dict(id=scalar(call.get('id')) if type(call) is dict else None,type=scalar(call.get('type')) if type(call) is dict else None,function={k:scalar(fn.get(k)) for k in ('name','arguments')} if type(fn) is dict else None))
        result.update(model_id=data.get('model') if type(data.get('model')) is str else None,finish_reason=choice.get('finish_reason') if type(choice.get('finish_reason')) is str else None,
            content=msg.get('content') if type(msg.get('content')) is str else None,tool_calls=kept if type(calls) is list else None)
        usage=data.get('usage');result['usage']={k:usage.get(k) for k in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens') if type(usage.get(k)) is int and usage[k]>=0} if type(usage) is dict else None
    except Exception:
        result['diagnostic_gap']='Unidentifiable HTTP200 envelope withheld; no parameter text reconstructed.'
    return result
