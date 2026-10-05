"""Server-owned local configuration. API requests cannot override destinations."""
from dataclasses import dataclass, field, replace
from pathlib import Path
import os
from harness.contracts import RunBudget
from services.citation_workload import CitationWorkload

ROOT=Path(__file__).resolve().parents[1]
BASELINE_KNOWLEDGE='k-182e01fab54ebfada841fb108061c127273e9cfcd551b6f5a8888a769215e385'

@dataclass(frozen=True)
class ServiceConfig:
    profile: str='real'
    run_db: Path=ROOT/'data/runtime_local/runs.sqlite3'
    token_file: Path=ROOT/'data/runtime_local/access-token'
    index_db: Path=ROOT/'data/retrieval_local/semantic/corpus.sqlite3'
    knowledge_version: str=BASELINE_KNOWLEDGE
    queue_capacity: int=2
    fact_strategy: str='aggregate'
    retrieval_mode: str='bm25'
    embedding_model_dir: Path=ROOT/'data/retrieval_local/semantic/e5-small'
    vector_db: Path=ROOT/'data/retrieval_local/semantic/vectors.sqlite3'
    nli_enabled: bool=False
    nli_python: Path|None=None
    nli_checkpoint: Path|None=None
    nli_profile: Path|None=None
    nli_timeout_seconds: float=5.0
    citation_workload: CitationWorkload=field(default_factory=CitationWorkload)
    budget: RunBudget=field(default_factory=lambda:RunBudget(max_revision_rounds=1,max_model_calls=40,
        max_duration_seconds=800,step_timeout_seconds=110,max_transient_retries=0,max_retrieval_chars_total=160000))

    def __post_init__(self):
        if type(self.nli_enabled) is not bool or not 0<float(self.nli_timeout_seconds)<=60:
            raise ValueError('Invalid local NLI diagnostic configuration')
        if self.retrieval_mode not in ('bm25','dense','hybrid'):raise ValueError('Unknown retrieval mode')
        if self.fact_strategy not in ('aggregate','per_claim_v1'):raise ValueError('Unknown fact retrieval strategy')
        if self.profile not in ('real','synthetic_fixture') or type(self.queue_capacity) is not int or not 1<=self.queue_capacity<=16:
            raise ValueError('Invalid local service configuration')
        if Path(self.run_db).resolve()==Path(self.index_db).resolve():
            raise ValueError('Run store must be separate from the knowledge index')

    @classmethod
    def from_environment(cls,*,demo=False):
        if not demo:
            from harness.deepseek_trial import load_project_env
            load_project_env() # existing absolute-root literal loader; never display it
        strategy=os.environ.get('POWERTRUST_FACT_RETRIEVAL_STRATEGY','aggregate')
        budget=replace(cls().budget,max_retrieval_calls=int(os.environ.get('POWERTRUST_MAX_RETRIEVAL_CALLS','128' if strategy=='per_claim_v1' else '12')))
        return cls(profile='synthetic_fixture' if demo else 'real',budget=budget,
            nli_enabled=os.environ.get('POWERTRUST_LOCAL_NLI_ENABLED','0')=='1',
            nli_python=Path(os.environ['POWERTRUST_LOCAL_NLI_PYTHON']) if os.environ.get('POWERTRUST_LOCAL_NLI_PYTHON') else None,
            nli_checkpoint=Path(os.environ['POWERTRUST_LOCAL_NLI_CHECKPOINT']) if os.environ.get('POWERTRUST_LOCAL_NLI_CHECKPOINT') else None,
            nli_profile=Path(os.environ['POWERTRUST_LOCAL_NLI_PROFILE']) if os.environ.get('POWERTRUST_LOCAL_NLI_PROFILE') else None,
            nli_timeout_seconds=float(os.environ.get('POWERTRUST_LOCAL_NLI_TIMEOUT_SECONDS','5')),
            fact_strategy=strategy,
            retrieval_mode=os.environ.get('POWERTRUST_RETRIEVAL_MODE','bm25'),
            embedding_model_dir=Path(os.environ.get('POWERTRUST_EMBEDDING_MODEL_DIR',str(cls().embedding_model_dir))),
            vector_db=Path(os.environ.get('POWERTRUST_VECTOR_DB',str(cls().vector_db))),
            citation_workload=CitationWorkload(
                int(os.environ.get('POWERTRUST_CITATION_BATCH_ITEMS','32')),
                int(os.environ.get('POWERTRUST_REVIEW_MESSAGE_CHARS','64000')),
                int(os.environ.get('POWERTRUST_REVIEW_CORRECTION_CHARS','192000'))),
            queue_capacity=int(os.environ.get('POWERTRUST_QUEUE_CAPACITY','2')),
            knowledge_version=os.environ.get('POWERTRUST_KNOWLEDGE_VERSION',BASELINE_KNOWLEDGE))

