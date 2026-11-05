"""No native execution: fail-closed identity gates for the optional shim."""
import unittest
from unittest.mock import patch
from evaluation import tantivy_atomic_compat_v9 as compat


class AdmissionChecks(unittest.TestCase):
    def test_changed_original_binary_rejected_before_load(self):
        with patch.object(compat,'_library',None),patch.object(compat,'sha',return_value='different'),patch.object(compat.ctypes,'WinDLL',create=True) as loader:
            with self.assertRaisesRegex(RuntimeError,'Unverified Tantivy'):
                compat.install({},1,'stop')
            loader.assert_not_called()

    def test_changed_patch_binary_rejected_before_load(self):
        with patch.object(compat,'_library',None),patch.object(compat,'sha',side_effect=[compat.ORIGINAL_PYD,'different']),patch.object(compat.ctypes,'WinDLL',create=True) as loader:
            with self.assertRaisesRegex(RuntimeError,'DLL identity'):
                compat.install({'dll':'synthetic.dll','sha256':'expected'},1,'stop')
            loader.assert_not_called()

    def test_no_reinstall(self):
        with patch.object(compat,'_library',object()),patch.object(compat.ctypes,'WinDLL',create=True) as loader:
            with self.assertRaisesRegex(RuntimeError,'once'):
                compat.install({},1,'stop')
            loader.assert_not_called()

    def test_not_enabled_implicitly(self):
        with patch.object(compat,'_library',None):
            self.assertIsNone(compat.stats())


if __name__=='__main__':unittest.main()
