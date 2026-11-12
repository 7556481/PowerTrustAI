import unittest
from unittest.mock import patch
from types import SimpleNamespace
from backend.config import ServiceConfig
from backend.assembly import ComponentFactory,Bundle
from tools.managed_overlap import ManagedFactory
class ManagedSelectionTests(unittest.TestCase):
 def test_factory_selection_default_and_explicit(self):
  class Client:
   def __init__(self):self.adapter=object()
   async def complete(self,*a,**kw):pass
  def create(*a,**kw):
   agents={k:SimpleNamespace(client=Client()) for k in ('generation','extractor','verification','revision')}
   return Bundle(SimpleNamespace(retriever=None,**agents))
  from tests.fixture_paths import synthetic_diagnostics
  from pathlib import Path
  from dataclasses import replace
  with synthetic_diagnostics() as temp:
   c=replace(ServiceConfig(),run_db=Path(temp)/'runs.sqlite3')
   with patch.object(ComponentFactory,'create',create):
    for mode in ('component','overlap'):
     b=ManagedFactory(c,mode).create('test-'+mode,None)
     self.assertEqual(getattr(b.harness,'fact_domain_retrieval_overlap',False),mode=='overlap')
