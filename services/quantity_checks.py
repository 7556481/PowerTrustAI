"""Conservative, finite grammar checks; not a language or engineering oracle."""
import re
from core.models import ConsistencyCheck

VERSION = "quantity-enumeration-v1.1"
NUMBERS = dict(zip("one two three four five six seven eight nine ten".split(), range(1,11)))
NUMBERS.update(dict(zip("一二三四五六七八九十",range(1,11))))
COUNT = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:(?:equipment|different|types of|classes of)\s+)*ratings?\b|([一二三四五六七八九十\d]+)\s*(?:类|种|个)?额定值",re.I)
LIST = re.compile(r"(?:dependent on|depend on|depends on|include|includes|consist of|consists of|are:|ratings?:)\s*([^.;]*(?:))",re.I)


def enumeration_check(proposition, candidates, claim_id=None, *, version=VERSION, assertion_role='legacy_unspecified', source_text=''):
    if assertion_role!='legacy_unspecified' and version==VERSION:version='quantity-enumeration-v1.2'
    if version not in ("quantity-enumeration-v1","quantity-enumeration-v1.1","quantity-enumeration-v1.2","quantity-enumeration-v1.3"):raise ValueError("Unknown enumeration method version")
    matches=list(COUNT.finditer(proposition))
    def result(status,code,reason,**kwargs):
        return ConsistencyCheck("enumeration-"+(claim_id or "input"),status,version,code,reason,claim_id,**kwargs)
    if not matches:
        return result("not_applicable","no_recognized_rating_count","No explicit rating-category count in the supported grammar; other quantities were not checked.")
    if len(matches)!=1:
        return result("incomplete","ambiguous_count","Multiple rating counts; no reliable single enumeration comparison.")
    if version=='quantity-enumeration-v1.3':
        from services.claim_obligations import direct_rating_declaration
        if not direct_rating_declaration(proposition):
            return result('incomplete','count_context_requires_review','Count occurs outside a closed positive declaration grammar; reporting/negation/nested context is not mechanically established. Model stance alone does not prove endorsement.')
    if version=='quantity-enumeration-v1.2':
        attributed=bool(re.match(r'^\s*The (?:synthetic )?proposal (?:claims|states)\b',proposition,re.I))
        if assertion_role in ('input_report','reported_error') and attributed:
            return result('not_applicable','reported_input_not_endorsement','Recognized input-attribution grammar and model role agree; this does not assert the reported count is correct.')
        if assertion_role not in ('asserted','conditional') or attributed:
            return result('incomplete','count_context_requires_review','Role/context do not establish an endorsed category count; no polarity shortcut used.')
    if version not in ("quantity-enumeration-v1","quantity-enumeration-v1.3") and re.search(r"\b(?:not|no|never|paraphrase|phrasing|wording|quoted)\b|并非|不是|并不|措辞|改写",proposition,re.I):
        return result("incomplete","count_assertion_polarity_or_attribution_unclear","Negated or reported wording is not a positive count assertion; do not report an answer count mismatch.")
    word=(matches[0].group(1) or matches[0].group(2)).lower()
    count=int(word) if word.isdigit() else NUMBERS.get(word)
    if count is None:return result("incomplete","unparsed_count","Count outside supported finite grammar.")
    lists={}
    for c in candidates:
        # Normalization is local to this parser, never written into evidence.
        for match in LIST.finditer(c.text):
            raw=match.group(1)
            parts=[p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+",raw) if p.strip()]
            if len(parts)<2 or len(parts)>10:continue
            rating_items=[p for p in parts if re.search(r"\bratings?\b",p,re.I)]
            if len(rating_items)<2 or any(len(p)>100 for p in parts):continue
            if any(re.search(r"\bor\b|\betc\b|\bincluding\b",p,re.I) for p in parts):continue
            if any(re.search(r"\bratings?\b",p,re.I) and not re.search(r"\bratings?\s*$",p,re.I) for p in parts):continue
            normalized=tuple(re.sub(r"\s+"," ",p).lower().removeprefix("the ") for p in rating_items)
            if len(set(normalized))!=len(normalized):continue
            lists.setdefault(normalized,[]).append(c.quote_id)
    if len(lists)!=1:
        return result("incomplete","no_unique_complete_enumeration","No unique fully enumerated rating categories; do not infer from shared labels or prose.",expected_count=count)
    items,ids=next(iter(lists.items()));observed=len(items)
    return result("warning" if count!=observed else "completed","rating_count_mismatch" if count!=observed else "rating_count_consistent",
        f"Explicit count {count}; source names {observed} rating categories. Items without a rating label, including power output, are not automatically rating categories.",
        basis_quote_ids=tuple(dict.fromkeys(ids)),expected_count=count,observed_count=observed,observed_items=items)


def check_verification_quantities(output, *, version=VERSION):
    if version=='quantity-enumeration-v1.2' and output.prompt_version in ('evidence-verification-v9.3-target-fidelity','evidence-verification-v9.4-standalone-templates'):version='quantity-enumeration-v1.3'
    catalog={c.quote_id:c for c in output.quote_candidates};claims={c.claim_id:c for c in output.claims}
    return tuple(enumeration_check(claims[f.claim_id].proposition or claims[f.claim_id].text,
        tuple(catalog[b.quote_id] for b in f.bases if b.type=="text_excerpt" and b.quote_id in catalog),f.claim_id,version=version,
        assertion_role=claims[f.claim_id].assertion_role if version=='quantity-enumeration-v1.2' else 'legacy_unspecified',source_text=claims[f.claim_id].text) for f in output.findings)


UNITS = {"voltage":{"V":1.,"kV":1000.},"active_power":{"W":1.,"kW":1000.,"MW":1000000.},
         "reactive_power":{"var":1.,"kvar":1000.,"Mvar":1000000.,"MVAr":1000000.,"kVAr":1000.},"apparent_power":{"VA":1.,"kVA":1000.,"MVA":1000000.}}


def check_input_units(context):
    import math
    if context is None or not context.quantities:
        return (ConsistencyCheck("units-input","incomplete","dimensional-input-v1","no_structured_quantities","No structured quantities; this is not a completed free-text unit audit."),)
    checks=[];values={}
    for q in context.quantities:
        if q.kind not in UNITS or q.unit not in UNITS[q.kind] or not math.isfinite(q.value):
            checks.append(ConsistencyCheck("units-"+q.quantity_id,"warning" if any(q.unit in units for units in UNITS.values()) else "incomplete",
                "dimensional-input-v1","dimension_mismatch_or_unknown_unit","Expected dimensional unit for "+q.kind+"; received "+q.unit+". No per-unit base or unrecognized unit is inferred."))
            continue
        normalized=q.value*UNITS[q.kind][q.unit];key=(q.kind,q.reference)
        mismatch=key in values and not math.isclose(values[key],normalized,rel_tol=1e-9,abs_tol=1e-9)
        checks.append(ConsistencyCheck("units-"+q.quantity_id,"warning" if mismatch else "completed","dimensional-input-v1",
            "same_reference_value_mismatch" if mismatch else "known_dimension_and_scale","Same-reference quantities compared in SI scale; no operating acceptability was computed."))
        values[key]=normalized
    return tuple(checks)
