"""Production composition uses existing components, never evaluation CLIs."""
import asyncio
import os
from dataclasses import asdict
from pathlib import Path
import hashlib
from backend.config import ROOT
from harness.runtime import OfflineHarness
from harness.policy import LimitedRepairPolicy
from harness.contracts import RetrievalSettings

class ConfigurationError(RuntimeError):
    code='CONFIGURATION_UNAVAILABLE'

class Bundle:
    def __init__(self,harness,resources=()):self.harness=harness;self.resources=resources
    async def drain(self):
        # Await completion, not termination. Cancelled shielded workers may still be active.
        while any(getattr(r,'_active',None) is not None and not r._active.done() for r in self.resources):
            await asyncio.sleep(.05)
    def close(self):
        for resource in self.resources:resource.close()

class ComponentFactory:
    def __init__(self,config):self.config=config;self.semantic_resource=None;self.retrieval_metrics=None
    def warm_corpus_index(self):
        """Open-time validation before accepting HTTP; never a model request."""
        if self.config.profile!='real' or not self.config.index_db.is_file():return
        from rag.storage import KnowledgeStore
        from rag.corpus_index import seal
        with KnowledgeStore(self.config.index_db,readonly=True) as store:seal(store,self.config.knowledge_version)
    def initialize_retrieval(self,encoder=None):
        if self.config.profile=='synthetic_fixture' or self.config.retrieval_mode=='bm25':return
        if self.semantic_resource is not None:return
        from rag.semantic import AsyncSQLiteSemanticRetriever,VectorIndex
        from rag.storage import KnowledgeStore
        try:
            if encoder is None:
                from rag.embedding import E5ONNXEncoder
                encoder=E5ONNXEncoder(self.config.embedding_model_dir)
            with KnowledgeStore(self.config.index_db,readonly=True) as store, VectorIndex(self.config.vector_db,readonly=True) as index:
                index.load(store,self.config.knowledge_version,encoder)
            self.semantic_resource=AsyncSQLiteSemanticRetriever(self.config.index_db,self.config.vector_db,encoder,mode=self.config.retrieval_mode)
        except Exception:
            if encoder is not None and hasattr(encoder,'close'):encoder.close()
            raise ConfigurationError('Semantic model/profile/dimension/index/knowledge configuration unavailable or mismatched') from None
    async def close(self):
        resource=self.semantic_resource
        if resource:
            await Bundle(None,(resource,)).drain()
            self.retrieval_metrics={'query_encodings':resource.query_encodings,
                'validation_replays':resource.validation_replays,'encoding_seconds':resource.encoder.encoding_seconds}
            resource.close()
            if hasattr(resource.encoder,'close'):resource.encoder.close()
            self.semantic_resource=None
    def preflight(self):
        if self.config.profile=='synthetic_fixture':return None
        if not os.environ.get('DEEPSEEK_API_KEY') or not os.environ.get('DEEPSEEK_MODEL_ID'):
            raise ConfigurationError('Explicit model configuration required; no simulated fallback')
        if not self.config.index_db.is_file():raise ConfigurationError('Knowledge index unavailable')
        from rag.storage import KnowledgeStore
        try:
            with KnowledgeStore(self.config.index_db,readonly=True) as store:
                from rag.corpus_index import seal
                corpus=seal(store,self.config.knowledge_version)
                if corpus is None:store.rows(self.config.knowledge_version)
        except Exception:raise ConfigurationError('Fixed knowledge snapshot unavailable') from None
        self.initialize_retrieval()
        return self.config.knowledge_version

    def manifest(self,knowledge_version):
        from agents.review_templates_v3 import INDEPENDENT
        from services.review_fidelity import FROZEN_BINDING_INSTRUCTIONS
        INDEPENDENT += FROZEN_BINDING_INSTRUCTIONS
        from services.support_relation import instructions
        INDEPENDENT=INDEPENDENT.replace('Optional classification_issue EXACT suggested_category,rationale.',
            'Optional support_relation (required for definitive body-based judgments) and classification_issue EXACT suggested_category,rationale.')
        INDEPENDENT += instructions(2)
        from agents.verification_contract_v10_batched import PROMPT_VERSION,CONTRACT_VERSION,original_template
        ORIGINAL=original_template(support_relation_checks=True,support_relation_version=2)
        PROMPT_VERSION='evidence-verification-v9.8-whole-claim-conditions'
        CONTRACT_VERSION='evidence-verification-output-v9.8'
        if self.config.fact_strategy=='per_claim_v1':PROMPT_VERSION+='-fact-delivery-v1'
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for name in ('core','agents','harness','tools','services','rag','model_adapter','backend') for p in (ROOT/name).glob('*.py')}
        hashes.update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (ROOT/'backend/static').glob('*') if p.is_file()})
        manifest={'schema_version':'local-review-service-v1','profile':self.config.profile,
            'components':'simulated_synthetic_fixture' if self.config.profile=='synthetic_fixture' else 'real_model_with_demo_domain_rules',
            'model_id':os.environ.get('DEEPSEEK_MODEL_ID') if self.config.profile=='real' else None,
            'knowledge_version':knowledge_version,'budget':asdict(self.config.budget),
            'protocols':{'generation':3,'claim_extraction':7,'evidence_verification':13,'domain_review':4,'revision':2},
            'citation_workload':asdict(self.config.citation_workload),
            'prompts':{'generation':'evidence-bound-generation-v3-answer-units-product-v1' if self.config.decision_policy=='product-v1' else 'evidence-bound-generation-v3-answer-units','extraction':'atomic-claims-v7-obligations-category-clarity-v1' if self.config.decision_policy=='product-v1' else 'atomic-claims-v7-obligations',
              'verification':PROMPT_VERSION,'domain':'power-domain-review-v3.1-applicability','revision':'bounded-revision-v2-per-finding-actions-explicit-limit-v1'},
            'contracts':{'generation':'generation-output-v3','extraction':'atomic-claims-v7','verification':CONTRACT_VERSION,
              'domain':'power-domain-review-output-v3.1','revision':'revision-output-v2'},
            'rules':'power-demo-rules-v1.1','policy':'product-decision-v1.1' if self.config.decision_policy=='product-v1' else 'limited-repair-policy-v1','unit_tool':'scalar-si-conversion-v2',
            'retrieval':'existing BM25 with default RetrievalSettings and adjacent-context order',
            'fact_retrieval_strategy':self.config.fact_strategy,
            'fact_delivery_contract':'fact-evidence-delivery-v1' if self.config.fact_strategy=='per_claim_v1' else None,
            'source_sha256':hashes,'template_sha256':{'independent':hashlib.sha256(INDEPENDENT.encode()).hexdigest(),
              'original_citation':hashlib.sha256(ORIGINAL.encode()).hexdigest()},
            'model_settings':{'timeout_seconds':90,'max_output_tokens':8000,'max_response_chars':96000}}
        from rag.bm25 import SCORING_METHOD
        from rag.semantic import RRF_VERSION
        manifest.update(retrieval_mode=self.config.retrieval_mode,
            embedding_profile=None if self.semantic_resource is None else dict(self.semantic_resource.encoder.profile),
            scoring_method=SCORING_METHOD if self.config.retrieval_mode=='bm25' else RRF_VERSION if self.config.retrieval_mode=='hybrid' else 'Dense-cosine-v1(positive-only)')
        manifest['retrieval']='fixed-index '+self.config.retrieval_mode+'; full result replay validation'
        manifest['performance_profile']='validated-pdf-report-cache-v1: connection-local immutable body verification only; full ranking replay retained' if self.config.retrieval_mode=='bm25' else 'legacy-semantic-full-replay'
        if self.config.profile=='real' and self.config.retrieval_mode=='bm25':
            from rag.storage import KnowledgeStore
            from rag.corpus_index import seal,SCORING
            with KnowledgeStore(self.config.index_db,readonly=True) as store:
                corpus=seal(store,knowledge_version)
            if corpus is not None:
                manifest['corpus_index']={key:corpus.get(key) for key in ('version','revision','tokenizer','query_version','complete','records','chunks','duplicates','chunks_root')}
                manifest['scoring_method']=SCORING
                manifest['retrieval']='immutable SQLite FTS5 postings; versioned Chinese segmentation/topic query; strict hit replay'
                manifest['performance_profile']='build/publication FTS integrity; open structural checks; immutable-file stamp; strict per-hit original/span verification; no full snapshot query scan'
        manifest['generation_query_conversion']='generation-cross-language-query-v1: once after successful empty BM25; Chinese question / fixed English body available (mixed-snapshot-gate-v2)'
        manifest['prompts']['generation'] += ('-question-language-v5-scope-preservation-explicit-limit-v1' if self.config.decision_policy=='product-v1' else '-question-language-v4-explicit-limit-v1')
        if self.config.profile=='synthetic_fixture':
            manifest['available_real_protocols']=manifest.pop('protocols')
            manifest['protocols']={k:'fake-v1' for k in ('generation','claim_extraction','evidence_verification','domain_review','revision')}
            manifest['prompts']={};manifest['contracts']={};manifest['model_settings']=None
            manifest['rules']='offline-rules-v1';manifest['policy']='product-decision-v1.1-synthetic_fixture' if self.config.decision_policy=='product-v1' else 'offline-policy-v1';manifest['unit_tool']=None
            manifest['retrieval']='none: synthetic_fixture only'
            manifest['configured_retrieval_mode']=manifest['retrieval_mode']
            manifest['retrieval_mode']='none';manifest['scoring_method']=None
        return manifest

    def create(self,rid,observer):
        if self.config.profile=='synthetic_fixture':
            from agents.fakes import make_fake_harness
            harness=make_fake_harness();harness.observer=observer
            if self.config.decision_policy=='product-v1':
                from harness.product_policy import ProductAuditPolicy
                harness.policy=ProductAuditPolicy(synthetic_fixture=True)
            return Bundle(harness)
        from agents.generation import EvidenceGenerationAgent
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from agents.power_domain_review import ModelPowerDomainReviewAgent
        from agents.revision import ModelRevisionAgent
        from services.claim_extractor import ModelClaimExtractor
        from tools.unit_conversion import UnitConversionTool
        from model_adapter.contracts import ModelSettings
        from model_adapter.deepseek import create_adapter
        from rag.retriever import AsyncSQLiteBM25Retriever
        from services.generation_query import GenerationQueryConverter, english_fallback_available
        from rag.storage import KnowledgeStore
        settings=ModelSettings(os.environ['DEEPSEEK_MODEL_ID'],90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')
        resources=[]
        try:
            model=create_adapter(settings);resources.append(model)
            domain_model=create_adapter(settings);resources.append(domain_model)
            if self.config.retrieval_mode=='bm25':
                retriever=AsyncSQLiteBM25Retriever(self.config.index_db);resources.append(retriever)
            else:
                self.initialize_retrieval();retriever=self.semantic_resource;resources.append(RetrieverLease(retriever))
            diag=ROOT/'data/retrieval_local/service_private'/rid
            with KnowledgeStore(self.config.index_db, readonly=True) as store:
                from rag.corpus_index import seal
                corpus=seal(store,self.config.knowledge_version)
                corpus_english = (corpus['has_english'] or english_fallback_available(store.rows(corpus['base_knowledge_version']))) if corpus is not None else english_fallback_available(store.rows(self.config.knowledge_version))
            harness=OfflineHarness(EvidenceGenerationAgent(model,settings,diagnostic_dir=diag,schema_version=3,product_guidance=self.config.decision_policy=='product-v1'),
                ModelEvidenceVerificationAgent(model,settings,diagnostic_dir=diag,schema_version=13,citation_workload=self.config.citation_workload,support_relation_checks=True,support_relation_version=2),
                ModelPowerDomainReviewAgent(domain_model,settings,diagnostic_dir=diag,protocol_version=4),
                ModelRevisionAgent(model,settings,diagnostic_dir=diag,protocol_version=2),
                ModelClaimExtractor(model,settings,diagnostic_dir=diag,typed_components=True,protocol_version=7,daily_guidance=self.config.decision_policy=='product-v1'),
                policy=self.product_policy(),retriever=retriever,retrieval_settings=RetrievalSettings(fact_strategy=self.config.fact_strategy),unit_tool=UnitConversionTool(version='scalar-si-conversion-v2'),observer=observer,
                generation_query_converter=GenerationQueryConverter(model,settings,diag) if self.config.retrieval_mode=='bm25' else None,
                generation_corpus_english=corpus_english)
            return Bundle(harness,resources)
        except Exception:
            for resource in resources:resource.close()
            raise ConfigurationError('Required component could not be constructed') from None

    def product_policy(self):
        if self.config.decision_policy=='legacy-v1':return LimitedRepairPolicy()
        from harness.product_policy import ProductAuditPolicy
        return ProductAuditPolicy()

class RetrieverLease:
    """Drain per-run work without closing the service-owned encoder."""
    def __init__(self,resource):self.resource=resource
    @property
    def _active(self):return self.resource._active
    def close(self):pass

