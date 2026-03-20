import unittest
import subprocess
from pathlib import Path

class TestLangSet(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.tool_bin = self.project_root / "bin" / "TOOL"
        if not self.tool_bin.exists():
            subprocess.run(["python3", "setup.py"], cwd=str(self.project_root))

    def run_tool(self, args):
        cmd = [str(self.tool_bin)] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_root))

    def get_current_lang(self):
        res = self.run_tool(["lang"])
        output = res.stdout.strip()
        if "(" in output and output.endswith(")"):
            return output.split("(")[-1][:-1]
        return None

    def test_06_lang_set(self):
        """(6) 测试设置语言偏好. """
        original = self.get_current_lang()
        
        # Set to zh
        res = self.run_tool(["lang", "set", "zh"])
        self.assertEqual(res.returncode, 0)
        self.assertEqual(self.get_current_lang(), "zh")
        
        # Set back to en
        res = self.run_tool(["lang", "set", "en"])
        self.assertEqual(res.returncode, 0)
        self.assertEqual(self.get_current_lang(), "en")
        
        # Restore original
        if original:
            self.run_tool(["lang", "set", original])

if __name__ == "__main__":
    unittest.main()

