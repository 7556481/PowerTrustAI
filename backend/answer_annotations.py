"""Read-only, code-point indexed review locations. Never changes stored judgments."""

VERSION = 'answer-inline-review-v1'


def identity(obj, answer):
    return (bool(answer.get('answer_id')) and type(answer.get('version')) is int
            and obj.get('answer_id') == answer['answer_id']
            and type(obj.get('answer_version')) is int
            and obj['answer_version'] == answer['version'])


def locate(answer, binding):
    """Explicit invalid offsets never fall back to text search."""
    if not identity(binding, answer):
        return None, '缺少或不符的回答版本绑定'
    text = answer.get('text')
    original = binding.get('text')
    if not isinstance(text, str) or not isinstance(original, str) or not original:
        return None, '缺少逐字原文；不能使用改述主张定位'
    start, end = binding.get('start_offset'), binding.get('end_offset')
    if 'start_offset' in binding or 'end_offset' in binding:
        if (type(start) is int and type(end) is int and 0 <= start < end <= len(text)
                and text[start:end] == original):
            return (start, end, original, 'saved_offset'), None
        return None, '原文区间或逐字核验不符'
    start = text.find(original)
    if start < 0 or text.find(original, start + 1) >= 0:
        return None, '逐字原文不存在或重复出现，不能唯一定位'
    return (start, start + len(original), original, 'unique_literal'), None


def project(result):
    answer = (result.get('answer') or {}).get('final') or {}
    ex = result.get('execution') or {}
    extraction = (result.get('snapshots') or {}).get('extraction') or {}
    findings = result.get('findings') or {}
    verification = (result.get('review_bindings') or {}).get('verification') or {}
    current_round = None
    # Older API snapshots may carry the same immutable identity through a full round.
    for round_ in result.get('review_rounds', []):
        a = round_.get('answer') or {}
        if (a.get('answer_id'), a.get('version'), a.get('text')) == (answer.get('answer_id'), answer.get('version'), answer.get('text')):
            current_round = round_
            if not verification:
                verification = round_.get('verification') or {}
    if not extraction and current_round and identity(current_round.get('verification') or {}, answer):
        # Legacy extractors persist Claim objects in the same version's verification.
        saved = current_round['verification']
        extraction = dict(answer_id=saved['answer_id'], answer_version=saved['answer_version'], claims=saved.get('claims') or [])
    rows = extraction.get('claims', [])
    claims = {c.get('claim_id'): c for c in rows if c.get('claim_id') and sum(x.get('claim_id') == c.get('claim_id') for x in rows) == 1}
    ready = (ex.get('status') == 'finished' and ex.get('required_stages_complete') is True
             and not result.get('no_substantive_answer'))
    opinions = []

    def add(origin, f, binding, *, status=None, key=None, reason=None, problem=None):
        status = status or f.get('status') or f.get('check_status') or 'concern'
        row = dict(opinion_id=f'{origin}:{key if key is not None else len(opinions)}',
                   origin=origin, finding_id=f.get('finding_id'), status=status,
                   reason=reason or f.get('rationale') or f.get('reason') or '具体原因未提供',
                   evidence_ids=list(f.get('evidence_ids') or []),
                   answer_id=binding.get('answer_id'), answer_version=binding.get('answer_version'))
        span, failure = locate(answer, binding)
        if span and not problem:
            row.update(start=span[0], end=span[1], original_text=span[2], location_method=span[3])
        else:
            row['location_failure'] = problem or failure
        row['located'] = bool(span and not problem)
        opinions.append(row)

    for i, f in enumerate(findings.get('model_fact', [])):
        if f.get('status') == 'supported':
            continue
        c = claims.get(f.get('claim_id')) or {}
        problem = None
        if verification and not identity(verification, answer):
            problem = '事实审核版本不符'
        if any(k in extraction for k in ('answer_id', 'answer_version')) and not identity(extraction, answer):
            problem = '提取快照版本不符'
        if any(k in f for k in ('answer_id', 'answer_version')) and not identity(f, answer):
            problem = '发现所属版本不符'
        add('fact', f, c, key=i, problem=problem)
    for i, f in enumerate(findings.get('original_citations', [])):
        if f.get('status') == 'supported':
            continue
        index = f.get('citation_index');citations = answer.get('citations') or []
        citation = citations[index] if type(index) is int and 0 <= index < len(citations) else {}
        start, end = citation.get('start_offset'), citation.get('end_offset')
        binding = dict(answer_id=verification.get('answer_id'), answer_version=verification.get('answer_version'))
        # A citation's exact text is derived only after its saved range is validated.
        if type(start) is int and type(end) is int and 0 <= start < end <= len(answer.get('text') or ''):
            binding.update(text=answer['text'][start:end], start_offset=start, end_offset=end)
        else:
            binding.update(start_offset=start, end_offset=end)
        problem = None
        if any(k in f for k in ('answer_id', 'answer_version')) and not identity(f, answer):
            problem = '引用发现版本不符'
        add('citation', f, binding, key=i, problem=problem)
    for i, f in enumerate(findings.get('domain', [])):
        if (f.get('check_status') not in ('warning', 'not_assessable', 'incomplete', 'failed')
                and f.get('severity') not in ('low', 'medium', 'high', 'critical') and not f.get('missing_prerequisites')):
            continue
        ids = f.get('claim_ids') or []
        if not ids:
            add('domain', f, f, key=i, problem='任务或工程前提意见没有正文锚点')
        for j, cid in enumerate(ids):
            add('domain', f, claims.get(cid) or {}, key=f'{i}:{j}',
                problem=None if identity(f, answer) else '领域发现版本不符')
    for i, f in enumerate(findings.get('program_rules', [])):
        if f.get('status') in ('warning', 'incomplete', 'failed'):
            add('rule', f, {}, key=i, problem='程序检查没有已核验正文锚点')
    valid = sorted((o for o in opinions if o['located']), key=lambda o: (o['start'], o['end'], o['opinion_id']))
    regions = []
    for o in valid:
        if not regions or o['start'] >= regions[-1]['end']:
            regions.append(dict(start=o['start'], end=o['end'], opinion_ids=[o['opinion_id']]))
        else:
            regions[-1]['end'] = max(regions[-1]['end'], o['end'])
            regions[-1]['opinion_ids'].append(o['opinion_id'])
    return dict(version=VERSION, offset_unit='unicode_codepoint', answer_id=answer.get('answer_id'),
                answer_version=answer.get('version'), ready=ready, opinions=opinions,
                regions=regions if ready else [], located_region_count=len(regions) if ready else 0,
                unlocated_count=sum(not o['located'] for o in opinions))
