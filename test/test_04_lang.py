import unittest
import subprocess
import json
import os
from pathlib import Path

class LangTest(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.tool_bin = self.project_root / "bin" / "TOOL"
        # Ensure bin/TOOL exists
        if not self.tool_bin.exists():
            subprocess.run(["python3", "setup.py"], cwd=str(self.project_root))

    def run_tool(self, args):
        cmd = [str(self.tool_bin)] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_root))

    def get_current_lang(self):
        res = self.run_tool(["lang"])
        # Format: LocalizedName (code)
        output = res.stdout.strip()
        if "(" in output and output.endswith(")"):
            return output.split("(")[-1][:-1]
        return None

    def test_01_show_current(self):
        """Test showing current language."""
        res = self.run_tool(["lang"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("(", res.stdout)
        self.assertIn(")", res.stdout)

    def test_02_list_languages(self):
        """Test listing supported languages."""
        res = self.run_tool(["lang", "list"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("English", res.stdout)
        # Check for current language indicator '*'
        current = self.get_current_lang()
        if current:
            self.assertIn("*", res.stdout)

    def test_03_set_language(self):
        """Test setting language preference."""
        # Store original
        original = self.get_current_lang()
        
        # Set to zh
        res = self.run_tool(["lang", "set", "zh"])
        self.assertEqual(res.returncode, 0)
        self.assertEqual(self.get_current_lang(), "zh")
        
        # Set back or to en
        res = self.run_tool(["lang", "set", "en"])
        self.assertEqual(res.returncode, 0)
        self.assertEqual(self.get_current_lang(), "en")
        
        # Restore original
        if original:
            self.run_tool(["lang", "set", original])

    def test_04_audit_lang(self):
        """Test language auditing."""
        res = self.run_tool(["audit-lang", "zh"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("zh", res.stdout)

if __name__ == "__main__":
    unittest.main()

