"""The reader is isolated from runtime credentials and treats Markdown as text."""
import unittest
from tools.learning_site import render,highlight

class LearningTests(unittest.TestCase):
 def test_folded_answers_and_markdown_diagram(self):
  import json
  spec={'title':'Synthetic control/data/persistence','width':400,'height':200,
   'nodes':[{'id':'a','x':10,'y':10,'w':100,'h':50,'label':'API'},{'id':'b','x':200,'y':10,'w':100,'h':50,'label':'Store'}],
   'edges':[{'from':'a','to':'b','kind':'persist','label':'save'}]}
  h,_=render('```diagram\n'+json.dumps(spec)+'\n```\n\n::: answer Show answer\nLiteral <script> is text\n:::')
  self.assertIn('<svg role="img"',h);self.assertIn('stroke-dasharray="2 4"',h)
  self.assertIn('<details class="self-answer">',h);self.assertNotIn('<details open',h);self.assertNotIn('<script>',h)
 def test_unclosed_fold_is_explicit_error(self):
  with self.assertRaises(ValueError):render('::: answer Missing closer\ntext')
 def test_heading_table_fence_and_literal_html(self):
  h,toc=render('# Title\n\n<script>alert(1)</script>\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nif True:\n    value = "x"\n```')
  self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h);self.assertIn('<table>',h);self.assertIn('class="keyword"',h);self.assertEqual(toc[0][1],'Title')
 def test_unsafe_link_not_executable(self):
  h,_=render('[unsafe](javascript:alert)\n\n[chapter](01-product.md)')
  self.assertNotIn('href="javascript:',h);self.assertIn('01-product.html',h)
