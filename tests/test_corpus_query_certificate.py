"""Public synthetic fixtures: skip redundant ranking, never skip identity checks."""
import asyncio
from dataclasses import replace
from unittest.mock import patch
from tests.test_corpus_index import CorpusTests
from rag.retriever import AsyncSQLiteBM25Retriever
from rag.corpus_index import CorpusRetriever
from rag.contracts import RetrievalPurpose
from core.validation import ContractError

class CertificateTests(CorpusTests):
 def test_same_request_validation_reuses_only_program_query_not_ranking(self):
  async def run():
   r=AsyncSQLiteBM25Retriever(self.p)
   try:
    q=self.request('无功功率');out=await r.retrieve(q)
    with patch.object(CorpusRetriever,'_retrieve',side_effect=AssertionError('Redundant ranking')):
     await r.validate_result(q,out)
     with self.assertRaises(ContractError):await r.validate_result(q,replace(out,hits=()))
     bad=replace(out.evidence[0],text='synthetic tampering')
     with self.assertRaises(ContractError):await r.validate_result(q,replace(out,evidence=(bad,)))
   finally:r.close()
  asyncio.run(run())
 def test_different_scope_request_never_reuses_certificate(self):
  async def run():
   r=AsyncSQLiteBM25Retriever(self.p)
   try:
    q=self.request('无功功率');out=await r.retrieve(q)
    with patch.object(CorpusRetriever,'_validate_result',side_effect=RuntimeError('Full replay')):
     for changed in (replace(q,purpose=RetrievalPurpose.VERIFICATION),replace(q,query='电压'),replace(q,max_results=1),replace(q,scenario_id='different')):
      with self.assertRaisesRegex(RuntimeError,'Full replay'):await r.validate_result(changed,out)
   finally:r.close()
  asyncio.run(run())
 def test_changed_file_rejected_even_for_certified_result(self):
  async def run():
   r=AsyncSQLiteBM25Retriever(self.p)
   try:
    q=self.request('无功功率');out=await r.retrieve(q)
    import os
    stat=self.p.stat();os.utime(self.p,ns=(stat.st_atime_ns,stat.st_mtime_ns+1000000000))
    with self.assertRaises(ContractError):await r.validate_result(q,out)
   finally:r.close()
  asyncio.run(run())
