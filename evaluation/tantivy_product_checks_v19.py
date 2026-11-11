"""Same public Factory/API fixture with v18 single-group wiring, no real model."""
import json,sqlite3
from dataclasses import replace
from unittest.mock import patch
from pathlib import Path
from backend.config import ServiceConfig
from rag.storage import KnowledgeStore
from rag.tantivy_members import members
from evaluation import tantivy_fast_factory_checks_v1 as previous

class ProductV18(previous.FactoryFast):
 def test_product_versions_and_worker_reuse(self):
  def config(*a,**kw):
   c=ServiceConfig(*a,**kw);m=c.tantivy_manifest;sp=m.parent/'input.sqlite3';g=m.parent/'group.json'
   with KnowledgeStore(c.index_db,readonly=True) as store:rows=list(members(store,c.knowledge_version))
   con=sqlite3.connect(sp);con.execute('create table input(position integer primary key,rowid integer,terms_sha text,terms text)')
   for r in rows:con.execute('insert into input values(?,?,?,?)',(-r[1]-1 if r[1]<0 else r[1]+673,r[1],r[4],r[5]))
   con.commit();con.close();g.write_text(json.dumps({'complete':True,'count':len(rows),'manifests':[str(m)]}))
   return replace(c,tantivy_manifest=g,tantivy_worker_mode='sharded_v18',tantivy_spool=sp)
  with patch.object(previous,'ServiceConfig',config):super().test_product_versions_and_worker_reuse()
