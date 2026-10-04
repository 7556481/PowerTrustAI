import unittest
from evaluation.body_priority_trial import structural_reason, ranking

class BodyPriorityTests(unittest.TestCase):
    def test_url_footer_demoted(self):
        self.assertEqual(structural_reason('https://example.org/report.pdf\nSmall Signal Stability Monitoring 28'),'isolated_link_footer')
    def test_substantive_footnote_retained(self):
        self.assertIsNone(structural_reason('Footnote: A STATCOM overload is not a sustained reserve. The requirement depends on duration and operating conditions.'))
    def test_table_and_caption_retained(self):
        self.assertIsNone(structural_reason('Table 3: Reactive output: 20 MVAr at 0.95 pu. Limits apply only at the specified ambient temperature.'))
    def test_short_repeated_header(self):
        self.assertEqual(structural_reason('Reactive Power Planning Guideline',True),'short_repeated_header')
    def test_contents(self):
        self.assertEqual(structural_reason('A .... 3\nB .... 4\nC .... 5'),'table_of_contents')
    def test_demotion_keeps_ids(self):
        rows=[dict(document_id='d',version='v',ordinal=i,fragment_id=str(i)) for i in range(2)]
        self.assertEqual(ranking([(0,1),(1,.5)],[],rows,['footer',None],body=True),[1,0])
        self.assertEqual(ranking([(0,1),(1,.5)],[],rows,['footer',None]),[0,1])

if __name__=='__main__':unittest.main()
