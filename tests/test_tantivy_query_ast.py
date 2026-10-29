"""Query conversion rejects unsupported syntax instead of rewriting it."""
import unittest
from evaluation.tantivy_bounded_v1 import ast
class QueryAstTests(unittest.TestCase):
 def test_explicit_group_and_precedence(self):
  self.assertEqual(ast('("a" OR "b") AND "c"'),['and',['or',['phrase',['a']],['phrase',['b']]],['phrase',['c']]])
  self.assertEqual(ast('"a" OR "b" AND "c"')[0],'or')
 def test_phrase_and_negative_scope(self):
  self.assertEqual(ast('terms:"power factor" NOT "missing"'),['not',['phrase',['power','factor']],['phrase',['missing']]])
 def test_unsupported_is_explicit(self):
  for text in ['title:"a"','"a" NEAR "b"','"a" "b"','"a" AND','"a-b"','("a"']:
   with self.subTest(text=text),self.assertRaises(ValueError):ast(text)
if __name__=='__main__':unittest.main()
