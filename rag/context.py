"""Read bounded, independently traceable neighbors; never score them as hits."""
from core.validation import ContractError, InputError, validate_types
from rag.contracts import ContextEvidence, ContextLink, ContextOptions, ContextResult


def read_adjacent_context(store, core_evidence, knowledge_version, options=ContextOptions()):
    validate_types(options, ContextOptions)
    if options.max_chars < 0 or options.max_fragments < 0 or not 0 <= options.depth <= 4:
        raise InputError("Context budgets must be nonnegative and depth must be in [0,4]")
    if options.priority not in ("storage_order", "cross_page_next_first"):
        raise InputError("Unknown context priority")
    roots = {}
    for core in core_evidence:
        core = store.verify_evidence(core)
        if core.provenance.knowledge_version != knowledge_version:
            raise ContractError("Context core snapshot mismatch")
        roots.setdefault(core.evidence_id, core)
    core_fragments = {core.provenance.fragment_id for core in roots.values()}
    candidates, omitted = {}, []
    # Each hop stays within a document version; reading order is storage order,
    # not a statement that the next fragment semantically completes the sentence.
    for distance in range(1, options.depth + 1):
        for core in roots.values():
            for direction in ("previous", "next"):
                current = core
                for hop in range(distance):
                    fid = getattr(current.provenance, direction + "_fragment_id")
                    if fid is None:
                        break
                    neighbor = store.evidence(fid, knowledge_version)
                    p, root = neighbor.provenance, core.provenance
                    if (p.document_id, p.document_version) != (root.document_id, root.document_version):
                        raise ContractError("Context crossed document/version boundary")
                    if not options.allow_cross_page and p.file_page != root.file_page:
                        break
                    current = neighbor
                else:
                    if fid in core_fragments:
                        continue
                    link = ContextLink(core.evidence_id, direction, distance, current.provenance.file_page != core.provenance.file_page)
                    if fid not in candidates:
                        candidates[fid] = [current, []]
                    if link not in candidates[fid][1]:
                        candidates[fid][1].append(link)
    selected, chars = [], 0
    ordered = list(candidates.items())
    if options.priority == "cross_page_next_first":
        # Only reorder existing mechanical neighbors before the same whole-fragment
        # budget. Adjacency is not semantic continuation or factual support.
        ordered.sort(key=lambda item: not any(link.crosses_page and link.direction == "next" for link in item[1][1]))
    for fid, (evidence, links) in ordered:
        length = len(evidence.text)
        if len(selected) >= options.max_fragments:
            omitted.append("fragment_limit:" + fid)
        elif chars + length > options.max_chars:
            omitted.append("character_limit:" + fid)
        else:
            selected.append(ContextEvidence(evidence, tuple(links)))
            chars += length
    return ContextResult(tuple(selected), chars, options, tuple(omitted))
