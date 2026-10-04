"""Offline source-anchored additions; reuse the frozen support dataset pipeline.

No downloader, model caller or production configuration mutation lives here.
Manifests and curated family plans contain private source text, outside Git.
"""
import argparse
from contextlib import closing
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import hashlib
import sqlite3
from urllib.parse import urlsplit

from evaluation.support_dataset import (make_sample, deduplicate, group,
    export_review, digest, normalized, read, write, LABELS)
from rag.storage import KnowledgeStore, SourceMetadata

VERSION = 'source-anchored-support-expansion-v1'


def ingest_sources(base, destination, manifest, role):
    """Copy immutable history, then add only the chosen source partition."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError('destination already exists; never overwrite a snapshot')
    selected = [s for s in manifest['sources'] if s['role'] == role]
    ids = [s['document_id'] for s in manifest['sources']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate document ID')
    for s in selected:
        u = urlsplit(s['metadata']['source_uri'])
        if u.scheme != 'https' or not u.hostname or u.username or u.password:
            raise ValueError('public HTTPS provenance required')
        if hashlib.sha256(Path(s['file']).read_bytes()).hexdigest() != s['sha256']:
            raise ValueError('acquired file hash mismatch')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(Path(base).resolve().as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
    results, failures = [], []
    with KnowledgeStore(destination) as store:
        old = store.latest()
        before = [(r['fragment_id'], digest(store.evidence(r['fragment_id'], old).text))
                  for r in store.rows(old)]
        for s in selected:
            try:
                metadata = dict(s['metadata'])
                metadata['applicability'] = tuple(metadata.get('applicability', []))
                results.append(asdict(store.ingest(s['file'], s['document_id'], SourceMetadata(**metadata))))
            except Exception as exc:
                failures.append({'document_id': s['document_id'], 'error_type': type(exc).__name__,
                                 'reason': str(exc)})
        after = [(r['fragment_id'], digest(store.evidence(r['fragment_id'], old).text))
                 for r in store.rows(old)]
        if before != after:
            raise ValueError('old snapshot changed')
        return {'version': VERSION, 'role': role, 'old_knowledge_version': old,
                'knowledge_version': store.latest(), 'results': results, 'failures': failures,
                'old_snapshot_verified_fragments': len(before), 'old_snapshot_unchanged': True}


def build(store, knowledge_version, manifest, families):
    roles = {s['document_id']: s['role'] for s in manifest['sources']}
    if len(roles) != len(manifest['sources']):
        raise ValueError('duplicate source role assignment')
    rows = store.rows(knowledge_version)
    samples, failures = [], []
    family_ids = [f['family_id'] for f in families]
    if len(family_ids) != len(set(family_ids)):
        raise ValueError('duplicate family ID')
    for family in families:
        try:
            if roles.get(family['document_id']) != 'development':
                raise ValueError('reserved/unregistered document cannot generate training candidates')
            anchor = family['anchor_text']
            if not anchor.strip():
                raise ValueError('empty anchor')
            candidates = []
            for row in rows:
                if row['document_id'] != family['document_id']:
                    continue
                e = store.evidence(row['fragment_id'], knowledge_version)
                if getattr(e.provenance, 'file_page', None) == family.get('file_page') and anchor in e.text:
                    candidates.append(e)
            if len(candidates) != 1:
                raise ValueError('anchor must match exactly one immutable page/fragment')
            e = candidates[0]
            if e.text.count(anchor) != 1:
                raise ValueError('ambiguous anchor within fragment')
            if ' '.join(family['base_proposition'].split()) != ' '.join(anchor.split()):
                raise ValueError('base proposition must faithfully reproduce its literal anchor')
            start = e.provenance.start_offset + e.text.index(anchor)
            metadata = asdict(e)
            metadata.pop('text')
            quoted = {'basis_id': 'q-source', 'evidence_id': e.evidence_id,
                      'text': anchor, 'text_sha256': digest(anchor), 'start_offset': start,
                      'end_offset': start + len(anchor), 'warnings': list(e.provenance.quality_warnings),
                      'metadata': metadata}
            local = []
            edits = [{'proposition': family['base_proposition'], 'operation': 'literal_source_statement',
                      'suggestion': 'supported', 'reason': '与已回查原文逐字对应，仍待用户确认适用范围与标签。'}] + family['variants']
            for edit in edits:
                if edit['suggestion'] not in LABELS or not edit['reason'].strip():
                    raise ValueError('explicit suggestion and reasoning required')
                prop = edit['proposition']
                task = {'task_type': edit.get('task_type', family.get('task_type', 'factual_support')),
                        'claim': {'text': prop, 'proposition': prop,
                                  'assertion_role': 'asserted_synthetic_variant',
                                  'qualifiers': family.get('qualifiers', []), 'category': family['family_id'],
                                  'basis_target': 'literature', 'scope': list(e.applicability)},
                        'answer_excerpt': prop, 'evidence': [quoted], 'other_basis': [],
                        'knowledge_version': knowledge_version, 'delivery_state': 'curated_exact_anchor_delivered',
                        'required_evidence_delivery': 'exact_source_quote_only_not_a_production_retrieval_test'}
                origin = {'run_id': None, 'answer_id': 'constructed-' + family['family_id'],
                          'answer_version': 1, 'claim_id': 'claim-' + family['family_id'],
                          'component_id': 'component-1', 'question_family': family['family_id'],
                          'lineage_root_sha256': digest(family['family_id'] + family['base_proposition']),
                          'source_document_id': e.source_id, 'source_document_version': e.source_version,
                          'request_sha256': None, 'response_sha256': None,
                          'source_method': 'curated_literal_anchor_no_model_request'}
                if local:
                    origin['parent_sample_id'] = local[0]['sample_id']
                sample = make_sample(task, origin, {'structure_valid': True, 'model_status': None,
                    'model_rationale': None, 'program_validation': None, 'human_feedback': [],
                    'source_anchor_verified': True, 'pdf_visual_semantics_verified': False}, synthetic=True,
                    recipe={'method': VERSION, 'operation': edit['operation'],
                            'before': family['base_proposition'], 'after': prop}, suggestion=edit['suggestion'])
                sample['supervision']['rationale'] = edit['reason']
                local.append(sample)
            samples.extend(local)  # atomic family: invalid sibling cannot silently disappear
        except Exception as exc:
            failures.append({'family_id': family['family_id'], 'error_type': type(exc).__name__, 'reason': str(exc)})
    unique = deduplicate(samples)
    grouping = group(unique)
    grouping['scope'] = 'new constructed developer cohort; within-document preliminary split, not independent gold'
    for name, key in (('shared_evidence_ids_across_splits', 'evidence_id'),
                      ('shared_documents_across_splits', 'source_id')):
        exposures = {}
        for sample in unique:
            for quote in sample['task']['evidence']:
                identity = quote.get(key) if key == 'evidence_id' else quote['metadata'][key]
                exposures.setdefault(identity, set()).add(sample['split'])
        grouping[name] = {key: sorted(value) for key, value in exposures.items() if len(value) > 1}
    return unique, {'version': VERSION, 'raw_count': len(samples), 'deduplicated_count': len(unique),
                    'family_count': len({o['question_family'] for s in unique for o in s['origins']}),
                    'pending_count': sum(s['supervision']['status'] == 'pending' for s in unique),
                    'suggestion_distribution': dict(Counter(s['supervision']['suggestion_label'] for s in unique)),
                    'task_distribution': dict(Counter(s['task']['task_type'] for s in unique)),
                    'grouping': grouping, 'failures': failures}


def seed_overlap(samples, seed):
    """Report cross-version exposure without changing either frozen partition."""
    pairs = []
    for a in samples:
        ta = set(normalized(a['task']['claim']['proposition']).split())
        for b in seed:
            tb = set(normalized(b['task']['claim']['proposition']).split())
            if ta and tb and len(ta & tb) / len(ta | tb) >= .9:
                pairs.append({'new_sample_id': a['sample_id'], 'seed_sample_id': b['sample_id'],
                              'seed_split': b['split'], 'new_split': a['split']})
    old_quotes = {e['text_sha256'] for s in seed for e in s['task']['evidence']}
    return {'near_duplicate_pairs': pairs,
            'shared_exact_quote_sha256': sorted({e['text_sha256'] for s in samples for e in s['task']['evidence']} & old_quotes),
            'warning': 'Shared documents/concepts can still leak; no independent test claim. Keep seeds frozen.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('ingest')
    for arg in ('base', 'destination', 'manifest', 'role', 'report'):
        ingest.add_argument('--' + arg, required=True)
    prepare = commands.add_parser('prepare')
    for arg in ('database', 'knowledge-version', 'manifest', 'families', 'output', 'seed'):
        prepare.add_argument('--' + arg, required=True)
    args = parser.parse_args()
    manifest = read(args.manifest)
    if args.command == 'ingest':
        write(args.report, ingest_sources(args.base, args.destination, manifest, args.role))
    else:
        output = Path(args.output)
        if output.exists():
            raise ValueError('new output version required')
        output.mkdir(parents=True)
        with KnowledgeStore(args.database, readonly=True) as store:
            samples, report = build(store, args.knowledge_version, manifest, read(args.families))
        seed = read(args.seed)
        if isinstance(seed, dict):
            seed = seed['samples']
        report['seed_overlap'] = seed_overlap(samples, seed)
        write(output / 'dataset.json', {'version': VERSION, 'samples': samples, 'report': report})
        export_review(samples, output / 'review')
        write(output / 'report.json', report)


if __name__ == '__main__':
    main()
