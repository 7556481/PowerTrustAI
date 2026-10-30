"""v3 reuses the frozen v2 builder and measurements, not its supervisor/ID heap."""
import json,sys,sqlite3,hashlib,time
from pathlib import Path
from unittest.mock import patch
from evaluation import tantivy_stability_v2 as old
from evaluation import tantivy_medium_measure_v2 as measure
from evaluation.tantivy_supervision_v3 import Guard,Writer
LOCAL=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-supervision-v3')
SPOOL=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/input/spool.sqlite3')

def validate(g):
 import tantivy
 g.check('validation open');folder=LOCAL/'million';assert old.read(folder/'built.json')['input_sha']==old.read(LOCAL/'spool-verified.json')['input_sha'];idx=old.v1.index(folder/'tantivy');search=idx.searcher();meta=old.read(folder/'tantivy/meta.json');assert search.num_docs==1000000;assert len(meta['segments'])==search.num_segments
 assert sum(x['max_doc'] for x in meta['segments'])==1000000 and not any(x.get('deletes') for x in meta['segments'])
 c=sqlite3.connect(folder/'acceptance.sqlite3');c.execute('create table seen(rowid integer primary key)');src=sqlite3.connect(SPOOL.as_uri()+'?mode=ro',uri=True);fts=sqlite3.connect((folder/'fts.sqlite3').as_uri()+'?mode=ro',uri=True);n=0
 for ordinal,segment in enumerate(meta['segments']):
  for doc in range(segment['max_doc']):
   if n%1000==0:g.check('bounded stored-ID traversal')
   rid=search.doc(tantivy.DocAddress(ordinal,doc))['rowid'][0];c.execute('insert into seen values(?)',(rid,));r=src.execute('select position,fragment_id,body_sha,terms_sha from rows where rowid=?',(rid,)).fetchone();assert r and r[0]<1000000
   assert tuple(fts.execute('select fragment_id,body_sha,terms_sha from mapping where rowid=?',(rid,)).fetchone())==r[1:];n+=1
 assert n==1000000;c.commit();assert fts.execute('select count(*) from corpus_fts').fetchone()[0]==n
 g.check('validation finalize');old.save(folder/'acceptance.json',dict(passed=True,n=n,method='stored doc address per deletion-free segment, one doc at a time; SQLite unique membership',new_process=True,complete_id_set=True));c.close();src.close();fts.close()

def main(action):
 old.configure();g=Guard(LOCAL/'plan.json');g.check(action);
 for path,expected in g.plan['files'].items():assert hashlib.sha256((old.ROOT/path).read_bytes()).hexdigest()==expected,'Frozen implementation changed'
 old.LOCAL=LOCAL;measure.LOCAL=LOCAL
 # Reuse the immutable prepared input through a read-only URI path, not a copy.
 if action=='build':
  class Index:
   def __init__(self,idx):self.idx=idx
   def __getattr__(self,name):return getattr(self.idx,name)
   def writer(self,**kw):g.check('writer start');return Writer(self.idx.writer(**kw),g)
  original=old.v1.index
  with patch.object(old.v1,'index',side_effect=lambda p:Index(original(p))),patch.object(old,'checkpoint',side_effect=lambda writer=None:g.check('feed checkpoint')):
   old.build_sample('million',1000000)
 elif action=='validate':validate(g)
 elif action=='measure':
  with patch.object(measure,'checkpoint',side_effect=lambda:g.check('measure')):measure.measure('million',1000000)

if __name__=='__main__':main(sys.argv[1])
