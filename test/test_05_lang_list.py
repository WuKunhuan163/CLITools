import unittest
import subprocess
from pathlib import Path

class TestLangList(unittest.TestCase):
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

    def test_05_lang_list(self):
        """(5) 测试列出支持的语言。"""
        res = self.run_tool(["lang", "list"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("English", res.stdout)
        current = self.get_current_lang()
        if current:
            self.assertIn("*", res.stdout)

if __name__ == "__main__":
    unittest.main()

