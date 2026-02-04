import unittest
import sys
import os
import io
from pathlib import Path
from contextlib import redirect_stderr

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tool.FITZ.logic.pdf.wrapper import FitzWrapper

class TestFitzSuppression(unittest.TestCase):
    def test_open_suppression(self):
        """Test that opening a 'problematic' PDF doesn't produce stderr output."""
        pdf_path = project_root / "tool" / "READ" / "logic" / "test" / "001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
        
        if not pdf_path.exists():
            self.skipTest(f"PDF not found at {pdf_path}")

        # Capture stderr
        f = io.StringIO()
        with redirect_stderr(f):
            doc = FitzWrapper.open(str(pdf_path))
            doc.close()
        
        output = f.getvalue()
        self.assertEqual(output, "", f"Stderr should be empty, but got: {output}")

if __name__ == "__main__":
    unittest.main()

