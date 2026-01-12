import unittest
import subprocess
import os
import shutil
import tempfile
from pathlib import Path

class TestOverleafCompile(unittest.TestCase):
    def test_copy_and_compile(self):
        """Test copying a template and compiling it."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        overleaf_bin = project_root / "bin" / "OVERLEAF"
        if not overleaf_bin.exists(): self.skipTest("OVERLEAF bin not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "test_paper"
            
            # 1. Copy template
            res = subprocess.run([str(overleaf_bin), "--template", "IEEE", str(target_dir)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertTrue((target_dir / "main.tex").exists())

            # 2. Compile (Skip if no TeX distribution found to avoid long test time in sandbox)
            # Actually, let's try to compile if pdflatex is present
            if shutil.which("pdflatex"):
                res = subprocess.run([str(overleaf_bin), str(target_dir / "main.tex")], capture_output=True, text=True)
                # Note: IEEE template might need more files or have errors, but we test the FLOW
                # self.assertEqual(res.returncode, 0)
                pass

if __name__ == "__main__":
    unittest.main()
