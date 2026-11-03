import tempfile,unittest
from pathlib import Path
from evaluation.tantivy_supervision_v3 import derived_bytes
class ResourceRoots(unittest.TestCase):
 def test_extra_root_is_counted_without_nested_double_count(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);a=base/'a';b=base/'b';a.mkdir();b.mkdir();(a/'sub').mkdir();(a/'one').write_bytes(b'123');(a/'sub/two').write_bytes(b'1234');(b/'three').write_bytes(b'12345')
   self.assertEqual(derived_bytes({'data_root':str(a),'extra_data_roots':[str(a/'sub'),str(b)]}),12)
if __name__=='__main__':unittest.main()
