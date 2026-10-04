"""Count actual delivered literal data; never estimate tokens or log body text."""
import hashlib
import json


def measure(messages):
    candidates=0;texts=[];scope_ids=[]
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
        try:walk(json.loads(message.content))
        except (ValueError,TypeError):pass
    unique={hashlib.sha256(t.encode()).hexdigest():t for t in texts}
    return {"method":"literal-delivered-json-fields-v1","candidate_count":candidates,
        "evidence_chars_delivered":sum(len(t) for t in texts),"evidence_chars_unique":sum(len(t) for t in unique.values()),
        "message_chars":sum(len(m.content) for m in messages),"scope_ids":sorted(set(scope_ids))}
