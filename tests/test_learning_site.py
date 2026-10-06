"""The reader is isolated from runtime credentials and treats Markdown as text."""
import unittest
from tools.learning_site import render,highlight

class LearningTests(unittest.TestCase):
 def test_heading_table_fence_and_literal_html(self):
  h,toc=render('# Title\n\n<script>alert(1)</script>\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nif True:\n    value = "x"\n```')
  self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h);self.assertIn('<table>',h);self.assertIn('class="keyword"',h);self.assertEqual(toc[0][1],'Title')
 def test_unsafe_link_not_executable(self):
  h,_=render('[unsafe](javascript:alert)\n\n[chapter](01-product.md)')
  self.assertNotIn('href="javascript:',h);self.assertIn('01-product.html',h)
