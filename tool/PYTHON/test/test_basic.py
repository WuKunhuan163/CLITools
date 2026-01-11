import unittest
import sys
import subprocess
from pathlib import Path

class TestPython(unittest.TestCase):
    def test_version(self):
        """Check if python version is 3.10."""
        self.assertEqual(sys.version_info.major, 3)
        self.assertEqual(sys.version_info.minor, 10)

    def test_import_tk(self):
        """Check if tkinter is available."""
        try:
            import tkinter
            self.assertTrue(True)
        except ImportError:
            self.fail("tkinter not found")

if __name__ == '__main__':
    unittest.main()
