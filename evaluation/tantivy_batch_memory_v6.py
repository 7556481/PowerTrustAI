"""Fixed stopped-window Python allocation diagnostic, no writer/model calls."""
import json,sqlite3,sys,psutil,time
from pathlib import Path
from evaluation.tantivy_full_build_v1 import ROOT
from rag.tantivy_build import atomic
n=int(sys.argv[1]);assert n in (5000,50000)
c=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);c.execute('pragma cache_size=-4096');p=psutil.Process();baseline=p.memory_info();sql='select * from input where position>=? order by position limit ?';a=c.execute(sql,(510674,n)).fetchall();one=p.memory_info();b=c.execute(sql,(510674,n)).fetchall();two=p.memory_info()
result={'n':n,'window_start':510674,'two_lists':'same fixed rows; simulate next fetch while previous list remains referenced','baseline_rss':baseline.rss,'one_batch_rss':one.rss,'two_batch_rss':two.rss,'two_batch_private':getattr(two,'private',two.vms),'python_batch_objects_bytes':sys.getsizeof(a)+sum(sys.getsizeof(row)+sum(sys.getsizeof(x) for x in row) for row in a),'native_writer_used':False,'limitations':'process snapshots, not peak sampler; no claim about Rust merge mmap working set','wall':time.time()};atomic(ROOT/('python-batch-memory-v6-'+str(n)+'.json'),result);print(json.dumps(result))
