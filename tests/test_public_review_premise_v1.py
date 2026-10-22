"""New synthetic tasks and scripted model outputs, no historical experiment replay."""
import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
import json
import socket
import unittest
from unittest.mock import patch

from agents.generation import EvidenceGenerationAgent
from agents.premise_verification_v1 import PremiseVerificationAgent
from agents.power_domain_review import ModelPowerDomainReviewAgent
from agents.fakes import FakeRevisionAgent
from agents.contracts import ReliabilityVerificationInput
from core.models import (AnswerDraft, Evidence, PremiseTaskRequest, PremiseDeclaration,
    TaskMode, VerificationStatus, EngineeringContext)
from core.validation import ContractError, validate_review
from harness.runtime import OfflineHarness
from harness.contracts import RunBudget
from harness.product_policy import ProductAuditPolicy
from model_adapter.contracts import ModelResponse, ModelSettings
from services.premise_claim_extractor_v1 import PremiseClaimExtractor
from services.task_premises_v1 import catalog, parse_extraction, PROFILE
from services.review_transport import expand
from tests.test_audit_interface_v2 import warrant

RULE = 'Synthetic rule: if a score of at least 42 is assumed, option O may be omitted.'
TEXTS = ('按题设，分值为42。', '规则为：假定分值至少42时，可以省略O，并非必须省略。', '按该题设与规则，允许省略O，但不强制省略。')


def task(mode=TaskMode.QUESTION_ANSWER, **changes):
    req = PremiseTaskRequest('synthetic-B-marker', mode, 'conceptual', '解释给定规则，并应用题设判断能否省略O。',
        user_context='教学假设：分值为42。', provided_evidence=(Evidence('synthetic-rule', 'synthetic-source', 'v1',
        'teaching paragraph', RULE, 'synthetic_fixture'),), engineering_context=EngineeringContext(),
        premise_declarations=(PremiseDeclaration('user_context', '分值为42。'),))
    return replace(req, **changes)


def extract_wire(payload):
    ids = [p['premise_id'] for p in payload['TASK_PREMISES']]
    claims = []
    for n, anchor in enumerate(payload['ANSWER_ANCHORS']):
        kind = ('premise_restatement', 'literature', 'scenario_application')[min(n, 2)]
        premise = kind == 'premise_restatement'
        claims.append({'anchor_id': anchor['anchor_id'], 'proposition': anchor['text'], 'claim_type': 'mixed',
            'assertion_role': 'assumption' if premise else 'conditional' if kind == 'scenario_application' else 'asserted',
            'semantic_qualifiers': [], 'components': [{'category': 'input_evidence_coverage' if premise else 'technical_fact',
                'proposition': anchor['text'], 'basis_target': 'task_premise' if premise else 'technical_content',
                'verification_obligation': 'input_provided' if premise else 'technical_truth', 'object_kind': kind,
                'premise_ids': ids if kind in ('premise_restatement', 'scenario_application') else []}]})
    return {'claims': claims, 'non_claims': []}


def fact_wire(payload):
    if 'ORIGINAL_CITATION_SCOPES' in payload:
        return {'citation_reviews': [{'citation_index': s['citation_index'], 'status': 'supported', 'rationale': 'Synthetic bounded original citation.',
            'applicability_conditions': [], 'bases': [{'type': 'text_excerpt', 'quote_id': s['QUOTE_CANDIDATES'][0]['quote_id']}],
            'support_relation': warrant(payload, [s['QUOTE_CANDIDATES'][0]['quote_id']])} for s in payload['ORIGINAL_CITATION_SCOPES']]}
    findings = []
    for claim in payload['claims']:
        bases, reviews = [], []
        for i, part in enumerate(claim['components']):
            kind = claim['component_objects'][i]
            selected = []
            if kind != 'premise_restatement':
                selected.append(len(bases))
                bases.append({'type': 'text_excerpt', 'quote_id': payload['QUOTE_CANDIDATES'][0]['quote_id']})
            for pid in claim['component_premise_ids'][i]:
                selected.append(len(bases)); bases.append({'type': 'task_premise_reference', 'premise_id': pid})
            row = {'component_index': i, 'status': 'supported', 'basis_indexes': selected, 'rationale': 'Synthetic classified object checked.',
                'semantic_review': {'fidelity': 'faithful', 'assertion_role': claim['assertion_role'],
                    'verification_obligation': claim['component_obligations'][i], 'rationale': 'Synthetic target and actual answer compared.'}}
            if kind != 'premise_restatement':
                row['support_relation'] = warrant(payload, [bases[k]['quote_id'] for k in selected if bases[k]['type'] == 'text_excerpt'])
            reviews.append(row)
        findings.append({'claim_id': claim['claim_id'], 'rationale': 'Synthetic whole finding.', 'applicability_conditions': [],
                         'bases': bases, 'component_reviews': reviews})
    return {'findings': findings}


class Scripted:
    def __init__(self, *, extraction_change=None, fact_change=None, fail_domain=False, fail_fact=False):
        self.requests = []
        self.extraction_change, self.fact_change = extraction_change, fact_change
        self.fail_domain, self.fail_fact = fail_domain, fail_fact

    async def complete(self, request):
        self.requests.append(request)
        payload = json.loads(request.messages[1].content)
        if 'TRANSPORT_SHARED_VALUES' in payload:
            payload = expand(payload)
        if request.prompt_version.startswith('evidence-bound-generation'):
            wire = {'answer_units': [{'kind': 'technical', 'text': text, 'evidence_ids': ['synthetic-rule'] if n == 1 else []}
                                    for n, text in enumerate(TEXTS)], 'assumptions': ['答案自称分值999，不能登记为题设。'],
                    'missing_information': [], 'evidence_sufficient': True}
        elif request.prompt_version == PROFILE + '-extraction':
            wire = extract_wire(payload)
            if self.extraction_change: self.extraction_change(wire, payload)
        elif request.prompt_version.startswith('evidence-verification-v9.21'):
            if self.fail_fact: return ModelResponse('{bad')
            wire = fact_wire(payload)
            if self.fact_change: self.fact_change(wire, payload)
        else:
            if self.fail_domain: return ModelResponse('{bad')
            wire = {'checks': [{'check_id': k, 'status': 'no_issue', 'claim_ids': [], 'quote_ids': [],
                               'basis_kind': 'engineering_rule', 'rationale': 'Synthetic conceptual, no actual operation.', 'missing_prerequisites': []}
                              for k in payload['MODEL_KEYS']], 'missing_information_review': [],
                    'safety_reviews': [{'claim_id': c['claim_id'], 'verdict': 'not_applicable', 'reason': 'Synthetic nonoperational concept.',
                                       'source_ids': []} for c in payload['claims']]}
            next(x for x in wire['checks'] if x['check_id'] == 'analysis_scope')['task_scope'] = 'conceptual'
        return ModelResponse(json.dumps(wire, ensure_ascii=False), request.model_id, finish_reason='stop')


def harness(adapter, *, path='sequential', observer=None, accounting='invocation_scoped_v1'):
    settings = ModelSettings('synthetic_fixture', max_output_tokens=8000, max_response_chars=96000)
    return OfflineHarness(EvidenceGenerationAgent(adapter, settings, schema_version=3, product_guidance=True),
        PremiseVerificationAgent(adapter, settings, correction_accounting=accounting),
        ModelPowerDomainReviewAgent(adapter, settings, protocol_version=5, safety_review=True, task_applicability=True),
        FakeRevisionAgent(), PremiseClaimExtractor(adapter, settings), policy=ProductAuditPolicy(), execution_path=path, observer=observer)


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        block = patch.object(socket.socket, 'connect', side_effect=AssertionError('offline only'))
        block.start(); self.addCleanup(block.stop)

    async def test_full_harness_both_input_modes_no_fabricated_snapshot(self):
        adapter = Scripted()
        self.assertEqual(harness(adapter).extractor.protocol_version, 7)
        self.assertTrue(harness(adapter).extractor.typed_components)
        generated = await harness(adapter).run(task(), RunBudget(max_revision_rounds=0))
        self.assertFalse(generated.execution_issues)
        self.assertEqual(generated.report.decision.kind.value, 'pass')
        self.assertEqual([f.status.value for f in generated.verification_output.findings], ['supported'] * 3)
        self.assertEqual(len(adapter.requests), 5)
        req = task(TaskMode.ASSESS_EXISTING, existing_answer=generated.answer)
        other = Scripted()
        diagnosed = await harness(other).run(req, RunBudget(max_revision_rounds=0))
        self.assertFalse(diagnosed.execution_issues)
        self.assertEqual(diagnosed.report.decision.kind.value, 'pass')
        self.assertIsNone(diagnosed.verification_output.generation_snapshot)
        self.assertIsNotNone(generated.verification_output.generation_snapshot)
        self.assertEqual(diagnosed.verification_output.task_premises, generated.verification_output.task_premises)
        self.assertEqual(len(other.requests), 4)
        self.assertNotIn('999', str(asdict(generated.verification_output.task_premises[0])))

    async def test_no_premise_or_body_alone_can_support_application(self):
        for drop_type in ('task_premise_reference', 'text_excerpt'):
            def change(wire, payload):
                if 'findings' not in wire: return
                for f, c in zip(wire['findings'], payload['claims']):
                    if c['component_objects'][0] == 'scenario_application':
                        f['bases'] = [b for b in f['bases'] if b['type'] != drop_type]
                        f['component_reviews'][0]['basis_indexes'] = list(range(len(f['bases'])))
            result = await harness(Scripted(fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
            self.assertTrue(result.execution_issues)
            self.assertEqual(result.report.decision.execution_integrity, 'incomplete')
            self.assertEqual(result.verification_output.findings[0].status, VerificationStatus.SUPPORTED)

    async def test_missing_basis_can_be_honest_insufficient_without_execution_failure(self):
        def change(wire, payload):
            for f, c in zip(wire.get('findings', []), payload.get('claims', [])):
                if c['component_objects'][0] == 'scenario_application':
                    f['bases'] = []
                    r = f['component_reviews'][0]
                    r.update(status='insufficient_evidence', basis_indexes=[], rationale='Synthetic required premise/rule unavailable.')
                    r.pop('support_relation', None)
        result = await harness(Scripted(fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        self.assertEqual(result.verification_output.findings[-1].status, VerificationStatus.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.report.decision.kind.value, 'needs_information')

    async def test_legacy_snapshot_cannot_replace_rule_even_with_full_generation_snapshot(self):
        def change(wire, payload):
            for f, c in zip(wire.get('findings', []), payload.get('claims', [])):
                if c['component_objects'][0] == 'literature':
                    f['bases'] = [{'type': 'input_snapshot_reference'}]
                    f['component_reviews'][0].pop('support_relation', None)
        result = await harness(Scripted(fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertEqual(result.verification_output.findings[1].component_reviews[0].origin, 'execution_incomplete')
        self.assertIsNotNone(result.verification_output.generation_snapshot)

    async def test_cross_task_or_forged_premise_reference_is_strictly_rejected(self):
        wrong = catalog(task(task_id='other'))[0].premise_id
        def change(wire, payload):
            for f in wire.get('findings', []):
                for b in f['bases']:
                    if b['type'] == 'task_premise_reference': b['premise_id'] = wrong
        adapter = Scripted(fact_change=change)
        result = await harness(adapter).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertEqual(sum(r.correction for r in adapter.requests), 1)
        self.assertEqual(result.verification_output.findings[1].status, VerificationStatus.SUPPORTED)

    async def test_unverified_report_remains_report_and_does_not_prove_application(self):
        req = task(premise_declarations=(PremiseDeclaration('user_context', '分值为42。', 'unverified_report'),))
        result = await harness(Scripted()).run(req, RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertEqual(result.verification_output.findings[0].status, VerificationStatus.SUPPORTED)
        self.assertEqual(result.verification_output.findings[-1].status, VerificationStatus.NOT_ASSESSABLE)

    async def test_external_assertion_cannot_borrow_premise_even_if_rule_text_is_present(self):
        def extraction(wire, payload):
            c = wire['claims'][-1]['components'][0]
            c.update(object_kind='external_claim', premise_ids=[])
        def change(wire, payload):
            if 'findings' not in wire: return
            f = wire['findings'][-1]
            f['bases'].append({'type': 'task_premise_reference', 'premise_id': payload['TASK_PREMISES'][0]['premise_id']})
            f['component_reviews'][0]['basis_indexes'].append(len(f['bases']) - 1)
        result = await harness(Scripted(extraction_change=extraction, fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertNotEqual(result.report.decision.kind.value, 'pass')

    async def test_disputed_object_fidelity_is_review_required_not_auto_reclassification(self):
        def change(wire, payload):
            if 'findings' in wire:
                wire['findings'][-1]['component_reviews'][0]['semantic_review']['fidelity'] = 'disputed'
        result = await harness(Scripted(fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        review = result.verification_output.findings[-1].component_reviews[0]
        self.assertEqual(review.raw_support_status, 'supported')
        self.assertEqual(review.status, VerificationStatus.NOT_ASSESSABLE)
        self.assertEqual(result.report.decision.kind.value, 'review_required')

    async def test_body_only_original_citation_cannot_use_task_premise_basis(self):
        def change(wire, payload):
            if 'citation_reviews' not in wire: return
            c = wire['citation_reviews'][0]
            c['bases'].append({'type': 'task_premise_reference', 'premise_id': payload['TASK_PREMISES'][0]['premise_id']})
        result = await harness(Scripted(fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertEqual(result.verification_output.citation_reviews[0].status, VerificationStatus.NOT_ASSESSABLE)

    async def test_partial_fact_failure_preserves_domain_and_valid_peer_results(self):
        adapter = Scripted(fail_fact=True)
        result = await harness(adapter).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertIsNotNone(result.domain_output)
        self.assertFalse(result.domain_output.execution_issues)
        self.assertEqual(result.report.decision.kind.value, 'execution_incomplete')
        self.assertTrue(all(r.origin == 'execution_incomplete' for f in result.verification_output.findings for r in f.component_reviews))

    async def test_shared_budget_and_storage_failure_stop_without_fallback(self):
        adapter = Scripted()
        result = await harness(adapter).run(task(), RunBudget(max_model_calls=3, max_revision_rounds=0))
        self.assertLessEqual(len(adapter.requests), 3)
        self.assertTrue(result.execution_issues)
        failed = Scripted()
        def observer(snapshot):
            if snapshot['event'].component == 'claim_extraction': raise OSError('synthetic storage failure')
        from harness.execution import HarnessObserverError
        with self.assertRaises(HarnessObserverError):
            await harness(failed, observer=observer).run(task(), RunBudget(max_revision_rounds=0))
        self.assertEqual(len(failed.requests), 2)

    async def test_optional_graph_differential_with_same_synthetic_responses(self):
        left, right = Scripted(), Scripted()
        a = await harness(left).run(task(), RunBudget(max_revision_rounds=0))
        b = await harness(right, path='langgraph_v1').run(task(), RunBudget(max_revision_rounds=0))
        self.assertEqual(a.answer, b.answer)
        self.assertEqual(a.extraction_output, b.extraction_output)
        self.assertEqual(a.report.decision, b.report.decision)
        self.assertEqual(a.verification_output.findings, b.verification_output.findings)
        self.assertEqual(left.requests, right.requests)
        self.assertEqual(a.state, b.state)

    async def test_semantic_and_accounting_modes_have_separate_no_correction_differential(self):
        left, right = Scripted(), Scripted()
        a = await harness(left, accounting='shared_slice_v1').run(task(), RunBudget(max_revision_rounds=0))
        b = await harness(right, accounting='invocation_scoped_v1').run(task(), RunBudget(max_revision_rounds=0))
        self.assertEqual(a.report.decision, b.report.decision)
        self.assertEqual(left.requests, right.requests)

    async def test_original_vs_candidate_plain_literature_harness_differential(self):
        from services.claim_extractor import ModelClaimExtractor
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        def literature(wire, payload):
            for c in wire['claims']:
                c['assertion_role'] = 'asserted'
                for part in c['components']:
                    part.update(category='technical_fact', basis_target='technical_content',
                        verification_obligation='technical_truth', object_kind='literature', premise_ids=[])
        class Plain(Scripted):
            async def complete(self, request):
                if request.prompt_version.startswith('atomic-claims-v7'):
                    self.requests.append(request)
                    payload = json.loads(request.messages[1].content)
                    wire = extract_wire(dict(payload, TASK_PREMISES=[]))
                    literature(wire, payload)
                    for c in wire['claims']:
                        for p in c['components']:
                            del p['object_kind']; del p['premise_ids']
                    return ModelResponse(json.dumps(wire))
                if request.prompt_version.startswith('evidence-verification-v9.20'):
                    self.requests.append(request)
                    payload = json.loads(request.messages[1].content)
                    if 'TRANSPORT_SHARED_VALUES' in payload: payload = expand(payload)
                    for c in payload.get('claims', []):
                        c['component_objects'] = ['literature'] * len(c['components'])
                        c['component_premise_ids'] = [[] for _ in c['components']]
                    return ModelResponse(json.dumps(fact_wire(payload)))
                return await super().complete(request)
        req = task(TaskMode.ASSESS_EXISTING, existing_answer=AnswerDraft('synthetic-B-plain', 1, TEXTS[1]), premise_declarations=())
        left, right = Plain(), Plain(extraction_change=literature)
        old = harness(left)
        settings = ModelSettings('synthetic_fixture', max_output_tokens=8000, max_response_chars=96000)
        old.extractor = ModelClaimExtractor(left, settings, protocol_version=7, typed_components=True, daily_guidance=True)
        old.verification = ModelEvidenceVerificationAgent(left, settings, schema_version=13, support_relation_checks=True,
            support_relation_version=6, review_message_profile='lossless_v1')
        a = await old.run(req, RunBudget(max_revision_rounds=0))
        b = await harness(right).run(req, RunBudget(max_revision_rounds=0))
        self.assertFalse(a.execution_issues); self.assertFalse(b.execution_issues)
        self.assertEqual(a.answer, b.answer)
        self.assertEqual(a.report.decision.kind, b.report.decision.kind)
        self.assertEqual(a.report.decision.reason_codes, b.report.decision.reason_codes)
        self.assertEqual(a.report.domain_findings, b.report.domain_findings)
        self.assertEqual([f.status for f in a.verification_output.findings], [f.status for f in b.verification_output.findings])
        self.assertEqual([c.proposition for c in a.extraction_output.claims], [c.proposition for c in b.extraction_output.claims])
        self.assertEqual(len(left.requests), len(right.requests))
        self.assertTrue(all(not r.correction for r in left.requests + right.requests))

    async def test_default_factory_and_original_parser_do_not_enable_candidate(self):
        from backend.config import ServiceConfig
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from tests.test_fact_rereview_v3 import inputs
        from agents.verification_contract_v9 import parse, catalog as quote_scopes
        inp = inputs(False)
        wire = {'findings': [{'claim_id': inp.claims[0].claim_id, 'rationale': 'Synthetic illegal premise.',
            'applicability_conditions': [], 'bases': [{'type': 'task_premise_reference', 'premise_id': catalog(task())[0].premise_id}],
            'component_reviews': [{'component_index': 0, 'status': 'supported', 'basis_indexes': [0], 'rationale': 'Illegal.'}]}], 'citation_reviews': []}
        with self.assertRaises(ContractError): parse(wire, inp, quote_scopes(inp))
        self.assertEqual(ServiceConfig().verification_schema, 13)
        original = ModelEvidenceVerificationAgent(Scripted(), ModelSettings('synthetic_fixture'), schema_version=13)
        self.assertIsNone(getattr(original, 'premise_profile', None))
        self.assertEqual(original.correction_accounting, 'shared_slice_v1')

    async def test_mixed_components_keep_independent_statuses_and_aggregate(self):
        def extraction(wire, payload):
            c = wire['claims'][0]
            premise = deepcopy(c['components'][0])
            c['assertion_role'] = 'conditional'
            c['components'] = [premise,
                dict(premise, category='technical_fact', proposition=TEXTS[1], basis_target='technical_content', verification_obligation='technical_truth', object_kind='literature', premise_ids=[]),
                dict(premise, category='technical_fact', proposition=TEXTS[2], basis_target='technical_content', verification_obligation='technical_truth', object_kind='scenario_application')]
        def change(wire, payload):
            if 'findings' not in wire: return
            row = wire['findings'][0]['component_reviews'][2]
            row.update(status='insufficient_evidence', rationale='Synthetic application conclusion not established.')
            row.pop('support_relation', None)
        req = task(TaskMode.ASSESS_EXISTING, existing_answer=AnswerDraft('synthetic-B-mixed', 1, ' '.join(TEXTS)))
        result = await harness(Scripted(extraction_change=extraction, fact_change=change)).run(req, RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        self.assertEqual(len(result.verification_output.findings), 1)
        finding = result.verification_output.findings[0]
        self.assertEqual([r.status.value for r in finding.component_reviews], ['supported', 'supported', 'insufficient_evidence'])
        self.assertEqual(finding.status, VerificationStatus.INSUFFICIENT_EVIDENCE)

    async def test_necessary_condition_missing_uses_existing_support_projection(self):
        def change(wire, payload):
            for f, c in zip(wire.get('findings', []), payload.get('claims', [])):
                if c['component_objects'][0] != 'scenario_application': continue
                carrier = payload['SOURCE_CONDITION_CANDIDATES']['candidates'][0]
                f['component_reviews'][0]['support_relation']['answer_conditions'] = [{
                    'condition_id': carrier['condition_id'], 'necessity': 'required', 'answer_quote': '',
                    'relationship': 'missing', 'reason': 'Synthetic reviewer says required condition absent from actual assertion.'}]
        result = await harness(Scripted(fact_change=change)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        review = result.verification_output.findings[-1].component_reviews[0]
        self.assertEqual(review.raw_support_status, 'supported')
        self.assertEqual(review.status, VerificationStatus.INSUFFICIENT_EVIDENCE)

    async def test_legal_ids_and_contract_cannot_prove_semantic_correctness(self):
        # Deliberately wrong scripted reviewer: actual premise is 41, answer says 42.
        # This MUST NOT be advertised as a semantic success by the passing gate.
        req = task(user_context='教学假设：分值为41。', premise_declarations=(PremiseDeclaration('user_context', '分值为41。'),))
        result = await harness(Scripted()).run(req, RunBudget(max_revision_rounds=0))
        self.assertFalse(result.execution_issues)
        self.assertEqual(result.report.decision.kind.value, 'pass')
        self.assertIn('42', result.answer.text)
        self.assertEqual(result.verification_output.task_premises[0].text, '分值为41。')

    async def test_tampered_reference_version_rejected_by_core_validation(self):
        result = await harness(Scripted()).run(task(), RunBudget(max_revision_rounds=0))
        out = result.verification_output
        first = out.findings[0]
        basis = first.bases[0]
        bad = replace(out, findings=(replace(first, bases=(replace(basis,
            premise_reference=replace(basis.premise_reference, version='forged-version')),)),) + out.findings[1:])
        with self.assertRaises(ContractError): validate_review(bad, result.answer, out.claims, out.evidence, True)

    async def test_cancellation_preserves_completed_domain_event_and_never_retries(self):
        entered, domain_saved = asyncio.Event(), asyncio.Event()
        saved = []
        class Waiting(Scripted):
            async def complete(self, request):
                if request.prompt_version.startswith('evidence-verification-v9.21'):
                    self.requests.append(request)
                    entered.set()
                    await asyncio.Event().wait()
                return await super().complete(request)
        def observer(snapshot):
            if snapshot['event'].component == 'power_domain_review':
                saved.append(snapshot['stage_output'])
                domain_saved.set()
        adapter = Waiting()
        h = harness(adapter, observer=observer)
        running = asyncio.create_task(h.run(task(), RunBudget(max_revision_rounds=0), run_id='synthetic-B-cancel'))
        await asyncio.wait_for(entered.wait(), 2)
        await asyncio.wait_for(domain_saved.wait(), 2)
        await h.cancel('synthetic-B-cancel')
        result = await running
        self.assertEqual(result.state.value, 'cancelled')
        self.assertEqual(len(saved), 1)
        self.assertFalse(saved[0].execution_issues)
        self.assertEqual(sum(r.prompt_version.startswith('evidence-verification-v9.21') for r in adapter.requests), 1)
        self.assertEqual(h._runs, {})

    async def test_timeout_is_execution_failure_and_not_semantic_insufficiency(self):
        from model_adapter.contracts import ModelTimeoutError
        class Timed(Scripted):
            async def complete(self, request):
                if request.prompt_version.startswith('evidence-verification-v9.21'):
                    self.requests.append(request)
                    raise ModelTimeoutError()
                return await super().complete(request)
        adapter = Timed()
        result = await harness(adapter).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertTrue(any(r.status.value == 'timed_out' for r in result.model_records))
        self.assertTrue(all(r.origin == 'execution_incomplete' for f in result.verification_output.findings for r in f.component_reviews))
        self.assertFalse(any(r.correction for r in adapter.requests))

    async def test_candidate_domain_failure_does_not_discard_completed_fact_result(self):
        result = await harness(Scripted(fail_domain=True)).run(task(), RunBudget(max_revision_rounds=0))
        self.assertTrue(result.execution_issues)
        self.assertFalse(result.verification_output.execution_issues)
        self.assertTrue(all(f.status == VerificationStatus.SUPPORTED for f in result.verification_output.findings))
        self.assertTrue(result.domain_output.execution_issues)

    async def test_request_declaration_failure_precedes_all_model_calls(self):
        adapter = Scripted()
        req = task(premise_declarations=(PremiseDeclaration('user_context', 'answer-invented-premise'),))
        with self.assertRaises(ContractError): await harness(adapter).run(req, RunBudget(max_revision_rounds=0))
        self.assertFalse(adapter.requests)


class CatalogTests(unittest.TestCase):
    def test_task_only_stable_between_modes_and_exact_identity(self):
        a = catalog(task())
        self.assertEqual(a, catalog(task(TaskMode.ASSESS_EXISTING)))
        self.assertEqual(task().user_context[a[0].start_offset:a[0].end_offset], a[0].text)
        self.assertNotEqual(a, catalog(task(task_id='another-task')))
        self.assertNotEqual(a, catalog(task(question='Changed question')))
        self.assertNotEqual(a, catalog(task(premise_declarations=(PremiseDeclaration('user_context', '分值为42。', 'unverified_report'),))))

    def test_reject_generated_or_ambiguous_or_duplicate_declarations(self):
        for declarations in ((PremiseDeclaration('assumptions', '999'),),
                (PremiseDeclaration('user_context', 'absent'),),
                (PremiseDeclaration('user_context', '分值为42。'),) * 2):
            with self.assertRaises(ContractError): catalog(task(premise_declarations=declarations))
        with self.assertRaises(ContractError): catalog(task(user_context='分值为42。分值为42。'))


if __name__ == '__main__': unittest.main()
