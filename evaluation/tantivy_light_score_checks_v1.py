"""Reference semantics only, not acceptance of a new exact scorer."""
import sqlite3,unittest
class StatisticsRequirements(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.execute('create virtual table f using fts5(t)');self.c.executemany('insert into f(rowid,t) values(?,?)',[(1,'a a b'),(2,'a b'),(3,'a c'),(4,'a b')])
 def tearDown(self):self.c.close()
 def rows(self,q):return self.c.execute('select rowid,bm25(f) from f where f match ? order by bm25(f),rowid',(q,)).fetchall()
 def test_phrase_df_is_not_word_df_or_occurrence_count(self):
  self.assertEqual(len(self.rows('"a"')),4);self.assertEqual(len(self.rows('"a a"')),1);self.assertEqual(len(self.rows('"a b"')),3)
 def test_boolean_and_supported_binary_negation(self):
  self.assertEqual({r[0] for r in self.rows('"a" AND "b"')},{1,2,4});self.assertEqual(len(self.rows('"a" OR "b"')),4);self.assertEqual([r[0] for r in self.rows('"a" NOT "b"')],[3])
 def test_repeated_query_phrase_and_tie_rule(self):
  one=dict(self.rows('"a"'));two=dict(self.rows('"a" OR "a"'))
  for rid in one:self.assertAlmostEqual(two[rid],2*one[rid],places=12)
  rows=self.rows('"a b"');scores=dict(rows);self.assertEqual(scores[2],scores[4]);self.assertLess([r[0] for r in rows].index(2),[r[0] for r in rows].index(4))
if __name__=='__main__':unittest.main()
