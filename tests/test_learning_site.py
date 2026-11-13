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

class DocumentationTextIdentityTests(unittest.TestCase):
 def test_git_lf_and_windows_crlf_have_identical_documentation_identity(self):
  from tools.learning_checks import source_text_digest
  self.assertEqual(source_text_digest(b'def f():\n    return 1\n'),source_text_digest(b'def f():\r\n    return 1\r\n'))
 def test_content_change_is_not_normalized_away(self):
  from tools.learning_checks import source_text_digest
  self.assertNotEqual(source_text_digest(b'return 1\n'),source_text_digest(b'return 2\n'))

class ExternalReportLinksTests(unittest.TestCase):
 def test_github_markdown_report_is_not_rewritten_as_html(self):
  h,_=render('[report](https://github.com/owner/repo/blob/abc/report.md)\n\n[chapter](18-operations.md)')
  self.assertIn('href="https://github.com/owner/repo/blob/abc/report.md"',h)
  self.assertIn('href="18-operations.html"',h)
  self.assertNotIn('blob/abc/report.html',h)


class PortableLearningLinksTests(unittest.TestCase):
 def test_markdown_fragment_is_converted_and_legacy_heading_alias_remains(self):
  h,_=render('## 从产品到代码：常见与最典型\n\n[exercise](20-workshops.md#从产品到代码常见与最典型)')
  self.assertIn('id="section-1"',h)
  self.assertIn('id="从产品到代码常见与最典型"',h)
  self.assertIn('href="20-workshops.html#从产品到代码常见与最典型"',h)
 def test_source_paths_are_portable_and_external_fixed_reports_are_preserved(self):
  from pathlib import Path
  from tools.learning_site import ROOT,source_link_resolver
  source=ROOT/'docs/learning/index.md';chapter=ROOT/'docs/learning/chapters/18-operations.md';status=ROOT/'docs/current-status.md'
  resolve=source_link_resolver(source,{chapter.resolve():'18-operations.html',status.resolve():'current-status.html'})
  self.assertEqual(resolve('chapters/18-operations.md#从正确入口开始'),'18-operations.html#从正确入口开始')
  self.assertEqual(resolve('../current-status.md'),'current-status.html')
  fixed='https://github.com/owner/repo/blob/fixed/report.md#result'
  self.assertEqual(resolve(fixed),fixed)
 def test_missing_local_fragment_is_rejected_even_when_page_exists(self):
  from tempfile import TemporaryDirectory
  from pathlib import Path
  from tools.learning_checks import validate_local_links
  with TemporaryDirectory() as temp:
   root=Path(temp);(root/'index.html').write_text('<a href="chapter.html#missing">chapter</a>');(root/'chapter.html').write_text('<h1 id="present">Title</h1>')
   with self.assertRaisesRegex(ValueError,'Broken local anchor'):validate_local_links(root)
   (root/'index.html').write_text('<a href="chapter.html#present">chapter</a>')
   validate_local_links(root)
