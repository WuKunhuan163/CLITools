import unittest
import subprocess
from pathlib import Path

class TestOverleafTemplates(unittest.TestCase):
    def test_list_templates(self):
        """Test listing available templates."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        overleaf_bin = project_root / "bin" / "OVERLEAF"
        if not overleaf_bin.exists(): self.skipTest("OVERLEAF bin not found")

        res = subprocess.run([str(overleaf_bin), "--list-templates"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("ACM", res.stdout)
        self.assertIn("IEEE", res.stdout)

if __name__ == "__main__":
    unittest.main()
