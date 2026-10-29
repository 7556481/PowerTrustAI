"""Diagnostic limits and examples; no unimplemented tie algorithm is claimed."""
import sqlite3,unittest
from evaluation.retrieval_rank_v7 import BASE,RANK,bounded
class RankDiagnosticTests(unittest.TestCase):
    def test_ties_short_and_empty_diagnostic_does_not_prove_full_boundary(self):
        db=sqlite3.connect(':memory:');db.execute('CREATE VIRTUAL TABLE corpus_fts USING fts5(terms)')
        db.executemany('INSERT INTO corpus_fts(rowid,terms) VALUES(?,?)',[(i,'same words') for i in range(1,5002)])
        a=db.execute(BASE,('same',3)).fetchall();b=db.execute(RANK,('same',3)).fetchall()
        self.assertEqual(len(a),3);self.assertEqual(len(b),3);self.assertEqual(len({s for _,s in a+b}),1)
        self.assertEqual(db.execute(BASE,('absent',3)).fetchall(),[])
        self.assertEqual(len(db.execute(RANK,('same',6000)).fetchall()),5001)
        db.close()
    def test_nondefault_rank_mapping_must_not_be_assumed_unweighted(self):
        db=sqlite3.connect(':memory:');db.execute('CREATE VIRTUAL TABLE corpus_fts USING fts5(a,b)')
        db.executemany('INSERT INTO corpus_fts VALUES(?,?)',[('target','other'),('other','target')])
        db.execute("INSERT INTO corpus_fts(corpus_fts,rank) VALUES('rank','bm25(10.0,0.0)')")
        self.assertNotEqual(db.execute(BASE,('target',2)).fetchall(),db.execute(RANK,('target',2)).fetchall());db.close()
    def test_deadline_interrupt_unknown_and_handler_cleaned(self):
        db=sqlite3.connect(':memory:')
        result=bounded(db,'WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n) SELECT count(*) FROM n',(),.02)
        self.assertEqual(result['status'],'timeout_unknown');self.assertIsNone(result['rows'])
        self.assertEqual(db.execute('SELECT 1').fetchall(),[(1,)]);db.close()
