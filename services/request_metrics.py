"""Count actual delivered literal data; never estimate tokens or log body text."""
import hashlib
import json


def measure(messages):
    candidates=0;texts=[];scope_ids=[]
    transport_count=0
    def walk(value):
        nonlocal candidates
        if type(value) is dict:
            if type(value.get("QUOTE_CANDIDATES")) is list:candidates+=len(value["QUOTE_CANDIDATES"])
            if type(value.get("scope_id")) is str:scope_ids.append(value["scope_id"])
            if type(value.get("evidence_id")) is str and type(value.get("text")) is str:texts.append(value["text"])
            for key,item in value.items():
                if key=="context_text" and type(item) is str:texts.append(item)
                elif key=="answer_requirements" and type(item) is list:
                    for s in item:
                        if type(s) is str:
                            try:walk(json.loads(s))
                            except (ValueError,TypeError):pass
                else:walk(item)
        elif type(value) in (list,tuple):
            for item in value:walk(item)
    for message in messages:
        try:
            value=json.loads(message.content)
            if type(value) is dict and value.get('TRANSPORT_VERSION')=='review-lossless-shared-values-v1':
                from services.review_transport import expand
                expanded=expand(value)
                # Measure semantic coverage after exact expansion, then actual
                # literal repetitions on the compact wire below.
                before=len(texts);walk(expanded);semantic=set(texts[before:]);del texts[before:]
                def literals(item):
                    if type(item) is str and item in semantic:texts.append(item)
                    elif type(item) is dict:
                        for child in item.values():literals(child)
                    elif type(item) is list:
                        for child in item:literals(child)
                literals(value);transport_count+=1
            else:walk(value)
        except (ValueError,TypeError):pass
    unique={hashlib.sha256(t.encode()).hexdigest():t for t in texts}
    return {"method":"literal-delivered-json-fields-v1","candidate_count":candidates,
        "evidence_chars_delivered":sum(len(t) for t in texts),"evidence_chars_unique":sum(len(t) for t in unique.values()),
        "message_chars":sum(len(m.content) for m in messages),"scope_ids":sorted(set(scope_ids)),
        **({'lossless_transport_messages':transport_count} if transport_count else {})}
